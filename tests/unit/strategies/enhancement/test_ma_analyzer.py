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
