from unittest.mock import patch

import pytest

from src.trading_bot.strategies.enhancement.rsi_analyzer import RSIAnalyzer


@pytest.fixture
def rsi_config():
    return {"rsi": {"period": 14, "overbought": 70, "oversold": 30}}


@pytest.fixture
def analyzer(rsi_config):
    return RSIAnalyzer(rsi_config)


@pytest.mark.asyncio
async def test_oversold_signal(analyzer):
    """Test RSI oversold condition (Buy signal)."""
    # Mock calculator to return RSI values ending below 30
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Create a series ending at 25 (Oversold)
        rsi_values = [50] * 10 + [40, 35, 25]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 13  # Dummy prices

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.rsi_value == 25
        assert signal.signal_type == "BUY"
        assert signal.confidence >= 20
        assert signal.details["condition"] == "OVERSOLD"


@pytest.mark.asyncio
async def test_overbought_signal(analyzer):
    """Test RSI overbought condition (Sell signal)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Create a series ending at 75 (Overbought)
        rsi_values = [50] * 10 + [60, 65, 75]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 13

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.rsi_value == 75
        assert signal.signal_type == "SELL"
        assert signal.confidence >= 20
        assert signal.details["condition"] == "OVERBOUGHT"


@pytest.mark.asyncio
async def test_bullish_divergence(analyzer):
    """Test Bullish Divergence (Price Lower Low, RSI Higher Low)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Construct Bullish Divergence scenario with sufficient length (>20)
        # We add padding at the start
        padding_len = 20
        padding_price = [100.0] * padding_len
        padding_rsi = [50.0] * padding_len

        # Pattern: High -> Low -> High -> Lower Low
        # We append the pattern to the padding
        pattern_prices = [100, 100, 100, 100, 90, 100, 100, 100, 85, 100, 100, 100]
        prices = padding_price + pattern_prices

        # Pattern: Neutral -> Low -> Neutral -> Higher Low
        pattern_rsi = [50, 50, 50, 50, 30, 50, 50, 50, 35, 50, 50, 50]
        rsi_values = padding_rsi + pattern_rsi

        mock_calc.return_value = {"rsi": rsi_values}

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.signal_type == "BUY"
        # Should have divergence bonus
        assert "Bullish Divergence" in str(signal.details.get("divergence"))
        assert signal.confidence >= 25


@pytest.mark.asyncio
async def test_bearish_divergence(analyzer):
    """Test Bearish Divergence (Price Higher High, RSI Lower High)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # Construct Bearish Divergence scenario with sufficient length
        padding_len = 20
        padding_price = [100.0] * padding_len
        padding_rsi = [50.0] * padding_len

        # Pattern: High -> High -> High -> Higher High
        pattern_prices = [100, 100, 100, 100, 110, 100, 100, 100, 115, 100, 100, 100]
        prices = padding_price + pattern_prices

        # Pattern: Neutral -> High -> Neutral -> Lower High
        pattern_rsi = [50, 50, 50, 50, 70, 50, 50, 50, 65, 50, 50, 50]
        rsi_values = padding_rsi + pattern_rsi

        mock_calc.return_value = {"rsi": rsi_values}

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.signal_type == "SELL"
        assert "Bearish Divergence" in str(signal.details.get("divergence"))
        assert signal.confidence >= 25


@pytest.mark.asyncio
async def test_neutral_signal(analyzer):
    """Test Neutral RSI."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        rsi_values = [50] * 20  # Flat RSI
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 20

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1")

        assert signal.signal_type == "NEUTRAL"
        assert signal.confidence == 0


@pytest.mark.asyncio
async def test_no_rsi_data(analyzer):
    """Test when no RSI data is available (line 64)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        mock_calc.return_value = {"rsi": []}  # Empty RSI values

        prices = [100.0] * 20

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1")

        assert signal.signal_type == "NEUTRAL"
        assert signal.confidence == 0
        assert "error" in signal.details
        assert "No RSI data" in signal.details["error"]


@pytest.mark.asyncio
async def test_rising_from_oversold(analyzer):
    """Test rising from oversold reversal (line 93-96)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # RSI rising from oversold: 25 -> 35
        rsi_values = [50] * 10 + [25, 35]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 12

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "DEMAND")

        assert signal.signal_type == "BUY"
        assert signal.confidence >= 15
        assert "reversal" in signal.details
        assert "Bullish Reversal" in signal.details["reversal"]


@pytest.mark.asyncio
async def test_falling_from_overbought(analyzer):
    """Test falling from overbought reversal (line 100-103)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # RSI falling from overbought: 75 -> 65
        rsi_values = [50] * 10 + [75, 65]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 12

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "SUPPLY")

        assert signal.signal_type == "SELL"
        assert signal.confidence >= 15
        assert "reversal" in signal.details
        assert "Bearish Reversal" in signal.details["reversal"]


@pytest.mark.asyncio
async def test_bullish_momentum_trend(analyzer):
    """Test bullish momentum trend context (line 116-118)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # RSI between 50-70 for DEMAND zone
        rsi_values = [50] * 10 + [60]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 11

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "DEMAND")

        assert "trend" in signal.details
        assert "Bullish Momentum" in signal.details["trend"]
        assert signal.confidence >= 8


@pytest.mark.asyncio
async def test_bearish_momentum_trend(analyzer):
    """Test bearish momentum trend context (line 119-121)."""
    with patch(
        "src.trading_bot.strategies.enhancement.technical_analyzer.RobustIndicatorCalculator.calculate_all"
    ) as mock_calc:
        # RSI between 30-50 for SUPPLY zone
        rsi_values = [50] * 10 + [40]
        mock_calc.return_value = {"rsi": rsi_values}

        prices = [100.0] * 11

        signal = await analyzer.analyze_rsi_signal("EURUSD", prices, "H1", "SUPPLY")

        assert "trend" in signal.details
        assert "Bearish Momentum" in signal.details["trend"]
        assert signal.confidence >= 8
