"""Tests for ConservativeRiskManager."""

import pytest

from trading_bot.risk.risk_manager_conservative import (
    ConservativeRiskManager,
    RecoveryMode,
    RiskParameters,
)


@pytest.fixture
def conservative_manager():
    """Create a ConservativeRiskManager instance with default config."""
    config = {
        "risk_management": {
            "max_risk_per_trade": 0.5,
            "max_portfolio_risk": 1.5,
            "max_daily_loss": 1.0,
            "max_total_positions": 3,
            "max_positions_per_symbol": 1,
            "recovery_mode": {
                "enabled": True,
                "trigger_drawdown": 5.0,
                "reduced_risk": 0.25,
                "max_positions": 1,
                "exit_drawdown": 3.0,
            },
        }
    }
    return ConservativeRiskManager(config)


@pytest.fixture
def manager_without_recovery():
    """Create manager with recovery mode disabled."""
    config = {
        "risk_management": {
            "max_risk_per_trade": 0.5,
            "max_portfolio_risk": 1.5,
            "max_daily_loss": 1.0,
            "max_total_positions": 3,
            "max_positions_per_symbol": 1,
            "recovery_mode": {
                "enabled": False,
            },
        }
    }
    return ConservativeRiskManager(config)


class TestConservativeRiskManagerInitialization:
    """Test ConservativeRiskManager initialization."""

    def test_initialization_with_config(self, conservative_manager):
        """Test initialization with custom config."""
        assert conservative_manager.max_risk_per_trade == 0.5
        assert conservative_manager.max_portfolio_risk == 1.5
        assert conservative_manager.max_daily_loss == 1.0
        assert conservative_manager.max_total_positions == 3
        assert conservative_manager.max_positions_per_symbol == 1
        assert conservative_manager.recovery_enabled is True
        assert conservative_manager.recovery_trigger_drawdown == 5.0
        assert conservative_manager.recovery_reduced_risk == 0.25
        assert conservative_manager.recovery_max_positions == 1
        assert conservative_manager.recovery_exit_drawdown == 3.0
        assert conservative_manager.is_recovery_mode_active is False

    def test_initialization_without_config(self):
        """Test initialization with default config."""
        manager = ConservativeRiskManager()
        assert manager.max_risk_per_trade == 0.5
        assert manager.max_portfolio_risk == 1.5
        assert manager.max_daily_loss == 1.0
        assert manager.max_total_positions == 3
        assert manager.max_positions_per_symbol == 1
        assert manager.recovery_enabled is True
        assert manager.is_recovery_mode_active is False

    def test_initialization_with_empty_config(self):
        """Test initialization with empty config dict."""
        manager = ConservativeRiskManager({})
        assert manager.max_risk_per_trade == 0.5
        assert manager.max_portfolio_risk == 1.5
        assert manager.is_recovery_mode_active is False


