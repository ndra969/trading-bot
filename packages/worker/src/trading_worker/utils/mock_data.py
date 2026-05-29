"""Mock OHLCV data generator for dry-run testing without MT5 connection.

Generates realistic-looking price data with a consolidation phase at the end
to ensure zone-based strategies have testable data.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


_BASE_PRICES: dict[str, float] = {
    "JPY": 145.00,
    "XAU": 2000.00,
    "BTC": 90000.00,
    "ETH": 3000.00,
    "GBP": 1.2500,
}


def _resolve_base_price(symbol: str) -> float:
    """Get a reasonable base price for the symbol (rough approximation)."""
    for keyword, price in _BASE_PRICES.items():
        if keyword in symbol:
            return price
    return 1.1000  # Default for most forex majors


def generate_mock_ohlcv(symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame | None:
    """Generate mock OHLCV DataFrame for dry-run testing.

    Creates a random-walk price series with the last ~20 candles forced into
    a tight consolidation so zone detection has something to work with.

    Args:
        symbol: Trading symbol (e.g., "EURUSD", "XAUUSD")
        timeframe: Timeframe label (currently unused, kept for API compatibility)
        count: Number of candles to generate (default 100)

    Returns:
        DataFrame with columns: open, high, low, close, tick_volume, spread,
        real_volume, volume. Index is "time" (datetime). None on error.
    """
    try:
        base_price = _resolve_base_price(symbol)

        # Generate random walk + consolidation at the end
        prices = [base_price]
        for i in range(count - 1):
            # Last ~25 candles: tight consolidation (creates testable zones)
            # Earlier candles: normal trending movement
            if i > count - 25:
                change = np.random.normal(0, 0.0001) * prices[-1]
            else:
                change = prices[-1] * np.random.normal(0, 0.0005)
            prices.append(prices[-1] + change)

        # 1 hour per candle (approximation, regardless of timeframe param)
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(count)]
        timestamps.reverse()

        df = pd.DataFrame(
            {
                "time": timestamps,
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.001))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.001))) for p in prices],
                "close": [p * (1 + np.random.normal(0, 0.0005)) for p in prices],
                "tick_volume": np.random.randint(100, 500, count),
                "spread": np.random.randint(0, 10, count),
                "real_volume": np.random.randint(100, 500, count),
            }
        )

        # Strategy expects "volume" column (alias for tick_volume)
        df["volume"] = df["tick_volume"]

        df.set_index("time", inplace=True)

        # Ensure high/low consistency (high >= open/close, low <= open/close)
        df["high"] = df[["open", "close", "high"]].max(axis=1)
        df["low"] = df[["open", "close", "low"]].min(axis=1)

        return df

    except ImportError:
        logger.error("Pandas/Numpy not available for mock data generation")
        return None
    except Exception as e:
        logger.error(f"Error generating mock data: {e}")
        return None
