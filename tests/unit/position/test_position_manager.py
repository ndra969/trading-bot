"""Tests for PositionManager."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from trading_core.data.models import Position as DBPosition
from trading_worker.position.position_manager import PositionManager
from trading_worker.position.position_models import PositionStatus, PositionType
from trading_worker.strategies.models import SignalDirection, TradingSignal


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

    def test_create_position_persists_confluence_breakdown(self, position_manager, buy_signal):
        """confluence_breakdown from the signal is copied to position.metadata (Goal 7)."""
        breakdown = {
            "foundation_share": 24.0,
            "enhancement_share": 12.0,
            "raw_confidences": {"price_action": 70.0, "ma": 50.0},
            "active_layers": ["ma", "price_action"],
        }
        buy_signal.metadata = {"confluence_breakdown": breakdown}

        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        assert position.metadata["confluence_breakdown"] == breakdown

    def test_create_position_without_breakdown_omits_key(self, position_manager, buy_signal):
        """No breakdown in signal → key absent (old/partial signals don't crash)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        assert "confluence_breakdown" not in position.metadata


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
        """Test closing nonexistent position returns None."""
        result = position_manager.close_position("nonexistent_id", 1.1050)
        assert result is None


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
        assert position.close_reason == "TAKE_PROFIT"

    def test_check_and_close_stop_loss_records_stop_loss_reason(self, position_manager, buy_signal):
        """Plain SL hit (no BE/trailing) records STOP_LOSS."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        prices = {"EURUSD": 1.0945}
        position_manager.check_and_close_positions(prices)

        assert position.close_reason == "STOP_LOSS"

    def test_check_and_close_sl_with_breakeven_records_breakeven_stop(
        self, position_manager, buy_signal
    ):
        """SL hit after breakeven activated → BREAKEVEN_STOP."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position.breakeven_activated = True

        prices = {"EURUSD": 1.0945}
        position_manager.check_and_close_positions(prices)

        assert position.close_reason == "BREAKEVEN_STOP"

    def test_check_and_close_sl_with_trailing_records_trailing_stop(
        self, position_manager, buy_signal
    ):
        """SL hit after trailing activated → TRAILING_STOP (priority over BE)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position.breakeven_activated = True
        position.trailing_activated = True

        prices = {"EURUSD": 1.0945}
        position_manager.check_and_close_positions(prices)

        assert position.close_reason == "TRAILING_STOP"

    def test_check_and_close_no_hits(self, position_manager, buy_signal):
        """Test that position stays open when SL/TP not hit."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Price in middle range
        prices = {"EURUSD": 1.1050}
        closed = position_manager.check_and_close_positions(prices)

        assert len(closed) == 0
        assert position.status == PositionStatus.OPEN

    def test_check_and_close_positions_symbol_not_in_prices(self, position_manager, buy_signal):
        """Test check_and_close_positions skips positions when symbol not in prices."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Prices dict doesn't include this symbol
        prices = {"OTHER_SYMBOL": 1.1050}
        closed = position_manager.check_and_close_positions(prices)

        # Should skip position (continue) and return empty list
        assert len(closed) == 0
        assert position.is_open


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


class TestDatabaseOperations:
    """Test database operations (load_positions_from_db, save_position)."""

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_success(self, mock_get_session, position_manager):
        """Test loading positions from database successfully."""
        # Create mock database position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_test_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions
        await position_manager.load_positions_from_db()

        # Verify position was loaded
        assert len(position_manager.positions) == 1
        assert "pos_test_001" in position_manager.positions
        assert position_manager.positions["pos_test_001"].symbol == "EURUSD"

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_invalid_pending_buy(
        self, mock_get_session, position_manager
    ):
        """Test loading invalid PENDING BUY position (SL >= Entry)."""
        # Create invalid mock database position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_invalid_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.1100  # Invalid: SL > Entry for BUY
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - invalid position should be skipped
        await position_manager.load_positions_from_db()

        # Verify invalid position was NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_invalid_pending_buy_tp(
        self, mock_get_session, position_manager
    ):
        """Test loading invalid PENDING BUY position (TP <= Entry)."""
        # Create invalid mock database position with TP <= Entry
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_invalid_tp_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950  # Valid SL
        mock_db_pos.take_profit = 1.0990  # Invalid: TP <= Entry for BUY
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - invalid position should be skipped
        await position_manager.load_positions_from_db()

        # Verify invalid position was NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_create_new(self, mock_get_session, position_manager, buy_signal):
        """Test saving new position to database."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # Position doesn't exist
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify position was added and committed
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_update_existing(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test updating existing position in database."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos  # Position exists
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify position was updated and committed
        assert mock_db_pos.status == PositionStatus.OPEN.value
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_invalid_pending_buy(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving invalid PENDING BUY position logs error (error is caught and logged)."""
        # Create position with invalid SL
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position.stop_loss = 1.1100  # Invalid: SL > Entry for BUY
        position.status = PositionStatus.PENDING

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged, not raised
        await position_manager.save_position(position)

        # Verify error was logged (error is caught in try-except)
        # Position should not be saved (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_open_position_validation(
        self, mock_get_session, position_manager
    ):
        """Test loading OPEN positions with validation (SL/TP must be positive)."""
        # Create mock OPEN position with invalid SL (negative)
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_open_invalid_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.OPEN.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = -1.0  # Invalid: negative SL
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - invalid OPEN position should be skipped
        await position_manager.load_positions_from_db()

        # Verify invalid position was NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_open_position_invalid_tp(
        self, mock_get_session, position_manager
    ):
        """Test loading OPEN position with invalid TP (zero or negative)."""
        # Create mock OPEN position with invalid TP
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_open_invalid_tp_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.OPEN.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 0.0  # Invalid: zero TP
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - invalid OPEN position should be skipped
        await position_manager.load_positions_from_db()

        # Verify invalid position was NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_with_ticket(self, mock_get_session, position_manager):
        """Test loading position with ticket in metadata."""
        # Create mock position with ticket
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_with_ticket_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {"ticket": 12345}  # Ticket in metadata

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions
        await position_manager.load_positions_from_db()

        # Verify position was loaded with ticket
        assert len(position_manager.positions) == 1
        position = position_manager.positions["pos_with_ticket_001"]
        assert position.ticket == 12345

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_value_error_handling(
        self, mock_get_session, position_manager
    ):
        """Test handling ValueError when creating Position object."""
        # Create mock position that will cause ValueError in Position.__post_init__
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_value_error_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = "INVALID_TYPE"  # Will cause ValueError
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - ValueError should be caught and logged
        await position_manager.load_positions_from_db()

        # Verify invalid position was NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_exception_handling(
        self, mock_get_session, position_manager
    ):
        """Test handling unexpected exceptions when loading positions."""
        # Create mock position that will cause unexpected exception
        mock_db_pos = MagicMock(spec=DBPosition)
        # Make accessing position_id raise exception
        type(mock_db_pos).position_id = PropertyMock(side_effect=Exception("Unexpected error"))
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - Exception should be caught and logged
        await position_manager.load_positions_from_db()

        # Verify no positions were loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_database_error(self, mock_get_session, position_manager):
        """Test handling database errors when loading positions."""
        # Mock session to raise exception
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        mock_get_session.return_value = mock_session_context

        # Load positions - Exception should be caught and logged
        await position_manager.load_positions_from_db()

        # Verify no positions were loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_with_ticket_sync(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving position syncs ticket from position object to metadata."""
        # Create position with ticket
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position.ticket = 54321  # Set ticket on position object

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # New position
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify ticket was synced to metadata
        assert position.metadata.get("ticket") == 54321
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_pending_sell_validation(
        self, mock_get_session, position_manager, sell_signal
    ):
        """Test saving PENDING SELL position with invalid SL/TP raises error."""
        # Create SELL position with invalid SL (SL <= Entry for SELL)
        position = position_manager.create_position_from_signal(sell_signal, volume=1.0)
        position.stop_loss = 1.2400  # Invalid: SL < Entry for SELL
        position.status = PositionStatus.PENDING

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged
        await position_manager.save_position(position)

        # Verify error was handled (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_open_negative_sl(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving OPEN position with negative SL raises error."""
        # Create position and open it
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position.stop_loss = -1.0  # Invalid: negative SL

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged
        await position_manager.save_position(position)

        # Verify error was handled (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_open_negative_tp(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving OPEN position with negative TP raises error."""
        # Create position and open it
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position.take_profit = -1.0  # Invalid: negative TP

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged
        await position_manager.save_position(position)

        # Verify error was handled (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_database_error(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test handling database errors when saving position."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        # Mock session to raise exception
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(side_effect=Exception("Database error"))
        mock_get_session.return_value = mock_session_context

        # Save position - Exception should be caught and logged
        await position_manager.save_position(position)

        # Position should still exist in memory (not removed)
        assert position.position_id in position_manager.positions

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_invalid_pending_sell(
        self, mock_get_session, position_manager
    ):
        """Test loading invalid PENDING SELL position (SL <= Entry or TP >= Entry)."""
        # Test SELL with invalid SL
        mock_db_pos_sl = MagicMock(spec=DBPosition)
        mock_db_pos_sl.position_id = "pos_sell_invalid_sl_001"
        mock_db_pos_sl.symbol = "EURUSD"
        mock_db_pos_sl.position_type = PositionType.SELL.value
        mock_db_pos_sl.status = PositionStatus.PENDING.value
        mock_db_pos_sl.entry_price = 1.2500
        mock_db_pos_sl.stop_loss = 1.2400  # Invalid: SL < Entry for SELL
        mock_db_pos_sl.take_profit = 1.2350
        mock_db_pos_sl.volume = 1.0
        mock_db_pos_sl.pip_size = 0.0001
        mock_db_pos_sl.pip_value_per_lot = 10.0
        mock_db_pos_sl.open_time = datetime.now()
        mock_db_pos_sl.close_time = None
        mock_db_pos_sl.close_price = None
        mock_db_pos_sl.current_price = 1.2500
        mock_db_pos_sl.current_profit_pips = 0.0
        mock_db_pos_sl.current_pnl_usd = 0.0
        mock_db_pos_sl.risk_amount_usd = 50.0
        mock_db_pos_sl.potential_profit_usd = 150.0
        mock_db_pos_sl.meta_data = {}

        # Test SELL with invalid TP
        mock_db_pos_tp = MagicMock(spec=DBPosition)
        mock_db_pos_tp.position_id = "pos_sell_invalid_tp_001"
        mock_db_pos_tp.symbol = "EURUSD"
        mock_db_pos_tp.position_type = PositionType.SELL.value
        mock_db_pos_tp.status = PositionStatus.PENDING.value
        mock_db_pos_tp.entry_price = 1.2500
        mock_db_pos_tp.stop_loss = 1.2550
        mock_db_pos_tp.take_profit = 1.2600  # Invalid: TP > Entry for SELL
        mock_db_pos_tp.volume = 1.0
        mock_db_pos_tp.pip_size = 0.0001
        mock_db_pos_tp.pip_value_per_lot = 10.0
        mock_db_pos_tp.open_time = datetime.now()
        mock_db_pos_tp.close_time = None
        mock_db_pos_tp.close_price = None
        mock_db_pos_tp.current_price = 1.2500
        mock_db_pos_tp.current_profit_pips = 0.0
        mock_db_pos_tp.current_pnl_usd = 0.0
        mock_db_pos_tp.risk_amount_usd = 50.0
        mock_db_pos_tp.potential_profit_usd = 150.0
        mock_db_pos_tp.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos_sl, mock_db_pos_tp]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - invalid positions should be skipped
        await position_manager.load_positions_from_db()

        # Verify invalid positions were NOT loaded
        assert len(position_manager.positions) == 0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_ticket_sync_no_metadata(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving position syncs ticket when metadata doesn't exist."""
        # Create position with ticket but no metadata
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position.ticket = 99999
        position.metadata = None  # No metadata initially

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # New position
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify ticket was synced to metadata (metadata should be created)
        assert position.metadata is not None
        assert position.metadata.get("ticket") == 99999

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_pending_sell_invalid_tp(
        self, mock_get_session, position_manager, sell_signal
    ):
        """Test saving PENDING SELL position with invalid TP raises error."""
        # Create SELL position with invalid TP (TP >= Entry for SELL)
        position = position_manager.create_position_from_signal(sell_signal, volume=1.0)
        position.take_profit = 1.2600  # Invalid: TP > Entry for SELL
        position.status = PositionStatus.PENDING

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged
        await position_manager.save_position(position)

        # Verify error was handled (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_pending_buy_invalid_tp(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving PENDING BUY position with invalid TP raises error."""
        # Create BUY position with invalid TP (TP <= Entry for BUY)
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position.take_profit = 1.0900  # Invalid: TP < Entry for BUY
        position.status = PositionStatus.PENDING

        # Create mock existing DB position
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = position.position_id

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_db_pos
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - error is caught and logged
        await position_manager.save_position(position)

        # Verify error was handled (commit should not be called)
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_positions_from_db_general_exception(
        self, mock_get_session, position_manager
    ):
        """Test handling general exceptions (not ValueError) when loading positions (lines 184-191)."""
        # Create mock position that will cause general exception (not ValueError)
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_exception_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Patch Position to raise general exception (not ValueError) during creation
        # This triggers the Exception handler (lines 184-191)
        with patch(
            "trading_worker.position.position_manager.Position",
            side_effect=RuntimeError("General error"),
        ):
            # Load positions - exception should be caught and logged
            await position_manager.load_positions_from_db()

            # Position should not be loaded
            assert len(position_manager.positions) == 0


class TestAutomationLogic:
    """Test automation logic (breakeven and trailing stop) within PositionManager."""

    def test_manage_automation_pending_position(self, position_manager, buy_signal):
        """Test that automation is skipped for PENDING positions."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        # Position is PENDING by default

        # Mock automation managers to verify they are NOT called
        position_manager.breakeven_manager.should_move_to_breakeven = MagicMock()
        position_manager.trailing_stop_manager.should_activate_trailing = MagicMock()

        position_manager._manage_automation(position)

        position_manager.breakeven_manager.should_move_to_breakeven.assert_not_called()
        position_manager.trailing_stop_manager.should_activate_trailing.assert_not_called()

    def test_manage_automation_breakeven_exception(self, position_manager, buy_signal):
        """Test handling exception during breakeven update."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Mock breakeven manager to raise exception
        position_manager.breakeven_manager.should_move_to_breakeven = MagicMock(return_value=True)
        position_manager.breakeven_manager.move_to_breakeven = MagicMock(
            side_effect=ValueError("Breakeven failed")
        )

        # Should catch exception and log error, not crash
        position_manager._manage_automation(position)

        # Verify it tried to move to breakeven
        position_manager.breakeven_manager.move_to_breakeven.assert_called_once()

    def test_manage_automation_trailing_stop_update_exception(self, position_manager, buy_signal):
        """Test handling exception during trailing stop update."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Mock trailing stop manager to raise exception
        position_manager.trailing_stop_manager.should_activate_trailing = MagicMock(
            return_value=False
        )
        position_manager.trailing_stop_manager.should_update_trailing_stop = MagicMock(
            return_value=True
        )
        position_manager.trailing_stop_manager.update_trailing_stop = MagicMock(
            side_effect=ValueError("Trailing update failed")
        )

        # Should catch exception and log error, not crash
        position_manager._manage_automation(position)

        # Verify it tried to update trailing stop
        position_manager.trailing_stop_manager.update_trailing_stop.assert_called_once()


class TestOrphanedPositions:
    """Test handling of orphaned positions (OPEN positions without ticket)."""

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_orphaned_open_position_without_ticket(
        self, mock_get_session, position_manager
    ):
        """Test that OPEN position without ticket is closed and skipped (lines 186-206)."""
        # Create mock OPEN position without ticket (orphaned)
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_orphaned_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.OPEN.value  # OPEN status
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}  # No ticket in metadata
        mock_db_pos.ticket = None  # No ticket field

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - orphaned position should be closed in DB and not loaded
        await position_manager.load_positions_from_db()

        # Verify orphaned position was NOT loaded into memory
        assert len(position_manager.positions) == 0

        # Verify position was closed in database
        assert mock_db_pos.status == PositionStatus.CLOSED.value
        assert mock_db_pos.close_time is not None
        assert mock_db_pos.close_price == 1.1000  # Should use entry_price as fallback
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_pending_position_without_ticket_is_allowed(
        self, mock_get_session, position_manager
    ):
        """Test that PENDING position without ticket is allowed (not considered orphaned)."""
        # Create mock PENDING position without ticket
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_pending_no_ticket_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.PENDING.value  # PENDING status
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1000
        mock_db_pos.current_profit_pips = 0.0
        mock_db_pos.current_pnl_usd = 0.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.meta_data = {}  # No ticket
        mock_db_pos.ticket = None

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Load positions - PENDING position without ticket should be loaded
        await position_manager.load_positions_from_db()

        # Verify position WAS loaded (orphaned check only applies to OPEN positions)
        assert len(position_manager.positions) == 1
        assert "pos_pending_no_ticket_001" in position_manager.positions


class TestSavePositionDryRun:
    """Test save_position in dry-run mode."""

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_dry_run_mode(self, mock_get_session, position_manager, buy_signal):
        """Test that save_position skips database in dry-run mode (lines 254-257)."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        # Save position in dry-run mode
        await position_manager.save_position(position, is_dry_run=True)

        # Verify get_session was NOT called (skipped database)
        mock_get_session.assert_not_called()

        # Position should still exist in memory
        assert position.position_id in position_manager.positions


class TestSavePositionConfluenceScore:
    """Test save_position with confluence_score handling."""

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_confluence_score_from_attribute(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving position with confluence_score from position attribute (line 266)."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position.confluence_score = 85.5  # Set as attribute

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # New position
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify position was saved with confluence_score
        mock_session.add.assert_called_once()
        added_pos = mock_session.add.call_args[0][0]
        assert added_pos.confluence_score == 85.5

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_ticket_from_metadata(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Test saving position with ticket from metadata when not on position object (line 278)."""
        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        # Set ticket in metadata, not on position object
        position.metadata["ticket"] = 67890
        # Don't set position.ticket (it's None)

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # New position
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position
        await position_manager.save_position(position)

        # Verify ticket was retrieved from metadata
        mock_session.add.assert_called_once()
        added_pos = mock_session.add.call_args[0][0]
        assert added_pos.ticket == 67890


class TestCreatePositionWithPriceAction:
    """Test create_position_from_signal with price_action metadata."""

    def test_create_position_with_price_action_info(self, position_manager, buy_signal):
        """Test creating position with price_action info from signal metadata (lines 413-418)."""
        # Add price_action info to signal metadata
        buy_signal.metadata = {
            "price_action": {
                "desc": "Bullish Engulfing",
                "status": "confirmed",
                "confidence": 0.85,
            }
        }

        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        # Verify price_action info was stored in position metadata
        assert "price_action" in position.metadata
        assert position.metadata["price_action"]["pattern_type"] == "Bullish Engulfing"
        assert position.metadata["price_action"]["status"] == "confirmed"
        assert position.metadata["price_action"]["pattern_details"]["confidence"] == 0.85

    def test_create_position_without_price_action_info(self, position_manager, buy_signal):
        """Test creating position without price_action info (metadata is None or empty)."""
        # No price_action in metadata
        buy_signal.metadata = {}

        # Create position
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)

        # Verify price_action is NOT in position metadata
        assert "price_action" not in position.metadata


class TestMaxDurationChecking:
    """Test _check_max_duration method (lines 605-609, 643, 661-699)."""

    def test_check_max_duration_no_open_time(self, position_manager, buy_signal):
        """Test _check_max_duration returns False when position has no open_time (line 643)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position.open_time = None  # No open time

        # Should return False (skip check)
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is False

    def test_check_max_duration_no_config(self, position_manager, buy_signal):
        """Test _check_max_duration when max_duration_hours is not configured."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config without max_position_duration_hours
        position_manager.config["trading_types"] = {"day_trading": {}}

        # Should return False (skip check)
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is False

    def test_check_max_duration_not_exceeded(self, position_manager, buy_signal):
        """Test _check_max_duration when duration not exceeded (line 668)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with 4 hour max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 4.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Create position that was opened 1 hour ago (not exceeded)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=1)

        # Should return False (duration not exceeded)
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is False

    def test_check_max_duration_exceeded_but_in_loss(self, position_manager, buy_signal):
        """Test _check_max_duration when exceeded but position is in loss (lines 669-687)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with 1 hour max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 1.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Create position that was opened 2 hours ago (exceeded)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=2)

        # Update position to be in loss (price moved against us)
        position_manager.update_position(position.position_id, 1.0970)  # Below entry
        # Position is now in loss (negative profit)

        # Should return False (in loss, don't force close)
        result = position_manager._check_max_duration(position, 1.0970)
        assert result is False
        assert position.is_open  # Position should still be open

    def test_check_max_duration_exceeded_and_in_profit(self, position_manager, buy_signal):
        """Test _check_max_duration when exceeded and position is in profit (lines 689-697)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with 1 hour max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 1.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Create position that was opened 2 hours ago (exceeded)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=2)

        # Update position to be in profit
        position_manager.update_position(position.position_id, 1.1050)  # Above entry
        # Position is now in profit

        # Should return True and close position
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is True
        assert position.is_closed  # Position should be closed
        assert position.close_price == 1.1050
        assert position.metadata.get("close_reason") == "MAX_DURATION"

    def test_check_max_duration_with_pnl_profit_check(self, position_manager, buy_signal):
        """Test _check_max_duration uses both pips and USD to determine profit (line 677)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with 1 hour max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 1.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Create position that was opened 2 hours ago (exceeded)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=2)

        # Update position - manually set profit values to test both checks
        position.current_price = 1.1050
        position.current_profit_pips = 50.0  # Positive pips
        position.current_pnl_usd = 0.0  # Zero USD (but pips is positive)

        # Should return True (profit detected via pips)
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is True

    def test_check_max_duration_root_trading_type_config(self, position_manager, buy_signal):
        """Test _check_max_duration reads active_trading_type from root config (line 650)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with active_trading_type at root level (not in trading_types section)
        position_manager.config["active_trading_type"] = "scalping"
        position_manager.config["trading_types"] = {
            "scalping": {"max_position_duration_hours": 0.5}
        }

        # Create position that was opened 1 hour ago (exceeded for scalping)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=1)

        # Update position to be in profit
        position_manager.update_position(position.position_id, 1.1050)

        # Should return True (uses root config)
        result = position_manager._check_max_duration(position, 1.1050)
        assert result is True

    def test_check_max_duration_duration_seconds_none(self, position_manager, buy_signal):
        """Test _check_max_duration when duration_seconds is None (line 663)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 1.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Set open_time but mock duration_seconds to return None
        # This can happen in edge cases where the calculation fails
        position.open_time = datetime.now()

        # Mock the duration_seconds property to return None
        with patch.object(
            type(position), "duration_seconds", new_callable=PropertyMock
        ) as mock_duration:
            mock_duration.return_value = None

            # Should return False (skip check when duration_seconds is None)
            result = position_manager._check_max_duration(position, 1.1050)
            assert result is False


class TestCheckAndClosePositionsMaxDuration:
    """Test check_and_close_positions with max duration logging (lines 605-609)."""

    def test_check_and_close_max_duration_exceeded(self, position_manager, buy_signal):
        """Test check_and_close_positions closes position when max duration exceeded (lines 605-609)."""
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        position_manager.open_position(position.position_id)

        # Config with 1 hour max duration
        position_manager.config["trading_types"] = {
            "day_trading": {"max_position_duration_hours": 1.0}
        }
        position_manager.config["active_trading_type"] = "day_trading"

        # Create position that was opened 2 hours ago (exceeded)
        from datetime import timedelta

        position.open_time = datetime.now() - timedelta(hours=2)

        # Update position to be in profit
        position_manager.update_position(position.position_id, 1.1050)

        # Check and close positions
        prices = {"EURUSD": 1.1050}
        closed = position_manager.check_and_close_positions(prices)

        # Verify position was closed
        assert len(closed) == 1
        assert position.is_closed
        assert position.metadata.get("close_reason") == "MAX_DURATION"


class TestRestoreAutomationTracking:
    """Test _restore_automation_tracking method (coverage gap fix)."""

    def _build_mock_db_position(self, breakeven=False, trailing=False, profit_pips=0.0):
        """Build a mock DB position with automation flags."""
        mock_db_pos = MagicMock(spec=DBPosition)
        mock_db_pos.position_id = "pos_auto_001"
        mock_db_pos.symbol = "EURUSD"
        mock_db_pos.position_type = PositionType.BUY.value
        mock_db_pos.status = PositionStatus.OPEN.value
        mock_db_pos.entry_price = 1.1000
        mock_db_pos.stop_loss = 1.0950
        mock_db_pos.take_profit = 1.1150
        mock_db_pos.volume = 1.0
        mock_db_pos.pip_size = 0.0001
        mock_db_pos.pip_value_per_lot = 10.0
        mock_db_pos.open_time = datetime.now()
        mock_db_pos.close_time = None
        mock_db_pos.close_price = None
        mock_db_pos.current_price = 1.1050
        mock_db_pos.current_profit_pips = profit_pips
        mock_db_pos.current_pnl_usd = 50.0
        mock_db_pos.risk_amount_usd = 50.0
        mock_db_pos.potential_profit_usd = 150.0
        mock_db_pos.breakeven_activated = breakeven
        mock_db_pos.trailing_activated = trailing
        mock_db_pos.meta_data = {"ticket": "12345"}
        mock_db_pos.ticket = 12345
        return mock_db_pos

    def _mock_session_with_position(self, db_pos):
        """Build mock session yielding the given DB position."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [db_pos]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        return mock_session_context

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_restores_breakeven_tracking(self, mock_get_session, position_manager):
        """Lines 302-304: Restore breakeven tracking when position has breakeven_activated."""
        db_pos = self._build_mock_db_position(breakeven=True)
        mock_get_session.return_value = self._mock_session_with_position(db_pos)

        await position_manager.load_positions_from_db()

        # Verify position loaded and breakeven tracking restored
        assert "pos_auto_001" in position_manager.positions
        assert "pos_auto_001" in position_manager.breakeven_manager.breakeven_positions

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_restores_trailing_tracking(self, mock_get_session, position_manager):
        """Lines 306-311: Restore trailing tracking when position has trailing_activated."""
        db_pos = self._build_mock_db_position(trailing=True, profit_pips=30.0)
        mock_get_session.return_value = self._mock_session_with_position(db_pos)

        await position_manager.load_positions_from_db()

        # Verify position loaded and trailing tracking restored
        assert "pos_auto_001" in position_manager.positions
        assert "pos_auto_001" in position_manager.trailing_stop_manager.trailing_active
        assert position_manager.trailing_stop_manager.highest_profit["pos_auto_001"] == 30.0

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_load_restores_both_automations(self, mock_get_session, position_manager):
        """Both breakeven and trailing restored when both activated."""
        db_pos = self._build_mock_db_position(breakeven=True, trailing=True, profit_pips=45.0)
        mock_get_session.return_value = self._mock_session_with_position(db_pos)

        await position_manager.load_positions_from_db()

        assert "pos_auto_001" in position_manager.breakeven_manager.breakeven_positions
        assert "pos_auto_001" in position_manager.trailing_stop_manager.trailing_active


class TestSavePositionMetadataFallback:
    """Test save_position metadata fallbacks (coverage gap fix)."""

    @pytest.mark.asyncio
    @patch("trading_worker.position.position_manager.get_session")
    async def test_save_position_confluence_from_metadata(
        self, mock_get_session, position_manager, buy_signal
    ):
        """Lines 346-347: confluence_score fallback to metadata when attribute missing/zero."""
        # Create position - confluence_score will be 75 from signal
        position = position_manager.create_position_from_signal(buy_signal, volume=1.0)
        # Force confluence_score to 0 so fallback kicks in
        position.confluence_score = 0
        position.metadata = {"confluence_score": 88.0, "ticket": 99999}
        position.ticket = 99999

        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # New position
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_session.return_value = mock_session_context

        # Save position - should pull confluence from metadata
        await position_manager.save_position(position)

        # Verify save happened
        mock_session.add.assert_called_once()
        added_db_pos = mock_session.add.call_args[0][0]
        # The confluence_score from metadata should be used
        assert added_db_pos.confluence_score == 88.0
