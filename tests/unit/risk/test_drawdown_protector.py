"""Tests for DrawdownProtector."""

import pytest

from trading_bot.risk.drawdown_protector import DrawdownProtector


@pytest.fixture
def drawdown_protector():
    """Create a DrawdownProtector instance."""
    config = {
        "risk_management": {
            "drawdown_warning_percent": 10.0,
            "drawdown_emergency_percent": 15.0,
        }
    }
    return DrawdownProtector(config)


class TestDrawdownProtectorInitialization:
    """Test DrawdownProtector initialization."""

    def test_initialization_default(self):
        """Test initialization with default config."""
        protector = DrawdownProtector()
        assert protector.warning_threshold_pct == 10.0
        assert protector.emergency_threshold_pct == 15.0

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            "risk_management": {
                "drawdown_warning_percent": 8.0,
                "drawdown_emergency_percent": 12.0,
            }
        }
        protector = DrawdownProtector(config)
        assert protector.warning_threshold_pct == 8.0
        assert protector.emergency_threshold_pct == 12.0


class TestInitializeBalance:
    """Test balance initialization."""

    def test_initialize_balance(self, drawdown_protector):
        """Test initializing balance."""
        drawdown_protector.initialize_balance(10000.0)

        assert drawdown_protector.starting_balance == 10000.0
        assert drawdown_protector.current_balance == 10000.0
        assert drawdown_protector.peak_balance == 10000.0
        assert drawdown_protector.warning_triggered is False
        assert drawdown_protector.emergency_triggered is False


class TestUpdateBalance:
    """Test balance updates and triggers."""

    def test_update_balance_no_drawdown(self, drawdown_protector):
        """Test updating balance with profit (no drawdown)."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(10500.0)

        assert drawdown_protector.current_balance == 10500.0
        assert drawdown_protector.peak_balance == 10500.0
        assert drawdown_protector.warning_triggered is False
        assert drawdown_protector.emergency_triggered is False

    def test_update_balance_triggers_warning(self, drawdown_protector):
        """Test balance update triggers warning (10% drawdown)."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)  # 10% drawdown

        assert drawdown_protector.warning_triggered is True
        assert drawdown_protector.warning_timestamp is not None
        assert drawdown_protector.emergency_triggered is False

    def test_update_balance_triggers_emergency(self, drawdown_protector):
        """Test balance update triggers emergency (15% drawdown)."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(8500.0)  # 15% drawdown

        assert drawdown_protector.emergency_triggered is True
        assert drawdown_protector.emergency_timestamp is not None

    def test_update_balance_recovery_resets_warning(self, drawdown_protector):
        """Test balance recovery resets warning."""
        drawdown_protector.initialize_balance(10000.0)

        # Trigger warning
        drawdown_protector.update_balance(9000.0)
        assert drawdown_protector.warning_triggered is True

        # Recover to new peak
        drawdown_protector.update_balance(10500.0)
        assert drawdown_protector.warning_triggered is False


class TestGetDrawdownPercent:
    """Test drawdown percentage calculation."""

    def test_get_drawdown_percent_no_loss(self, drawdown_protector):
        """Test drawdown with no loss."""
        drawdown_protector.initialize_balance(10000.0)

        assert drawdown_protector.get_drawdown_percent() == 0.0

    def test_get_drawdown_percent_with_loss(self, drawdown_protector):
        """Test drawdown with 10% loss."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)

        assert drawdown_protector.get_drawdown_percent() == pytest.approx(10.0, abs=0.1)

    def test_get_drawdown_percent_from_peak(self, drawdown_protector):
        """Test drawdown calculated from peak."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(12000.0)  # New peak
        drawdown_protector.update_balance(10800.0)  # Down from peak

        # (12000 - 10800) / 12000 = 10%
        assert drawdown_protector.get_drawdown_percent() == pytest.approx(10.0, abs=0.1)


class TestGetDrawdownAmount:
    """Test drawdown amount calculation."""

    def test_get_drawdown_amount(self, drawdown_protector):
        """Test getting drawdown amount in USD."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)

        assert drawdown_protector.get_drawdown_amount() == pytest.approx(1000.0, abs=0.01)


class TestIsWarningTriggered:
    """Test warning trigger status."""

    def test_is_warning_triggered_false(self, drawdown_protector):
        """Test warning not triggered."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9500.0)  # 5% drawdown

        assert drawdown_protector.is_warning_triggered() is False

    def test_is_warning_triggered_true(self, drawdown_protector):
        """Test warning triggered."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)  # 10% drawdown

        assert drawdown_protector.is_warning_triggered() is True


class TestIsEmergencyTriggered:
    """Test emergency trigger status."""

    def test_is_emergency_triggered_false(self, drawdown_protector):
        """Test emergency not triggered."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)  # 10% drawdown

        assert drawdown_protector.is_emergency_triggered() is False

    def test_is_emergency_triggered_true(self, drawdown_protector):
        """Test emergency triggered."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(8500.0)  # 15% drawdown

        assert drawdown_protector.is_emergency_triggered() is True


class TestShouldCloseAllPositions:
    """Test position closure recommendation."""

    def test_should_close_all_positions_false(self, drawdown_protector):
        """Test should not close all positions."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)  # 10% drawdown (warning only)

        assert drawdown_protector.should_close_all_positions() is False

    def test_should_close_all_positions_true(self, drawdown_protector):
        """Test should close all positions."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(8500.0)  # 15% drawdown (emergency)

        assert drawdown_protector.should_close_all_positions() is True


class TestGetDrawdownStatus:
    """Test drawdown status reporting."""

    def test_get_drawdown_status(self, drawdown_protector):
        """Test getting drawdown status."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)

        status = drawdown_protector.get_drawdown_status()

        assert status["peak_balance"] == 10000.0
        assert status["current_balance"] == 9000.0
        assert status["drawdown_pct"] == pytest.approx(10.0, abs=0.1)
        assert status["drawdown_amount"] == pytest.approx(1000.0, abs=0.01)
        assert status["warning_triggered"] is True
        assert status["emergency_triggered"] is False


class TestResetProtector:
    """Test reset functionality."""

    def test_reset_protector(self, drawdown_protector):
        """Test resetting protector state."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)  # Trigger warning

        drawdown_protector.reset_protector()

        assert drawdown_protector.warning_triggered is False
        assert drawdown_protector.emergency_triggered is False
        assert drawdown_protector.warning_timestamp is None


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation_ok(self, drawdown_protector):
        """Test string representation when OK."""
        drawdown_protector.initialize_balance(10000.0)

        str_repr = str(drawdown_protector)
        assert "DrawdownProtector" in str_repr
        assert "OK" in str_repr

    def test_string_representation_warning(self, drawdown_protector):
        """Test string representation when warning."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(9000.0)

        str_repr = str(drawdown_protector)
        assert "WARNING" in str_repr

    def test_string_representation_emergency(self, drawdown_protector):
        """Test string representation when emergency."""
        drawdown_protector.initialize_balance(10000.0)
        drawdown_protector.update_balance(8500.0)

        str_repr = str(drawdown_protector)
        assert "EMERGENCY" in str_repr
