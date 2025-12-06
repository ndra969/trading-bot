"""Tests for ExposureManager."""

import pytest

from trading_bot.risk.exposure_manager import ExposureManager


@pytest.fixture
def exposure_manager():
    """Create an ExposureManager instance."""
    config = {
        "risk_management": {
            "max_positions_per_symbol": 1,
            "max_total_positions": 10,
            "max_leverage": 10.0,
        }
    }
    return ExposureManager(config)


class TestExposureManagerInitialization:
    """Test ExposureManager initialization."""

    def test_initialization_default(self):
        """Test initialization with default config."""
        manager = ExposureManager()
        assert manager.max_positions_per_symbol == 1
        assert manager.max_total_positions == 10

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            "risk_management": {
                "max_positions_per_symbol": 2,
                "max_total_positions": 20,
            }
        }
        manager = ExposureManager(config)
        assert manager.max_positions_per_symbol == 2
        assert manager.max_total_positions == 20


class TestCanOpenPosition:
    """Test position opening validation."""

    def test_can_open_position_valid(self, exposure_manager):
        """Test can open position when all conditions met."""
        can_open, reason = exposure_manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0
        )

        assert can_open is True
        assert reason == "OK"

    def test_can_open_position_symbol_limit_reached(self, exposure_manager):
        """Test cannot open when symbol limit reached."""
        # Register first position
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)

        # Try to open second position for same symbol
        can_open, reason = exposure_manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0
        )

        assert can_open is False
        assert "Symbol limit reached" in reason

    def test_can_open_position_total_limit_reached(self, exposure_manager):
        """Test cannot open when total position limit reached."""
        # Register 10 positions (max limit)
        for i in range(10):
            exposure_manager.register_position(f"SYMBOL{i}", "forex_major", 1.0)

        # Try to open 11th position
        can_open, reason = exposure_manager.can_open_position(
            symbol="NEWSY", asset_class="forex_major", risk_amount=200.0
        )

        assert can_open is False
        assert "Total position limit" in reason


class TestRegisterPosition:
    """Test position registration."""

    def test_register_position(self, exposure_manager):
        """Test registering a position."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)

        assert exposure_manager.get_symbol_position_count("EURUSD") == 1
        assert exposure_manager.get_total_position_count() == 1
        assert exposure_manager.get_asset_class_exposure("forex_major") == 1

    def test_register_multiple_positions(self, exposure_manager):
        """Test registering multiple positions."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        exposure_manager.register_position("GBPUSD", "forex_major", 1.0)
        exposure_manager.register_position("USDJPY", "forex_jpy", 1.0)

        assert exposure_manager.get_total_position_count() == 3
        assert exposure_manager.get_asset_class_exposure("forex_major") == 2
        assert exposure_manager.get_asset_class_exposure("forex_jpy") == 1

    def test_register_position_with_currency_exposure(self, exposure_manager):
        """Test registering position tracks currency exposure."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0, currency_pair="EUR/USD")

        assert exposure_manager.get_currency_exposure("EUR") == 1.0
        assert exposure_manager.get_currency_exposure("USD") == -1.0


class TestUnregisterPosition:
    """Test position unregistration."""

    def test_unregister_position(self, exposure_manager):
        """Test unregistering a position."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        exposure_manager.unregister_position("EURUSD", "forex_major", 1.0)

        assert exposure_manager.get_symbol_position_count("EURUSD") == 0
        assert exposure_manager.get_total_position_count() == 0

    def test_unregister_position_with_currency_exposure(self, exposure_manager):
        """Test unregistering position updates currency exposure."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0, currency_pair="EUR/USD")
        exposure_manager.unregister_position("EURUSD", "forex_major", 1.0, currency_pair="EUR/USD")

        assert exposure_manager.get_currency_exposure("EUR") == 0.0
        assert exposure_manager.get_currency_exposure("USD") == 0.0


class TestGetExposureCounts:
    """Test exposure counting methods."""

    def test_get_symbol_position_count(self, exposure_manager):
        """Test getting position count for symbol."""
        assert exposure_manager.get_symbol_position_count("EURUSD") == 0

        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        assert exposure_manager.get_symbol_position_count("EURUSD") == 1

    def test_get_asset_class_exposure(self, exposure_manager):
        """Test getting asset class exposure."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        exposure_manager.register_position("GBPUSD", "forex_major", 1.0)
        exposure_manager.register_position("XAUUSD", "commodities", 1.0)

        assert exposure_manager.get_asset_class_exposure("forex_major") == 2
        assert exposure_manager.get_asset_class_exposure("commodities") == 1


class TestGetExposureSummary:
    """Test exposure summary."""

    def test_get_exposure_summary(self, exposure_manager):
        """Test getting exposure summary."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        exposure_manager.register_position("GBPUSD", "forex_major", 1.0)

        summary = exposure_manager.get_exposure_summary()

        assert summary["total_positions"] == 2
        assert "EURUSD" in summary["positions_by_symbol"]
        assert "forex_major" in summary["positions_by_asset_class"]


class TestResetTracking:
    """Test reset functionality."""

    def test_reset_tracking(self, exposure_manager):
        """Test resetting tracking."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)
        exposure_manager.reset_tracking()

        assert exposure_manager.get_total_position_count() == 0


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation(self, exposure_manager):
        """Test string representation."""
        exposure_manager.register_position("EURUSD", "forex_major", 1.0)

        str_repr = str(exposure_manager)
        assert "ExposureManager" in str_repr
        assert "1 positions" in str_repr

