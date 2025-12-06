"""Tests for PortfolioRiskManager."""

import pytest

from trading_bot.risk.portfolio_risk_manager import PortfolioRiskManager


@pytest.fixture
def risk_manager():
    """Create a PortfolioRiskManager instance."""
    config = {
        "risk_management": {
            "max_risk_per_trade_percent": 2.0,
            "daily_loss_limit_percent": 1.0,
            "emergency_stop_percent": 15.0,
        }
    }
    return PortfolioRiskManager(config)


class TestPortfolioRiskManagerInitialization:
    """Test PortfolioRiskManager initialization."""

    def test_initialization_default(self):
        """Test initialization with default config."""
        manager = PortfolioRiskManager()
        assert manager.max_risk_per_trade_pct == 2.0
        assert manager.daily_loss_limit_pct == 1.0
        assert manager.emergency_stop_pct == 15.0

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            "risk_management": {
                "max_risk_per_trade_percent": 1.5,
                "daily_loss_limit_percent": 0.5,
                "emergency_stop_percent": 10.0,
            }
        }
        manager = PortfolioRiskManager(config)
        assert manager.max_risk_per_trade_pct == 1.5
        assert manager.daily_loss_limit_pct == 0.5
        assert manager.emergency_stop_pct == 10.0


class TestInitializeBalance:
    """Test balance initialization."""

    def test_initialize_balance(self, risk_manager):
        """Test initializing portfolio balance."""
        risk_manager.initialize_balance(10000.0)

        assert risk_manager.starting_balance == 10000.0
        assert risk_manager.current_balance == 10000.0
        assert risk_manager.peak_balance == 10000.0
        assert risk_manager.daily_start_balance == 10000.0
        assert risk_manager.daily_pnl == 0.0


class TestUpdateBalance:
    """Test balance updates."""

    def test_update_balance_profit(self, risk_manager):
        """Test updating balance with profit."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(10500.0)

        assert risk_manager.current_balance == 10500.0
        assert risk_manager.peak_balance == 10500.0
        assert risk_manager.daily_pnl == 500.0

    def test_update_balance_loss(self, risk_manager):
        """Test updating balance with loss."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9500.0)

        assert risk_manager.current_balance == 9500.0
        assert risk_manager.peak_balance == 10000.0  # Peak stays at initial
        assert risk_manager.daily_pnl == -500.0


class TestCalculateMaxRiskAmount:
    """Test max risk amount calculation."""

    def test_calculate_max_risk_amount(self, risk_manager):
        """Test calculating max risk amount (2% of balance)."""
        max_risk = risk_manager.calculate_max_risk_amount(10000.0)
        assert max_risk == pytest.approx(200.0, abs=0.01)  # 2% of 10000

    def test_calculate_max_risk_amount_different_balance(self, risk_manager):
        """Test max risk with different balance."""
        max_risk = risk_manager.calculate_max_risk_amount(50000.0)
        assert max_risk == pytest.approx(1000.0, abs=0.01)  # 2% of 50000


class TestCalculatePositionSize:
    """Test position size calculation."""

    def test_calculate_position_size_forex(self, risk_manager):
        """Test calculating position size for forex."""
        # Risk $200, SL distance 50 pips, pip value $10/lot
        position_size = risk_manager.calculate_position_size(
            account_balance=10000.0,
            risk_amount_usd=200.0,
            stop_distance_pips=50.0,
            pip_value_per_lot=10.0,
        )

        # position_size = 200 / (50 * 10) = 0.4 lots
        assert position_size == pytest.approx(0.4, abs=0.01)

    def test_calculate_position_size_different_risk(self, risk_manager):
        """Test position size with different risk amount."""
        position_size = risk_manager.calculate_position_size(
            account_balance=10000.0,
            risk_amount_usd=500.0,
            stop_distance_pips=100.0,
            pip_value_per_lot=10.0,
        )

        # position_size = 500 / (100 * 10) = 0.5 lots
        assert position_size == pytest.approx(0.5, abs=0.01)

    def test_calculate_position_size_invalid_params(self, risk_manager):
        """Test position size with invalid parameters."""
        position_size = risk_manager.calculate_position_size(
            account_balance=10000.0,
            risk_amount_usd=200.0,
            stop_distance_pips=0.0,  # Invalid
            pip_value_per_lot=10.0,
        )

        assert position_size == 0.0


