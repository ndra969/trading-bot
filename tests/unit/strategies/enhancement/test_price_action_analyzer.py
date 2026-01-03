import pytest

from src.trading_bot.strategies.enhancement.price_action_analyzer import PriceActionAnalyzer


@pytest.fixture
def pa_config():
    return {}


@pytest.fixture
def analyzer(pa_config):
    return PriceActionAnalyzer(pa_config)


def create_ohlc(o, h, low, c):
    """Helper to create OHLC lists with dummy history."""
    # Add dummy history so we have enough candles
    opens = [100.0] * 5 + [o]
    highs = [105.0] * 5 + [h]
    lows = [95.0] * 5 + [low]
    closes = [100.0] * 5 + [c]
    return opens, highs, lows, closes


@pytest.mark.asyncio
async def test_bullish_pinbar(analyzer):
    """Test Bullish Pinbar (Hammer)."""
    # Open=100, High=102, Low=90, Close=101
    # Long lower wick (100-90=10), Small body (101-100=1), Small upper wick (102-101=1)

    opens, highs, lows, closes = create_ohlc(100.0, 102.0, 90.0, 101.0)

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes, "DEMAND")

    assert signal is not None
    assert signal.pattern_type == "PINBAR"
    assert signal.direction == "BULLISH"
    assert signal.confidence >= 75


@pytest.mark.asyncio
async def test_bearish_pinbar(analyzer):
    """Test Bearish Pinbar (Shooting Star)."""
    # Open=100, High=110, Low=99, Close=99.5
    # Long upper wick (110-100=10), Small body (0.5), Small lower wick (0.5)

    opens, highs, lows, closes = create_ohlc(100.0, 110.0, 99.0, 99.5)

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes, "SUPPLY")

    assert signal is not None
    assert signal.pattern_type == "PINBAR"
    assert signal.direction == "BEARISH"
    assert signal.confidence >= 75


@pytest.mark.asyncio
async def test_bullish_engulfing(analyzer):
    """Test Bullish Engulfing."""
    # Prev Candle: Red (Open=100, Close=95)
    # Curr Candle: Green (Open=94, Close=101) -> Engulfs prev body

    opens = [100.0] * 4 + [100.0, 94.0]
    highs = [105.0] * 4 + [100.0, 102.0]
    lows = [95.0] * 4 + [95.0, 93.0]
    closes = [100.0] * 4 + [95.0, 101.0]

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes, "DEMAND")

    assert signal is not None
    assert signal.pattern_type == "ENGULFING"
    assert signal.direction == "BULLISH"
    assert signal.confidence >= 85


@pytest.mark.asyncio
async def test_bearish_engulfing(analyzer):
    """Test Bearish Engulfing."""
    # Prev Candle: Green (Open=100, Close=105)
    # Curr Candle: Red (Open=106, Close=99) -> Engulfs prev body

    opens = [100.0] * 4 + [100.0, 106.0]
    highs = [105.0] * 4 + [105.0, 107.0]
    lows = [95.0] * 4 + [100.0, 98.0]
    closes = [100.0] * 4 + [105.0, 99.0]

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes, "SUPPLY")

    assert signal is not None
    assert signal.pattern_type == "ENGULFING"
    assert signal.direction == "BEARISH"
    assert signal.confidence >= 85


@pytest.mark.asyncio
async def test_no_pattern(analyzer):
    """Test Normal Candle (No Pattern)."""
    # Just a regular candle
    opens, highs, lows, closes = create_ohlc(100.0, 105.0, 95.0, 102.0)

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes)

    # Might be detected as Doji if body is small, or None
    # Body ratio = 2 / 10 = 0.2. Doji threshold < 0.1. Pinbar < 0.3.
    # Wicks are balanced.
    # Not Pinbar (wicks not long enough relative to body/each other).

    # Wait, 0.2 < 0.3 (Pinbar threshold).
    # Upper wick: 105-102 = 3. Lower wick: 100-95 = 5. Body = 2.
    # Bullish Pinbar req: lower > 2*upper (5 < 6 -> False).
    # Bearish Pinbar req: upper > 2*lower (3 < 10 -> False).

    # So should be None
    assert signal is None


@pytest.mark.asyncio
async def test_insufficient_data(analyzer):
    """Test with insufficient data (line 45)."""
    # Less than 3 candles
    opens = [100.0] * 2
    highs = [105.0] * 2
    lows = [95.0] * 2
    closes = [100.0] * 2

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes)

    assert signal is None


@pytest.mark.asyncio
async def test_zero_range_candle(analyzer):
    """Test with zero range candle (line 66)."""
    # Candle with zero range (high == low)
    opens = [100.0] * 5 + [100.0]
    highs = [105.0] * 5 + [100.0]
    lows = [95.0] * 5 + [100.0]
    closes = [100.0] * 5 + [100.0]

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes)

    assert signal is None


@pytest.mark.asyncio
async def test_inside_bar(analyzer):
    """Test Inside Bar pattern (line 120)."""
    # Current candle is inside previous candle
    # Prev: High=105, Low=95
    # Curr: High=103, Low=97 (inside prev)
    opens = [100.0] * 4 + [100.0, 100.0]
    highs = [105.0] * 4 + [105.0, 103.0]
    lows = [95.0] * 4 + [95.0, 97.0]
    closes = [100.0] * 4 + [100.0, 100.0]

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes)

    assert signal is not None
    assert signal.pattern_type == "INSIDE_BAR"
    assert signal.direction == "NEUTRAL"
    assert signal.confidence == 50.0


@pytest.mark.asyncio
async def test_doji(analyzer):
    """Test Doji pattern (line 124)."""
    # Very small body relative to range
    # Open=100, High=105, Low=95, Close=100.1
    # Body = 0.1, Range = 10, Ratio = 0.01 (< 0.1)
    opens = [100.0] * 5 + [100.0]
    highs = [105.0] * 5 + [105.0]
    lows = [95.0] * 5 + [95.0]
    closes = [100.0] * 5 + [100.1]

    signal = await analyzer.analyze_pattern("EURUSD", opens, highs, lows, closes)

    assert signal is not None
    assert signal.pattern_type == "DOJI"
    assert signal.direction == "NEUTRAL"
    assert signal.confidence == 60.0
