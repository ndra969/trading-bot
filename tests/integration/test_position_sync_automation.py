"""
Integration tests for position synchronization preventing automation on closed positions.

Tests that automation (breakeven, trailing stop, partial close) does not run
on positions that have been closed in MT5.
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
        bot.position_orchestrator._check_position_automation = AsyncMock()

        yield bot


@pytest.mark.asyncio
async def test_automation_not_run_on_position_closed_during_update(trading_bot):
    """Test that automation is not run on position closed during update check."""
    # Create mock position with ticket
    position = Position(
        position_id="pos_auto_001",
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
    position.ticket = 12345

    # Setup: Position exists in DB but not in MT5 (closed during update)
    def mock_get_open_positions():
        # First call: return position (before update check)
        # Second call: return empty (after close)
        if not hasattr(mock_get_open_positions, "call_count"):
            mock_get_open_positions.call_count = 0
        mock_get_open_positions.call_count += 1
        if mock_get_open_positions.call_count == 1:
            return [position]
        else:
            return []

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions
    trading_bot.mt5.get_positions.return_value = []  # No positions in MT5
    trading_bot.mt5.get_history_deal.return_value = {
        "price": 1.1050,
        "profit": 50.0,
        "swap": 0.0,
        "commission": 0.0,
    }

    # Mock close_position
    trading_bot.position_manager.close_position.return_value = {
        "pnl_usd": 50.0,
        "pips": 50.0,
    }
    trading_bot.position_manager.save_position = AsyncMock()

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was closed during update check
    trading_bot.position_manager.close_position.assert_called()

    # CRITICAL: Verify automation was NOT called (position was closed)
    trading_bot.position_orchestrator._check_position_automation.assert_not_called()


@pytest.mark.asyncio
async def test_automation_run_on_position_still_open(trading_bot):
    """Test that automation is run on position that is still open."""
    # Create mock position with ticket
    position = Position(
        position_id="pos_auto_002",
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
    position.ticket = 12345

    # Setup: Position exists in both DB and MT5
    def mock_get_open_positions():
        return [position]

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions
    trading_bot.mt5.get_positions.return_value = [
        {"ticket": 12345, "symbol": "EURUSDm", "price_open": 1.1000}
    ]

    trading_bot.position_manager.update_position = MagicMock()
    trading_bot.position_manager.save_position = AsyncMock()

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify position was NOT closed
    trading_bot.position_manager.close_position.assert_not_called()

    # Verify automation WAS called (position still open)
    trading_bot.position_orchestrator._check_position_automation.assert_called_once_with(position)


@pytest.mark.asyncio
async def test_automation_not_run_on_position_already_closed(trading_bot):
    """Test that automation is not run on position that is already closed."""

    # Setup: Position is closed (get_open_positions should not return closed positions)
    def mock_get_open_positions():
        # get_open_positions should not return closed positions
        return []

    trading_bot.position_manager.get_open_positions.side_effect = mock_get_open_positions

    # Run sync
    await trading_bot.position_orchestrator.manage_positions()

    # Verify automation was NOT called (position is closed)
    trading_bot.position_orchestrator._check_position_automation.assert_not_called()
