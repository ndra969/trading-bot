"""Tests for market session bucketing."""

from datetime import datetime

import pytest
from trading_core.utils.market_session import derive_market_session


@pytest.mark.parametrize(
    "hour,expected",
    [
        (0, "tokyo"),
        (5, "tokyo"),
        (7, "tokyo"),
        (8, "london"),
        (12, "london"),
        (13, "london_ny_overlap"),
        (16, "london_ny_overlap"),
        (17, "new_york"),
        (21, "new_york"),
        (22, "off_hours"),
        (23, "off_hours"),
    ],
)
def test_session_bucketing_by_hour(hour, expected):
    """Each hour should map to the documented bucket."""
    ts = datetime(2026, 5, 26, hour, 30, 0)
    assert derive_market_session(ts) == expected


def test_boundary_hour_8_is_london_not_tokyo():
    """Boundary at 08:00 belongs to london (inclusive)."""
    assert derive_market_session(datetime(2026, 5, 26, 8, 0, 0)) == "london"


def test_boundary_hour_13_is_overlap():
    """Boundary at 13:00 belongs to london_ny_overlap."""
    assert derive_market_session(datetime(2026, 5, 26, 13, 0, 0)) == "london_ny_overlap"


def test_boundary_hour_17_is_new_york():
    """Boundary at 17:00 belongs to new_york."""
    assert derive_market_session(datetime(2026, 5, 26, 17, 0, 0)) == "new_york"
