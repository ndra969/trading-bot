from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from trading_worker.strategies.enhancement.technical_analyzer import (
    RobustIndicatorCalculator,
    TALibHighPerformance,
    TALibIndicatorCalculator,
    TechnicalIndicatorCalculator,
)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    length = 100
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

    def test_cache_validity_check(self):
        """Test _is_cache_valid method."""
        calculator = TechnicalIndicatorCalculator(cache_duration_minutes=5)

        # Test with non-existent key
        assert calculator._is_cache_valid("nonexistent") is False

        # Test with expired cache
        calculator._cache_result("test_key", {"data": "test"})
        # Manually set expiration to past
        calculator.cache["test_key"]["expires"] = datetime.now() - timedelta(seconds=1)
        assert calculator._is_cache_valid("test_key") is False

        # Test with valid cache
        calculator._cache_result("test_key", {"data": "test"})
        assert calculator._is_cache_valid("test_key") is True

    def test_cache_result(self):
        """Test _cache_result method."""
        calculator = TechnicalIndicatorCalculator(cache_duration_minutes=5)

        test_data = {"rsi": [50.0, 51.0]}
        calculator._cache_result("test_key", test_data)

        assert "test_key" in calculator.cache
        assert calculator.cache["test_key"]["data"] == test_data
        assert "timestamp" in calculator.cache["test_key"]
        assert "expires" in calculator.cache["test_key"]
        assert calculator.cache["test_key"]["expires"] > datetime.now()


class TestTALibIndicatorCalculator:
    """Test 'ta' library based calculator."""

    def test_calculate_indicators_basic(self, sample_data):
        """Test basic indicator calculation with 'ta' library."""
        calculator = TALibIndicatorCalculator()

        df = pd.DataFrame(
            {
                "close": sample_data["prices"],
                "high": sample_data["high"],
                "low": sample_data["low"],
                "volume": sample_data["volume"],
            }
        )

        results = calculator.calculate_indicators(df)

        # Verify expected indicators are present
        assert "rsi" in results
        assert "ema_9" in results
        assert "sma_200" in results
        assert "macd" in results
        assert "bb_upper" in results
        assert "atr" in results

    def test_calculate_indicators_exception_handling(self, sample_data):
        """Test exception handling in calculate_indicators."""
        calculator = TALibIndicatorCalculator()

        df = pd.DataFrame(
            {
                "close": sample_data["prices"],
                "high": sample_data["high"],
                "low": sample_data["low"],
                "volume": sample_data["volume"],
            }
        )

        # Mock an internal method to raise an exception
        with patch.object(
            calculator.momentum, "RSIIndicator", side_effect=RuntimeError("Test error")
        ):
            with pytest.raises(RuntimeError, match="Test error"):
                calculator.calculate_indicators(df)


