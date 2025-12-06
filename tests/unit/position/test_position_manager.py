"""Tests for PositionManager."""

import pytest

from trading_bot.position.position_manager import PositionManager
from trading_bot.position.position_models import PositionStatus, PositionType
from trading_bot.strategies.models import SignalDirection, TradingSignal


@pytest.fixture
def position_manager():
    """Create a PositionManager instance."""
    config = {"position_manager": {"max_positions_per_symbol": 1}}
    return PositionManager(config)


@pytest.fixture
def buy_signal():
    """Create a BUY trading signal."""
    return TradingSignal(
        signal_id="sig_001",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        confluence_score=75.0,
        risk_reward_ratio=3.0,
    )


@pytest.fixture
def sell_signal():
    """Create a SELL trading signal."""
    return TradingSignal(
        signal_id="sig_002",
        symbol="GBPUSD",
        direction=SignalDirection.SELL,
        entry_price=1.2500,
        stop_loss=1.2550,
        take_profit=1.2350,
        confluence_score=70.0,
        risk_reward_ratio=3.0,
    )


class TestPositionManagerInitialization:
    """Test PositionManager initialization."""

    def test_initialization_default_config(self):
        """Test initialization with default config."""
        manager = PositionManager()
        assert manager.pip_calculator is not None
        assert manager.tracker is not None
        assert len(manager.positions) == 0

    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {"position_manager": {"max_positions_per_symbol": 2}}
        manager = PositionManager(config)
        assert manager.max_positions_per_symbol == 2


class TestCreatePositionFromSignal:
    """Test creating positions from signals."""

    def test_create_position_from_buy_signal(self, position_manager, buy_signal):
        """Test creating position from BUY signal."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        assert position.symbol == "EURUSD"
        assert position.position_type == PositionType.BUY
        assert position.entry_price == 1.1000
        assert position.stop_loss == 1.0950
        assert position.take_profit == 1.1150
        assert position.volume == 1.0
        assert position.status == PositionStatus.PENDING
        assert position.pip_size == 0.0001  # Forex major

    def test_create_position_from_sell_signal(self, position_manager, sell_signal):
        """Test creating position from SELL signal."""
        position = position_manager.create_position_from_signal(sell_signal, volume=0.5)

        assert position.symbol == "GBPUSD"
        assert position.position_type == PositionType.SELL
        assert position.volume == 0.5
        assert position.status == PositionStatus.PENDING

    def test_create_position_stores_in_manager(self, position_manager, buy_signal):
        """Test that created position is stored in manager."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        assert position.position_id in position_manager.positions
        assert position_manager.get_position_count() == 1

    def test_create_position_updates_symbol_index(self, position_manager, buy_signal):
        """Test that created position updates symbol index."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        positions = position_manager.get_positions_by_symbol("EURUSD")
        assert len(positions) == 1
        assert positions[0].position_id == position.position_id

    def test_create_position_limit_enforcement(self, position_manager, buy_signal):
        """Test that position limit per symbol is enforced."""
        # Create first position
        pos1 = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(pos1.position_id)

        # Try to create second position for same symbol
        with pytest.raises(ValueError, match="Position limit reached"):
            position_manager.create_position_from_signal(buy_signal, volume=1.0)

    def test_create_position_stores_signal_metadata(self, position_manager, buy_signal):
        """Test that position stores signal metadata."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        assert "signal_id" in position.metadata
        assert position.metadata["signal_id"] == "sig_001"
        assert "confluence_score" in position.metadata


