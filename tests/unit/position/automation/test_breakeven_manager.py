"""Tests for BreakevenManager."""

import pytest

from trading_bot.position.automation.breakeven_manager import BreakevenManager
from trading_bot.position.position_models import Position, PositionStatus, PositionType


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "position_management": {
            "forex_major": {
                "breakeven_trigger": 15.0,
                "breakeven_offset": 2.0,
            },
            "forex_jpy": {
                "breakeven_trigger": 150.0,
                "breakeven_offset": 20.0,
            },
            "commodities": {
                "breakeven_trigger": 500.0,
                "breakeven_offset": 50.0,
            },
            "crypto": {
                "breakeven_trigger": 1000.0,
                "breakeven_offset": 300.0,
            },
        }
    }


@pytest.fixture
def breakeven_manager(mock_config):
    """Create a BreakevenManager instance."""
    return BreakevenManager(config=mock_config)


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


@pytest.fixture
def sell_position_jpy():
    """Create a SELL position for JPY pair."""
    position = Position(
        position_id="pos_002",
        symbol="USDJPY",
        position_type=PositionType.SELL,
        entry_price=150.00,
        stop_loss=150.50,
        take_profit=149.00,
        volume=1.0,
        pip_size=0.01,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
    )
    position.current_price = 150.00
    position.current_profit_pips = 0.0
    return position


