"""Tests for TrailingStopManager."""

import pytest

from trading_bot.position.automation.trailing_stop_manager import TrailingStopManager
from trading_bot.position.position_models import Position, PositionStatus, PositionType


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "trade_management": {
            "defaults": {
                "trailing_stop": {"enabled": True, "activation_pips": 20.0, "limit_pips": 10.0}
            },
            "overrides": {
                "forex_jpy": {"trailing_stop": {"activation_pips": 100.0, "limit_pips": 20.0}},
                "commodities": {"trailing_stop": {"activation_pips": 500.0, "limit_pips": 50.0}},
                "crypto": {"trailing_stop": {"activation_pips": 1000.0, "limit_pips": 300.0}},
            },
        }
    }


@pytest.fixture
def trailing_manager(mock_config):
    """Create a TrailingStopManager instance."""
    return TrailingStopManager(config=mock_config)


@pytest.fixture
def buy_position_forex():
    """Create a BUY position for forex major."""
    position = Position(
        position_id="pos_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
    )
    position.current_price = 1.1000
    position.current_profit_pips = 0.0
    return position


class TestTrailingStopManagerInitialization:
    """Test TrailingStopManager initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        manager = TrailingStopManager()
        assert manager.pip_calculator is not None
        assert len(manager.trailing_active) == 0
        assert len(manager.highest_profit) == 0


class TestShouldActivateTrailing:
    """Test should_activate_trailing method."""

    def test_should_activate_forex_threshold_hit(self, trailing_manager, buy_position_forex):
        """Test trailing should activate when threshold hit."""
        # Config threshold is 20.0 pips
        buy_position_forex.current_price = 1.1020
        buy_position_forex.current_profit_pips = 20.0

        assert trailing_manager.should_activate_trailing(buy_position_forex) is True

    def test_should_activate_forex_threshold_not_hit(self, trailing_manager, buy_position_forex):
        """Test trailing should not activate when threshold not hit."""
        # Config threshold is 20.0 pips
        buy_position_forex.current_price = 1.1015
        buy_position_forex.current_profit_pips = 15.0

        assert trailing_manager.should_activate_trailing(buy_position_forex) is False

    def test_should_activate_already_active(self, trailing_manager, buy_position_forex):
        """Test trailing should not activate if already active."""
        buy_position_forex.current_profit_pips = 25.0
        trailing_manager.trailing_active.add(buy_position_forex.position_id)

        assert trailing_manager.should_activate_trailing(buy_position_forex) is False


class TestActivateTrailing:
    """Test activate_trailing method."""

    def test_activate_trailing(self, trailing_manager, buy_position_forex):
        """Test activating trailing stop."""
        buy_position_forex.current_profit_pips = 25.0

        trailing_manager.activate_trailing(buy_position_forex)

        assert buy_position_forex.position_id in trailing_manager.trailing_active
        assert trailing_manager.highest_profit[buy_position_forex.position_id] == 25.0


class TestShouldUpdateTrailingStop:
    """Test should_update_trailing_stop method."""

    def test_should_update_profit_increased(self, trailing_manager, buy_position_forex):
        """Test trailing should update when profit increases."""
        # Activate trailing at 25 pips
        buy_position_forex.current_profit_pips = 25.0
        trailing_manager.activate_trailing(buy_position_forex)

        # Profit increases to 30 pips
        buy_position_forex.current_profit_pips = 30.0

        assert trailing_manager.should_update_trailing_stop(buy_position_forex) is True

    def test_should_update_profit_not_increased(self, trailing_manager, buy_position_forex):
        """Test trailing should not update when profit hasn't increased."""
        buy_position_forex.current_profit_pips = 25.0
        trailing_manager.activate_trailing(buy_position_forex)

        # Profit decreases (not increased)
        buy_position_forex.current_profit_pips = 20.0

        assert trailing_manager.should_update_trailing_stop(buy_position_forex) is False

    def test_should_update_not_active(self, trailing_manager, buy_position_forex):
        """Test trailing should not update if not active."""
        buy_position_forex.current_profit_pips = 30.0

        assert trailing_manager.should_update_trailing_stop(buy_position_forex) is False


