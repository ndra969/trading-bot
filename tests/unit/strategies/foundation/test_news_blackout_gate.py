"""Phase 3: FoundationEngine news-blackout gate.

Focuses on the gate methods directly (not the full signal pipeline). The key
guarantee is flag-off byte-for-byte behaviour: with no NewsService, or with the
gate disabled, `_passes_news_blackout` is an inert pass-through.
"""

from datetime import UTC, datetime

import pandas as pd
import pytest
from trading_core.enums.rejection_stage import RejectionStage
from trading_worker.news.models import NewsEvent, NewsImpact
from trading_worker.news.news_service import BlackoutStatus
from trading_worker.strategies.foundation.foundation_engine import FoundationEngine
from trading_worker.strategies.models import SignalDirection

pytestmark = pytest.mark.asyncio


class FakeNewsService:
    def __init__(self, *, blackout_enabled=True, status=None, raises=False):
        self.blackout_enabled = blackout_enabled
        self._status = status or BlackoutStatus(blocked=False)
        self._raises = raises
        self.calls = 0

    async def in_blackout(self, symbol, now):
        self.calls += 1
        if self._raises:
            raise RuntimeError("news layer boom")
        return self._status


class SpyRecorder:
    def __init__(self):
        self.records: list[dict] = []

    def record(self, **kwargs):
        self.records.append(kwargs)


def _engine(news_service=None, recorder=None) -> FoundationEngine:
    return FoundationEngine(
        config={}, use_database=False, news_service=news_service, rejection_recorder=recorder
    )


def _data(ts="2026-06-25 12:00:00") -> pd.DataFrame:
    idx = pd.DatetimeIndex([pd.Timestamp(ts)])
    return pd.DataFrame({"close": [1.0]}, index=idx)


def _blocked_status() -> BlackoutStatus:
    event = NewsEvent(
        event_time_utc=datetime(2026, 6, 25, 12, 15, tzinfo=UTC),
        currency="USD",
        impact=NewsImpact.HIGH,
        name="NFP",
        source_id="1",
    )
    return BlackoutStatus(blocked=True, event=event, minutes_to_event=15.0)


async def _gate(engine, data=None):
    return await engine._passes_news_blackout(
        "EURUSD", SignalDirection.BUY, "forex", 80.0, data or _data()
    )


class TestFlagOffIsInert:
    async def test_no_news_service_passes(self):
        assert await _gate(_engine(news_service=None)) is True

    async def test_no_service_reports_disabled(self):
        assert _engine(news_service=None)._news_blackout_enabled() is False

    async def test_service_present_but_gate_disabled_passes(self):
        svc = FakeNewsService(blackout_enabled=False, status=_blocked_status())
        engine = _engine(news_service=svc)
        assert await _gate(engine) is True
        assert svc.calls == 0  # short-circuits before querying


class TestGateEnabled:
    async def test_blocks_and_records_rejection(self):
        recorder = SpyRecorder()
        svc = FakeNewsService(blackout_enabled=True, status=_blocked_status())
        engine = _engine(news_service=svc, recorder=recorder)

        assert await _gate(engine) is False
        assert svc.calls == 1
        assert len(recorder.records) == 1
        rec = recorder.records[0]
        assert rec["stage"] is RejectionStage.NEWS_BLACKOUT
        assert rec["details"]["currency"] == "USD"
        assert rec["details"]["event"] == "NFP"

    async def test_not_in_window_passes(self):
        svc = FakeNewsService(blackout_enabled=True, status=BlackoutStatus(blocked=False))
        assert await _gate(_engine(news_service=svc)) is True

    async def test_news_error_degrades_to_allow(self):
        svc = FakeNewsService(blackout_enabled=True, raises=True)
        assert await _gate(_engine(news_service=svc)) is True  # never blocks on error


class TestEvaluationTime:
    async def test_naive_index_becomes_utc(self):
        dt = FoundationEngine._evaluation_time(_data("2026-06-25 12:00:00"))
        assert dt == datetime(2026, 6, 25, 12, 0, tzinfo=UTC)

    async def test_non_datetime_index_returns_none(self):
        df = pd.DataFrame({"close": [1.0]}, index=[0])
        assert FoundationEngine._evaluation_time(df) is None
