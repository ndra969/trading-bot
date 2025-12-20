import pytest

from src.trading_bot.strategies.enhancement.trendline_analyzer import TrendlineAnalyzer


@pytest.fixture
def trendline_config():
    return {"trendline": {"min_touches": 3, "tolerance": 0.001}}


@pytest.fixture
def analyzer(trendline_config):
    return TrendlineAnalyzer(trendline_config)


@pytest.mark.asyncio
async def test_support_trendline_detection(analyzer):
    """Test detection of an ascending support trendline."""
    # Create an uptrend: Lows at 100, 102, 104, 106...
    # Indices: 10, 20, 30, 40...

    length = 100
    prices = [110.0] * length  # Base price

    # Create 3 swing lows that form a line
    # y = mx + c
    # Let's say starts at index 10, price 100.
    # Slope = 0.2

    # Swing 1: Index 10, Price 100
    prices[10] = 100.0
    prices[9] = 105.0
    prices[11] = 105.0  # Ensure it's a valley

    # Swing 2: Index 30, Price 104 (100 + 0.2 * 20)
    prices[30] = 104.0
    prices[29] = 109.0
    prices[31] = 109.0

    # Swing 3: Index 50, Price 108 (100 + 0.2 * 40)
    prices[50] = 108.0
    prices[49] = 113.0
    prices[51] = 113.0

    # Current Price near the projected line
    # Index 99. Expected: 100 + 0.2 * (99-10) = 100 + 17.8 = 117.8
    prices[99] = 117.85  # Very close (0.05 diff)

    # Use pip_value=1.0 so that 0.05 diff is 0.05 pips (< 20 threshold)
    signal = await analyzer.analyze_trendline_signal("EURUSD", prices, "H1", pip_value=1.0)

    # Check if any support line was detected
    support_lines = [line for line in signal.trendlines if line.line_type == "SUPPORT"]

    assert len(support_lines) > 0
    best_line = support_lines[0]
    assert best_line.touches >= 3
    assert best_line.slope > 0  # Ascending

    # Check signal type (Price is near the line)
    # Distance is small enough
    assert signal.signal_type == "BOUNCE_SUPPORT"


@pytest.mark.asyncio
async def test_resistance_trendline_detection(analyzer):
    """Test detection of a descending resistance trendline."""
    length = 100
    prices = [90.0] * length

    # Create 3 swing highs forming a downtrend
    # Swing 1: Index 10, Price 120
    prices[10] = 120.0
    prices[9] = 115.0
    prices[11] = 115.0

    # Swing 2: Index 30, Price 116 (Down 4)
    prices[30] = 116.0
    prices[29] = 111.0
    prices[31] = 111.0

    # Swing 3: Index 50, Price 112 (Down 4)
    prices[50] = 112.0
    prices[49] = 107.0
    prices[51] = 107.0

    # Current price near projected line
    # Line drops 0.2 per index
    # Index 99: 120 - 0.2 * (89) = 120 - 17.8 = 102.2
    prices[99] = 102.25  # Very close (0.05 diff)

    signal = await analyzer.analyze_trendline_signal("EURUSD", prices, "H1", pip_value=1.0)

    resistance_lines = [line for line in signal.trendlines if line.line_type == "RESISTANCE"]
    assert len(resistance_lines) > 0

    best_line = resistance_lines[0]
    assert best_line.touches >= 3
    assert best_line.slope < 0  # Descending

    assert signal.signal_type == "BOUNCE_RESISTANCE"


@pytest.mark.asyncio
async def test_insufficient_data(analyzer):
    """Test behavior with insufficient data."""
    prices = [100.0] * 10
    signal = await analyzer.analyze_trendline_signal("EURUSD", prices, "H1")
    assert signal.signal_type == "NEUTRAL"
    assert "error" in signal.details


@pytest.mark.asyncio
async def test_invalid_line_cutting_price(analyzer):
    """Test that lines cutting through price are invalidated."""
    length = 100
    prices = [110.0] * length

    # Swing 1: Index 10, Price 100
    prices[10] = 100.0
    prices[9] = 105.0
    prices[11] = 105.0

    # Swing 2: Index 50, Price 100
    prices[50] = 100.0
    prices[49] = 105.0
    prices[51] = 105.0

    # BUT, in between at Index 30, price dips to 90 (Way below the hypothetical line at 100)
    # This should invalidate a SUPPORT line connecting 10 and 50
    prices[30] = 90.0

    signal = await analyzer.analyze_trendline_signal("EURUSD", prices, "H1")

    # Should NOT find a support line connecting index 10 and 50 because index 30 broke it
    # Note: We need another point to even form 3 touches, let's add one at 70
    prices[70] = 100.0
    prices[69] = 105.0
    prices[71] = 105.0

    # Re-run
    signal = await analyzer.analyze_trendline_signal("EURUSD", prices, "H1")

    # Check if that specific line exists (Flat line at 100)
    # It might find other lines, but not the one connecting 10-50-70 as support
    # because 30 is below it.

    for line in signal.trendlines:
        if line.line_type == "SUPPORT":
            # If slope is roughly 0 and intercept roughly 100
            if abs(line.slope) < 0.01 and abs(line.intercept - 100) < 1:
                assert False, "Should not detect support line cut by price"