class TestOpenPosition:
    """Test opening positions."""

    def test_open_position(self, position_manager, buy_signal):
        """Test opening a position."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        position_manager.open_position(position.position_id)

        assert position.status == PositionStatus.OPEN
        assert position.open_time is not None

    def test_open_nonexistent_position(self, position_manager):
        """Test opening nonexistent position raises error."""
        with pytest.raises(ValueError, match="not found"):
            position_manager.open_position("nonexistent_id")


class TestUpdatePosition:
    """Test updating positions."""

    def test_update_position_price(self, position_manager, buy_signal):
        """Test updating position with current price."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Update with new price
        position_manager.update_position(position.position_id, 1.1050)

        assert position.current_price == 1.1050
        assert position.current_profit_pips == pytest.approx(50.0, abs=0.1)
        assert position.current_pnl_usd == pytest.approx(500.0, abs=1.0)

    def test_update_nonexistent_position(self, position_manager):
        """Test updating nonexistent position raises error."""
        with pytest.raises(ValueError, match="not found"):
            position_manager.update_position("nonexistent_id", 1.1050)


class TestClosePosition:
    """Test closing positions."""

    def test_close_position(self, position_manager, buy_signal):
        """Test closing a position."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Close at profit
        position_manager.close_position(position.position_id, 1.1050)

        assert position.status == PositionStatus.CLOSED
        assert position.close_time is not None
        assert position.close_price == 1.1050

    def test_close_nonexistent_position(self, position_manager):
        """Test closing nonexistent position raises error."""
        with pytest.raises(ValueError, match="not found"):
            position_manager.close_position("nonexistent_id", 1.1050)


class TestGetPositions:
    """Test getting positions."""

    def test_get_position(self, position_manager, buy_signal):
        """Test getting a position by ID."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        retrieved = position_manager.get_position(position.position_id)
        assert retrieved is not None
        assert retrieved.position_id == position.position_id

    def test_get_nonexistent_position(self, position_manager):
        """Test getting nonexistent position returns None."""
        position = position_manager.get_position("nonexistent_id")
        assert position is None

    def test_get_all_positions(self, position_manager, buy_signal, sell_signal):
        """Test getting all positions."""
        position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.create_position_from_signal(sell_signal, volume=1.0)

        all_positions = position_manager.get_all_positions()
        assert len(all_positions) == 2

    def test_get_open_positions(self, position_manager, buy_signal, sell_signal):
        """Test getting only open positions."""
        pos1 = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        _pos2 = position_manager.create_position_from_signal(sell_signal, volume=1.0)

        position_manager.open_position(pos1.position_id)
        # _pos2 remains pending

        open_positions = position_manager.get_open_positions()
        assert len(open_positions) == 1
        assert open_positions[0].position_id == pos1.position_id

    def test_get_closed_positions(self, position_manager, buy_signal):
        """Test getting only closed positions."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position_manager.close_position(position.position_id, 1.1050)

        closed_positions = position_manager.get_closed_positions()
        assert len(closed_positions) == 1
        assert closed_positions[0].position_id == position.position_id

    def test_get_positions_by_symbol(self, position_manager, buy_signal, sell_signal):
        """Test getting positions by symbol."""
        position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.create_position_from_signal(sell_signal, volume=1.0)

        eurusd_positions = position_manager.get_positions_by_symbol("EURUSD")
        assert len(eurusd_positions) == 1
        assert eurusd_positions[0].symbol == "EURUSD"

        gbpusd_positions = position_manager.get_positions_by_symbol("GBPUSD")
        assert len(gbpusd_positions) == 1
        assert gbpusd_positions[0].symbol == "GBPUSD"


class TestPositionCounts:
    """Test position counting methods."""

    def test_get_position_count(self, position_manager, buy_signal, sell_signal):
        """Test getting total position count."""
        assert position_manager.get_position_count() == 0

        position_manager.create_position_from_signal(buy_signal, volume=1.0)
        assert position_manager.get_position_count() == 1

        position_manager.create_position_from_signal(sell_signal, volume=1.0)
        assert position_manager.get_position_count() == 2

    def test_get_open_position_count(self, position_manager, buy_signal, sell_signal):
        """Test getting open position count."""
        pos1 = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        pos2 = position_manager.create_position_from_signal(sell_signal, volume=1.0)

        assert position_manager.get_open_position_count() == 0

        position_manager.open_position(pos1.position_id)
        assert position_manager.get_open_position_count() == 1

        position_manager.open_position(pos2.position_id)
        assert position_manager.get_open_position_count() == 2


class TestUpdateAllPositions:
    """Test updating all positions."""

    def test_update_all_positions(self, position_manager, buy_signal, sell_signal):
        """Test updating all open positions with current prices."""
        pos1 = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        pos2 = position_manager.create_position_from_signal(sell_signal, volume=1.0)

        position_manager.open_position(pos1.position_id)
        position_manager.open_position(pos2.position_id)

        # Update all positions
        prices = {"EURUSD": 1.1050, "GBPUSD": 1.2450}
        position_manager.update_all_positions(prices)

        assert pos1.current_price == 1.1050
        assert pos2.current_price == 1.2450
        assert pos1.current_profit_pips == pytest.approx(50.0, abs=0.1)
        assert pos2.current_profit_pips == pytest.approx(50.0, abs=0.1)


class TestCheckAndClosePositions:
    """Test automatic position closing."""

    def test_check_and_close_stop_loss(self, position_manager, buy_signal):
        """Test auto-closing position when stop loss hit."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Price hits stop loss
        prices = {"EURUSD": 1.0945}
        closed = position_manager.check_and_close_positions(prices)

        assert len(closed) == 1
        assert position.status == PositionStatus.CLOSED
        assert position.close_price == 1.0945

    def test_check_and_close_take_profit(self, position_manager, buy_signal):
        """Test auto-closing position when take profit hit."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Price hits take profit
        prices = {"EURUSD": 1.1155}
        closed = position_manager.check_and_close_positions(prices)

        assert len(closed) == 1
        assert position.status == PositionStatus.CLOSED
        assert position.close_price == 1.1155

    def test_check_and_close_no_hits(self, position_manager, buy_signal):
        """Test that position stays open when SL/TP not hit."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Price in middle range
        prices = {"EURUSD": 1.1050}
        closed = position_manager.check_and_close_positions(prices)

        assert len(closed) == 0
        assert position.status == PositionStatus.OPEN


