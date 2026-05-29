"""Tests for TrailingStopManager."""

import pytest
from trading_worker.position.automation.trailing_stop_manager import TrailingStopManager
from trading_worker.position.position_models import Position, PositionStatus, PositionType

pytest_plugins = ("pytest_mock",)


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


class TestTieredTrailingConfig:
    """Test TieredTrailingConfig initialization."""

    def test_tiered_trailing_config_default_initialization(self):
        """Test TieredTrailingConfig initializes with defaults."""
        from trading_worker.position.automation.trailing_stop_manager import (
            TieredTrailingConfig,
        )

        config = TieredTrailingConfig()
        assert config.use_tiered_trailing is True
        assert config.tier_thresholds == [10.0, 20.0, 30.0]
        assert config.tier_distances == [8.0, 12.0, 15.0]

    def test_tiered_trailing_config_custom_values(self):
        """Test TieredTrailingConfig with custom values."""
        from trading_worker.position.automation.trailing_stop_manager import (
            TieredTrailingConfig,
        )

        config = TieredTrailingConfig(
            use_tiered_trailing=False,
            tier_thresholds=[15.0, 25.0, 35.0],
            tier_distances=[10.0, 15.0, 20.0],
        )
        assert config.use_tiered_trailing is False
        assert config.tier_thresholds == [15.0, 25.0, 35.0]
        assert config.tier_distances == [10.0, 15.0, 20.0]

    def test_tiered_trailing_config_mismatched_lengths_raises_error(self):
        """Test TieredTrailingConfig raises error when lengths don't match."""
        from trading_worker.position.automation.trailing_stop_manager import (
            TieredTrailingConfig,
        )

        with pytest.raises(ValueError, match="Tier thresholds and distances must have same length"):
            TieredTrailingConfig(
                tier_thresholds=[10.0, 20.0, 30.0],
                tier_distances=[8.0, 12.0],  # Mismatched length
            )


class TestGetSettingsNewConfig:
    """Test _get_settings with new config structure."""

    def test_get_settings_new_config_structure(self):
        """Test _get_settings with new position_management structure."""
        new_config = {
            "position_management": {
                "forex_major": {
                    "trailing_activation": 25.0,
                    "trailing_distance": 12.0,
                }
            }
        }
        manager = TrailingStopManager(config=new_config)
        settings = manager._get_settings("EURUSD", "forex_major")
        assert settings["activation_pips"] == 25.0
        assert settings["limit_pips"] == 12.0

    def test_get_settings_old_config_structure(self, mock_config):
        """Test _get_settings falls back to old trade_management structure."""
        manager = TrailingStopManager(config=mock_config)
        settings = manager._get_settings("USDJPY", "forex_jpy")
        # Should use old structure overrides
        assert settings["activation_pips"] == 100.0
        assert settings["limit_pips"] == 20.0

    def test_per_symbol_override_wins(self):
        """Per-symbol config overrides asset-class config."""
        cfg = {
            "position_management": {
                "commodities": {"trailing_activation": 80, "trailing_distance": 40},
            },
            "symbols": {
                "XAUUSD": {"trailing_activation": 280, "trailing_distance": 100},
            },
        }
        manager = TrailingStopManager(config=cfg)
        settings = manager._get_settings("XAUUSD", "commodities")
        assert settings["activation_pips"] == 280
        assert settings["limit_pips"] == 100

    def test_other_symbol_uses_asset_class_default(self):
        """Symbol without override falls back to asset-class config."""
        cfg = {
            "position_management": {
                "commodities": {"trailing_activation": 80, "trailing_distance": 40},
            },
            "symbols": {
                "XAUUSD": {"trailing_activation": 280, "trailing_distance": 100},
            },
        }
        manager = TrailingStopManager(config=cfg)
        # XAGUSD has no per-symbol override → falls back to commodities defaults
        settings = manager._get_settings("XAGUSD", "commodities")
        assert settings["activation_pips"] == 80
        assert settings["limit_pips"] == 40


