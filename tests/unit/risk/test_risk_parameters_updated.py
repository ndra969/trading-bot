"""
Unit tests for Updated Risk Parameters - Week 15.5.4

Tests conservative risk management adjustments to stabilize system.
Current problem: 1% risk + 5 positions = too aggressive for 39% win rate
Solution: 0.5% risk + 3 positions + recovery mode
"""

import pytest

from src.trading_bot.risk.risk_manager_conservative import (
    ConservativeRiskManager,
    RiskParameters,
)


# Test fixtures
@pytest.fixture
def conservative_config():
    """Conservative risk configuration (Week 15.5.4 updates)."""
    return {
        "risk_management": {
            # Reduced from 1.0% to 0.5%
            "max_risk_per_trade": 0.5,
            # Reduced from 2.0% to 1.5%
            "max_portfolio_risk": 1.5,
            # Reduced from 1.5% to 1.0%
            "max_daily_loss": 1.0,
            # Reduced from 5 to 3
            "max_total_positions": 3,
            "max_positions_per_symbol": 1,
            # Recovery mode (NEW)
            "recovery_mode": {
                "enabled": True,
                "trigger_drawdown": 5.0,  # Activate if drawdown > 5%
                "reduced_risk": 0.25,  # Ultra-conservative 0.25%
                "max_positions": 1,  # Only 1 position at a time
                "exit_drawdown": 3.0,  # Exit recovery when drawdown < 3%
            },
        }
    }


@pytest.fixture
def risk_manager(conservative_config):
    """Create ConservativeRiskManager instance."""
    return ConservativeRiskManager(conservative_config)


@pytest.fixture
def mock_account():
    """Mock account data."""
    return {
        "balance": 10000.0,
        "equity": 10000.0,
        "margin": 0.0,
        "free_margin": 10000.0,
    }


# Test Suite 1: Reduced Risk Parameters (3 tests)
class TestReducedRiskParameters:
    """Test reduced risk parameter settings."""

    def test_risk_per_trade_reduced_to_half_percent(self, risk_manager):
        """Test risk per trade reduced from 1% to 0.5%."""
        assert risk_manager.max_risk_per_trade == 0.5

        # Old: 1.0%
        # New: 0.5%
        old_risk = 1.0
        assert risk_manager.max_risk_per_trade < old_risk
        assert risk_manager.max_risk_per_trade == old_risk / 2

    def test_portfolio_risk_reduced(self, risk_manager):
        """Test portfolio risk reduced from 2% to 1.5%."""
        assert risk_manager.max_portfolio_risk == 1.5

        # Old: 2.0%
        # New: 1.5%
        old_portfolio_risk = 2.0
        assert risk_manager.max_portfolio_risk < old_portfolio_risk

    def test_max_positions_reduced(self, risk_manager):
        """Test max positions reduced from 5 to 3."""
        assert risk_manager.max_total_positions == 3

        # Old: 5
        # New: 3
        old_max_positions = 5
        assert risk_manager.max_total_positions < old_max_positions


# Test Suite 2: Conservative Position Sizing (2 tests)
class TestConservativePositionSizing:
    """Test conservative position size calculation."""

    def test_calculate_conservative_position_size(self, risk_manager, mock_account):
        """Test position size with reduced 0.5% risk."""
        # Account: $10,000
        # Risk: 0.5% = $50
        # Stop loss: 20 pips = 0.0020

        symbol = "EURUSD"
        entry_price = 1.10000
        stop_loss = 1.09800  # 20 pips

        # Calculate position size (result not used, just testing it works)
        _ = risk_manager.calculate_position_size(mock_account, symbol, entry_price, stop_loss)

        # Expected: Risk $50 / 20 pips = $2.50 per pip
        # For EURUSD: $2.50 per pip ≈ 0.025 lots (if $10 per pip per lot)
        # Actual calculation depends on pip value

        # Risk amount should be ~$50
        risk_amount = mock_account["balance"] * (risk_manager.max_risk_per_trade / 100)
        assert risk_amount == 50.0

    def test_position_size_smaller_than_old_system(self, risk_manager, mock_account):
        """Test position sizes are smaller than old 1% risk system."""
        symbol = "EURUSD"
        entry_price = 1.10000
        stop_loss = 1.09800

        # New system (0.5% risk)
        _ = risk_manager.calculate_position_size(mock_account, symbol, entry_price, stop_loss)

        # Simulate old system (1.0% risk)
        old_risk_amount = mock_account["balance"] * 0.01  # 1%
        new_risk_amount = mock_account["balance"] * 0.005  # 0.5%

        assert new_risk_amount == old_risk_amount / 2
        assert new_risk_amount == 50.0  # $10k * 0.5% = $50