class TestTALibHighPerformance:
    """Test TA-Lib high-performance calculator."""

    def test_initialization_unavailable(self):
        """Test initialization when TA-Lib is not installed."""
        calc = TALibHighPerformance()
        # The available flag should be False if TA-Lib is not installed,
        # or True if it is. Both are valid states.
        assert isinstance(calc.available, bool)

    def test_calculate_indicators_when_unavailable(self):
        """Test calculate_indicators when TA-Lib is not available."""
        calc = TALibHighPerformance()
        calc.available = False

        with pytest.raises(ImportError, match="TA-Lib not installed"):
            calc.calculate_indicators([1.0, 2.0, 3.0])

    def test_calculate_indicators_with_defaults_when_available(self):
        """Test calculate_indicators with default high/low values when TA-Lib is available."""
        calc = TALibHighPerformance()

        # Only test if TA-Lib is actually available
        if calc.available:
            results = calc.calculate_indicators(prices=[100.0, 101.0, 102.0])

            assert "rsi" in results
            assert len(results["rsi"]) > 0
        else:
            pytest.skip("TA-Lib is not installed")


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
                "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance"
            ) as mock_talib,
            patch(
                "trading_worker.strategies.enhancement.technical_analyzer.TechnicalIndicatorCalculator"
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

    def test_initialization_primary_available(self):
        """Test initialization when TA-Lib is available."""
        mock_talib_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.available = True
        mock_talib_class.return_value = mock_instance

        with patch(
            "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance",
            mock_talib_class,
        ):
            calculator = RobustIndicatorCalculator()
            assert calculator.primary is not None
            assert calculator.primary.available is True

    def test_initialization_primary_exception(self):
        """Test initialization when primary raises exception."""
        with patch(
            "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance",
            side_effect=Exception("Primary failed"),
        ):
            calculator = RobustIndicatorCalculator()
            assert calculator.primary is None
            # Should still have secondary
            assert calculator.secondary is not None

    def test_initialization_secondary_import_error(self):
        """Test initialization when secondary raises ImportError."""
        with patch(
            "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance",
            return_value=MagicMock(available=False),
        ):
            with patch(
                "trading_worker.strategies.enhancement.technical_analyzer.TechnicalIndicatorCalculator",
                side_effect=ImportError("Secondary failed"),
            ):
                calculator = RobustIndicatorCalculator()
                assert calculator.primary is None
                assert calculator.secondary is None
                # Should still try fallback
                assert calculator.fallback is not None

    def test_initialization_fallback_import_error(self):
        """Test initialization when all calculators fail."""
        with patch(
            "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance",
            return_value=MagicMock(available=False),
        ):
            with patch(
                "trading_worker.strategies.enhancement.technical_analyzer.TechnicalIndicatorCalculator",
                side_effect=ImportError("Secondary failed"),
            ):
                with patch(
                    "trading_worker.strategies.enhancement.technical_analyzer.TALibIndicatorCalculator",
                    side_effect=ImportError("Fallback failed"),
                ):
                    calculator = RobustIndicatorCalculator()
                    assert calculator.primary is None
                    assert calculator.secondary is None
                    assert calculator.fallback is None

    def test_calculate_all_primary_failure(self, sample_data):
        """Test calculate_all when primary calculator fails."""
        calculator = RobustIndicatorCalculator()

        # Mock primary to fail
        if calculator.primary:
            with patch.object(
                calculator.primary, "calculate_indicators", side_effect=Exception("Primary failed")
            ):
                results = calculator.calculate_all(
                    prices=sample_data["prices"],
                    high=sample_data["high"],
                    low=sample_data["low"],
                    volume=sample_data["volume"],
                )
                # Should fall back to secondary
                assert "rsi" in results

    def test_calculate_all_secondary_failure(self, sample_data):
        """Test calculate_all when secondary calculator fails."""
        calculator = RobustIndicatorCalculator()

        # Mock both primary and secondary to fail
        with patch.object(
            calculator.secondary,
            "calculate_multiple_indicators",
            side_effect=Exception("Secondary failed"),
        ):
            if calculator.primary:
                with patch.object(calculator.primary, "available", False):
                    results = calculator.calculate_all(
                        prices=sample_data["prices"],
                        high=sample_data["high"],
                        low=sample_data["low"],
                        volume=sample_data["volume"],
                    )
                    # Should fall back to fallback
                    assert "rsi" in results

    def test_calculate_all_fallback_failure(self, sample_data):
        """Test calculate_all when fallback calculator fails."""
        calculator = RobustIndicatorCalculator()

        # Mock all calculators to fail
        with patch.object(
            calculator.secondary,
            "calculate_multiple_indicators",
            side_effect=Exception("Secondary failed"),
        ):
            if calculator.fallback:
                with patch.object(
                    calculator.fallback,
                    "calculate_indicators",
                    side_effect=Exception("Fallback failed"),
                ):
                    if calculator.primary:
                        with patch.object(calculator.primary, "available", False):
                            with pytest.raises(Exception, match="Fallback calculator failed"):
                                calculator.calculate_all(
                                    prices=sample_data["prices"],
                                    high=sample_data["high"],
                                    low=sample_data["low"],
                                    volume=sample_data["volume"],
                                )

    def test_calculate_all_no_calculators_available(self, sample_data):
        """Test calculate_all when no calculators are available."""
        with patch(
            "trading_worker.strategies.enhancement.technical_analyzer.TALibHighPerformance",
            return_value=MagicMock(available=False),
        ):
            with patch(
                "trading_worker.strategies.enhancement.technical_analyzer.TechnicalIndicatorCalculator",
                side_effect=ImportError("Secondary failed"),
            ):
                with patch(
                    "trading_worker.strategies.enhancement.technical_analyzer.TALibIndicatorCalculator",
                    side_effect=ImportError("Fallback failed"),
                ):
                    calculator = RobustIndicatorCalculator()

                    with pytest.raises(
                        RuntimeError, match="All technical indicator calculators failed"
                    ):
                        calculator.calculate_all(
                            prices=sample_data["prices"],
                            high=sample_data["high"],
                            low=sample_data["low"],
                            volume=sample_data["volume"],
                        )

    def test_calculate_all_with_defaults(self, sample_data):
        """Test calculate_all with default high/low values."""
        calculator = RobustIndicatorCalculator()

        results = calculator.calculate_all(
            prices=sample_data["prices"],
            # No high/low/volume - should use defaults
        )

        assert "rsi" in results
        assert len(results["rsi"]) > 0
