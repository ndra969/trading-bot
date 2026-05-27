"""Tests for market_hours.is_market_open — weekend + session filtering."""

from datetime import UTC, datetime

import pytest

from trading_bot.utils.market_hours import is_market_open


# ─────────────────────────────────────────────────────────────────
# Weekend filter
# ─────────────────────────────────────────────────────────────────


class TestWeekendFilter:
    """Crypto stays open all weekend; forex/commodities follow standard hours."""

    def test_crypto_open_on_saturday(self):
        sat = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)  # Saturday
        assert is_market_open("crypto", now=sat) is True

    def test_forex_closed_on_saturday(self):
        sat = datetime(2026, 5, 30, 12, 0, tzinfo=UTC)
        assert is_market_open("forex_major", now=sat) is False

    def test_forex_closed_sunday_before_21utc(self):
        sun = datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
        assert is_market_open("forex_major", now=sun) is False

    def test_forex_open_sunday_after_21utc(self):
        sun = datetime(2026, 5, 31, 22, 0, tzinfo=UTC)
        # No session filter → only weekend rule applies, Sunday 22:00 UTC is open
        assert is_market_open("forex_major", now=sun) is True

    def test_forex_closed_friday_after_22utc(self):
        fri = datetime(2026, 5, 29, 23, 0, tzinfo=UTC)
        assert is_market_open("forex_major", now=fri) is False

    def test_weekday_open(self):
        wed = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
        assert is_market_open("forex_major", now=wed) is True


# ─────────────────────────────────────────────────────────────────
# Session filter
# ─────────────────────────────────────────────────────────────────


class TestSessionFilter:
    """Per-symbol allowed_sessions gate trading inside weekday hours."""

    # Wed 2026-05-27 — picked because it's a normal weekday in all the tests below.

    def test_no_session_filter_passes(self):
        wed_3utc = datetime(2026, 5, 27, 3, 0, tzinfo=UTC)
        # No allowed_sessions → only weekend rule, Wed 3 UTC is open
        assert is_market_open("forex_major", allowed_sessions=None, now=wed_3utc) is True

    def test_24_7_overrides_any_hour(self):
        wed_3utc = datetime(2026, 5, 27, 3, 0, tzinfo=UTC)
        assert is_market_open("crypto", allowed_sessions=["24/7"], now=wed_3utc) is True

    def test_london_only_skips_asian_hours(self):
        wed_3utc = datetime(2026, 5, 27, 3, 0, tzinfo=UTC)
        # 3 UTC is in tokyo bucket — london-only symbol skips
        assert (
            is_market_open("forex_major", allowed_sessions=["london"], now=wed_3utc)
            is False
        )

    def test_london_session_matches_london_bucket(self):
        wed_10utc = datetime(2026, 5, 27, 10, 0, tzinfo=UTC)
        assert (
            is_market_open("forex_major", allowed_sessions=["london"], now=wed_10utc)
            is True
        )

    def test_overlap_matches_london_only_symbol(self):
        wed_15utc = datetime(2026, 5, 27, 15, 0, tzinfo=UTC)
        # london_ny_overlap bucket — admits london-only too
        assert (
            is_market_open("forex_major", allowed_sessions=["london"], now=wed_15utc)
            is True
        )

    def test_overlap_matches_ny_only_symbol(self):
        wed_15utc = datetime(2026, 5, 27, 15, 0, tzinfo=UTC)
        assert (
            is_market_open(
                "forex_major", allowed_sessions=["new_york"], now=wed_15utc
            )
            is True
        )

    def test_new_york_session_matches_ny_bucket(self):
        wed_19utc = datetime(2026, 5, 27, 19, 0, tzinfo=UTC)
        assert (
            is_market_open(
                "forex_major", allowed_sessions=["new_york"], now=wed_19utc
            )
            is True
        )

    def test_off_hours_blocks_all_session_symbols(self):
        wed_2230utc = datetime(2026, 5, 27, 22, 30, tzinfo=UTC)
        assert (
            is_market_open(
                "forex_major",
                allowed_sessions=["tokyo", "london", "new_york"],
                now=wed_2230utc,
            )
            is False
        )

    def test_tokyo_matches_tokyo_bucket(self):
        wed_5utc = datetime(2026, 5, 27, 5, 0, tzinfo=UTC)
        assert (
            is_market_open("forex_jpy", allowed_sessions=["tokyo"], now=wed_5utc)
            is True
        )

    def test_sydney_accepted_in_tokyo_bucket(self):
        """Sydney session shares the 00-08 UTC slot with Tokyo in our buckets."""
        wed_5utc = datetime(2026, 5, 27, 5, 0, tzinfo=UTC)
        assert (
            is_market_open("forex_major", allowed_sessions=["sydney"], now=wed_5utc)
            is True
        )


class TestCombinedFilters:
    """Weekend rule wins over session match."""

    def test_session_match_on_saturday_still_closed(self):
        sat_10utc = datetime(2026, 5, 30, 10, 0, tzinfo=UTC)
        assert (
            is_market_open(
                "forex_major", allowed_sessions=["london"], now=sat_10utc
            )
            is False
        )