class TestCalculatePositionSize:
    """Test position size calculation."""

    def test_calculate_position_size_normal(self, conservative_manager):
        """Test position size calculation in normal mode."""
        account = {"balance": 10000.0}
        symbol = "EURUSD"
        entry_price = 1.1000
        stop_loss = 1.0900
        pip_size = 0.0001
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Risk amount = 10000 * 0.5% = 50
        # SL distance = 100 pips
        # Position size = 50 / (100 * 10) = 0.05
        assert position_size == 0.05

    def test_calculate_position_size_recovery_mode(self, conservative_manager):
        """Test position size calculation in recovery mode."""
        conservative_manager.is_recovery_mode_active = True

        account = {"balance": 10000.0}
        symbol = "EURUSD"
        entry_price = 1.1000
        stop_loss = 1.0900
        pip_size = 0.0001
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Risk amount = 10000 * 0.25% = 25 (recovery mode)
        # SL distance = 100 pips
        # Position size = 25 / (100 * 10) = 0.025
        assert position_size == 0.02  # Rounded to 2 decimals

    def test_calculate_position_size_zero_sl_distance(self, conservative_manager):
        """Test position size when SL distance is zero (edge case)."""
        account = {"balance": 10000.0}
        symbol = "EURUSD"
        entry_price = 1.1000
        stop_loss = 1.1000  # Same as entry
        pip_size = 0.0001
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Should return minimum when sl_distance is 0
        assert position_size == 0.01

    def test_calculate_position_size_zero_pip_value(self, conservative_manager):
        """Test position size when pip value per lot is zero (edge case)."""
        account = {"balance": 10000.0}
        symbol = "EURUSD"
        entry_price = 1.1000
        stop_loss = 1.0900
        pip_size = 0.0001
        pip_value_per_lot = 0.0  # Zero pip value

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Should return minimum when pip_value_per_lot is 0
        assert position_size == 0.01

    def test_calculate_position_size_jpy_pair(self, conservative_manager):
        """Test position size calculation for JPY pair."""
        account = {"balance": 10000.0}
        symbol = "USDJPY"
        entry_price = 150.00
        stop_loss = 149.00
        pip_size = 0.01  # JPY pip size
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Risk amount = 10000 * 0.5% = 50
        # SL distance = 100 pips (150.00 - 149.00) / 0.01
        # Position size = 50 / (100 * 10) = 0.05
        assert position_size == 0.05

    def test_calculate_position_size_gold(self, conservative_manager):
        """Test position size calculation for Gold."""
        account = {"balance": 10000.0}
        symbol = "XAUUSD"
        entry_price = 2000.00
        stop_loss = 1990.00
        pip_size = 0.1  # Gold pip size
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Risk amount = 10000 * 0.5% = 50
        # SL distance = 100 pips
        # Position size = 50 / (100 * 10) = 0.05
        assert position_size == 0.05

    def test_calculate_position_size_no_balance_key(self, conservative_manager):
        """Test position size when account dict has no balance key."""
        account = {}  # No balance key (balance defaults to 0)
        symbol = "EURUSD"
        entry_price = 1.1000
        stop_loss = 1.0900
        pip_size = 0.0001
        pip_value_per_lot = 10.0

        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            pip_size=pip_size,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Should handle gracefully with balance = 0, which means 0 risk amount
        # 0 / (100 * 10) = 0.0
        assert position_size == 0.0


class TestGetActiveRiskPerTrade:
    """Test getting active risk per trade."""

    def test_get_active_risk_normal_mode(self, conservative_manager):
        """Test active risk in normal mode."""
        conservative_manager.is_recovery_mode_active = False
        assert conservative_manager.get_active_risk_per_trade() == 0.5

    def test_get_active_risk_recovery_mode(self, conservative_manager):
        """Test active risk in recovery mode."""
        conservative_manager.is_recovery_mode_active = True
        assert conservative_manager.get_active_risk_per_trade() == 0.25

    def test_get_active_risk_recovery_disabled(self, manager_without_recovery):
        """Test active risk when recovery mode disabled."""
        manager_without_recovery.is_recovery_mode_active = True
        # Should return normal risk even if recovery flag is set
        assert manager_without_recovery.get_active_risk_per_trade() == 0.5


class TestGetMaxPositions:
    """Test getting max positions."""

    def test_get_max_positions_normal_mode(self, conservative_manager):
        """Test max positions in normal mode."""
        conservative_manager.is_recovery_mode_active = False
        assert conservative_manager.get_max_positions() == 3

    def test_get_max_positions_recovery_mode(self, conservative_manager):
        """Test max positions in recovery mode."""
        conservative_manager.is_recovery_mode_active = True
        assert conservative_manager.get_max_positions() == 1

    def test_get_max_positions_recovery_disabled(self, manager_without_recovery):
        """Test max positions when recovery mode disabled."""
        manager_without_recovery.is_recovery_mode_active = True
        # Should return normal max positions even if recovery flag is set
        assert manager_without_recovery.get_max_positions() == 3


class TestShouldActivateRecoveryMode:
    """Test recovery mode activation logic."""

    def test_should_activate_at_trigger_threshold(self, conservative_manager):
        """Test activation at exactly trigger threshold."""
        # At 5% drawdown, should NOT activate (needs to be > 5%)
        assert conservative_manager.should_activate_recovery_mode(5.0) is False

    def test_should_activate_above_threshold(self, conservative_manager):
        """Test activation above trigger threshold."""
        assert conservative_manager.should_activate_recovery_mode(5.1) is True
        assert conservative_manager.should_activate_recovery_mode(6.0) is True
        assert conservative_manager.should_activate_recovery_mode(10.0) is True

    def test_should_not_activate_below_threshold(self, conservative_manager):
        """Test no activation below trigger threshold."""
        assert conservative_manager.should_activate_recovery_mode(4.9) is False
        assert conservative_manager.should_activate_recovery_mode(3.0) is False
        assert conservative_manager.should_activate_recovery_mode(0.0) is False

    def test_should_not_activate_when_disabled(self, manager_without_recovery):
        """Test no activation when recovery mode disabled."""
        # Even at high drawdown, should not activate
        assert manager_without_recovery.should_activate_recovery_mode(10.0) is False
        assert manager_without_recovery.should_activate_recovery_mode(20.0) is False


