"""
Unit tests for zone-based SL calculation.

Tests the new _get_sl_config() and _calculate_zone_based_sl() methods
in FoundationEngine.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from trading_worker.strategies.foundation.foundation_engine import FoundationEngine
from trading_worker.strategies.foundation.zone_detector import DetectedZone, ZoneType


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "symbols": {
            "XAUUSD": {
                "use_zone_based_sl": True,
                "zone_sl_buffer_multiplier": 1.2,
                "min_stop_loss_pips": 80,
                "max_stop_loss_pips": 300,
                "default_stop_loss_pips": 150,
            },
            "EURUSD": {
                "use_zone_based_sl": False,
                "zone_sl_buffer_multiplier": 1.2,
                "min_stop_loss_pips": 15,
                "max_stop_loss_pips": 60,
                "default_stop_loss_pips": 30,
            },
        },
        "signal_generation": {
            "risk_reward": {
                "use_zone_based_sl": False,
                "zone_sl_buffer_multiplier": 1.2,
                "min_stop_loss_distance": {
                    "forex_major": 15.0,
                    "commodities": 80.0,
                    "crypto": 100.0,
                },
                "max_stop_loss_distance": {
                    "forex_major": 60.0,
                    "commodities": 300.0,
                    "crypto": 500.0,
                },
            }
        },
    }


@pytest.fixture
def engine(mock_config):
    """Create FoundationEngine instance with mock config."""
    return FoundationEngine(config=mock_config, use_database=False)


def create_test_zone(lower_bound: float, upper_bound: float) -> DetectedZone:
    """Helper to create a test zone."""
    return DetectedZone(
        zone_type=ZoneType.REJECTION,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        strength=0.8,
        touches=3,
        volume_confirmed=True,
        first_detected=datetime.now(),
        last_tested=datetime.now(),
    )


class TestGetSLConfig:
    """Test _get_sl_config() method."""

    def test_symbol_specific_config_takes_priority(self, engine):
        """Symbol-specific config should override asset class defaults."""
        config = engine._get_sl_config("XAUUSD")

        assert config["source"] == "symbol_config"
        assert config["use_zone_based"] is True
        assert config["min_sl"] == 80
        assert config["max_sl"] == 300
        assert config["default_sl"] == 150
        assert config["zone_buffer"] == 1.2

    def test_forex_symbol_config_loaded(self, engine):
        """Forex symbols should load their symbol-specific config."""
        config = engine._get_sl_config("EURUSD")

        assert config["source"] == "symbol_config"
        assert config["use_zone_based"] is False
        assert config["min_sl"] == 15
        assert config["max_sl"] == 60
        assert config["default_sl"] == 30

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_asset_class_fallback_for_unknown_symbol(self, mock_pip_calc, engine):
        """Unknown symbols should fall back to asset class config."""
        # Mock PipCalculator to return 'commodities' asset class
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance._determine_asset_class.return_value = "commodities"
        mock_pip_calc.return_value = mock_pip_calc_instance

        config = engine._get_sl_config("XAGEUR")  # Unknown symbol

        assert config["source"] == "asset_class_config"
        assert config["min_sl"] == 80.0  # From commodities config
        assert config["max_sl"] == 300.0

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_forex_asset_class_fallback(self, mock_pip_calc, engine):
        """Forex symbols without symbol config should use asset class."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance._determine_asset_class.return_value = "forex_major"
        mock_pip_calc.return_value = mock_pip_calc_instance

        config = engine._get_sl_config("NZDUSD")  # Not in symbol config

        assert config["source"] == "asset_class_config"
        assert config["min_sl"] == 15.0
        assert config["max_sl"] == 60.0


