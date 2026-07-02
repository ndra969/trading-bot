"""Pure unit tests for the calendar numeric parser (no DB)."""

import pytest
from trading_worker.news.news_service import _parse_numeric


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("200K", 200_000.0),
        ("3.2%", 3.2),
        ("-2.5M", -2_500_000.0),
        ("1.5B", 1.5e9),
        ("1,234", 1234.0),
        ("$50", 50.0),
        ("0", 0.0),
        ("", None),
        (None, None),
        ("—", None),
        ("n/a", None),
    ],
)
def test_parse_numeric(raw, expected):
    assert _parse_numeric(raw) == expected
