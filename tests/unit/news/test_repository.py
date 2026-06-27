"""Unit tests for NewsRepository (DB-backed, opt-in `db` fixture)."""

from datetime import UTC, datetime

import pytest
from trading_worker.news.models import NewsEvent, NewsImpact
from trading_worker.news.repository import NewsRepository

pytestmark = pytest.mark.asyncio


def _event(**overrides) -> NewsEvent:
    base = {
        "event_time_utc": datetime(2026, 6, 25, 12, 30, tzinfo=UTC),
        "currency": "USD",
        "impact": NewsImpact.HIGH,
        "name": "Nonfarm Payrolls",
        "source_id": "551001",
    }
    base.update(overrides)
    return NewsEvent(**base)


class TestUpsert:
    async def test_insert_new_events(self, db):
        repo = NewsRepository()
        written = await repo.upsert_events([_event(), _event(source_id="551002", currency="EUR")])
        assert written == 2

        got = await repo.get_between(
            datetime(2026, 6, 25, tzinfo=UTC), datetime(2026, 6, 26, tzinfo=UTC)
        )
        assert len(got) == 2

    async def test_upsert_is_idempotent_and_fills_actual(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event(actual=None)])
        # Re-fetch the same release, now with the printed actual.
        await repo.upsert_events([_event(actual="200K")])

        got = await repo.get_between(
            datetime(2026, 6, 25, tzinfo=UTC), datetime(2026, 6, 26, tzinfo=UTC)
        )
        assert len(got) == 1  # updated in place, not duplicated
        assert got[0].actual == "200K"

    async def test_empty_list_is_noop(self, db):
        assert await NewsRepository().upsert_events([]) == 0

    async def test_events_without_source_id_always_insert(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event(source_id=None)])
        await repo.upsert_events([_event(source_id=None)])
        got = await repo.get_between(
            datetime(2026, 6, 25, tzinfo=UTC), datetime(2026, 6, 26, tzinfo=UTC)
        )
        assert len(got) == 2  # no key to dedup on


class TestGetInWindow:
    async def test_high_impact_within_window(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event()])  # 12:30 USD HIGH

        at = datetime(2026, 6, 25, 12, 45, tzinfo=UTC)  # 15 min after
        assert len(await repo.get_in_window(["USD"], at, window_min=30)) == 1
        assert len(await repo.get_in_window(["USD"], at, window_min=10)) == 0  # outside

    async def test_currency_filter(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event()])
        at = datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
        assert await repo.get_in_window(["EUR"], at, window_min=30) == []

    async def test_min_impact_tier(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event(source_id="m1", impact=NewsImpact.MEDIUM)])
        at = datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
        # Default HIGH-only excludes the medium event...
        assert await repo.get_in_window(["USD"], at, window_min=30) == []
        # ...but MEDIUM threshold includes it.
        got = await repo.get_in_window(["USD"], at, window_min=30, min_impact=NewsImpact.MEDIUM)
        assert len(got) == 1

    async def test_returned_times_are_utc_aware(self, db):
        repo = NewsRepository()
        await repo.upsert_events([_event()])
        at = datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
        got = await repo.get_in_window(["USD"], at, window_min=30)
        assert got[0].event_time_utc.tzinfo == UTC

    async def test_empty_currencies_returns_empty(self, db):
        at = datetime(2026, 6, 25, 12, 30, tzinfo=UTC)
        assert await NewsRepository().get_in_window([], at, window_min=30) == []


class TestGetBetween:
    async def test_range_and_currency_filter(self, db):
        repo = NewsRepository()
        await repo.upsert_events(
            [
                _event(source_id="a", event_time_utc=datetime(2026, 6, 25, 8, tzinfo=UTC)),
                _event(
                    source_id="b",
                    currency="EUR",
                    event_time_utc=datetime(2026, 6, 26, 8, tzinfo=UTC),
                ),
                _event(source_id="c", event_time_utc=datetime(2026, 6, 28, 8, tzinfo=UTC)),
            ]
        )
        got = await repo.get_between(
            datetime(2026, 6, 25, tzinfo=UTC), datetime(2026, 6, 27, tzinfo=UTC)
        )
        assert len(got) == 2  # the 28th is out of range
        # sorted ascending by time
        assert got[0].event_time_utc < got[1].event_time_utc

        usd_only = await repo.get_between(
            datetime(2026, 6, 25, tzinfo=UTC), datetime(2026, 6, 30, tzinfo=UTC), currencies=["USD"]
        )
        assert {e.currency for e in usd_only} == {"USD"}
