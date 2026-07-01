"""Unit tests for NewsService (Phase 2): mapping + blackout + dampen."""

from datetime import UTC, datetime, timedelta

import pytest
from trading_worker.news.models import NewsEvent, NewsImpact
from trading_worker.news.news_service import NewsService
from trading_worker.news.repository import NewsRepository

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


def _event(
    minutes_from_now: float, *, currency="USD", impact=NewsImpact.HIGH, actual=None, sid="1"
):
    return NewsEvent(
        event_time_utc=NOW + timedelta(minutes=minutes_from_now),
        currency=currency,
        impact=impact,
        name="Event",
        actual=actual,
        source_id=sid,
    )


class TestNearestEvent:
    async def test_returns_closest_high_impact(self, db):
        # Distances from now: a=90, b=20, c=15 → c (already released 15m ago).
        await NewsRepository().upsert_events(
            [_event(90, sid="a"), _event(20, sid="b"), _event(-15, sid="c")]
        )
        svc = NewsService(NewsRepository())
        nearest = await svc.nearest_event("EURUSD", NOW)
        assert nearest is not None
        assert nearest.source_id == "c"

    async def test_none_when_outside_lookahead(self, db):
        await NewsRepository().upsert_events([_event(600, sid="far")])  # 10h ahead
        svc = NewsService(NewsRepository())  # default lookahead 240 min
        assert await svc.nearest_event("EURUSD", NOW) is None

    async def test_none_for_non_calendar_symbol(self, db):
        svc = NewsService(NewsRepository())
        assert await svc.nearest_event("BTCETH", NOW) is None


class TestInBlackout:
    async def test_high_impact_within_window_blocks(self, db):
        await NewsRepository().upsert_events([_event(25)])  # HIGH, +25 min (< 30)
        svc = NewsService(NewsRepository())
        status = await svc.in_blackout("EURUSD", NOW)
        assert status.blocked
        assert status.minutes_to_event == pytest.approx(25.0)

    async def test_high_impact_outside_window_clears(self, db):
        await NewsRepository().upsert_events([_event(45)])  # HIGH, +45 min (> 30)
        svc = NewsService(NewsRepository())
        assert not (await svc.in_blackout("EURUSD", NOW)).blocked

    async def test_medium_uses_narrower_window(self, db):
        # MEDIUM at +20 min: inside the 30-min high window but OUTSIDE the
        # 10-min medium window → must NOT block.
        await NewsRepository().upsert_events([_event(20, impact=NewsImpact.MEDIUM)])
        svc = NewsService(NewsRepository())
        assert not (await svc.in_blackout("EURUSD", NOW)).blocked

    async def test_medium_within_its_window_blocks(self, db):
        await NewsRepository().upsert_events([_event(8, impact=NewsImpact.MEDIUM)])
        svc = NewsService(NewsRepository())
        assert (await svc.in_blackout("EURUSD", NOW)).blocked

    async def test_currency_must_match_symbol(self, db):
        await NewsRepository().upsert_events([_event(5, currency="JPY")])
        svc = NewsService(NewsRepository())
        assert not (await svc.in_blackout("EURUSD", NOW)).blocked  # no JPY leg
        assert (await svc.in_blackout("USDJPY", NOW)).blocked  # has JPY leg

    async def test_custom_windows_from_config(self, db):
        await NewsRepository().upsert_events([_event(45)])
        svc = NewsService(NewsRepository(), {"blackout": {"high": {"window_min": 60}}})
        assert (await svc.in_blackout("EURUSD", NOW)).blocked  # 45 < 60


class TestConfidenceAdjustment:
    async def test_pending_high_impact_dampens(self, db):
        await NewsRepository().upsert_events([_event(15, actual=None)])
        svc = NewsService(NewsRepository())
        adj = await svc.confidence_adjustment("EURUSD", "BUY", NOW)
        assert adj == pytest.approx(0.85)

    async def test_already_printed_is_neutral(self, db):
        # Event within window but actual has printed → Phase 2 stays neutral.
        await NewsRepository().upsert_events([_event(-5, actual="200K")])
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == 1.0

    async def test_no_event_is_neutral(self, db):
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == 1.0

    async def test_custom_dampen_from_config(self, db):
        await NewsRepository().upsert_events([_event(15)])
        svc = NewsService(NewsRepository(), {"confidence": {"pre_event_dampen": 0.5}})
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == pytest.approx(0.5)