class TestBreakevenManagerInitialization:
    """Test BreakevenManager initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        manager = BreakevenManager()
        assert manager.pip_calculator is not None
        assert len(manager.breakeven_positions) == 0


class TestShouldMoveToBreakeven:
    """Test should_move_to_breakeven method."""

    def test_should_move_to_breakeven_forex_trigger_hit(
        self, breakeven_manager, buy_position_forex
    ):
        """Test forex position should move to breakeven when trigger hit."""
        # Move price to trigger breakeven (15 pips)
        buy_position_forex.current_price = 1.1015
        buy_position_forex.current_profit_pips = 15.0

        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is True

    def test_should_move_to_breakeven_forex_not_hit(self, breakeven_manager, buy_position_forex):
        """Test forex position should not move when trigger not hit."""
        # Only 10 pips profit (trigger is 15)
        buy_position_forex.current_price = 1.1010
        buy_position_forex.current_profit_pips = 10.0

        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is False

    def test_should_move_to_breakeven_jpy_trigger_hit(self, breakeven_manager, sell_position_jpy):
        """Test JPY position should move to breakeven when trigger hit."""
        # Move price to trigger breakeven (150 pips for JPY)
        sell_position_jpy.current_price = 148.50
        sell_position_jpy.current_profit_pips = 150.0

        assert breakeven_manager.should_move_to_breakeven(sell_position_jpy) is True

    def test_should_move_already_at_breakeven(self, breakeven_manager, buy_position_forex):
        """Test position already at breakeven should not trigger again."""
        buy_position_forex.current_price = 1.1015
        buy_position_forex.current_profit_pips = 15.0

        # First trigger
        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is True

        # Mark as moved
        breakeven_manager.breakeven_positions.add(buy_position_forex.position_id)

        # Should not trigger again
        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is False

    def test_should_move_closed_position(self, breakeven_manager, buy_position_forex):
        """Test closed position should not trigger breakeven."""
        buy_position_forex.status = PositionStatus.CLOSED
        buy_position_forex.current_profit_pips = 20.0

        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is False

    def test_should_move_current_price_none(self, breakeven_manager, buy_position_forex):
        """Test position with None current_price should not trigger breakeven."""
        buy_position_forex.current_price = None
        buy_position_forex.current_profit_pips = 20.0

        assert breakeven_manager.should_move_to_breakeven(buy_position_forex) is False


class TestMoveToBreakeven:
    """Test move_to_breakeven method."""

    def test_move_to_breakeven_buy_forex(self, breakeven_manager, buy_position_forex):
        """Test moving BUY forex position to breakeven."""
        buy_position_forex.current_price = 1.1015
        buy_position_forex.current_profit_pips = 15.0

        new_sl = breakeven_manager.move_to_breakeven(buy_position_forex)

        # New SL should be entry + buffer (2 pips for forex)
        expected_sl = 1.1000 + (2 * 0.0001)  # 1.1002
        assert new_sl == pytest.approx(expected_sl, abs=0.00001)
        assert buy_position_forex.stop_loss == pytest.approx(expected_sl, abs=0.00001)
        assert buy_position_forex.position_id in breakeven_manager.breakeven_positions

    def test_move_to_breakeven_sell_forex(self, breakeven_manager):
        """Test moving SELL forex position to breakeven."""
        position = Position(
            position_id="pos_003",
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
        position.current_price = 1.2485
        position.current_profit_pips = 15.0

        new_sl = breakeven_manager.move_to_breakeven(position)

        # New SL should be entry - buffer (2 pips for forex)
        expected_sl = 1.2500 - (2 * 0.0001)  # 1.2498
        assert new_sl == pytest.approx(expected_sl, abs=0.00001)

    def test_move_to_breakeven_jpy(self, breakeven_manager, sell_position_jpy):
        """Test moving JPY position to breakeven."""
        sell_position_jpy.current_price = 148.50
        sell_position_jpy.current_profit_pips = 150.0

        new_sl = breakeven_manager.move_to_breakeven(sell_position_jpy)

        # New SL should be entry - buffer (20 pips for JPY)
        expected_sl = 150.00 - (20 * 0.01)  # 149.80
        assert new_sl == pytest.approx(expected_sl, abs=0.01)

    def test_move_to_breakeven_gold(self, breakeven_manager):
        """Test moving Gold position to breakeven."""
        position = Position(
            position_id="pos_004",
            symbol="XAUUSD",
            position_type=PositionType.BUY,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2060.0,
            volume=1.0,
            pip_size=0.1,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )
        position.current_price = 2050.0
        position.current_profit_pips = 500.0

        new_sl = breakeven_manager.move_to_breakeven(position)

        # New SL should be entry + buffer (50 pips for Gold)
        expected_sl = 2000.0 + (50 * 0.1)  # 2005.0
        assert new_sl == pytest.approx(expected_sl, abs=0.1)

    def test_move_to_breakeven_closed_position(self, breakeven_manager, buy_position_forex):
        """Test moving closed position raises error."""
        buy_position_forex.status = PositionStatus.CLOSED

        with pytest.raises(ValueError, match="not open"):
            breakeven_manager.move_to_breakeven(buy_position_forex)


class TestIsAtBreakeven:
    """Test is_at_breakeven method."""

    def test_is_at_breakeven_true(self, breakeven_manager, buy_position_forex):
        """Test position is at breakeven."""
        breakeven_manager.breakeven_positions.add(buy_position_forex.position_id)
        assert breakeven_manager.is_at_breakeven(buy_position_forex.position_id) is True

    def test_is_at_breakeven_false(self, breakeven_manager, buy_position_forex):
        """Test position is not at breakeven."""
        assert breakeven_manager.is_at_breakeven(buy_position_forex.position_id) is False


class TestGetBreakevenParameters:
    """Test get breakeven parameters methods."""

    def test_get_breakeven_distance_forex(self, breakeven_manager):
        """Test get breakeven distance for forex."""
        distance = breakeven_manager.get_breakeven_distance("EURUSD")
        assert distance == 15.0

    def test_get_breakeven_distance_jpy(self, breakeven_manager):
        """Test get breakeven distance for JPY pair."""
        distance = breakeven_manager.get_breakeven_distance("USDJPY")
        assert distance == 150.0

    def test_get_breakeven_distance_gold(self, breakeven_manager):
        """Test get breakeven distance for Gold."""
        distance = breakeven_manager.get_breakeven_distance("XAUUSD")
        assert distance == 500.0

    def test_get_breakeven_distance_crypto(self, breakeven_manager):
        """Test get breakeven distance for crypto."""
        distance = breakeven_manager.get_breakeven_distance("BTCUSD")
        assert distance == 1000.0  # Crypto uses 1000 pips/USD for breakeven trigger

    def test_get_breakeven_buffer_forex(self, breakeven_manager):
        """Test get breakeven buffer for forex."""
        buffer = breakeven_manager.get_breakeven_buffer("EURUSD")
        assert buffer == 2.0

    def test_get_breakeven_buffer_jpy(self, breakeven_manager):
        """Test get breakeven buffer for JPY pair."""
        buffer = breakeven_manager.get_breakeven_buffer("USDJPY")
        assert buffer == 20.0


class TestPerSymbolBreakeven:
    """Per-symbol overrides take priority over asset-class defaults."""

    def test_per_symbol_override_used(self):
        from trading_bot.position.automation.breakeven_manager import BreakevenManager

        cfg = {
            "position_management": {
                "commodities": {"breakeven_trigger": 50, "breakeven_offset": 10},
            },
            "symbols": {
                "XAUUSD": {"breakeven_trigger": 175, "breakeven_offset": 20},
            },
        }
        mgr = BreakevenManager(config=cfg)
        assert mgr.get_breakeven_distance("XAUUSD") == 175
        assert mgr.get_breakeven_buffer("XAUUSD") == 20

    def test_symbol_without_override_uses_asset_default(self):
        from trading_bot.position.automation.breakeven_manager import BreakevenManager

        cfg = {
            "position_management": {
                "commodities": {"breakeven_trigger": 50, "breakeven_offset": 10},
            },
            "symbols": {
                "XAUUSD": {"breakeven_trigger": 175, "breakeven_offset": 20},
            },
        }
        mgr = BreakevenManager(config=cfg)
        # XAGUSD has no per-symbol override → falls back to commodities defaults
        assert mgr.get_breakeven_distance("XAGUSD") == 50
        assert mgr.get_breakeven_buffer("XAGUSD") == 10


class TestResetPosition:
    """Test reset_position method."""

    def test_reset_position(self, breakeven_manager, buy_position_forex):
        """Test resetting position breakeven tracking."""
        breakeven_manager.breakeven_positions.add(buy_position_forex.position_id)

        breakeven_manager.reset_position(buy_position_forex.position_id)

        assert buy_position_forex.position_id not in breakeven_manager.breakeven_positions


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_breakeven_positions_count(self, breakeven_manager, buy_position_forex):
        """Test getting breakeven positions count."""
        assert breakeven_manager.get_breakeven_positions_count() == 0

        breakeven_manager.breakeven_positions.add(buy_position_forex.position_id)
        assert breakeven_manager.get_breakeven_positions_count() == 1

    def test_string_representation(self, breakeven_manager):
        """Test string representation."""
        str_repr = str(breakeven_manager)
        assert "BreakevenManager" in str_repr
        assert "0 positions at BE" in str_repr


class TestRatioBasedTrigger:
    """Breakeven trigger scaling with each position's actual stop distance.

    Regression for the gold/BTC bug: a fixed pip trigger never armed because
    the dynamic zone-based SL made it nearly 1R. Ratio mode keys the trigger
    off entry_to_sl_pips so it stays correct regardless of SL size.
    """

    @pytest.fixture
    def ratio_config(self):
        return {
            "position_management": {
                "commodities": {
                    "breakeven_trigger_r": 0.4,
                    "breakeven_trigger": 175.0,  # fixed fallback
                    "breakeven_offset": 20.0,
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

    def test_arms_at_ratio_of_actual_risk(self, ratio_config):
        mgr = BreakevenManager(config=ratio_config)
        # SL 188 pips -> 0.4R = 75.2 pips. Real peak was +134 -> must arm.
        assert mgr.should_move_to_breakeven(self._xau_sell(88.0, 188.1)) is True

    def test_does_not_arm_below_ratio(self, ratio_config):
        mgr = BreakevenManager(config=ratio_config)
        assert mgr.should_move_to_breakeven(self._xau_sell(50.0, 188.1)) is False

    def test_fixed_fallback_when_risk_unknown(self, ratio_config):
        mgr = BreakevenManager(config=ratio_config)
        # entry_to_sl_pips=0 -> falls back to fixed 175 pips
        assert mgr.should_move_to_breakeven(self._xau_sell(100.0, 0.0)) is False
        assert mgr.should_move_to_breakeven(self._xau_sell(180.0, 0.0)) is True

    def test_resolve_trigger_pips_modes(self, ratio_config):
        mgr = BreakevenManager(config=ratio_config)
        pos = self._xau_sell(0.0, 200.0)
        settings = mgr._get_settings("XAUUSD", "commodities")
        pips, mode = mgr._resolve_trigger_pips(pos, settings)
        assert pips == pytest.approx(80.0)  # 0.4 * 200
        assert mode == "0.4R"
        pos.entry_to_sl_pips = 0.0
        pips, mode = mgr._resolve_trigger_pips(pos, settings)
        assert pips == 175.0
        assert mode == "fixed"
