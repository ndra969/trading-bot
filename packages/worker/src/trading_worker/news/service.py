"""News fetch orchestration: fetch (bounded retry) → persist → alert on failure.

This is the operability layer the spec calls for. The feature is silent by
design (a missing calendar = no blackout), so the operator must be told when a
fetch ultimately fails — otherwise the bot trades through news unprotected for
days unnoticed.

Policy (all config-driven):
* Retry transient fetch failures (network / 5xx / 429) with bounded backoff via
  tenacity — NOT hard 4xx / ToS blocks, and NOT forever.
* After all retries are exhausted: one ERROR Telegram alert ("protection OFF"),
  never one-per-retry. Success is quiet (log only / daily-report line).
* Never raise into the trading loop: a failed fetch leaves the last-known
  calendar in place and is surfaced via ``last_result`` / ``is_stale``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt
from trading_core.utils.logger import get_logger

from .repository import NewsRepository
from .source import NewsSource

logger = get_logger(__name__)

# Default bounded-retry policy (overridable from config). Minutes between tries.
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_BACKOFF_MIN: tuple[int, ...] = (5, 15, 30, 60)
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _is_transient(exc: BaseException) -> bool:
    """Retry network blips and server-side/rate-limit errors, not hard 4xx."""
    if isinstance(exc, httpx.TransportError):  # connect/read/timeout
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    return False


@dataclass(frozen=True)
class NewsFetchResult:
    """Outcome of one fetch-and-store cycle."""

    success: bool
    events_written: int = 0
    attempts: int = 0
    error: str | None = None

    @property
    def is_stale(self) -> bool:
        """True when this cycle failed — blackout protection is running blind."""
        return not self.success


class NewsFetchService:
    """Fetch the calendar with bounded retry, persist it, alert on failure."""

    def __init__(
        self,
        source: NewsSource,
        repository: NewsRepository,
        notifier: object | None = None,
        *,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        backoff_min: tuple[int, ...] | list[int] = _DEFAULT_BACKOFF_MIN,
        notify_on_failure: bool = True,
        notify_on_success: bool = False,
    ):
        self.source = source
        self.repository = repository
        # Duck-typed NotificationManager (has async send_message); optional so
        # the service is usable headless / in tests.
        self.notifier = notifier
        self.max_attempts = max(1, max_attempts)
        self.backoff_min = tuple(backoff_min) or _DEFAULT_BACKOFF_MIN
        self.notify_on_failure = notify_on_failure
        self.notify_on_success = notify_on_success
        self.last_result: NewsFetchResult | None = None

    @classmethod
    def from_config(
        cls,
        news_config: dict[str, Any],
        source: NewsSource,
        repository: NewsRepository,
        notifier: object | None = None,
    ) -> NewsFetchService:
        """Build from the ``news`` config block (single wiring entry point).

        Reads ``fetch.retry.{max_attempts,backoff_min}`` and
        ``notify.{on_fetch_failure,on_fetch_success}``; missing keys fall back to
        the bounded defaults. Does not look at ``news.enabled`` — the caller
        decides whether to schedule this at all.
        """
        retry = (news_config.get("fetch") or {}).get("retry") or {}
        notify = news_config.get("notify") or {}
        return cls(
            source,
            repository,
            notifier,
            max_attempts=int(retry.get("max_attempts", _DEFAULT_MAX_ATTEMPTS)),
            backoff_min=tuple(retry.get("backoff_min", _DEFAULT_BACKOFF_MIN)),
            notify_on_failure=bool(notify.get("on_fetch_failure", True)),
            notify_on_success=bool(notify.get("on_fetch_success", False)),
        )

    def _wait_seconds(self, attempt_number: int) -> float:
        """Backoff for the Nth retry (1-based), clamped to the configured list."""
        idx = min(attempt_number - 1, len(self.backoff_min) - 1)
        return self.backoff_min[max(0, idx)] * 60.0

    async def fetch_and_store(self) -> NewsFetchResult:
        """Run one fetch→persist cycle. Never raises; returns the outcome."""
        attempts = 0
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.max_attempts),
                wait=self._tenacity_wait(),
                retry=retry_if_exception(_is_transient),
                reraise=True,
            ):
                with attempt:
                    attempts = attempt.retry_state.attempt_number
                    events = await self.source.fetch()
        except Exception as e:  # transient-exhausted or a non-retryable error
            result = NewsFetchResult(
                success=False, attempts=attempts, error=f"{type(e).__name__}: {e}"
            )
            self.last_result = result
            logger.error(
                f"News fetch failed after {attempts} attempt(s) — blackout "
                f"protection OFF: {result.error}"
            )
            await self._alert_failure(result)
            return result

        written = await self.repository.upsert_events(events)
        result = NewsFetchResult(success=True, events_written=written, attempts=attempts)
        self.last_result = result
        logger.info(f"News fetch ok: {written} events stored ({attempts} attempt(s))")
        await self._alert_success(result)
        return result

    def _tenacity_wait(self) -> Callable[[Any], float]:
        # tenacity wait callable: map attempt number → seconds via our list.
        def _wait(retry_state: Any) -> float:
            return self._wait_seconds(retry_state.attempt_number)

        return _wait

    async def _alert_failure(self, result: NewsFetchResult) -> None:
        if not (self.notify_on_failure and self.notifier):
            return
        await self._notify(
            "📰 **News fetch failed** — blackout protection is OFF.\n"
            f"Attempts: `{result.attempts}` · Error: `{result.error}`",
            level="ERROR",
        )

    async def _alert_success(self, result: NewsFetchResult) -> None:
        if not (self.notify_on_success and self.notifier):
            return
        await self._notify(
            f"📰 News calendar refreshed: `{result.events_written}` events.",
            level="INFO",
        )

    async def _notify(self, message: str, level: str) -> None:
        """Best-effort Telegram send; a notifier failure must not break fetch."""
        try:
            send = getattr(self.notifier, "send_message", None)
            if send is None:
                return
            # NotificationManager.send_message(message, level=NotificationLevel).
            from trading_worker.utils.notification_manager import NotificationLevel

            await send(message, level=NotificationLevel[level])
        except Exception as e:  # noqa: BLE001 - alerting must never raise
            logger.warning(f"News alert delivery failed: {e}")
