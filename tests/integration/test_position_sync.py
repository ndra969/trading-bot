"""
Integration tests for position synchronization with MT5.

Tests the _manage_positions function to ensure positions closed in MT5
are properly updated in the database.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from trading_worker.main import TradingBot
from trading_worker.position.position_models import Position, PositionStatus, PositionType
from trading_worker.services.position_orchestrator import PositionOrchestrator


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "trading": {"dry_run": False},
        "position_manager": {"max_positions_per_symbol": 1},
    }


@pytest.fixture
def trading_bot(mock_config):
    """Create TradingBot instance with mocked dependencies."""
    with (
        patch("trading_worker.main.MT5Connector"),
        patch("trading_worker.main.SymbolMapper"),
        patch("trading_worker.main.FoundationEngine"),
        patch("trading_worker.main.PositionManager"),
        patch("trading_worker.main.PortfolioRiskManager"),
        patch("trading_worker.main.ExposureManager"),
        patch("trading_worker.main.NotificationManager"),
    ):

        # Create bot instance
        bot = TradingBot(mock_config)

        # Setup mocks
        bot.mt5 = MagicMock()
        bot.mt5.is_connected.return_value = True
        bot.mt5.get_positions.return_value = []
        bot.mt5.get_history_deal.return_value = None

        bot.symbol_mapper = MagicMock()
        bot.active_broker = "exness_standard"

        bot.position_manager = MagicMock()
        bot.position_manager.get_open_positions.return_value = []

        bot.portfolio_risk = MagicMock()
        bot.portfolio_risk.current_balance = 10000.0

        bot.exposure_manager = MagicMock()

        bot._get_current_price = AsyncMock(return_value=1.1000)
        bot._get_asset_class = MagicMock(return_value="forex")

        # Position management lives in the orchestrator (normally wired in
        # _initialize_position_risk_system, which start() calls).
        bot.position_orchestrator = PositionOrchestrator(bot)

        yield bot


@pytest.mark.asyncio
async def test_sync_position_closed_in_mt5_with_ticket(trading_bot):
    """Test that position with ticket closed in MT5 is updated to CLOSED."""
    # Create mock position with ticket
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
    position.ticket = 12345

    # Setup: Position exists in DB but not in MT5
    trading_bot.position_manager.get_open_positions.return_value = [position]
    trading_bot.mt5.get_positions.return_value = []  # No positions in MT5
    trading_bot.mt5.get_history_deal.return_value = {
        "price": 1.1050,
        "profit": 50.0,
        "swap": 0.0,
        "commission": 0.0,
        "comment": "Closed by SL",
        "reason": 4,  # DEAL_REASON_SL
    }

    # Mock close_position and save_position
    trading_bot.position_manager.close_position.return_value = {
        "pnl_usd": 50.0,
        "pips": 50.0,
    }
    trading_bot.position_manager.save_position = AsyncMock()

    # After close_position is called, position status changes to CLOSED
    # So get_open_positions should return empty list after first call
    def mock_get_open_positions():
        # First call: return position (before close)
        # Second call: return empty (after close)
        if not hasattr(mock_get_open_positions, "call_count"):
            mock_get_open_positions.call_count = 0
        mock_get_open_positions.call_count += 1
        if mock_get_open_positions.call_count == 1:
            return [position]
        else:
            # After close, position status is CLOSED, so not returned
            return []

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was closed with canonical CloseReason
    trading_bot.position_manager.close_position.assert_called_once_with(
        "pos_001", 1.1050, "STOP_LOSS"
    )
    # save_position is called once during sync close, and once more during update
    # But since position is closed, second call shouldn't happen
    assert trading_bot.position_manager.save_position.call_count >= 1

    # Verify portfolio balance was updated
    trading_bot.portfolio_risk.update_balance.assert_called_once_with(10050.0)

    # Verify exposure was unregistered
    trading_bot.exposure_manager.unregister_position.assert_called_once_with("EURUSD", "forex", 1.0)

    # Verify outcome fields reflect the broker's AUTHORITATIVE MT5 deal P&L
    # (profit + swap + commission = 50.0), not a pip-recomputed approximation.
    # This is the MT5-server-side (SL) close path the bot only detects via sync.
    assert position.realized_pnl_usd == 50.0
    assert position.is_winner is True
    assert position.exit_type == "WIN"


@pytest.mark.asyncio
async def test_sync_position_closed_in_mt5_no_ticket_no_symbol_match(trading_bot):
    """Test that position without ticket not found in MT5 is closed."""
    # Create mock position without ticket
    position = Position(
        position_id="pos_002",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
        current_price=1.1000,
    )
    position.ticket = None

    # Setup: Position exists in DB but not in MT5 (no matching symbol)
    trading_bot.position_manager.get_open_positions.return_value = [position]
    trading_bot.mt5.get_positions.return_value = []  # No positions in MT5
    trading_bot._get_current_price.return_value = 1.1050

    # Mock close_position and save_position
    trading_bot.position_manager.close_position.return_value = {
        "pnl_usd": 50.0,
        "pips": 50.0,
    }
    trading_bot.position_manager.save_position = AsyncMock()

    # After close_position is called, position status changes to CLOSED
    def mock_get_open_positions():
        if not hasattr(mock_get_open_positions, "call_count"):
            mock_get_open_positions.call_count = 0
        mock_get_open_positions.call_count += 1
        if mock_get_open_positions.call_count == 1:
            return [position]
        else:
            return []

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was closed with estimated price
    trading_bot.position_manager.close_position.assert_called_once()
    call_args = trading_bot.position_manager.close_position.call_args
    assert call_args[0][0] == "pos_002"
    assert call_args[0][1] == 1.1050  # Current price
    # No ticket → orphaned path
    assert call_args[0][2] == "ORPHANED"

    # save_position is called at least once during sync close
    assert trading_bot.position_manager.save_position.call_count >= 1


@pytest.mark.asyncio
async def test_sync_position_still_open_in_mt5(trading_bot):
    """Test that position still open in MT5 is not closed."""
    # Create mock position with ticket
    position = Position(
        position_id="pos_003",
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
    position.ticket = 12345

    # Setup: Position exists in both DB and MT5
    def mock_get_open_positions():
        return [position]

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions
    trading_bot.mt5.get_positions.return_value = [
        {"ticket": 12345, "symbol": "EURUSDm", "price_open": 1.1000}
    ]

    # Mock update_position
    trading_bot.position_manager.update_position = MagicMock()
    trading_bot.position_manager.save_position = AsyncMock()
    trading_bot.position_orchestrator._check_position_automation = AsyncMock()

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was NOT closed
    trading_bot.position_manager.close_position.assert_not_called()

    # Verify position was updated with current price
    trading_bot.position_manager.update_position.assert_called()

    # Verify automation was checked (position still open)
    trading_bot.position_orchestrator._check_position_automation.assert_called_once()


@pytest.mark.asyncio
async def test_sync_position_no_ticket_symbol_exists_in_mt5(trading_bot):
    """Test that position without ticket but symbol exists in MT5 logs warning."""
    # Create mock position without ticket
    position = Position(
        position_id="pos_004",
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
    position.ticket = None

    # Setup: Position exists in DB; MT5 has a same-symbol position but with a
    # different entry price, so it cannot be matched to ours.
    trading_bot.position_manager.get_open_positions.return_value = [position]
    trading_bot.mt5.get_positions.return_value = [
        {"ticket": 99999, "symbol": "EURUSDm", "price_open": 1.2000}  # Different entry price
    ]
    trading_bot.symbol_mapper.convert_to_broker_symbol.return_value = "EURUSDm"
    trading_bot.position_manager.close_position.return_value = {"pnl_usd": 0.0, "pips": 0.0}
    trading_bot.position_manager.save_position = AsyncMock()

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # A ticketless position that can't be matched to any MT5 position is
    # reconciled by closing it as ORPHANED (see CloseReason.ORPHANED).
    trading_bot.position_manager.close_position.assert_called_once()
    assert trading_bot.position_manager.close_position.call_args.args[2] == "ORPHANED"


@pytest.mark.asyncio
async def test_sync_position_no_history_deal(trading_bot):
    """Test that position closed in MT5 without history deal uses estimated close."""
    # Create mock position with ticket
    position = Position(
        position_id="pos_005",
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
    position.ticket = 12345

    # Setup: Position exists in DB but not in MT5, no history deal
    trading_bot.position_manager.get_open_positions.return_value = [position]
    trading_bot.mt5.get_positions.return_value = []
    trading_bot.mt5.get_history_deal.return_value = None  # No history deal

    # Mock close_position and save_position
    trading_bot.position_manager.close_position.return_value = {
        "pnl_usd": 0.0,
        "pips": 0.0,
    }
    trading_bot.position_manager.save_position = AsyncMock()

    # After close_position is called, position status changes to CLOSED
    def mock_get_open_positions():
        if not hasattr(mock_get_open_positions, "call_count"):
            mock_get_open_positions.call_count = 0
        mock_get_open_positions.call_count += 1
        if mock_get_open_positions.call_count == 1:
            return [position]
        else:
            return []

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was closed with entry price (fallback)
    trading_bot.position_manager.close_position.assert_called_once()
    call_args = trading_bot.position_manager.close_position.call_args
    assert call_args[0][0] == "pos_005"
    assert call_args[0][1] == 1.1000  # Entry price as fallback
    # No MT5 deal info available → resolver returns UNKNOWN
    assert call_args[0][2] == "UNKNOWN"

    # save_position is called at least once during sync close
    assert trading_bot.position_manager.save_position.call_count >= 1


@pytest.mark.asyncio
async def test_sync_dry_run_mode(trading_bot, mock_config):
    """Test that sync is skipped in dry-run mode."""
    # Set dry-run mode
    mock_config["trading"]["dry_run"] = True

    # Create mock position
    position = Position(
        position_id="pos_006",
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
    position.ticket = 12345

    trading_bot.position_manager.get_open_positions.return_value = [position]

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify MT5 sync was not called
    trading_bot.mt5.get_positions.assert_not_called()


@pytest.mark.asyncio
async def test_sync_mt5_not_connected(trading_bot):
    """Test that sync is skipped when MT5 is not connected."""
    # Set MT5 as not connected
    trading_bot.mt5.is_connected.return_value = False

    # Create mock position
    position = Position(
        position_id="pos_007",
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

    trading_bot.position_manager.get_open_positions.return_value = [position]

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify MT5 sync was not called
    trading_bot.mt5.get_positions.assert_not_called()