class TestUpdateTrailingStop:
    """Test update_trailing_stop method."""

    def test_update_trailing_stop_buy_forex(self, trailing_manager, buy_position_forex):
        """Test updating trailing stop for BUY forex position."""
        # Activate at 25 pips
        buy_position_forex.current_profit_pips = 25.0
        trailing_manager.activate_trailing(buy_position_forex)

        # Move to 30 pips profit
        buy_position_forex.current_price = 1.1030
        buy_position_forex.current_profit_pips = 30.0

        new_sl = trailing_manager.update_trailing_stop(buy_position_forex)

        # New SL should be current price - trailing distance (10 pips)
        expected_sl = 1.1030 - (10 * 0.0001)  # 1.1020
        assert new_sl == pytest.approx(expected_sl, abs=0.00001)
        assert buy_position_forex.stop_loss == pytest.approx(expected_sl, abs=0.00001)

    def test_update_trailing_stop_sell_forex(self, trailing_manager):
        """Test updating trailing stop for SELL forex position."""
        position = Position(
            position_id="pos_002",
            symbol="GBPUSD",
            position_type=PositionType.SELL,
            entry_price=1.2500,
            stop_loss=1.2550,
            take_profit=1.2350,
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )

        # Activate at 25 pips profit
        position.current_price = 1.2475
        position.current_profit_pips = 25.0
        trailing_manager.activate_trailing(position)

        # Move to 30 pips profit
        position.current_price = 1.2470
        position.current_profit_pips = 30.0

        new_sl = trailing_manager.update_trailing_stop(position)

        # New SL should be current price + trailing distance (10 pips)
        expected_sl = 1.2470 + (10 * 0.0001)  # 1.2480
        assert new_sl == pytest.approx(expected_sl, abs=0.00001)

    def test_update_trailing_stop_never_moves_against(self, trailing_manager, buy_position_forex):
        """Test trailing stop never moves against position (only tightens)."""
        # Activate and set initial trailing
        buy_position_forex.current_price = 1.1030
        buy_position_forex.current_profit_pips = 30.0
        buy_position_forex.stop_loss = 1.1020  # Already trailed
        trailing_manager.activate_trailing(buy_position_forex)
        trailing_manager.highest_profit[buy_position_forex.position_id] = 30.0

        # Price retraces slightly
        buy_position_forex.current_price = 1.1025
        buy_position_forex.current_profit_pips = 25.0

        # Try to update (should not move SL down)
        new_sl = trailing_manager.update_trailing_stop(buy_position_forex)

        # SL should remain at previous level (not move down)
        assert new_sl == 1.1020  # Stays at old SL

    def test_update_trailing_stop_not_active_raises_error(
        self, trailing_manager, buy_position_forex
    ):
        """Test updating trailing when not active raises error."""
        with pytest.raises(ValueError, match="Trailing not active"):
            trailing_manager.update_trailing_stop(buy_position_forex)


class TestIsTrailingActive:
    """Test is_trailing_active method."""

    def test_is_trailing_active_true(self, trailing_manager, buy_position_forex):
        """Test trailing is active."""
        trailing_manager.trailing_active.add(buy_position_forex.position_id)
        assert trailing_manager.is_trailing_active(buy_position_forex.position_id) is True

    def test_is_trailing_active_false(self, trailing_manager, buy_position_forex):
        """Test trailing is not active."""
        assert trailing_manager.is_trailing_active(buy_position_forex.position_id) is False


class TestGetTrailingParameters:
    """Test get trailing parameters methods."""

    def test_get_trailing_distance_forex(self, trailing_manager):
        """Test get trailing distance for forex."""
        distance = trailing_manager.get_trailing_distance("EURUSD")
        assert distance == 10.0

    def test_get_trailing_distance_jpy(self, trailing_manager):
        """Test get trailing distance for JPY pair."""
        distance = trailing_manager.get_trailing_distance("USDJPY")
        assert distance == 20.0

    def test_get_activation_threshold_forex(self, trailing_manager):
        """Test get activation threshold for forex."""
        threshold = trailing_manager.get_activation_threshold("EURUSD")
        assert threshold == 20.0  # From mock config

    def test_get_activation_threshold_dynamic_is_deprecated(
        self, trailing_manager, buy_position_forex
    ):
        """Test dynamic activation is no longer used, returns static config."""
        # Previous logic used TP distance, new logic uses straightforward config
        threshold = trailing_manager.get_activation_threshold("EURUSD", buy_position_forex)
        assert threshold == 20.0

    def test_get_activation_threshold_jpy(self, trailing_manager):
        """Test get activation threshold for JPY pair."""
        threshold = trailing_manager.get_activation_threshold("USDJPY")
        assert threshold == 100.0  # From mock config override


class TestGetHighestProfit:
    """Test get_highest_profit method."""

    def test_get_highest_profit(self, trailing_manager, buy_position_forex):
        """Test getting highest profit."""
        trailing_manager.highest_profit[buy_position_forex.position_id] = 35.0

        assert trailing_manager.get_highest_profit(buy_position_forex.position_id) == 35.0

    def test_get_highest_profit_not_tracked(self, trailing_manager, buy_position_forex):
        """Test getting highest profit for untracked position."""
        assert trailing_manager.get_highest_profit(buy_position_forex.position_id) == 0.0


