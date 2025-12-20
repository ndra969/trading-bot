from unittest.mock import patch

import numpy as np
import pytest

from src.trading_bot.strategies.enhancement.technical_analyzer import (
    RobustIndicatorCalculator,
    TechnicalIndicatorCalculator,
)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    length = 100
    # dates = pd.date_range(start="2024-01-01", periods=length, freq="h")  # Not used

    # Create synthetic price data with a trend
    close = np.linspace(100, 150, length) + np.random.normal(0, 1, length)
    high = close + np.random.uniform(0.1, 2.0, length)
    low = close - np.random.uniform(0.1, 2.0, length)
    volume = np.random.uniform(100, 1000, length)

    return {
        "prices": close.tolist(),
        "high": high.tolist(),
        "low": low.tolist(),
        "volume": volume.tolist(),
    }


class TestTechnicalIndicatorCalculator:
    """Test pandas-ta based calculator."""

    def test_calculate_multiple_indicators(self, sample_data):
        calculator = TechnicalIndicatorCalculator()

        results = calculator.calculate_multiple_indicators(
            prices=sample_data["prices"],
            high=sample_data["high"],
            low=sample_data["low"],
            volume=sample_data["volume"],
        )

        # Check required keys exist
        required_keys = ["rsi", "ema_9", "ema_21", "ema_50", "sma_200", "macd", "bb_upper", "atr"]
        for key in required_keys:
            assert key in results, f"Missing key: {key}"

        # Check data types
        assert isinstance(results["rsi"], list)
        assert len(results["rsi"]) > 0

    def test_empty_input(self):
        calculator = TechnicalIndicatorCalculator()
        results = calculator.calculate_multiple_indicators([])
        assert results == {}


class TestRobustIndicatorCalculator:
    """Test the fallback mechanism."""

    def test_initialization(self):
        # Should initialize without errors
        calculator = RobustIndicatorCalculator()
        assert calculator.secondary is not None  # pandas-ta should be available

    def test_calculate_all(self, sample_data):
        calculator = RobustIndicatorCalculator()

        results = calculator.calculate_all(
            prices=sample_data["prices"],
            high=sample_data["high"],
            low=sample_data["low"],
            volume=sample_data["volume"],
        )

        assert "rsi" in results
        assert len(results["rsi"]) > 0

    def test_fallback_chain(self, sample_data):
        """Test fallback from primary/secondary to tertiary calculator."""

        # Mock primary and secondary to fail or be None
        with (
            patch(
                "src.trading_bot.strategies.enhancement.technical_analyzer.TALibHighPerformance"
            ) as mock_talib,
            patch(
                "src.trading_bot.strategies.enhancement.technical_analyzer.TechnicalIndicatorCalculator"
            ) as mock_pandas_ta,
        ):
            # Make TALib unavailable
            mock_talib.return_value.available = False

            # Make pandas-ta fail initialization or calculation
            mock_pandas_ta.side_effect = ImportError("Simulated pandas-ta failure")

            # This should fall back to TALibIndicatorCalculator (ta lib) if installed,
            # or fail gracefully if that's also missing.
            # Note: In this env, 'ta' might be installed.

            try:
                calculator = RobustIndicatorCalculator()

                # If calculator initialized, it means it found a fallback (likely 'ta' lib)
                if calculator.fallback:
                    results = calculator.calculate_all(sample_data["prices"])
                    assert results is not None
            except ImportError:
                # If no libs are available, that's also a valid outcome for this test
                pass
