import pytest
from trading_worker.strategies.enhancement.fibonacci_analyzer import FibonacciAnalyzer


@pytest.fixture
def fib_config():
    return {"fibonacci": {"lookback": 20, "tolerance": 0.01}}  # 1% tolerance


@pytest.fixture
def analyzer(fib_config):
    return FibonacciAnalyzer(fib_config)


# Pivot-shaped series (enhancement-layer-rework): swing legs must be real
# pivots (local extremes with swing_window=5 strictly higher/lower
# neighbours), not flat plateaus — the analyzer now measures retracements
# off the most recent structural leg instead of the global lookback extremes.

# UP leg: pivot low 100 @ idx 7 -> pivot high 200 @ idx 14, then retracement.
UP_LOWS = [
    140,
    135,
    130,
    125,
    120,
    115,
    110,
    100,
    120,
    135,
    150,
    165,
    180,
    190,
    196,
    185,
    170,
    160,
    150,
    140,
]
UP_HIGHS = [
    145,
    140,
    135,
    130,
    125,
    120,
    115,
    108,
    125,
    140,
    155,
    170,
    185,
    195,
    200,
    190,
    175,
    165,
    155,
    145,
]

# DOWN leg: pivot high 200 @ idx 7 -> pivot low 100 @ idx 14, then retracement.
DOWN_HIGHS = [
    160,
    165,
    170,
    175,
    180,
    185,
    190,
    200,
    180,
    165,
    150,
    135,
    120,
    110,
    104,
    115,
    130,
    140,
    150,
    160,
]
DOWN_LOWS = [
    155,
    160,
    165,
    170,
    175,
    180,
    185,
    195,
    175,
    160,
    145,
    130,
    115,
    105,
    100,
    110,
    125,
    135,
    145,
    155,
]


@pytest.mark.asyncio
async def test_demand_zone_confluence(analyzer):
    """Test confluence with Demand Zone (Uptrend Retracement)."""
    # Leg: pivot low 100 -> pivot high 200. Range: 100
    # 61.8% Retracement Level: 200 - 61.8 = 138.2
    zone_price = 138.2

    signal = await analyzer.analyze_fibonacci("EURUSD", UP_HIGHS, UP_LOWS, zone_price, "DEMAND")

    assert signal is not None
    assert signal.direction == "UP"
    assert signal.swing_high == 200
    assert signal.swing_low == 100
    assert signal.confluence_level.level == 0.618
    assert signal.score == 20  # Score for 61.8%
    assert abs(signal.confluence_level.price - 138.2) < 0.1


@pytest.mark.asyncio
async def test_supply_zone_confluence(analyzer):
    """Test confluence with Supply Zone (Downtrend Retracement)."""
    # Leg: pivot high 200 -> pivot low 100. Range: 100
    # 50% Retracement Level: 100 + 50 = 150
    zone_price = 150.0

    signal = await analyzer.analyze_fibonacci("EURUSD", DOWN_HIGHS, DOWN_LOWS, zone_price, "SUPPLY")

    assert signal is not None
    assert signal.direction == "DOWN"
    assert signal.confluence_level.level == 0.5
    assert signal.score == 15  # Score for 50%
    assert abs(signal.confluence_level.price - 150.0) < 0.1


@pytest.mark.asyncio
async def test_no_confluence(analyzer):
    """Test when zone is far from any Fibo level."""
    # Leg 100 -> 200. Levels: 121.4, 138.2, 150, 161.8
    zone_price = 180.0

    signal = await analyzer.analyze_fibonacci("EURUSD", UP_HIGHS, UP_LOWS, zone_price, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_invalid_swing_direction(analyzer):
    """Test invalid swing for the zone type."""
    # Downtrend leg (high before low), but we ask for DEMAND (needs UP leg)
    signal = await analyzer.analyze_fibonacci("EURUSD", DOWN_HIGHS, DOWN_LOWS, 150.0, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_insufficient_data(analyzer):
    """Test fibonacci analysis with insufficient data."""
    # Less than lookback (20) candles
    highs = [200.0] * 15
    lows = [100.0] * 15

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 150.0, "DEMAND")

    assert signal is None


@pytest.mark.asyncio
async def test_invalid_zone_type(analyzer):
    """Test fibonacci analysis with invalid zone type."""
    signal = await analyzer.analyze_fibonacci("EURUSD", UP_HIGHS, UP_LOWS, 150.0, "INVALID")

    assert signal is None


@pytest.mark.asyncio
async def test_supply_zone_invalid_swing(analyzer):
    """Test supply zone with invalid swing direction (uptrend data)."""
    signal = await analyzer.analyze_fibonacci("EURUSD", UP_HIGHS, UP_LOWS, 150.0, "SUPPLY")

    # The only pivot high comes AFTER the pivot low (UP leg) — no valid DOWN leg
    assert signal is None


@pytest.mark.asyncio
async def test_recent_leg_beats_stale_global_extreme(analyzer):
    """The retracement must be measured off the recent structural leg, not a
    stale global extreme (the old global max/min model returned None here
    because the lookback max sat before the min)."""
    # Old spike to 300 at idx 2 (inside the lookback, but NOT a pivot since
    # idx < swing_window), then a clean leg 100 @ idx 7 -> 200 @ idx 14.
    highs = [
        150,
        250,
        300,
        250,
        150,
        120,
        115,
        108,
        125,
        140,
        155,
        170,
        185,
        195,
        200,
        190,
        175,
        165,
        155,
        145,
    ]
    lows = [
        145,
        245,
        295,
        245,
        145,
        115,
        110,
        100,
        120,
        135,
        150,
        165,
        180,
        190,
        196,
        185,
        170,
        160,
        150,
        140,
    ]

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 150.0, "DEMAND")

    assert signal is not None
    assert signal.swing_high == 200  # the recent leg, not the stale 300
    assert signal.swing_low == 100
    assert signal.confluence_level.level == 0.5


@pytest.mark.asyncio
async def test_flat_data_has_no_leg(analyzer):
    """Flat plateaus contain no pivots, so no leg and no signal."""
    highs = [110.0] * 10 + [200.0] * 10
    lows = [100.0] * 10 + [150.0] * 10

    signal = await analyzer.analyze_fibonacci("EURUSD", highs, lows, 138.2, "DEMAND")

    assert signal is None
