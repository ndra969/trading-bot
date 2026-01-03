"""
Integration tests for opening new positions after sync close.

Tests that after a position is closed via MT5 sync, a new position
can be opened for the same symbol.
"""

import pytest

from trading_bot.position.position_manager import PositionManager
from trading_bot.position.position_models import PositionStatus
from trading_bot.strategies.models import SignalDirection, TradingSignal


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    return {
        "trading": {"dry_run": False},
        "position_manager": {"max_positions_per_symbol": 1},
    }


@pytest.fixture
def position_manager(mock_config):
    """Create PositionManager instance."""
    return PositionManager(mock_config)


@pytest.mark.asyncio
async def test_can_open_new_position_after_sync_close(position_manager):
    """Test that new position can be opened after old position is closed via sync."""
    # Create initial position
    signal1 = TradingSignal(
        signal_id="sig_001",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        confluence_score=75.0,
        risk_reward_ratio=3.0,
    )

    position1 = position_manager.create_position_from_signal(signal1, volume=1.0)
    position_manager.open_position(position1.position_id)

    # Verify position is open
    assert position1.is_open is True
    assert len(position_manager.get_open_positions()) == 1

    # Close position (simulating sync close)
    position_manager.close_position(position1.position_id, 1.1050)

    # Verify position is closed
    assert position1.is_open is False
    assert position1.status == PositionStatus.CLOSED
    assert len(position_manager.get_open_positions()) == 0

    # Verify get_positions_by_symbol still returns the closed position
    all_positions = position_manager.get_positions_by_symbol("EURUSD")
    assert len(all_positions) == 1
    assert all_positions[0].position_id == position1.position_id

    # But open_positions filter should exclude it
    open_positions = [p for p in all_positions if p.is_open]
    assert len(open_positions) == 0

    # Now try to create new position for same symbol - should succeed
    signal2 = TradingSignal(
        signal_id="sig_002",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1100,
        stop_loss=1.1050,
        take_profit=1.1250,
        confluence_score=80.0,
        risk_reward_ratio=3.0,
    )

    # Should NOT raise ValueError (position limit should not be reached)
    position2 = position_manager.create_position_from_signal(signal2, volume=1.0)

    # Verify new position was created
    assert position2.position_id != position1.position_id
    assert position2.symbol == "EURUSD"
    assert position2.status == PositionStatus.PENDING

    # Verify we now have 2 positions total
    all_positions = position_manager.get_positions_by_symbol("EURUSD")
    assert len(all_positions) == 2

    # Verify position limit check: only 0 open positions (old is closed, new is PENDING)
    open_positions = [p for p in all_positions if p.is_open]
    assert len(open_positions) == 0  # New position is PENDING, not OPEN yet

    # But new position exists and is PENDING (can be opened)
    pending_positions = [p for p in all_positions if p.status == PositionStatus.PENDING]
    assert len(pending_positions) == 1
    assert pending_positions[0].position_id == position2.position_id


@pytest.mark.asyncio
async def test_cannot_open_new_position_if_old_still_open(position_manager):
    """Test that new position cannot be opened if old position is still open."""
    # Create initial position
    signal1 = TradingSignal(
        signal_id="sig_001",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        confluence_score=75.0,
        risk_reward_ratio=3.0,
    )

    position1 = position_manager.create_position_from_signal(signal1, volume=1.0)
    position_manager.open_position(position1.position_id)

    # Verify position is open
    assert position1.is_open is True

    # Try to create new position for same symbol - should FAIL
    signal2 = TradingSignal(
        signal_id="sig_002",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1100,
        stop_loss=1.1050,
        take_profit=1.1250,
        confluence_score=80.0,
        risk_reward_ratio=3.0,
    )

    # Should raise ValueError (position limit reached)
    with pytest.raises(ValueError, match="Position limit reached"):
        position_manager.create_position_from_signal(signal2, volume=1.0)


@pytest.mark.asyncio
async def test_can_open_new_position_after_multiple_closes(position_manager):
    """Test that new position can be opened after multiple positions are closed."""
    # Create and close multiple positions
    for i in range(3):
        signal = TradingSignal(
            signal_id=f"sig_{i:03d}",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000 + i * 0.001,
            stop_loss=1.0950 + i * 0.001,
            take_profit=1.1150 + i * 0.001,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )

        position = position_manager.create_position_from_signal(signal, volume=1.0)
        position_manager.open_position(position.position_id)
        position_manager.close_position(position.position_id, 1.1050)

    # Verify all positions are closed
    assert len(position_manager.get_open_positions()) == 0

    # Verify we have 3 closed positions
    all_positions = position_manager.get_positions_by_symbol("EURUSD")
    assert len(all_positions) == 3
    assert all(p.status == PositionStatus.CLOSED for p in all_positions)

    # Now try to create new position - should succeed
    signal_new = TradingSignal(
        signal_id="sig_new",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1200,
        stop_loss=1.1150,
        take_profit=1.1350,
        confluence_score=85.0,
        risk_reward_ratio=3.0,
    )

    position_new = position_manager.create_position_from_signal(signal_new, volume=1.0)

    # Verify new position was created
    assert position_new.status == PositionStatus.PENDING

    # Verify we now have 4 positions total
    all_positions = position_manager.get_positions_by_symbol("EURUSD")
    assert len(all_positions) == 4

    # Verify position limit check: only 0 open positions (all old are closed, new is PENDING)
    open_positions = [p for p in all_positions if p.is_open]
    assert len(open_positions) == 0  # New position is PENDING, not OPEN yet

    # But new position exists and is PENDING (can be opened)
    pending_positions = [p for p in all_positions if p.status == PositionStatus.PENDING]
    assert len(pending_positions) == 1
    assert pending_positions[0].position_id == position_new.position_id


@pytest.mark.asyncio
async def test_position_limit_check_uses_is_open_filter(position_manager):
    """Test that position limit check correctly filters by is_open."""
    # Create position and open it
    signal1 = TradingSignal(
        signal_id="sig_001",
        symbol="EURUSD",
        direction=SignalDirection.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        confluence_score=75.0,
        risk_reward_ratio=3.0,
    )

    position1 = position_manager.create_position_from_signal(signal1, volume=1.0)
    position_manager.open_position(position1.position_id)

    # Close it
    position_manager.close_position(position1.position_id, 1.1050)

    # Verify position limit check works correctly
    existing_positions = position_manager.get_positions_by_symbol("EURUSD")
    open_positions = [p for p in existing_positions if p.is_open]

    assert len(existing_positions) == 1  # Total positions
    assert len(open_positions) == 0  # Open positions (should be 0)

    # Position limit should not be reached
    assert len(open_positions) < position_manager.max_positions_per_symbol