class TestGetPortfolioSummary:
    """Test portfolio summary."""

    def test_get_portfolio_summary_empty(self, position_manager):
        """Test portfolio summary with no positions."""
        summary = position_manager.get_portfolio_summary()

        assert summary["total_positions"] == 0
        assert summary["open_positions"] == 0
        assert summary["closed_positions"] == 0
        assert summary["total_pnl_usd"] == 0.0

    def test_get_portfolio_summary_with_positions(self, position_manager, buy_signal, sell_signal):
        """Test portfolio summary with positions."""
        pos1 = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        pos2 = position_manager.create_position_from_signal(sell_signal, volume=1.0)

        position_manager.open_position(pos1.position_id)
        position_manager.open_position(pos2.position_id)

        # Update prices
        prices = {"EURUSD": 1.1050, "GBPUSD": 1.2450}
        position_manager.update_all_positions(prices)

        summary = position_manager.get_portfolio_summary()

        assert summary["total_positions"] == 2
        assert summary["open_positions"] == 2
        assert summary["closed_positions"] == 0
        assert summary["total_pnl_usd"] == pytest.approx(1000.0, abs=10.0)  # Both +50 pips
        assert summary["symbols_traded"] == 2

    def test_get_portfolio_summary_with_closed_positions(self, position_manager, buy_signal):
        """Test portfolio summary with closed positions."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position_manager.close_position(position.position_id, 1.1050)

        summary = position_manager.get_portfolio_summary()

        assert summary["total_positions"] == 1
        assert summary["open_positions"] == 0
        assert summary["closed_positions"] == 1


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation(self, position_manager, buy_signal):
        """Test string representation."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        str_repr = str(position_manager)
        assert "1 open" in str_repr
        assert "0 closed" in str_repr

    def test_generate_position_id_unique(self, position_manager):
        """Test that generated position IDs are unique."""
        id1 = position_manager._generate_position_id()
        id2 = position_manager._generate_position_id()

        assert id1.startswith("pos_")
        assert id2.startswith("pos_")
        assert id1 != id2
