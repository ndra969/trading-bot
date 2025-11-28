"""
Test data generators.

Functions to generate realistic test data for OHLCV, ticks, etc.
"""

from datetime import datetime

import numpy as np


def generate_ohlcv_data(count: int = 100, start_price: float = 1.10000) -> np.ndarray:
    """
    Generate realistic OHLCV data for testing.

    Args:
        count: Number of bars to generate
        start_price: Starting price

    Returns:
        Numpy array with OHLCV data
    """
    data = []
    current_time = int(datetime.now().timestamp())
    current_price = start_price

    for i in range(count):
        # Generate OHLC with realistic movements
        open_price = current_price

        # Random volatility
        volatility = np.random.uniform(0.0001, 0.0010)
        high_price = open_price + np.random.uniform(0, volatility)
        low_price = open_price - np.random.uniform(0, volatility)

        # Close price within high/low range
        close_price = np.random.uniform(low_price, high_price)

        # Volume and spread
        tick_volume = np.random.randint(50, 500)
        spread = np.random.randint(1, 3)
        real_volume = tick_volume * 100

        # Create bar
        bar = (
            current_time - (count - i) * 3600,  # time (hourly bars)
            round(open_price, 5),  # open
            round(high_price, 5),  # high
            round(low_price, 5),  # low
            round(close_price, 5),  # close
            tick_volume,  # tick_volume
            spread,  # spread
            real_volume,  # real_volume
        )

        data.append(bar)
        current_price = close_price

    # Convert to structured array
    dtype = [
        ("time", "i8"),
        ("open", "f8"),
        ("high", "f8"),
        ("low", "f8"),
        ("close", "f8"),
        ("tick_volume", "i8"),
        ("spread", "i4"),
        ("real_volume", "i8"),
    ]

    return np.array(data, dtype=dtype)


def generate_tick_data(count: int = 100, start_price: float = 1.10000) -> np.ndarray:
    """
    Generate realistic tick data for testing.

    Args:
        count: Number of ticks to generate
        start_price: Starting price

    Returns:
        Numpy array with tick data
    """
    data = []
    current_time = int(datetime.now().timestamp())
    current_bid = start_price
    spread = 0.00010

    for i in range(count):
        # Small random movements
        bid_change = np.random.uniform(-0.00005, 0.00005)
        current_bid += bid_change
        current_ask = current_bid + spread

        # Create tick
        tick = (
            current_time - (count - i),  # time
            round(current_bid, 5),  # bid
            round(current_ask, 5),  # ask
            round((current_bid + current_ask) / 2, 5),  # last
            1,  # volume
            0,  # flags
        )

        data.append(tick)

    # Convert to structured array
    dtype = [
        ("time", "i8"),
        ("bid", "f8"),
        ("ask", "f8"),
        ("last", "f8"),
        ("volume", "i8"),
        ("flags", "i4"),
    ]

    return np.array(data, dtype=dtype)


def generate_symbol_info(symbol: str = "EURUSD") -> dict:
    """
    Generate symbol information for testing.

    Args:
        symbol: Symbol name

    Returns:
        Dictionary with symbol info
    """
    return {
        "name": symbol,
        "visible": True,
        "trade_mode": 4,
        "description": f"{symbol} Description",
        "digits": 5,
        "point": 0.00001,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "trade_contract_size": 100000.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "swap_long": -0.5,
        "swap_short": 0.3,
        "currency_base": symbol[:3],
        "currency_profit": symbol[3:] if len(symbol) > 3 else "USD",
        "currency_margin": symbol[:3],
        "bid": 1.10000,
        "ask": 1.10010,
        "spread": 1.0,
    }


def generate_position(
    ticket: int = 12345,
    symbol: str = "EURUSD",
    position_type: int = 0,
    volume: float = 0.01,
) -> dict:
    """
    Generate position data for testing.

    Args:
        ticket: Position ticket
        symbol: Symbol name
        position_type: 0=BUY, 1=SELL
        volume: Trade volume

    Returns:
        Dictionary with position data
    """
    return {
        "ticket": ticket,
        "symbol": symbol,
        "type": position_type,
        "volume": volume,
        "price_open": 1.10000,
        "price_current": 1.10050,
        "sl": 1.09500,
        "tp": 1.11000,
        "profit": 5.0,
        "swap": -0.5,
        "comment": "Test position",
        "time": int(datetime.now().timestamp()),
    }


def generate_account_info() -> dict:
    """
    Generate account information for testing.

    Returns:
        Dictionary with account info
    """
    return {
        "login": 12345,
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "margin_free": 10000.0,
        "margin_level": 0.0,
        "profit": 0.0,
        "leverage": 100,
        "currency": "USD",
        "server": "MockServer",
        "company": "MockBroker",
        "trade_allowed": True,
        "trade_mode": 0,  # DEMO
    }
