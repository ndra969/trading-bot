from unittest.mock import patch

import pytest

from src.trading_bot.strategies.enhancement.ma_analyzer import MovingAverageAnalyzer


@pytest.fixture
def ma_config():
    return {}  # Default config


@pytest.fixture
def analyzer(ma_config):
    return MovingAverageAnalyzer(ma_config)


@pytest.mark.asyncio
async def test_strong_uptrend(analyzer):
    """Test Strong Uptrend (Price > EMA21 > EMA50 > SMA200)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Mock MA values
        # Scenario: Strong Uptrend
        # SMA200: 100
        # EMA50:  110
        # EMA21:  120
        # Price:  130

        mock_calc.return_value = {
            "sma_200": [100.0] * 10,
            "ema_50": [110.0] * 10,
            "ema_21": [120.0] * 10,
            "ema_9": [125.0] * 10,
        }

        prices = [130.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.trend_direction == "BULLISH"
        assert signal.signal_type == "BUY"
        assert signal.confidence >= 25
        assert signal.details["alignment"] == "Strong Uptrend"


@pytest.mark.asyncio
async def test_strong_downtrend(analyzer):
    """Test Strong Downtrend (Price < EMA21 < EMA50 < SMA200)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Scenario: Strong Downtrend
        # SMA200: 150
        # EMA50:  140
        # EMA21:  130
        # Price:  120

        mock_calc.return_value = {
            "sma_200": [150.0] * 10,
            "ema_50": [140.0] * 10,
            "ema_21": [130.0] * 10,
            "ema_9": [125.0] * 10,
        }

        prices = [120.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.trend_direction == "BEARISH"
        assert signal.signal_type == "SELL"
        assert signal.confidence >= 25
        assert signal.details["alignment"] == "Strong Downtrend"


@pytest.mark.asyncio
async def test_golden_cross(analyzer):
    """Test Golden Cross (EMA21 crosses above EMA50)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Prev: EMA21 (100) < EMA50 (105)
        # Curr: EMA21 (110) > EMA50 (105)

        ema_21 = [100.0] * 9 + [110.0]
        ema_50 = [105.0] * 9 + [105.0]

        mock_calc.return_value = {
            "sma_200": [90.0] * 10,
            "ema_50": ema_50,
            "ema_21": ema_21,
            "ema_9": [115.0] * 10,
        }

        prices = [120.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.signal_type == "BUY"
        assert signal.details["crossover"] == "Golden Cross"
        assert signal.confidence >= 20


@pytest.mark.asyncio
async def test_death_cross(analyzer):
    """Test Death Cross (EMA21 crosses below EMA50)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Prev: EMA21 (110) > EMA50 (105)
        # Curr: EMA21 (100) < EMA50 (105)

        ema_21 = [110.0] * 9 + [100.0]
        ema_50 = [105.0] * 9 + [105.0]

        mock_calc.return_value = {
            "sma_200": [150.0] * 10,
            "ema_50": ema_50,
            "ema_21": ema_21,
            "ema_9": [90.0] * 10,
        }

        prices = [80.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.signal_type == "SELL"
        assert signal.details["crossover"] == "Death Cross"
        assert signal.confidence >= 20


@pytest.mark.asyncio
async def test_insufficient_ma_data(analyzer):
    """Test MA analysis with insufficient data (line 62)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Missing EMA50 or EMA21
        mock_calc.return_value = {
            "sma_200": [100.0] * 10,
            "ema_50": [],  # Empty
            "ema_21": [120.0] * 10,
            "ema_9": [125.0] * 10,
        }

        prices = [130.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.signal_type == "NEUTRAL"
        assert signal.trend_direction == "UNKNOWN"
        assert "error" in signal.details


@pytest.mark.asyncio
async def test_fallback_trend_without_sma200(analyzer):
    """Test fallback trend identification without SMA200 (line 86-89)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # No SMA200 data
        mock_calc.return_value = {
            "sma_200": [],  # Empty
            "ema_50": [110.0] * 10,
            "ema_21": [120.0] * 10,
            "ema_9": [125.0] * 10,
        }

        prices = [130.0] * 10  # Price > EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.trend_direction == "BULLISH"  # Fallback to EMA50 comparison

        # Test bearish fallback
        prices = [100.0] * 10  # Price < EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.trend_direction == "BEARISH"


@pytest.mark.asyncio
async def test_medium_uptrend(analyzer):
    """Test medium uptrend (line 98-102)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Price > EMA21 > EMA50 (but no SMA200 or not in strong alignment)
        mock_calc.return_value = {
            "sma_200": [],  # No SMA200
            "ema_50": [100.0] * 10,
            "ema_21": [110.0] * 10,
            "ema_9": [115.0] * 10,
        }

        prices = [120.0] * 10  # Price > EMA21 > EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.signal_type == "BUY"
        assert signal.details["alignment"] == "Medium Uptrend"
        assert signal.confidence >= 15


@pytest.mark.asyncio
async def test_weak_uptrend(analyzer):
    """Test weak uptrend (line 103-105)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Price > EMA21 but not > EMA50
        mock_calc.return_value = {
            "sma_200": [],
            "ema_50": [120.0] * 10,  # EMA50 > Price
            "ema_21": [110.0] * 10,
            "ema_9": [115.0] * 10,
        }

        prices = [115.0] * 10  # Price > EMA21 but < EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.details["alignment"] == "Weak Uptrend"
        assert signal.confidence >= 8


@pytest.mark.asyncio
async def test_medium_downtrend(analyzer):
    """Test medium downtrend (line 113-117)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Price < EMA21 < EMA50
        mock_calc.return_value = {
            "sma_200": [],
            "ema_50": [120.0] * 10,
            "ema_21": [110.0] * 10,
            "ema_9": [105.0] * 10,
        }

        prices = [100.0] * 10  # Price < EMA21 < EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.signal_type == "SELL"
        assert signal.details["alignment"] == "Medium Downtrend"
        assert signal.confidence >= 15


@pytest.mark.asyncio
async def test_weak_downtrend(analyzer):
    """Test weak downtrend (line 118-120)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Price < EMA21 but not < EMA50
        mock_calc.return_value = {
            "sma_200": [],
            "ema_50": [100.0] * 10,  # EMA50 < Price
            "ema_21": [110.0] * 10,
            "ema_9": [105.0] * 10,
        }

        prices = [105.0] * 10  # Price < EMA21 but > EMA50

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.details["alignment"] == "Weak Downtrend"
        assert signal.confidence >= 8


@pytest.mark.asyncio
async def test_bullish_fast_cross(analyzer):
    """Test bullish fast cross (EMA9 crosses above EMA21) (line 149-153)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Prev: EMA9 (100) <= EMA21 (110)
        # Curr: EMA9 (120) > EMA21 (110)
        ema_9 = [100.0] * 9 + [120.0]
        ema_21 = [110.0] * 10

        mock_calc.return_value = {
            "sma_200": [90.0] * 10,
            "ema_50": [100.0] * 10,
            "ema_21": ema_21,
            "ema_9": ema_9,
        }

        prices = [130.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "DEMAND")

        assert "fast_cross" in signal.details
        assert signal.details["fast_cross"] == "Bullish"
        assert signal.confidence >= 12


@pytest.mark.asyncio
async def test_bearish_fast_cross(analyzer):
    """Test bearish fast cross (EMA9 crosses below EMA21) (line 157-161)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Prev: EMA9 (120) >= EMA21 (110)
        # Curr: EMA9 (100) < EMA21 (110)
        ema_9 = [120.0] * 9 + [100.0]
        ema_21 = [110.0] * 10

        mock_calc.return_value = {
            "sma_200": [150.0] * 10,
            "ema_50": [120.0] * 10,
            "ema_21": ema_21,
            "ema_9": ema_9,
        }

        prices = [80.0] * 10

        signal = await analyzer.analyze_ma_signal("EURUSD", prices, "H1", "SUPPLY")

        assert "fast_cross" in signal.details
        assert signal.details["fast_cross"] == "Bearish"
        assert signal.confidence >= 12
