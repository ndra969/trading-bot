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


@pytest.mark.asyncio
async def test_finalize_max_duration_close_resolves_ticket_via_orchestrator(trading_bot):
    """Regression: max-duration close must resolve the MT5 ticket through the
    orchestrator, not via a (now-removed) TradingBot._resolve_mt5_ticket method.

    Previously this raised: 'TradingBot' object has no attribute '_resolve_mt5_ticket'.
    """
    position = Position(
        position_id="pos_maxdur_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
        current_price=1.1050,
    )
    position.ticket = 99999
    position.current_pnl_usd = 34.88
    position.current_profit_pips = 43.6

    trading_bot.symbol_mapper.convert_to_broker_symbol.return_value = "EURUSDm"
    trading_bot.position_manager.save_position = AsyncMock()
    trading_bot.position_orchestrator._update_session_on_position_close = AsyncMock()
    trading_bot.notification_manager.send_message = AsyncMock()

    # Must not raise AttributeError on _resolve_mt5_ticket.
    await trading_bot._finalize_max_duration_close(position, is_dry_run=False)

    # Ticket resolved via fast path and forwarded to the MT5 close call.
    trading_bot.mt5.close_position.assert_called_once()
    assert trading_bot.mt5.close_position.call_args.kwargs["ticket"] == 99999


@pytest.mark.asyncio
async def test_partial_close_reads_manager_result_key(trading_bot):
    """Regression: orchestrator must read 'close_volume' (the key the manager
    returns), not 'closed_volume'. The mismatch made the result look empty and
    silently skipped the MT5 sync + save + notify on every partial close.
    """
    position = Position(
        position_id="pos_partial_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
        current_price=1.1050,
    )

    # Manager returns the real key set ("close_volume", "profit_usd", ...).
    trading_bot.partial_manager = MagicMock()
    trading_bot.partial_manager.execute_partial_close.return_value = {
        "level": 1,
        "close_volume": 0.5,
        "remaining_volume": 0.5,
        "close_price": 1.1050,
        "profit_pips": 50.0,
        "profit_usd": 25.0,
    }
    trading_bot.position_manager.save_position = AsyncMock()

    # Dry-run skips MT5; if the result key matched, save_position runs.
    await trading_bot.position_orchestrator._handle_partial_close_automation(
        position, is_dry_run=True
    )

    # Pre-fix this early-returned (result.get("closed_volume", 0) == 0) and never saved.
    trading_bot.position_manager.save_position.assert_awaited_once()


@pytest.mark.asyncio
async def test_sl_close_uses_authoritative_mt5_pnl(trading_bot):
    """Regression: a price-based SL/TP close must record MT5's actual deal P&L
    (profit + swap + commission), not the pip recompute. The pip-only value
    over-reports held positions (omits swap, inherits pip-value/spread drift) —
    e.g. 2026-06-22 multi-day holds read ~+7 vs the broker's true figure.
    """
    position = Position(
        position_id="pos_auth_pnl_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.OPEN,
        current_price=1.0950,
    )
    position.ticket = 555

    trading_bot.data_manager = MagicMock()  # _check_position_closure early-returns without it
    trading_bot.position_manager.get_open_positions.return_value = [position]
    trading_bot.position_manager.update_position = MagicMock()
    trading_bot.position_manager._check_max_duration = MagicMock(return_value=False)
    # PositionTracker's pip recompute — optimistic, omits swap.
    trading_bot.position_manager.close_position.return_value = {"pnl_usd": 11.39, "pips": 17.9}
    trading_bot.position_manager.save_position = AsyncMock()
    trading_bot.notification_manager.send_message = AsyncMock()
    trading_bot.position_orchestrator._update_session_on_position_close = AsyncMock()
    trading_bot._get_current_price = AsyncMock(return_value=1.0950)  # at SL → should_close

    # Broker's authoritative deal: profit 9.00 + swap -1.24 = 7.76 net.
    trading_bot.mt5.get_history_deal.return_value = {
        "price": 1.0950,
        "profit": 9.00,
        "swap": -1.24,
        "commission": 0.0,
        "reason": 4,  # DEAL_REASON_SL (not None → authoritative)
    }

    await trading_bot.position_orchestrator._check_position_closure()

    # Realized P&L reflects the broker (7.76), NOT the pip recompute (11.39).
    assert position.realized_pnl_usd == pytest.approx(7.76)
    # And the balance update used the authoritative figure, not the pip value.
    trading_bot.portfolio_risk.update_balance.assert_called_once_with(10000.0 + 7.76)
