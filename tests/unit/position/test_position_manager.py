"""Tests for PositionManager."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from trading_bot.data.models import Position as DBPosition
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
    @patch("trading_bot.position.position_manager.get_session")
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
            "trading_bot.position.position_manager.Position",
            side_effect=RuntimeError("General error"),
        ):
            # Load positions - exception should be caught and logged
            await position_manager.load_positions_from_db()

            # Position should not be loaded
            assert len(position_manager.positions) == 0