class TestActivateRecoveryMode:
    """Test recovery mode activation."""

    def test_activate_recovery_mode(self, conservative_manager):
        """Test activating recovery mode."""
        assert conservative_manager.is_recovery_mode_active is False

        conservative_manager.activate_recovery_mode()

        assert conservative_manager.is_recovery_mode_active is True

    def test_activate_recovery_mode_already_active(self, conservative_manager):
        """Test activating when already active (idempotent)."""
        conservative_manager.is_recovery_mode_active = True

        # Should not cause error when already active
        conservative_manager.activate_recovery_mode()

        assert conservative_manager.is_recovery_mode_active is True


class TestShouldExitRecoveryMode:
    """Test recovery mode exit logic."""

    def test_should_exit_at_exit_threshold(self, conservative_manager):
        """Test exit at exactly exit threshold."""
        conservative_manager.is_recovery_mode_active = True

        # At 3% drawdown, should NOT exit (needs to be < 3%)
        assert conservative_manager.should_exit_recovery_mode(3.0) is False

    def test_should_exit_below_threshold(self, conservative_manager):
        """Test exit below exit threshold."""
        conservative_manager.is_recovery_mode_active = True

        assert conservative_manager.should_exit_recovery_mode(2.9) is True
        assert conservative_manager.should_exit_recovery_mode(2.0) is True
        assert conservative_manager.should_exit_recovery_mode(0.0) is True

    def test_should_not_exit_above_threshold(self, conservative_manager):
        """Test no exit above exit threshold."""
        conservative_manager.is_recovery_mode_active = True

        assert conservative_manager.should_exit_recovery_mode(3.1) is False
        assert conservative_manager.should_exit_recovery_mode(4.0) is False
        assert conservative_manager.should_exit_recovery_mode(5.0) is False

    def test_should_not_exit_when_not_active(self, conservative_manager):
        """Test exit logic when recovery mode not active."""
        conservative_manager.is_recovery_mode_active = False

        # Should not exit when not active
        assert conservative_manager.should_exit_recovery_mode(2.0) is False
        assert conservative_manager.should_exit_recovery_mode(3.0) is False


class TestDeactivateRecoveryMode:
    """Test recovery mode deactivation."""

    def test_deactivate_recovery_mode(self, conservative_manager):
        """Test deactivating recovery mode."""
        conservative_manager.is_recovery_mode_active = True

        conservative_manager.deactivate_recovery_mode()

        assert conservative_manager.is_recovery_mode_active is False

    def test_deactivate_recovery_mode_already_inactive(self, conservative_manager):
        """Test deactivating when already inactive (idempotent)."""
        conservative_manager.is_recovery_mode_active = False

        # Should not cause error when already inactive
        conservative_manager.deactivate_recovery_mode()

        assert conservative_manager.is_recovery_mode_active is False


class TestIsEmergencyStopTriggered:
    """Test emergency stop logic."""

    def test_emergency_stop_above_threshold(self, conservative_manager):
        """Test emergency stop triggered above 15%."""
        assert conservative_manager.is_emergency_stop_triggered(15.1) is True
        assert conservative_manager.is_emergency_stop_triggered(20.0) is True

    def test_emergency_stop_at_threshold(self, conservative_manager):
        """Test emergency stop at exactly 15%."""
        assert conservative_manager.is_emergency_stop_triggered(15.0) is False

    def test_emergency_stop_below_threshold(self, conservative_manager):
        """Test no emergency stop below 15%."""
        assert conservative_manager.is_emergency_stop_triggered(14.9) is False
        assert conservative_manager.is_emergency_stop_triggered(10.0) is False
        assert conservative_manager.is_emergency_stop_triggered(0.0) is False