class TestATRBasedTrailing:
    """Test ATR-based trailing stop methods."""

    def test_get_atr_returns_none_by_default(self, trailing_manager):
        """Test get_atr returns None (placeholder implementation)."""
        atr = trailing_manager.get_atr("EURUSD", "H1")
        assert atr is None

    def test_calculate_atr_activation_forex_major(self, trailing_manager):
        """Test calculate ATR activation threshold for forex major."""
        atr = 15.0
        activation = trailing_manager.calculate_atr_activation(atr, "forex_major")
        # Default multiplier is 1.5x
        assert activation == 22.5

    def test_calculate_atr_activation_forex_jpy(self, trailing_manager):
        """Test calculate ATR activation threshold for forex JPY."""
        atr = 150.0
        activation = trailing_manager.calculate_atr_activation(atr, "forex_jpy")
        # Default multiplier is 1.5x
        assert activation == 225.0

    def test_calculate_atr_distance_forex_major(self, trailing_manager):
        """Test calculate ATR trailing distance for forex major."""
        atr = 20.0
        distance = trailing_manager.calculate_atr_distance(atr, "forex_major")
        # Default multiplier is 1.0x
        assert distance == 20.0

    def test_calculate_atr_distance_commodities(self, trailing_manager):
        """Test calculate ATR trailing distance for commodities."""
        atr = 500.0
        distance = trailing_manager.calculate_atr_distance(atr, "commodities")
        # Default multiplier is 1.0x
        assert distance == 500.0

    def test_get_activation_threshold_atr_disabled_uses_fallback(
        self, trailing_manager, buy_position_forex
    ):
        """Test get_activation_threshold uses fallback when ATR disabled."""
        # Config has use_atr_trailing=False by default
        threshold = trailing_manager.get_activation_threshold("EURUSD", buy_position_forex)
        # Should return fallback from config
        assert threshold == 20.0

    def test_get_activation_threshold_atr_none_uses_fallback(
        self, trailing_manager, buy_position_forex
    ):
        """Test get_activation_threshold uses fallback when ATR is None."""
        threshold = trailing_manager.get_activation_threshold("EURUSD")
        # get_atr returns None, so should use fallback
        assert threshold == 20.0

    def test_get_activation_threshold_with_position_dict(self, trailing_manager):
        """Test get_activation_threshold with new signature (position dict)."""
        position_dict = {
            "symbol": "EURUSD",
            "current_profit_pips": 25.0,
        }
        threshold = trailing_manager.get_activation_threshold(position_dict)
        assert threshold == 20.0

    def test_get_activation_threshold_atr_enabled_with_atr_value(self, trailing_manager):
        """Test get_activation_threshold with ATR enabled and ATR value."""
        # Enable ATR for forex_major
        trailing_manager.atr_configs["forex_major"].use_atr_trailing = True

        # Mock get_atr to return a value
        def mock_get_atr(symbol, timeframe="H1"):
            return 20.0

        trailing_manager.get_atr = mock_get_atr

        threshold = trailing_manager.get_activation_threshold("EURUSD")
        # Should use ATR-based: 20.0 * 1.5 = 30.0
        assert threshold == 30.0

    def test_get_activation_threshold_atr_enabled_but_atr_none(self, trailing_manager):
        """Test get_activation_threshold with ATR enabled but get_atr returns None."""
        # Enable ATR for forex_major
        trailing_manager.atr_configs["forex_major"].use_atr_trailing = True

        # get_atr returns None by default, should use fallback
        threshold = trailing_manager.get_activation_threshold("EURUSD")
        # Should use fallback from atr_config (20.0)
        assert threshold == 20.0