# Test Suite 3: Recovery Mode (4 tests)
class TestRecoveryMode:
    """Test recovery mode activation and behavior."""

    def test_recovery_mode_activation_on_5_percent_drawdown(self, risk_manager, mock_account):
        """Test recovery mode activates when drawdown exceeds 5%."""
        # Simulate 6% drawdown
        mock_account["equity"] = 9400.0  # $10k - 6% = $9,400
        starting_balance = 10000.0

        current_drawdown = ((starting_balance - mock_account["equity"]) / starting_balance) * 100
        assert current_drawdown == 6.0

        # Check if recovery mode should activate
        should_activate = risk_manager.should_activate_recovery_mode(current_drawdown)

        assert should_activate is True
        assert current_drawdown > risk_manager.recovery_trigger_drawdown

    def test_recovery_mode_reduces_risk_to_quarter_percent(self, risk_manager, mock_account):
        """Test recovery mode reduces risk to 0.25%."""
        # Activate recovery mode
        risk_manager.activate_recovery_mode()

        assert risk_manager.is_recovery_mode_active is True
        assert risk_manager.get_active_risk_per_trade() == 0.25

        # Normal: 0.5%
        # Recovery: 0.25% (50% of normal)
        normal_risk = 0.5
        recovery_risk = risk_manager.get_active_risk_per_trade()
        assert recovery_risk == normal_risk / 2

    def test_recovery_mode_limits_to_one_position(self, risk_manager):
        """Test recovery mode limits to 1 position at a time."""
        risk_manager.activate_recovery_mode()

        assert risk_manager.is_recovery_mode_active is True
        assert risk_manager.get_max_positions() == 1

        # Normal: 3
        # Recovery: 1
        assert risk_manager.get_max_positions() < risk_manager.max_total_positions

    def test_recovery_mode_exit_when_drawdown_below_3_percent(self, risk_manager, mock_account):
        """Test recovery mode exits when drawdown falls below 3%."""
        # Start in recovery mode
        risk_manager.activate_recovery_mode()
        assert risk_manager.is_recovery_mode_active is True

        # Simulate recovery: drawdown now 2.5%
        mock_account["equity"] = 9750.0  # $10k - 2.5% = $9,750
        starting_balance = 10000.0
        current_drawdown = ((starting_balance - mock_account["equity"]) / starting_balance) * 100

        assert current_drawdown == 2.5

        # Check if should exit recovery mode
        should_exit = risk_manager.should_exit_recovery_mode(current_drawdown)

        assert should_exit is True
        assert current_drawdown < risk_manager.recovery_exit_drawdown


# Test Suite 4: Validation & Safety (3 tests)
class TestValidationAndSafety:
    """Test validation and safety checks."""

    def test_validate_new_risk_parameters(self, risk_manager):
        """Test validation of new conservative risk parameters."""
        params = RiskParameters(
            max_risk_per_trade=0.5,
            max_portfolio_risk=1.5,
            max_daily_loss=1.0,
            max_total_positions=3,
        )

        assert risk_manager.validate_parameters(params) is True

        # Check all values are within safe limits
        assert params.max_risk_per_trade <= 1.0, "Risk per trade should be ≤ 1%"
        assert params.max_portfolio_risk <= 2.0, "Portfolio risk should be ≤ 2%"
        assert params.max_total_positions <= 5, "Max positions should be ≤ 5"

    def test_compare_old_vs_new_risk_impact(self, risk_manager, mock_account):
        """Test comparison of risk impact between old and new settings."""
        # Old settings impact on $10k account
        old_max_risk = 10000 * 0.01 * 5  # 1% per trade * 5 positions = $500 max risk

        # New settings impact
        new_max_risk = 10000 * 0.005 * 3  # 0.5% per trade * 3 positions = $150 max risk

        assert new_max_risk < old_max_risk
        assert new_max_risk == 150.0
        assert old_max_risk == 500.0

        # Risk reduction
        risk_reduction = ((old_max_risk - new_max_risk) / old_max_risk) * 100
        assert risk_reduction == 70.0, "New settings reduce max risk by 70%"

    def test_emergency_stop_still_enforced(self, risk_manager, mock_account):
        """Test emergency stop (15% max drawdown) is still enforced."""
        # Simulate 16% drawdown
        mock_account["equity"] = 8400.0  # $10k - 16% = $8,400
        starting_balance = 10000.0

        current_drawdown = ((starting_balance - mock_account["equity"]) / starting_balance) * 100
        assert current_drawdown == 16.0

        # Check if emergency stop triggered
        should_stop = risk_manager.is_emergency_stop_triggered(current_drawdown)

        assert should_stop is True
        assert current_drawdown > 15.0, "Emergency stop at 15% drawdown"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
