import pytest
from trading_worker.strategies.enhancement.breakout_analyzer import BreakoutAnalyzer


@pytest.fixture
def breakout_config():
    return {"breakout": {"volume_threshold": 1.5, "min_body_ratio": 0.6}}


@pytest.fixture
def analyzer(breakout_config):
    return BreakoutAnalyzer(breakout_config)


def create_breakout_data(last_candle, last_volume, length=25):
    """
    Generate dummy OHLCV data.
    last_candle: (open, high, low, close)
    """
    opens = [100.0] * length
    highs = [105.0] * length
    lows = [95.0] * length
    closes = [100.0] * length
    volumes = [1000.0] * length  # Avg volume = 1000

    # Set last candle
    opens[-1] = last_candle[0]
    highs[-1] = last_candle[1]
    lows[-1] = last_candle[2]
    closes[-1] = last_candle[3]
    volumes[-1] = last_volume

    # Set previous candle to be neutral/below breakout level for testing
    closes[-2] = 100.0

    return opens, highs, lows, closes, volumes


@pytest.mark.asyncio
async def test_valid_bullish_breakout(analyzer):
    """Test Valid Bullish Breakout (Strong Body, High Volume)."""
    # Level at 102.
    # Candle: Open 100, High 105, Low 99, Close 104. (Breaks 102)
    # Body: 4. Range: 6. Ratio: 0.66 (> 0.6)
    # Volume: 2000 (2x avg)

    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 105.0, 99.0, 104.0), 2000.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=102.0,
        expected_direction="BULLISH",
    )

    assert signal is not None
    assert signal.breakout_type == "BULLISH"
    assert signal.confidence >= 80  # 40 (Candle) + 40 (Volume)
    assert "High" in signal.details["volume"]


@pytest.mark.asyncio
async def test_valid_bearish_breakout(analyzer):
    """Test Valid Bearish Breakout."""
    # Level at 98.
    # Candle: Open 100, High 101, Low 95, Close 96. (Breaks 98)
    # Body: 4. Range: 6. Ratio: 0.66
    # Volume: 1800 (1.8x avg)

    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 101.0, 95.0, 96.0), 1800.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=98.0,
        expected_direction="BEARISH",
    )

    assert signal is not None
    assert signal.breakout_type == "BEARISH"
    assert signal.confidence >= 80


@pytest.mark.asyncio
async def test_weak_body_breakout(analyzer):
    """Test Breakout with Weak Candle Body (Fakeout)."""
    # Level 102.
    # Candle: Open 100, High 105, Low 99, Close 102.5. (Breaks 102)
    # Body: 2.5. Range: 6. Ratio: 0.41 (< 0.6)

    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 105.0, 99.0, 102.5), 2000.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=102.0,
        expected_direction="BULLISH",
    )

    # Should return None because body is too weak (min_body_ratio check)
    assert signal is None


@pytest.mark.asyncio
async def test_low_volume_breakout(analyzer):
    """Test Breakout with Low Volume."""
    # Level 102.
    # Candle: Strong Body.
    # Volume: 1000 (1x avg, < 1.5 threshold)

    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 105.0, 99.0, 104.0), 1000.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=102.0,
        expected_direction="BULLISH",
    )

    assert signal is not None
    # Confidence should be lower (10 instead of 40 for volume)
    # Base 40 (Candle) + 10 (Vol) + 20 (Momentum) = ~70
    assert signal.confidence < 80
    assert "Low" in signal.details["volume"]


@pytest.mark.asyncio
async def test_no_breakout(analyzer):
    """Test when price doesn't break level."""
    # Level 105. Close 104.

    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 105.0, 99.0, 104.0), 2000.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=105.0,
        expected_direction="BULLISH",
    )

    assert signal is None


@pytest.mark.asyncio
async def test_insufficient_data(analyzer):
    """Test breakout analysis with insufficient data (line 61)."""
    # Less than 20 candles
    opens = [100.0] * 15
    highs = [105.0] * 15
    lows = [95.0] * 15
    closes = [100.0] * 15
    volumes = [1000.0] * 15

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=102.0,
        expected_direction="BULLISH",
    )

    assert signal is None


@pytest.mark.asyncio
async def test_zero_candle_range(analyzer):
    """Test breakout analysis with zero candle range (line 98)."""
    # Candle with zero range (high == low)
    opens, highs, lows, closes, volumes = create_breakout_data((100.0, 100.0, 100.0, 100.0), 2000.0)

    signal = await analyzer.analyze_breakout(
        "EURUSD",
        opens,
        highs,
        lows,
        closes,
        volumes,
        level_price=99.0,
        expected_direction="BULLISH",
    )

    assert signal is None