class TestTieredTrailingMethods:
    """Test tiered trailing stop methods."""

    def test_get_tiered_distance_tiered_disabled(self, trailing_manager):
        """Test get_tiered_distance uses fallback when tiered disabled."""
        position = {
            "symbol": "EURUSD",
            "current_profit_pips": 25.0,
        }
        # Config has use_tiered_trailing=False by default
        distance = trailing_manager.get_tiered_distance(position)
        assert distance == 15.0  # Fallback distance

    def test_get_tiered_distance_below_first_threshold(self, trailing_manager):
        """Test get_tiered_distance for profit below first threshold."""
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        position = {
            "symbol": "EURUSD",
            "current_profit_pips": 15.0,  # Below 20 pips
        }
        distance = trailing_manager.get_tiered_distance(position)
        # Should use tier 0 distance (8.0)
        assert distance == 8.0

    def test_get_tiered_distance_between_thresholds(self, trailing_manager):
        """Test get_tiered_distance for profit between thresholds."""
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        position = {
            "symbol": "EURUSD",
            "current_profit_pips": 25.0,  # Between 20 and 30
        }
        distance = trailing_manager.get_tiered_distance(position)
        # Should use tier 1 distance (12.0)
        assert distance == 12.0

    def test_get_tiered_distance_above_all_thresholds(self, trailing_manager):
        """Test get_tiered_distance for profit above all thresholds."""
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        position = {
            "symbol": "EURUSD",
            "current_profit_pips": 40.0,  # Above 30 pips
        }
        distance = trailing_manager.get_tiered_distance(position)
        # Should use tier 2 distance (15.0)
        assert distance == 15.0

    def test_get_tiered_distance_at_threshold_boundary(self, trailing_manager):
        """Test get_tiered_distance at exact threshold boundary."""
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        position = {
            "symbol": "EURUSD",
            "current_profit_pips": 30.0,  # Exactly at tier 2 threshold
        }
        distance = trailing_manager.get_tiered_distance(position)
        # Should use tier 2 distance (15.0)
        assert distance == 15.0

    def test_get_tiered_distance_jpy_pair(self, trailing_manager):
        """Test get_tiered_distance for JPY pair."""
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_jpy"].use_tiered_trailing = True

        position = {
            "symbol": "USDJPY",
            "current_profit_pips": 150.0,
        }
        distance = trailing_manager.get_tiered_distance(position)
        # Should use tier 2 distance for JPY (15.0)
        assert distance == 15.0


class TestOptimalDistance:
    """Test optimal trailing distance calculation."""

    def test_get_optimal_distance_atr_enabled_with_atr_value(self, trailing_manager):
        """Test get_optimal_distance with ATR enabled and ATR value."""
        position = {"symbol": "EURUSD", "current_profit_pips": 25.0}
        atr = 20.0

        # Mock ATR config to be enabled
        trailing_manager.atr_configs["forex_major"].use_atr_trailing = True

        distance = trailing_manager.get_optimal_distance(position, atr)
        # Should return max of ATR distance (20.0) and tiered distance (12.0)
        assert distance == 20.0

    def test_get_optimal_distance_no_atr_uses_tiered(self, trailing_manager):
        """Test get_optimal_distance falls back to tiered when no ATR."""
        position = {"symbol": "EURUSD", "current_profit_pips": 25.0}

        distance = trailing_manager.get_optimal_distance(position, atr=None)
        # ATR is None, so should use fallback (15.0)
        assert distance == 15.0

    def test_get_optimal_distance_both_disabled_uses_fallback(self, trailing_manager):
        """Test get_optimal_distance uses fallback when both disabled."""
        position = {"symbol": "EURUSD", "current_profit_pips": 25.0}

        # Mock configs to be disabled
        trailing_manager.atr_configs["forex_major"].use_atr_trailing = False
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = False

        distance = trailing_manager.get_optimal_distance(position)
        # Should use fallback distance (15.0)
        assert distance == 15.0

    def test_get_optimal_distance_wider_of_atr_and_tiered(self, trailing_manager):
        """Test get_optimal_distance returns wider of ATR and tiered."""
        position = {"symbol": "EURUSD", "current_profit_pips": 25.0}
        atr = 25.0

        # Mock ATR config to be enabled
        trailing_manager.atr_configs["forex_major"].use_atr_trailing = True
        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        distance = trailing_manager.get_optimal_distance(position, atr)
        # ATR distance = 25.0, tiered = 12.0, should return max (25.0)
        assert distance == 25.0

    def test_get_optimal_distance_tiered_enabled(self, trailing_manager):
        """Test get_optimal_distance with tiered enabled."""
        position = {"symbol": "EURUSD", "current_profit_pips": 25.0}

        # Enable tiered trailing
        trailing_manager.tiered_configs["forex_major"].use_tiered_trailing = True

        distance = trailing_manager.get_optimal_distance(position)
        # Should use tiered distance (12.0)
        assert distance == 12.0


