"""Unit tests for shared API dependencies (trading_api.deps)."""

from datetime import datetime, timedelta, timezone

from trading_api.deps import TimeRange, _to_naive_utc


def test_to_naive_utc_strips_tz_and_converts_to_utc():
    # 2026-05-14 04:31 +02:00 == 02:31 UTC, returned naive.
    aware = datetime(2026, 5, 14, 4, 31, tzinfo=timezone(timedelta(hours=2)))
    result = _to_naive_utc(aware)
    assert result == datetime(2026, 5, 14, 2, 31)
    assert result.tzinfo is None


def test_to_naive_utc_passes_through_naive_and_none():
    naive = datetime(2026, 5, 14, 2, 31)
    assert _to_naive_utc(naive) is naive
    assert _to_naive_utc(None) is None


def test_timerange_normalizes_aware_bounds_to_naive_utc():
    # Regression: tz-aware bounds (ISO strings ending in 'Z') must be stored as
    # naive UTC so they compare against TIMESTAMP WITHOUT TIME ZONE columns on
    # Postgres (asyncpg raises otherwise).
    since = datetime(2026, 5, 14, 2, 31, tzinfo=timezone.utc)
    until = datetime(2026, 6, 14, 2, 31, tzinfo=timezone.utc)
    window = TimeRange(since=since, until=until)
    assert window.since == datetime(2026, 5, 14, 2, 31)
    assert window.until == datetime(2026, 6, 14, 2, 31)
    assert window.since.tzinfo is None
    assert window.until.tzinfo is None