class TestResetPosition:
    """Test reset_position method."""

    def test_reset_position(self, trailing_manager, buy_position_forex):
        """Test resetting position trailing tracking."""
        trailing_manager.trailing_active.add(buy_position_forex.position_id)
        trailing_manager.highest_profit[buy_position_forex.position_id] = 30.0

        trailing_manager.reset_position(buy_position_forex.position_id)

        assert buy_position_forex.position_id not in trailing_manager.trailing_active
        assert buy_position_forex.position_id not in trailing_manager.highest_profit


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_trailing_positions_count(self, trailing_manager, buy_position_forex):
        """Test getting trailing positions count."""
        assert trailing_manager.get_trailing_positions_count() == 0

        trailing_manager.trailing_active.add(buy_position_forex.position_id)
        assert trailing_manager.get_trailing_positions_count() == 1

    def test_string_representation(self, trailing_manager):
        """Test string representation."""
        str_repr = str(trailing_manager)
        assert "TrailingStopManager" in str_repr
        assert "0 positions trailing" in str_repr

    def test_should_activate_closed_position(self, trailing_manager, buy_position_forex):
        """Test trailing should not activate for closed position."""
        buy_position_forex.status = PositionStatus.CLOSED
        buy_position_forex.current_profit_pips = 25.0

        assert trailing_manager.should_activate_trailing(buy_position_forex) is False

    def test_should_activate_sell_position(self, trailing_manager):
        """Test trailing activation for SELL position calculates TP correctly."""
        sell_position = Position(
            position_id="pos_sell_001",
            symbol="EURUSD",
            position_type=PositionType.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,  # TP below entry for SELL
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )
        sell_position.current_price = 1.0850
        # TP distance: 1.1000 - 1.0850 = 0.0150 = 150 pips
        # Activation: 66% of 150 = 99 pips, but static threshold is 20 pips
        # Min threshold = 20 pips
        sell_position.current_profit_pips = 25.0  # Above static threshold

        assert trailing_manager.should_activate_trailing(sell_position) is True

    def test_activate_trailing_closed_position(self, trailing_manager, buy_position_forex):
        """Test activating trailing for closed position does nothing."""
        buy_position_forex.status = PositionStatus.CLOSED
        buy_position_forex.current_profit_pips = 25.0

        trailing_manager.activate_trailing(buy_position_forex)

        # Should not be added to trailing_active
        assert buy_position_forex.position_id not in trailing_manager.trailing_active

    def test_should_update_closed_position(self, trailing_manager, buy_position_forex):
        """Test trailing should not update for closed position."""
        buy_position_forex.status = PositionStatus.CLOSED
        trailing_manager.trailing_active.add(buy_position_forex.position_id)

        assert trailing_manager.should_update_trailing_stop(buy_position_forex) is False

    def test_should_update_can_improve_sl(self, trailing_manager, buy_position_forex):
        """Test trailing updates when SL can be improved even if profit same."""
        # Activate trailing
        buy_position_forex.current_price = 1.1030
        buy_position_forex.current_profit_pips = 30.0
        buy_position_forex.stop_loss = 1.1020
        trailing_manager.activate_trailing(buy_position_forex)
        trailing_manager.highest_profit[buy_position_forex.position_id] = 30.0

        # Price moves up slightly, profit stays same but SL can improve
        buy_position_forex.current_price = 1.1035
        buy_position_forex.current_profit_pips = 30.0  # Same profit

        # Should update because SL can be improved (and profit >= 90% of highest)
        assert trailing_manager.should_update_trailing_stop(buy_position_forex) is True

    def test_should_update_can_improve_sl_sell(self, trailing_manager):
        """Test trailing updates when SL can be improved for SELL position."""
        sell_position = Position(
            position_id="pos_sell_001",
            symbol="EURUSD",
            position_type=PositionType.SELL,
            entry_price=1.1000,
            stop_loss=1.2480,  # Current SL
            take_profit=1.2350,
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )
        sell_position.current_price = 1.2470
        sell_position.current_profit_pips = 30.0
        trailing_manager.activate_trailing(sell_position)
        trailing_manager.highest_profit[sell_position.position_id] = 30.0

        # Price moves down (better for SELL), SL can improve (lower is better for SELL)
        sell_position.current_price = 1.2465
        sell_position.current_profit_pips = 30.0  # Same profit

        # Should update because SL can be improved (new SL would be lower, which is better for SELL)
        assert trailing_manager.should_update_trailing_stop(sell_position) is True

    def test_update_trailing_stop_closed_position(self, trailing_manager, buy_position_forex):
        """Test updating trailing for closed position raises error."""
        buy_position_forex.status = PositionStatus.CLOSED
        trailing_manager.trailing_active.add(buy_position_forex.position_id)

        with pytest.raises(ValueError, match="not open"):
            trailing_manager.update_trailing_stop(buy_position_forex)

    def test_update_trailing_stop_sell_no_improvement(self, trailing_manager):
        """Test trailing stop for SELL doesn't move when new SL would be worse."""
        sell_position = Position(
            position_id="pos_sell_001",
            symbol="EURUSD",
            position_type=PositionType.SELL,
            entry_price=1.1000,
            stop_loss=1.2480,  # Already trailed
            take_profit=1.2350,
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )
        sell_position.current_price = 1.2470
        sell_position.current_profit_pips = 30.0
        trailing_manager.activate_trailing(sell_position)
        trailing_manager.highest_profit[sell_position.position_id] = 30.0

        # Price moves up (worse for SELL), new SL would be higher (worse)
        sell_position.current_price = 1.2485
        sell_position.current_profit_pips = 25.0

        # Should not move SL (would be worse)
        new_sl = trailing_manager.update_trailing_stop(sell_position)
        assert new_sl == 1.2480  # Stays at old SL
