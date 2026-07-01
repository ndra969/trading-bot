"""Pure unit tests for symbol → calendar-currency mapping (no DB)."""

import pytest
from trading_worker.news.news_service import symbol_currencies


@pytest.mark.parametrize(
    "symbol,expected",
    [
        ("EURUSD", ["EUR", "USD"]),
        ("USDJPY", ["USD", "JPY"]),
        ("GBPJPY", ["GBP", "JPY"]),
        ("XAUUSD", ["USD"]),  # gold → USD only
        ("XAGUSD", ["USD"]),
        ("BTCUSD", ["USD"]),  # crypto → USD only
        ("EURUSDc", ["EUR", "USD"]),  # broker suffix tolerated
        ("eur/usd", ["EUR", "USD"]),
        ("BTCETH", []),  # no calendar currency
    ],
)
def test_symbol_currencies(symbol, expected):
    assert symbol_currencies(symbol) == expected
