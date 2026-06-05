"""Signal rejection telemetry recorder (ui-dashboard Goal 9).

Buffers rejected setups in memory and flushes them to the
``signal_rejections`` table in batches, then prunes old rows. Strictly
fire-and-forget: a telemetry failure is logged and swallowed so it can
never raise into — or slow — the trading loop.

`record()` is a no-op when disabled, so the signal path can call it
unconditionally (and tests/backtests that never wire a DB stay clean).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from trading_core.data.models import SignalRejection
from trading_core.enums.rejection_stage import RejectionStage
from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class RejectionRecorder:
    """In-memory buffer + batched DB writer for signal rejections."""

    def __init__(
        self,
        enabled: bool = True,
        retention_days: int = 30,
        max_buffer: int = 5000,
    ) -> None:
        self.enabled = enabled
        self.retention_days = retention_days
        self.max_buffer = max_buffer
        self._buffer: list[dict] = []
        self._last_prune: datetime | None = None

    def record(
        self,
        *,
        stage: RejectionStage | str,
        symbol: str,
        asset_class: str | None = None,
        direction: str | None = None,
        confluence_score: float | None = None,
        details: dict | None = None,
    ) -> None:
        """Buffer one rejection. Never raises."""
        if not self.enabled:
            return
        try:
            self._buffer.append(
                {
                    "created_at": datetime.now(UTC).replace(tzinfo=None),
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "direction": direction,
                    "stage": stage.value if isinstance(stage, RejectionStage) else str(stage),
                    "confluence_score": (
                        float(confluence_score) if confluence_score is not None else None
                    ),
                    "details": details or {},
                }
            )
            # Hard cap so a DB outage can't grow the buffer unbounded.
            if len(self._buffer) > self.max_buffer:
                self._buffer = self._buffer[-self.max_buffer :]
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"RejectionRecorder.record swallowed error: {e}")

    async def flush(self) -> int:
        """Write buffered rejections, then prune (hourly). Never raises.

        Returns number of rows written (0 on disabled/empty/error).
        """
        if not self.enabled or not self._buffer:
            return 0
        batch, self._buffer = self._buffer, []
        try:
            from trading_core.data.database import get_session

            async with get_session() as session:
                session.add_all([SignalRejection(**row) for row in batch])
                await session.commit()
            written = len(batch)
            logger.debug(f"RejectionRecorder flushed {written} rejections")
            await self._maybe_prune()
            return written
        except Exception as e:
            # Re-buffer the batch (capped) so a transient DB blip doesn't lose data.
            self._buffer = (batch + self._buffer)[-self.max_buffer :]
            logger.warning(f"RejectionRecorder flush failed (will retry): {e}")
            return 0

    async def _maybe_prune(self) -> None:
        """Delete rows older than retention_days, at most once per hour."""
        now = datetime.now(UTC).replace(tzinfo=None)
        if self._last_prune and (now - self._last_prune) < timedelta(hours=1):
            return
        cutoff = now - timedelta(days=self.retention_days)
        try:
            from trading_core.data.database import get_session

            async with get_session() as session:
                await session.execute(
                    delete(SignalRejection).where(SignalRejection.created_at < cutoff)
                )
                await session.commit()
            self._last_prune = now
        except Exception as e:  # pragma: no cover - defensive
            logger.debug(f"RejectionRecorder prune swallowed error: {e}")