class TestCanTakeTrade:
    """Test trade validation."""

    def test_can_take_trade_valid(self, risk_manager):
        """Test can take trade when all conditions met."""
        risk_manager.initialize_balance(10000.0)

        can_trade, reason = risk_manager.can_take_trade(risk_amount=200.0)

        assert can_trade is True
        assert reason == "OK"

    def test_can_take_trade_exceeds_max_risk(self, risk_manager):
        """Test cannot take trade when risk exceeds limit."""
        risk_manager.initialize_balance(10000.0)

        # Try to risk 3% (max is 2%)
        can_trade, reason = risk_manager.can_take_trade(risk_amount=300.0)

        assert can_trade is False
        assert "Risk exceeds limit" in reason

    def test_can_take_trade_daily_limit_reached(self, risk_manager):
        """Test cannot take trade when daily limit reached."""
        risk_manager.initialize_balance(10000.0)

        # Simulate daily loss of 1% ($100)
        risk_manager.update_balance(9900.0)
        risk_manager.daily_pnl = -100.0

        can_trade, reason = risk_manager.can_take_trade(risk_amount=50.0)

        assert can_trade is False
        assert "Daily loss limit" in reason

    def test_can_take_trade_emergency_stop(self, risk_manager):
        """Test cannot take trade when emergency stop triggered."""
        risk_manager.initialize_balance(10000.0)

        # Simulate 15% drawdown
        risk_manager.update_balance(8500.0)

        can_trade, reason = risk_manager.can_take_trade(risk_amount=100.0)

        assert can_trade is False
        assert "Emergency stop" in reason

    def test_can_take_trade_not_initialized(self, risk_manager):
        """Test cannot take trade when balance not initialized."""
        can_trade, reason = risk_manager.can_take_trade(risk_amount=100.0)

        assert can_trade is False
        assert "not initialized" in reason


class TestDrawdownCalculation:
    """Test drawdown calculations."""

    def test_get_drawdown_percent_no_drawdown(self, risk_manager):
        """Test drawdown when no loss."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(10500.0)  # Profit

        assert risk_manager.get_drawdown_percent() == 0.0

    def test_get_drawdown_percent_with_loss(self, risk_manager):
        """Test drawdown calculation with loss."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9000.0)  # 10% loss from peak

        assert risk_manager.get_drawdown_percent() == pytest.approx(10.0, abs=0.1)

    def test_get_drawdown_percent_from_peak(self, risk_manager):
        """Test drawdown calculated from peak, not starting balance."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(12000.0)  # New peak
        risk_manager.update_balance(10800.0)  # Down from peak

        # Drawdown should be from peak (12000), not starting (10000)
        # (12000 - 10800) / 12000 = 10%
        assert risk_manager.get_drawdown_percent() == pytest.approx(10.0, abs=0.1)


class TestEmergencyStop:
    """Test emergency stop functionality."""

    def test_is_emergency_stop_triggered_false(self, risk_manager):
        """Test emergency stop not triggered."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9000.0)  # 10% drawdown (below 15%)

        assert risk_manager.is_emergency_stop_triggered() is False

    def test_is_emergency_stop_triggered_true(self, risk_manager):
        """Test emergency stop triggered."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(8500.0)  # 15% drawdown

        assert risk_manager.is_emergency_stop_triggered() is True


class TestDailyLossLimit:
    """Test daily loss limit functionality."""

    def test_is_daily_limit_reached_false(self, risk_manager):
        """Test daily limit not reached."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9950.0)  # 0.5% daily loss (below 1%)

        assert risk_manager.is_daily_limit_reached() is False

    def test_is_daily_limit_reached_true(self, risk_manager):
        """Test daily limit reached."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9900.0)  # 1% daily loss

        assert risk_manager.is_daily_limit_reached() is True


class TestGetDailyPnlPercent:
    """Test daily P&L percentage calculation."""

    def test_get_daily_pnl_percent_profit(self, risk_manager):
        """Test daily P&L percentage with profit."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(10200.0)  # 2% profit

        assert risk_manager.get_daily_pnl_percent() == pytest.approx(2.0, abs=0.1)

    def test_get_daily_pnl_percent_loss(self, risk_manager):
        """Test daily P&L percentage with loss."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9900.0)  # 1% loss

        assert risk_manager.get_daily_pnl_percent() == pytest.approx(-1.0, abs=0.1)


class TestGetPortfolioSummary:
    """Test portfolio summary."""

    def test_get_portfolio_summary(self, risk_manager):
        """Test getting portfolio summary."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(10500.0)

        summary = risk_manager.get_portfolio_summary()

        assert summary["starting_balance"] == 10000.0
        assert summary["current_balance"] == 10500.0
        assert summary["peak_balance"] == 10500.0
        assert summary["total_pnl"] == 500.0
        assert summary["daily_pnl"] == 500.0
        assert "max_risk_per_trade" in summary
        assert "emergency_stop_triggered" in summary


class TestResetTracking:
    """Test reset functionality."""

    def test_reset_tracking(self, risk_manager):
        """Test resetting tracking."""
        risk_manager.initialize_balance(10000.0)
        risk_manager.update_balance(9900.0)
        risk_manager.daily_pnl = -100.0

        risk_manager.reset_tracking()

        assert risk_manager.daily_pnl == 0.0
        assert risk_manager.daily_start_balance == risk_manager.current_balance


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation(self, risk_manager):
        """Test string representation."""
        risk_manager.initialize_balance(10000.0)

        str_repr = str(risk_manager)
        assert "PortfolioRiskManager" in str_repr
        assert "$10,000.00" in str_repr