class TestValidateParameters:
    """Test risk parameter validation."""

    def test_validate_valid_parameters(self, conservative_manager):
        """Test validation with valid conservative parameters."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=3,
            max_positions_per_symbol=1,
        )

        assert conservative_manager.validate_parameters(params) is True

    def test_validate_max_risk_too_high(self, conservative_manager):
        """Test validation fails when risk per trade > 1%."""
        params = RiskParameters(
            max_risk_per_trade=1.5,  # Too high for conservative
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=3,
        )

        assert conservative_manager.validate_parameters(params) is False

    def test_validate_max_risk_at_limit(self, conservative_manager):
        """Test validation passes at exactly 1% risk per trade."""
        params = RiskParameters(
            max_risk_per_trade=1.0,  # At limit
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=3,
        )

        assert conservative_manager.validate_parameters(params) is True

    def test_validate_portfolio_risk_too_high(self, conservative_manager):
        """Test validation fails when portfolio risk > 2%."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=2.5,  # Too high
            max_daily_loss=1.0,
            max_total_positions=3,
        )

        assert conservative_manager.validate_parameters(params) is False

    def test_validate_portfolio_risk_at_limit(self, conservative_manager):
        """Test validation passes at exactly 2% portfolio risk."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=2.0,  # At limit
            max_daily_loss=1.0,
            max_total_positions=3,
        )

        assert conservative_manager.validate_parameters(params) is True

    def test_validate_max_positions_too_high(self, conservative_manager):
        """Test validation fails when max positions > 5."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=6,  # Too high
        )

        assert conservative_manager.validate_parameters(params) is False

    def test_validate_max_positions_at_limit(self, conservative_manager):
        """Test validation passes at exactly 5 max positions."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=5,  # At limit
        )

        assert conservative_manager.validate_parameters(params) is True

    def test_validate_all_params_too_high(self, conservative_manager):
        """Test validation fails when all params exceed limits."""
        params = RiskParameters(
            max_risk_per_trade=2.0,  # Too high
            max_portfolio_risk=3.0,  # Too high
            max_daily_loss=1.0,
            max_total_positions=10,  # Too high
        )

        assert conservative_manager.validate_parameters(params) is False


class TestCalculateDrawdown:
    """Test drawdown calculation."""

    def test_calculate_drawdown_profit(self, conservative_manager):
        """Test drawdown when in profit (negative drawdown)."""
        starting_balance = 10000.0
        current_equity = 10500.0  # 5% profit

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        # Should return 0.0 when in profit
        assert drawdown == 0.0

    def test_calculate_drawdown_break_even(self, conservative_manager):
        """Test drawdown at break even."""
        starting_balance = 10000.0
        current_equity = 10000.0

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        assert drawdown == 0.0

    def test_calculate_drawdown_loss(self, conservative_manager):
        """Test drawdown calculation with loss."""
        starting_balance = 10000.0
        current_equity = 9500.0  # 5% loss

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        assert drawdown == 5.0

    def test_calculate_drawdown_severe_loss(self, conservative_manager):
        """Test drawdown calculation with severe loss."""
        starting_balance = 10000.0
        current_equity = 8500.0  # 15% loss

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        assert drawdown == 15.0

    def test_calculate_drawdown_zero_starting_balance(self, conservative_manager):
        """Test drawdown with zero starting balance."""
        starting_balance = 0.0
        current_equity = 0.0

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        # Should return 0.0 when starting balance is 0
        assert drawdown == 0.0

    def test_calculate_drawdown_negative_starting_balance(self, conservative_manager):
        """Test drawdown with negative starting balance."""
        starting_balance = -1000.0  # Invalid
        current_equity = 0.0

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        # Should return 0.0 when starting balance is negative
        assert drawdown == 0.0

    def test_calculate_drawdown_negative_equity(self, conservative_manager):
        """Test drawdown with negative equity (debt)."""
        starting_balance = 10000.0
        current_equity = -1000.0  # In debt

        drawdown = conservative_manager.calculate_drawdown(starting_balance, current_equity)

        # Should calculate correctly: ((10000 - (-1000)) / 10000) * 100 = 110%
        # But max(0.0, drawdown) caps it at minimum 0
        # So it should be 110%, not capped (only negative values are capped)
        assert drawdown == pytest.approx(110.0)


class TestUpdateRecoveryMode:
    """Test recovery mode state updates."""

    def test_update_recovery_mode_activate(self, conservative_manager):
        """Test activating recovery mode through update."""
        assert conservative_manager.is_recovery_mode_active is False

        # Drawdown exceeds trigger threshold
        conservative_manager.update_recovery_mode(6.0)

        assert conservative_manager.is_recovery_mode_active is True

    def test_update_recovery_mode_deactivate(self, conservative_manager):
        """Test deactivating recovery mode through update."""
        conservative_manager.is_recovery_mode_active = True

        # Drawdown below exit threshold
        conservative_manager.update_recovery_mode(2.0)

        assert conservative_manager.is_recovery_mode_active is False

    def test_update_recovery_mode_no_change_normal(self, conservative_manager):
        """Test no change when drawdown in normal range."""
        conservative_manager.is_recovery_mode_active = False

        # Drawdown in normal range (3-5%)
        conservative_manager.update_recovery_mode(4.0)

        assert conservative_manager.is_recovery_mode_active is False

    def test_update_recovery_mode_no_change_recovery(self, conservative_manager):
        """Test no change when drawdown still high in recovery."""
        conservative_manager.is_recovery_mode_active = True

        # Drawdown still high (> 3%)
        conservative_manager.update_recovery_mode(4.0)

        assert conservative_manager.is_recovery_mode_active is True

    def test_update_recovery_mode_disabled(self, manager_without_recovery):
        """Test update does nothing when recovery mode disabled."""
        manager_without_recovery.is_recovery_mode_active = False

        # Even at high drawdown, should not activate
        manager_without_recovery.update_recovery_mode(10.0)

        assert manager_without_recovery.is_recovery_mode_active is False

    def test_update_recovery_mode_disabled_already_active(self, manager_without_recovery):
        """Test update when disabled but flag already set."""
        manager_without_recovery.is_recovery_mode_active = True

        # When recovery is disabled, update_recovery_mode just returns early
        # It won't deactivate automatically
        manager_without_recovery.update_recovery_mode(2.0)

        # Should still be active because update_recovery_mode exits early when disabled
        assert manager_without_recovery.is_recovery_mode_active is True


class TestGetRiskSummary:
    """Test risk summary generation."""

    def test_get_risk_summary_normal_mode(self, conservative_manager):
        """Test risk summary in normal mode."""
        summary = conservative_manager.get_risk_summary()

        assert summary["max_risk_per_trade"] == 0.5
        assert summary["max_portfolio_risk"] == 1.5
        assert summary["max_daily_loss"] == 1.0
        assert summary["max_total_positions"] == 3
        assert summary["recovery_mode_active"] is False
        assert summary["active_risk_per_trade"] == 0.5
        assert summary["active_max_positions"] == 3

    def test_get_risk_summary_recovery_mode(self, conservative_manager):
        """Test risk summary in recovery mode."""
        conservative_manager.is_recovery_mode_active = True

        summary = conservative_manager.get_risk_summary()

        assert summary["max_risk_per_trade"] == 0.5  # Original value
        assert summary["max_portfolio_risk"] == 1.5
        assert summary["recovery_mode_active"] is True
        assert summary["active_risk_per_trade"] == 0.25  # Reduced risk
        assert summary["active_max_positions"] == 1  # Reduced positions


class TestStringRepresentation:
    """Test string representations."""

    def test_str_normal_mode(self, conservative_manager):
        """Test string representation in normal mode."""
        conservative_manager.is_recovery_mode_active = False

        str_repr = str(conservative_manager)

        assert "ConservativeRiskManager" in str_repr
        assert "NORMAL" in str_repr
        assert "0.5%" in str_repr
        assert "max_pos=3" in str_repr

    def test_str_recovery_mode(self, conservative_manager):
        """Test string representation in recovery mode."""
        conservative_manager.is_recovery_mode_active = True

        str_repr = str(conservative_manager)

        assert "ConservativeRiskManager" in str_repr
        assert "RECOVERY" in str_repr
        assert "0.25%" in str_repr
        assert "max_pos=1" in str_repr

    def test_repr_same_as_str(self, conservative_manager):
        """Test repr returns same as str."""
        assert repr(conservative_manager) == str(conservative_manager)


class TestRecoveryModeDataclass:
    """Test RecoveryMode dataclass."""

    def test_recovery_mode_defaults(self):
        """Test RecoveryMode default values."""
        recovery = RecoveryMode()

        assert recovery.enabled is True
        assert recovery.trigger_drawdown == 5.0
        assert recovery.reduced_risk == 0.25
        assert recovery.max_positions == 1
        assert recovery.exit_drawdown == 3.0

    def test_recovery_mode_custom_values(self):
        """Test RecoveryMode with custom values."""
        recovery = RecoveryMode(
            enabled=False,
            trigger_drawdown=10.0,
            reduced_risk=0.1,
            max_positions=2,
            exit_drawdown=5.0,
        )

        assert recovery.enabled is False
        assert recovery.trigger_drawdown == 10.0
        assert recovery.reduced_risk == 0.1
        assert recovery.max_positions == 2
        assert recovery.exit_drawdown == 5.0


class TestRiskParametersDataclass:
    """Test RiskParameters dataclass."""

    def test_risk_parameters_defaults(self):
        """Test RiskParameters default values."""
        params = RiskParameters()

        assert params.max_risk_per_trade == 0.5
        assert params.max_portfolio_risk == 1.5
        assert params.max_daily_loss == 1.0
        assert params.max_total_positions == 3
        assert params.max_positions_per_symbol == 1

    def test_risk_parameters_custom_values(self):
        """Test RiskParameters with custom values."""
        params = RiskParameters(
            max_risk_per_trade=1.0,
            max_portfolio_risk=2.0,
            max_daily_loss=2.0,
            max_total_positions=5,
            max_positions_per_symbol=2,
        )

        assert params.max_risk_per_trade == 1.0
        assert params.max_portfolio_risk == 2.0
        assert params.max_daily_loss == 2.0
        assert params.max_total_positions == 5
        assert params.max_positions_per_symbol == 2


class TestRecoveryModeTransitions:
    """Test recovery mode state transitions."""

    def test_full_recovery_cycle(self, conservative_manager):
        """Test complete recovery mode cycle."""
        # Start in normal mode
        assert conservative_manager.is_recovery_mode_active is False
        assert conservative_manager.get_active_risk_per_trade() == 0.5
        assert conservative_manager.get_max_positions() == 3

        # Drawdown increases to 6% - should activate
        conservative_manager.update_recovery_mode(6.0)
        assert conservative_manager.is_recovery_mode_active is True
        assert conservative_manager.get_active_risk_per_trade() == 0.25
        assert conservative_manager.get_max_positions() == 1

        # Drawdown decreases to 2% - should deactivate
        conservative_manager.update_recovery_mode(2.0)
        assert conservative_manager.is_recovery_mode_active is False
        assert conservative_manager.get_active_risk_per_trade() == 0.5
        assert conservative_manager.get_max_positions() == 3

    def test_recovery_mode_persistence(self, conservative_manager):
        """Test recovery mode stays active until exit threshold."""
        conservative_manager.update_recovery_mode(6.0)
        assert conservative_manager.is_recovery_mode_active is True

        # Drawdown at 4% (still above exit threshold of 3%)
        conservative_manager.update_recovery_mode(4.0)
        assert conservative_manager.is_recovery_mode_active is True

        # Drawdown at 3.1% (still above exit threshold)
        conservative_manager.update_recovery_mode(3.1)
        assert conservative_manager.is_recovery_mode_active is True

        # Drawdown at 2.9% (below exit threshold)
        conservative_manager.update_recovery_mode(2.9)
        assert conservative_manager.is_recovery_mode_active is False


class TestPositionSizeEdgeCases:
    """Test edge cases in position size calculation."""

    def test_very_wide_stop_loss(self, conservative_manager):
        """Test position size with very wide stop loss."""
        account = {"balance": 10000.0}
        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0000,  # 1000 pip stop
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )

        # Risk amount = 50, SL distance = 1000 pips
        # Position size = 50 / (1000 * 10) = 0.005 -> rounded to 0.0
        assert position_size == 0.0

    def test_very_tight_stop_loss(self, conservative_manager):
        """Test position size with very tight stop loss."""
        account = {"balance": 10000.0}
        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0990,  # 10 pip stop
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )

        # Risk amount = 50, SL distance = 10 pips
        # Position size = 50 / (10 * 10) = 0.5
        assert position_size == 0.5

    def test_large_account_balance(self, conservative_manager):
        """Test position size with large account balance."""
        account = {"balance": 100000.0}  # 100k account
        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0900,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )

        # Risk amount = 100000 * 0.5% = 500
        # SL distance = 100 pips
        # Position size = 500 / (100 * 10) = 0.5
        assert position_size == 0.5

    def test_small_account_balance(self, conservative_manager):
        """Test position size with small account balance."""
        account = {"balance": 1000.0}  # 1k account
        position_size = conservative_manager.calculate_position_size(
            account=account,
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0900,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )

        # Risk amount = 1000 * 0.5% = 5
        # SL distance = 100 pips
        # Position size = 5 / (100 * 10) = 0.005 -> rounded to 0.0
        assert position_size == 0.0
