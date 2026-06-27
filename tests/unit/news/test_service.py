"""Unit tests for NewsFetchService (retry + alerting orchestration).

The repository is faked (no DB); the source and notifier are stubs. Backoff is
set to 0 so retries don't actually sleep.
"""

from datetime import UTC, datetime

import httpx
import pytest
from trading_worker.news.models import NewsEvent, NewsImpact
from trading_worker.news.service import NewsFetchService

pytestmark = pytest.mark.asyncio


def _event() -> NewsEvent:
    return NewsEvent(
        event_time_utc=datetime(2026, 6, 25, 12, 30, tzinfo=UTC),
        currency="USD",
        impact=NewsImpact.HIGH,
        name="NFP",
        source_id="1",
    )


class FakeRepo:
    def __init__(self):
        self.upserted: list[NewsEvent] = []

    async def upsert_events(self, events):
        self.upserted = events
        return len(events)


class FakeSource:
    """Source whose fetch() yields a scripted sequence of results/exceptions."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def parse(self, html):  # unused here
        return []

    async def fetch(self):
        self.calls += 1
        item = self._results.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class SpyNotifier:
    def __init__(self):
        self.messages: list[tuple[str, object]] = []

    async def send_message(self, message, level=None):
        self.messages.append((message, level))


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://x")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("err", request=request, response=response)


def _service(source, repo, notifier=None, **kw):
    kw.setdefault("backoff_min", [0])
    kw.setdefault("max_attempts", 3)
    return NewsFetchService(source, repo, notifier, **kw)


class TestSuccess:
    async def test_stores_events_and_is_quiet(self):
        repo = FakeRepo()
        notifier = SpyNotifier()
        svc = _service(FakeSource([[_event()]]), repo, notifier)

        result = await svc.fetch_and_store()

        assert result.success
        assert result.events_written == 1
        assert not result.is_stale
        assert len(repo.upserted) == 1
        assert notifier.messages == []  # success → no Telegram spam

    async def test_success_alert_when_opted_in(self):
        notifier = SpyNotifier()
        svc = _service(FakeSource([[_event()]]), FakeRepo(), notifier, notify_on_success=True)
        await svc.fetch_and_store()
        assert len(notifier.messages) == 1


class TestRetry:
    async def test_retries_transient_then_succeeds(self):
        repo = FakeRepo()
        source = FakeSource([_http_error(503), httpx.ConnectTimeout("slow"), [_event()]])
        svc = _service(source, repo)

        result = await svc.fetch_and_store()

        assert result.success
        assert source.calls == 3
        assert result.attempts == 3

    async def test_alerts_once_after_exhausting_retries(self):
        notifier = SpyNotifier()
        source = FakeSource([_http_error(503)] * 3)
        svc = _service(source, FakeRepo(), notifier)

        result = await svc.fetch_and_store()

        assert not result.success
        assert result.is_stale
        assert source.calls == 3  # max_attempts
        assert len(notifier.messages) == 1  # exactly one alert, not per-retry
        _, level = notifier.messages[0]
        assert getattr(level, "name", level) == "ERROR"

    async def test_does_not_retry_hard_4xx(self):
        source = FakeSource([_http_error(404), [_event()]])
        svc = _service(source, FakeRepo())

        result = await svc.fetch_and_store()

        assert not result.success
        assert source.calls == 1  # 404 is not transient → no retry

    async def test_failure_never_raises(self):
        source = FakeSource([ValueError("boom")])
        svc = _service(source, FakeRepo())
        result = await svc.fetch_and_store()
        assert not result.success
        assert "ValueError" in (result.error or "")


class TestFromConfig:
    async def test_reads_retry_and_notify(self):
        cfg = {
            "fetch": {"retry": {"max_attempts": 4, "backoff_min": [1, 2]}},
            "notify": {"on_fetch_failure": False, "on_fetch_success": True},
        }
        svc = NewsFetchService.from_config(cfg, FakeSource([]), FakeRepo())
        assert svc.max_attempts == 4
        assert svc.backoff_min == (1, 2)
        assert svc.notify_on_failure is False
        assert svc.notify_on_success is True

    async def test_defaults_when_keys_missing(self):
        svc = NewsFetchService.from_config({}, FakeSource([]), FakeRepo())
        assert svc.max_attempts == 5
        assert svc.notify_on_failure is True
        assert svc.notify_on_success is False


class TestAlertResilience:
    async def test_notifier_failure_does_not_break(self):
        class BrokenNotifier:
            async def send_message(self, *a, **k):
                raise RuntimeError("telegram down")

        source = FakeSource([_http_error(500)] * 3)
        svc = _service(source, FakeRepo(), BrokenNotifier())
        result = await svc.fetch_and_store()  # must not raise
        assert not result.success
