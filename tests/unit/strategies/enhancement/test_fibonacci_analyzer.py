import pytest
from trading_worker.strategies.enhancement.fibonacci_analyzer import FibonacciAnalyzer


@pytest.fixture
def fib_config():
    return {"fibonacci": {"lookback": 20, "tolerance": 0.01}}  # 1% tolerance


@pytest.fixture
def analyzer(fib_config):
    return FibonacciAnalyzer(fib_config)


@pytest.mark.asyncio
async def test_demand_zone_confluence(analyzer):
    """Test confluence with Demand Zone (Uptrend Retracement)."""
    # Swing: Low 100 -> High 200
    # Range: 100
    # 61.8% Retracement Level: 200 - 61.8 = 138.2

    # Create data: 10 points at 100, then 10 points at 200
    # This ensures Min=100, Max=200, and Low index < High index
    lows = [100.0] * 10 + [150.0] * 10
    highs = [110.0] * 10 + [200.0] * 10

    # Demand Zone at 138.2 (Golden Pocket)
    zone_price = 138.2

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, zone_price, "DEMAND")

    assert signal is not None
    assert signal.direction == "UP"
    assert signal.confluence_level.level == 0.618
    assert signal.score == 20  # Score for 61.8%
    assert abs(signal.confluence_level.price - 138.2) < 0.1


@pytest.mark.asyncio
async def test_supply_zone_confluence(analyzer):
    """Test confluence with Supply Zone (Downtrend Retracement)."""
    # Swing: High 200 -> Low 100
    # Range: 100
    # 50% Retracement Level: 100 + 50 = 150

    # Create data: 10 points at 200, then 10 points at 100
    # High index < Low index
    highs = [200.0] * 10 + [150.0] * 10
    lows = [190.0] * 10 + [100.0] * 10

    # Supply Zone at 150.0
    zone_price = 150.0

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, zone_price, "SUPPLY")

    assert signal is not None
    assert signal.direction == "DOWN"
    assert signal.confluence_level.level == 0.5
    assert signal.score == 15  # Score for 50%
    assert abs(signal.confluence_level.price - 150.0) < 0.1


@pytest.mark.asyncio
async def test_no_confluence(analyzer):
    """Test when zone is far from any Fibo level."""
    # Swing: 100 -> 200. Levels: 138.2, 150, 161.8
    lows = [100.0] * 10 + [150.0] * 10
    highs = [110.0] * 10 + [200.0] * 10

    # Zone at 180 (No key level nearby)
    zone_price = 180.0

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, zone_price, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_invalid_swing_direction(analyzer):
    """Test invalid swing for the zone type."""
    # Downtrend: 200 -> 100
    highs = [200.0] * 10 + [150.0] * 10
    lows = [190.0] * 10 + [100.0] * 10

    # We ask for DEMAND zone analysis (expecting Uptrend Retracement)
    # But data shows Downtrend (High before Low)

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 150.0, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_insufficient_data(analyzer):
    """Test fibonacci analysis with insufficient data (line 54)."""
    # Less than lookback (20) candles
    highs = [200.0] * 15
    lows = [100.0] * 15

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 150.0, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_invalid_zone_type(analyzer):
    """Test fibonacci analysis with invalid zone type (line 94-97)."""
    # Valid data
    lows = [100.0] * 10 + [150.0] * 10
    highs = [110.0] * 10 + [200.0] * 10

    # Invalid zone type (not DEMAND or SUPPLY)
    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 150.0, "INVALID")

    assert signal is None


@pytest.mark.asyncio
async def test_supply_zone_invalid_swing(analyzer):
    """Test supply zone with invalid swing direction (line 94)."""
    # Create data where High happens AFTER Low (invalid for SUPPLY zone)
    # For SUPPLY zone, we need High BEFORE Low (downtrend)
    # But here Low happens before High (uptrend)
    lows = [100.0] * 10 + [150.0] * 10  # Low at index 0-9
    highs = [110.0] * 10 + [200.0] * 10  # High at index 10-19 (after low)

    # Supply Zone at 150.0
    zone_price = 150.0

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, zone_price, "SUPPLY")

    # Should return None because high_idx >= low_idx (invalid for SUPPLY)
    assert signal is None
