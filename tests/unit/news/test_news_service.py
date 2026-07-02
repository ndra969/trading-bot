"""Unit tests for NewsService (Phase 2): mapping + blackout + dampen."""

from datetime import UTC, datetime, timedelta

import pytest
from trading_worker.news.models import NewsEvent, NewsImpact
from trading_worker.news.news_service import NewsService
from trading_worker.news.repository import NewsRepository

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)


def _event(
    minutes_from_now: float,
    *,
    currency="USD",
    impact=NewsImpact.HIGH,
    actual=None,
    forecast=None,
    sid="1",
):
    return NewsEvent(
        event_time_utc=NOW + timedelta(minutes=minutes_from_now),
        currency=currency,
        impact=impact,
        name="Event",
        actual=actual,
        forecast=forecast,
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

    async def test_printed_without_forecast_is_neutral(self, db):
        # Actual printed but no forecast → surprise unparseable → neutral.
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


class TestSurpriseDirection:
    async def test_usd_positive_surprise_favours_eurusd_sell(self, db):
        # USD (quote of EURUSD) beats forecast → USD strong → EURUSD down.
        await NewsRepository().upsert_events(
            [_event(-5, currency="USD", actual="250K", forecast="180K")]
        )
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "SELL", NOW) == pytest.approx(1.15)
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == pytest.approx(0.80)

    async def test_usd_negative_surprise_favours_eurusd_buy(self, db):
        await NewsRepository().upsert_events(
            [_event(-5, currency="USD", actual="120K", forecast="180K")]
        )
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == pytest.approx(1.15)

    async def test_base_currency_surprise_flips_mapping(self, db):
        # EUR is the BASE of EURUSD → strong EUR favours BUY.
        await NewsRepository().upsert_events(
            [_event(-5, currency="EUR", actual="1.5%", forecast="1.0%")]
        )
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == pytest.approx(1.15)

    async def test_gold_usd_surprise(self, db):
        # XAUUSD → USD is the quote; strong USD favours SELL (gold down).
        await NewsRepository().upsert_events(
            [_event(-5, currency="USD", actual="250K", forecast="180K")]
        )
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("XAUUSD", "SELL", NOW) == pytest.approx(1.15)

    async def test_pending_takes_precedence_over_printed(self, db):
        # A closer pending event dampens even if a printed one is also in window.
        await NewsRepository().upsert_events(
            [
                _event(20, currency="USD", actual=None, sid="pending"),
                _event(-25, currency="USD", actual="250K", forecast="180K", sid="printed"),
            ]
        )
        svc = NewsService(NewsRepository())
        assert await svc.confidence_adjustment("EURUSD", "SELL", NOW) == pytest.approx(0.85)

    async def test_custom_boost_dampen_from_config(self, db):
        await NewsRepository().upsert_events(
            [_event(-5, currency="USD", actual="250K", forecast="180K")]
        )
        svc = NewsService(
            NewsRepository(),
            {"confidence": {"surprise_boost": 1.3, "surprise_dampen": 0.6}},
        )
        assert await svc.confidence_adjustment("EURUSD", "SELL", NOW) == pytest.approx(1.3)
        assert await svc.confidence_adjustment("EURUSD", "BUY", NOW) == pytest.approx(0.6)