class TestCalculateZoneBasedSL:
    """Test _calculate_zone_based_sl() method."""

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_small_zone_uses_minimum_sl(self, mock_pip_calc, engine):
        """Small zones should be clamped to minimum SL."""
        # Mock PipCalculator
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1  # Gold pip size
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Create small zone: 4 pips (40 price points with 0.1 pip size)
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2004.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2002.0, direction="BUY", symbol="XAUUSD"
        )

        # Small zone (40 pips) × 1.2 = 48 pips → clamped to MIN 80 pips
        assert sl_distance_pips == 80.0
        # SL price should be entry - (80 pips × 0.1 pip size) = 2002.0 - 8.0
        assert sl_price == pytest.approx(1994.0, rel=0.01)

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_medium_zone_uses_calculated_sl(self, mock_pip_calc, engine):
        """Medium zones should use calculated SL (zone_size × buffer)."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Create medium zone: 150 pips (15.0 price points)
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2015.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2007.5, direction="BUY", symbol="XAUUSD"
        )

        # Medium zone (150 pips) × 1.2 = 180 pips (within 80-300 range)
        assert sl_distance_pips == 180.0
        # SL price = 2007.5 - 18.0
        assert sl_price == pytest.approx(1989.5, rel=0.01)

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_large_zone_uses_maximum_sl(self, mock_pip_calc, engine):
        """Large zones should be clamped to maximum SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Create large zone: 350 pips (35.0 price points)
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2035.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2017.5, direction="BUY", symbol="XAUUSD"
        )

        # Large zone (350 pips) × 1.2 = 420 pips → clamped to MAX 300 pips
        assert sl_distance_pips == 300.0
        # SL price = 2017.5 - 30.0
        assert sl_price == pytest.approx(1987.5, rel=0.01)

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_sell_direction_sl_above_entry(self, mock_pip_calc, engine):
        """SELL positions should have SL above entry price."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        zone = create_test_zone(lower_bound=2000.0, upper_bound=2015.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2007.5, direction="SELL", symbol="XAUUSD"
        )

        # SELL: SL should be ABOVE entry
        assert sl_price > 2007.5
        # Zone 150 pips × 1.2 = 180 pips above entry
        assert sl_price == pytest.approx(2025.5, rel=0.01)
        assert sl_distance_pips == 180.0

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_fixed_sl_for_forex(self, mock_pip_calc, engine):
        """Forex with zone-based disabled should use fixed default SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.0001  # Forex pip size
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Create zone (size doesn't matter for fixed SL)
        zone = create_test_zone(lower_bound=1.1000, upper_bound=1.1020)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone,
            entry_price=1.1010,
            direction="BUY",
            symbol="EURUSD",  # Forex with zone-based=false
        )

        # Should always use default 30 pips (fixed)
        assert sl_distance_pips == 30.0
        # SL price = 1.1010 - (30 × 0.0001) = 1.0980
        assert sl_price == pytest.approx(1.0980, rel=0.0001)

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_zone_buffer_multiplier_applied(self, mock_pip_calc, engine):
        """Verify zone buffer multiplier (1.2x) is applied correctly."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Zone exactly 100 pips
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2010.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2005.0, direction="BUY", symbol="XAUUSD"
        )

        # 100 pips × 1.2 buffer = 120 pips
        assert sl_distance_pips == 120.0
        assert sl_price == pytest.approx(1993.0, rel=0.01)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_zero_size_zone_uses_minimum(self, mock_pip_calc, engine):
        """Zero-size zones should use minimum SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Zero-size zone (theoretical edge case)
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2000.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2000.0, direction="BUY", symbol="XAUUSD"
        )

        # Should use minimum
        assert sl_distance_pips == 80.0

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_exact_min_sl_boundary(self, mock_pip_calc, engine):
        """Zone that calculates exactly to min SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Zone size that calculates to exactly 80 pips after buffer
        # 80 / 1.2 = 66.67 pips zone → 66.67 × 1.2 = 80.0
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2006.67)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2003.0, direction="BUY", symbol="XAUUSD"
        )

        # Should be exactly 80 pips (or very close)
        assert 79.9 <= sl_distance_pips <= 80.1

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_exact_max_sl_boundary(self, mock_pip_calc, engine):
        """Zone that calculates exactly to max SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Zone size that calculates to exactly 300 pips after buffer
        # 300 / 1.2 = 250 pips zone → 250 × 1.2 = 300.0
        zone = create_test_zone(lower_bound=2000.0, upper_bound=2025.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2012.5, direction="BUY", symbol="XAUUSD"
        )

        # Should be exactly 300 pips
        assert sl_distance_pips == 300.0


class TestIntegration:
    """Integration tests with realistic scenarios."""

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_realistic_gold_small_zone(self, mock_pip_calc, engine):
        """Realistic Gold scenario: 60 pip zone."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Realistic small zone for Gold
        zone = create_test_zone(lower_bound=2050.0, upper_bound=2056.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2053.0, direction="BUY", symbol="XAUUSD"
        )

        # 60 pips × 1.2 = 72 pips → clamped to 80 pips
        assert sl_distance_pips == 80.0
        assert 2044.0 <= sl_price <= 2046.0  # Entry 2053 - 8.0

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_realistic_gold_large_zone(self, mock_pip_calc, engine):
        """Realistic Gold scenario: 200 pip zone."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.1
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Realistic large zone for Gold
        zone = create_test_zone(lower_bound=2050.0, upper_bound=2070.0)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=2060.0, direction="BUY", symbol="XAUUSD"
        )

        # 200 pips × 1.2 = 240 pips (within range)
        assert sl_distance_pips == 240.0
        assert sl_price == pytest.approx(2036.0, rel=0.1)

    @patch("trading_worker.position.pip_calculator.PipCalculator")
    def test_realistic_eurusd_scenario(self, mock_pip_calc, engine):
        """Realistic EURUSD scenario: fixed 30 pip SL."""
        mock_pip_calc_instance = MagicMock()
        mock_pip_calc_instance.get_pip_size.return_value = 0.0001
        mock_pip_calc.return_value = mock_pip_calc_instance

        # Any zone size (doesn't matter for fixed SL)
        zone = create_test_zone(lower_bound=1.0800, upper_bound=1.0820)

        sl_price, sl_distance_pips = engine._calculate_zone_based_sl(
            zone=zone, entry_price=1.0810, direction="BUY", symbol="EURUSD"
        )

        # Always 30 pips for EURUSD
        assert sl_distance_pips == 30.0
        assert sl_price == pytest.approx(1.0780, rel=0.0001)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