class TestSessionAwareTrailing:
    """Test session-aware trailing stop methods."""

    def test_get_current_session_asian(self, trailing_manager, mocker):
        """Test get_current_session returns 'asian' session."""
        # Mock datetime.utcnow() to return 2:00 UTC (Asian session)
        mock_dt = mocker.patch("trading_worker.position.automation.trailing_stop_manager.datetime")
        mock_dt.utcnow.return_value.hour = 2

        session = trailing_manager.get_current_session()
        assert session == "asian"

    def test_get_current_session_london_open(self, trailing_manager, mocker):
        """Test get_current_session returns 'london_open' session."""
        # Mock datetime.utcnow() to return 9:00 UTC (London open)
        mock_dt = mocker.patch("trading_worker.position.automation.trailing_stop_manager.datetime")
        mock_dt.utcnow.return_value.hour = 9

        session = trailing_manager.get_current_session()
        assert session == "london_open"

    def test_get_current_session_ny_open(self, trailing_manager, mocker):
        """Test get_current_session returns 'ny_open' session."""
        # Mock datetime.utcnow() to return 14:00 UTC (NY open)
        mock_dt = mocker.patch("trading_worker.position.automation.trailing_stop_manager.datetime")
        mock_dt.utcnow.return_value.hour = 14

        session = trailing_manager.get_current_session()
        assert session == "ny_open"

    def test_get_current_session_regular(self, trailing_manager, mocker):
        """Test get_current_session returns 'regular' session."""
        # Mock datetime.utcnow() to return 16:00 UTC (regular hours)
        mock_dt = mocker.patch("trading_worker.position.automation.trailing_stop_manager.datetime")
        mock_dt.utcnow.return_value.hour = 16

        session = trailing_manager.get_current_session()
        assert session == "regular"

    def test_adjust_for_session_london_open(self, trailing_manager):
        """Test adjust_for_session widens during London open."""
        base_distance = 10.0
        adjusted = trailing_manager.adjust_for_session(base_distance, "london_open")
        # 1.5x multiplier
        assert adjusted == 15.0

    def test_adjust_for_session_ny_open(self, trailing_manager):
        """Test adjust_for_session widens during NY open."""
        base_distance = 10.0
        adjusted = trailing_manager.adjust_for_session(base_distance, "ny_open")
        # 1.5x multiplier
        assert adjusted == 15.0

    def test_adjust_for_session_asian(self, trailing_manager):
        """Test adjust_for_session tightens during Asian session."""
        base_distance = 10.0
        adjusted = trailing_manager.adjust_for_session(base_distance, "asian")
        # 0.7x multiplier
        assert adjusted == 7.0

    def test_adjust_for_session_regular(self, trailing_manager):
        """Test adjust_for_session keeps regular distance."""
        base_distance = 10.0
        adjusted = trailing_manager.adjust_for_session(base_distance, "regular")
        # 1.0x multiplier (no adjustment)
        assert adjusted == 10.0

    def test_adjust_for_session_unknown(self, trailing_manager):
        """Test adjust_for_session handles unknown session."""
        base_distance = 10.0
        adjusted = trailing_manager.adjust_for_session(base_distance, "unknown")
        # 1.0x multiplier (default)
        assert adjusted == 10.0


class TestCalculateTrailingSL:
    """Test calculate trailing stop loss method."""

    def test_calculate_trailing_sl_buy_position(self, trailing_manager):
        """Test calculate trailing SL for BUY position."""
        position = {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "pip_size": 0.0001,
            "stop_loss": 1.0950,
        }
        current_price = 1.1000
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # 1.1000 - (10 * 0.0001) = 1.0990
        assert new_sl == pytest.approx(1.0990, abs=0.00001)

    def test_calculate_trailing_sl_buy_never_moves_down(self, trailing_manager):
        """Test calculate trailing SL for BUY never moves down."""
        position = {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "pip_size": 0.0001,
            "stop_loss": 1.0990,  # Current SL is higher
        }
        current_price = 1.0980  # Lower price would calculate lower SL
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # Should return max of new (1.0970) and current (1.0990) = 1.0990
        assert new_sl == 1.0990

    def test_calculate_trailing_sl_sell_position(self, trailing_manager):
        """Test calculate trailing SL for SELL position."""
        position = {
            "symbol": "EURUSD",
            "position_type": "SELL",
            "pip_size": 0.0001,
            "stop_loss": 1.1050,
        }
        current_price = 1.1000
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # 1.1000 + (10 * 0.0001) = 1.1010
        assert new_sl == 1.1010

    def test_calculate_trailing_sl_sell_never_moves_up(self, trailing_manager):
        """Test calculate trailing SL for SELL never moves up."""
        position = {
            "symbol": "EURUSD",
            "position_type": "SELL",
            "pip_size": 0.0001,
            "stop_loss": 1.1010,  # Current SL is lower
        }
        current_price = 1.1020  # Higher price would calculate higher SL
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # Should return min of new (1.1030) and current (1.1010) = 1.1010
        assert new_sl == 1.1010

    def test_calculate_trailing_sl_missing_pip_size_uses_default(self, trailing_manager):
        """Test calculate trailing SL with missing pip_size uses default."""
        position = {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "stop_loss": 1.0950,
            # pip_size missing, should use default 0.0001
        }
        current_price = 1.1000
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # 1.1000 - (10 * 0.0001) = 1.0990
        assert new_sl == pytest.approx(1.0990, abs=0.00001)

    def test_calculate_trailing_sl_missing_stop_loss_uses_zero(self, trailing_manager):
        """Test calculate trailing SL with missing stop_loss uses 0."""
        position = {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "pip_size": 0.0001,
            # stop_loss missing, should use 0.0
        }
        current_price = 1.1000
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # 1.1000 - (10 * 0.0001) = 1.0990, max(1.0990, 0.0) = 1.0990
        assert new_sl == pytest.approx(1.0990, abs=0.00001)

    def test_calculate_trailing_sl_missing_position_type_defaults_to_buy(self, trailing_manager):
        """Test calculate trailing SL with missing position_type defaults to BUY."""
        position = {
            "symbol": "EURUSD",
            # position_type missing, should use default "BUY"
            "pip_size": 0.0001,
            "stop_loss": 1.0950,
        }
        current_price = 1.1000
        distance_pips = 10.0

        new_sl = trailing_manager.calculate_trailing_sl(position, current_price, distance_pips)
        # Should treat as BUY: 1.1000 - (10 * 0.0001) = 1.0990
        assert new_sl == pytest.approx(1.0990, abs=0.00001)


class TestReprMethod:
    """Test __repr__ method."""

    def test_repr_returns_same_as_str(self, trailing_manager):
        """Test __repr__ returns same as __str__."""
        str_repr = str(trailing_manager)
        repr_repr = repr(trailing_manager)
        assert str_repr == repr_repr


class TestRatioBasedTrailing:
    """Trailing activation/distance scaling with each position's stop distance."""

    @pytest.fixture
    def ratio_config(self):
        return {
            "position_management": {
                "commodities": {
                    "trailing_activation_r": 0.7,
                    "trailing_distance_r": 0.4,
                    "trailing_activation": 280.0,  # fixed fallback
                    "trailing_distance": 100.0,
                }
            }
        }

    def _xau_sell(self, profit_pips, risk_pips):
        pos = Position(
            position_id="pos_xau",
            symbol="XAUUSD",
            position_type=PositionType.SELL,
            entry_price=4432.226,
            stop_loss=4451.039,
            take_profit=4400.0,
            volume=0.04,
            pip_size=0.1,
            pip_value_per_lot=1.0,
            status=PositionStatus.OPEN,
        )
        pos.entry_to_sl_pips = risk_pips
        pos.current_profit_pips = profit_pips
        pos.current_price = 4432.226 - profit_pips * 0.1
        return pos

    def test_activates_at_ratio_of_risk(self, ratio_config):
        mgr = TrailingStopManager(config=ratio_config)
        # SL 188 -> 0.7R = 131.6 pips
        assert mgr.should_activate_trailing(self._xau_sell(140.0, 188.1)) is True
        assert mgr.should_activate_trailing(self._xau_sell(120.0, 188.1)) is False

    def test_distance_scales_with_risk(self, ratio_config):
        mgr = TrailingStopManager(config=ratio_config)
        pos = self._xau_sell(140.0, 200.0)
        settings = mgr._get_settings("XAUUSD", "commodities")
        # 0.4 * 200 = 80 pips distance
        assert mgr._resolve_distance_pips(pos, settings) == pytest.approx(80.0)

    def test_fixed_fallback_when_risk_unknown(self, ratio_config):
        mgr = TrailingStopManager(config=ratio_config)
        pos = self._xau_sell(290.0, 0.0)  # risk unknown -> fixed 280
        assert mgr.should_activate_trailing(pos) is True
        pos2 = self._xau_sell(200.0, 0.0)
        assert mgr.should_activate_trailing(pos2) is False
        settings = mgr._get_settings("XAUUSD", "commodities")
        assert mgr._resolve_distance_pips(pos2, settings) == 100.0
