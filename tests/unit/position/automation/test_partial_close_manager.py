"""Tests for PartialCloseManager."""

import pytest

from trading_bot.position.automation.partial_close_manager import (
    PartialCloseLevel,
    PartialCloseManager,
)
from trading_bot.position.position_models import Position, PositionStatus, PositionType


@pytest.fixture
def partial_manager():
    """Create a PartialCloseManager instance with partial-close enabled.

    Defaults to disabled per config (small/cent accounts can't satisfy the
    0.01-lot minimum on a 25% close anyway). Tests that exercise the
    fire-on-level logic need it explicitly on.
    """
    return PartialCloseManager(config={"partial_close": {"enabled": True}})


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


class TestPartialCloseManagerInitialization:
    """Test PartialCloseManager initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        manager = PartialCloseManager()
        assert manager.pip_calculator is not None
        assert len(manager.partial_closes) == 0
        assert len(manager.remaining_volume) == 0


class TestInitializePosition:
    """Test initialize_position method."""

    def test_initialize_position(self, partial_manager, buy_position_forex):
        """Test initializing position for tracking."""
        partial_manager.initialize_position(buy_position_forex)

        assert buy_position_forex.position_id in partial_manager.partial_closes
        assert buy_position_forex.position_id in partial_manager.remaining_volume
        assert partial_manager.remaining_volume[buy_position_forex.position_id] == 1.0


class TestGetNextLevel:
    """Test get_next_level method."""

    def test_get_next_level_first(self, partial_manager, buy_position_forex):
        """Test getting first partial close level (50% of TP)."""
        partial_manager.initialize_position(buy_position_forex)

        # TP distance: 1.1150 - 1.1000 = 0.0150 = 150 pips
        # Level 1: 50% of TP = 75 pips

        next_level = partial_manager.get_next_level(buy_position_forex)

        assert next_level is not None
        assert next_level.level == 1
        assert next_level.distance_pips == pytest.approx(75.0, abs=0.1)  # 50% of 150 pips
        assert next_level.close_percentage == 0.25

    def test_get_next_level_second(self, partial_manager, buy_position_forex):
        """Test getting second partial close level (80% of TP)."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1]

        # TP distance: 150 pips
        # Level 2: 80% of TP = 120 pips

        next_level = partial_manager.get_next_level(buy_position_forex)

        assert next_level is not None
        assert next_level.level == 2
        assert next_level.distance_pips == pytest.approx(120.0, abs=0.1)  # 80% of 150 pips

    def test_get_next_level_none_all_completed(self, partial_manager, buy_position_forex):
        """Test getting next level when all completed."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1, 2]

        next_level = partial_manager.get_next_level(buy_position_forex)

        assert next_level is None


class TestShouldClosePartial:
    """Test should_close_partial method."""

    def test_should_close_partial_level_1_hit(self, partial_manager, buy_position_forex):
        """Test should close partial when level 1 hit (50% of TP = 75 pips)."""
        partial_manager.initialize_position(buy_position_forex)
        # TP distance: 150 pips, Level 1: 75 pips (50% of TP)
        buy_position_forex.current_price = 1.1075
        buy_position_forex.current_profit_pips = 75.0

        assert partial_manager.should_close_partial(buy_position_forex) is True

    def test_should_close_partial_disabled(self, buy_position_forex):
        """Disabled manager never partial-closes (global off switch)."""
        manager = PartialCloseManager(config={"partial_close": {"enabled": False}})
        manager.initialize_position(buy_position_forex)
        buy_position_forex.current_profit_pips = 75.0  # would hit level 1 if enabled
        assert manager.should_close_partial(buy_position_forex) is False

    def test_should_close_partial_not_hit(self, partial_manager, buy_position_forex):
        """Test should not close partial when level not hit."""
        partial_manager.initialize_position(buy_position_forex)
        # Level 1 threshold: 75 pips (50% of 150 pips TP)
        buy_position_forex.current_profit_pips = 70.0  # Below threshold

        assert partial_manager.should_close_partial(buy_position_forex) is False

    def test_should_close_partial_all_levels_done(self, partial_manager, buy_position_forex):
        """Test should not close when all levels completed."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1, 2]
        buy_position_forex.current_profit_pips = 50.0

        assert partial_manager.should_close_partial(buy_position_forex) is False


class TestCalculateCloseVolume:
    """Test calculate_close_volume method."""

    def test_calculate_close_volume_level_1(self, partial_manager, buy_position_forex):
        """Test calculating close volume for level 1 (25%)."""
        partial_manager.initialize_position(buy_position_forex)
        level = PartialCloseLevel(1, 20.0, 0.25)

        close_volume = partial_manager.calculate_close_volume(buy_position_forex, level)

        assert close_volume == 0.25  # 25% of 1.0 lot

    def test_calculate_close_volume_level_2(self, partial_manager, buy_position_forex):
        """Test calculating close volume for level 2 (50% of remaining)."""
        partial_manager.initialize_position(buy_position_forex)

        # Level 1 already closed (0.25 lots)
        partial_manager.remaining_volume[buy_position_forex.position_id] = 0.75

        level = PartialCloseLevel(2, 40.0, 0.50)
        close_volume = partial_manager.calculate_close_volume(buy_position_forex, level)

        assert close_volume == pytest.approx(0.38, abs=0.01)  # 50% of 0.75 lots


class TestExecutePartialClose:
    """Test execute_partial_close method."""

    def test_execute_partial_close_level_1(self, partial_manager, buy_position_forex):
        """Test executing partial close for level 1 (50% of TP)."""
        partial_manager.initialize_position(buy_position_forex)
        # Level 1: 75 pips (50% of 150 pips TP)
        buy_position_forex.current_price = 1.1075
        buy_position_forex.current_profit_pips = 75.0

        result = partial_manager.execute_partial_close(buy_position_forex, close_price=1.1075)

        assert result["level"] == 1
        assert result["close_volume"] == 0.25
        assert result["remaining_volume"] == 0.75
        assert result["profit_pips"] == pytest.approx(75.0, abs=0.1)
        assert 1 in partial_manager.partial_closes[buy_position_forex.position_id]

    def test_execute_partial_close_level_2(self, partial_manager, buy_position_forex):
        """Test executing partial close for level 2 (80% of TP)."""
        partial_manager.initialize_position(buy_position_forex)

        # Execute level 1 first (75 pips = 50% of TP)
        buy_position_forex.current_price = 1.1075
        buy_position_forex.current_profit_pips = 75.0
        partial_manager.execute_partial_close(buy_position_forex, close_price=1.1075)

        # Now execute level 2 (120 pips = 80% of TP)
        buy_position_forex.current_price = 1.1120
        buy_position_forex.current_profit_pips = 120.0

        result = partial_manager.execute_partial_close(buy_position_forex, close_price=1.1120)

        assert result["level"] == 2
        assert result["close_volume"] == pytest.approx(0.38, abs=0.01)  # 50% of remaining 0.75
        assert result["remaining_volume"] == pytest.approx(0.37, abs=0.01)

    def test_execute_partial_close_no_more_levels(self, partial_manager, buy_position_forex):
        """Test executing partial close when no more levels."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1, 2]

        with pytest.raises(ValueError, match="No more partial close levels"):
            partial_manager.execute_partial_close(buy_position_forex, close_price=1.1050)

    def test_execute_partial_close_closed_position(self, partial_manager, buy_position_forex):
        """Test executing partial close on closed position raises error."""
        buy_position_forex.status = PositionStatus.CLOSED

        with pytest.raises(ValueError, match="not open"):
            partial_manager.execute_partial_close(buy_position_forex, close_price=1.1020)


class TestGetCompletedLevels:
    """Test get_completed_levels method."""

    def test_get_completed_levels(self, partial_manager, buy_position_forex):
        """Test getting completed levels."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1, 2]

        completed = partial_manager.get_completed_levels(buy_position_forex.position_id)

        assert completed == [1, 2]

    def test_get_completed_levels_none(self, partial_manager):
        """Test getting completed levels for untracked position."""
        completed = partial_manager.get_completed_levels("nonexistent")
        assert completed == []


class TestGetRemainingVolume:
    """Test get_remaining_volume method."""

    def test_get_remaining_volume(self, partial_manager, buy_position_forex):
        """Test getting remaining volume."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.remaining_volume[buy_position_forex.position_id] = 0.75

        remaining = partial_manager.get_remaining_volume(buy_position_forex.position_id)

        assert remaining == 0.75

    def test_get_remaining_volume_untracked(self, partial_manager):
        """Test getting remaining volume for untracked position."""
        remaining = partial_manager.get_remaining_volume("nonexistent")
        assert remaining == 0.0


class TestGetPartialCloseLevels:
    """Test get_partial_close_levels method."""

    def test_get_partial_close_levels_forex_static(self, partial_manager):
        """Test getting partial close levels for forex (static, for reference)."""
        levels = partial_manager.get_partial_close_levels("EURUSD")

        assert len(levels) == 2
        assert levels[0].distance_pips == 20.0  # Static default
        assert levels[1].distance_pips == 40.0  # Static default

    def test_get_partial_close_levels_forex_dynamic(self, partial_manager, buy_position_forex):
        """Test getting partial close levels dynamically based on TP."""
        # TP distance: 150 pips
        # Level 1: 50% = 75 pips, Level 2: 80% = 120 pips
        levels = partial_manager.get_partial_close_levels("EURUSD", buy_position_forex)

        assert len(levels) == 2
        assert levels[0].distance_pips == pytest.approx(75.0, abs=0.1)  # 50% of 150
        assert levels[1].distance_pips == pytest.approx(120.0, abs=0.1)  # 80% of 150

    def test_get_partial_close_levels_jpy(self, partial_manager):
        """Test getting partial close levels for JPY pair (static, for reference)."""
        levels = partial_manager.get_partial_close_levels("USDJPY")

        assert len(levels) == 2
        assert levels[0].distance_pips == 200.0  # Static default
        assert levels[1].distance_pips == 400.0  # Static default

    def test_get_partial_close_levels_gold(self, partial_manager):
        """Test getting partial close levels for Gold (static, for reference)."""
        levels = partial_manager.get_partial_close_levels("XAUUSD")

        assert len(levels) == 2
        assert levels[0].distance_pips == 600.0  # Static default
        assert levels[1].distance_pips == 1200.0  # Static default


class TestResetPosition:
    """Test reset_position method."""

    def test_reset_position(self, partial_manager, buy_position_forex):
        """Test resetting position tracking."""
        partial_manager.initialize_position(buy_position_forex)
        partial_manager.partial_closes[buy_position_forex.position_id] = [1]

        partial_manager.reset_position(buy_position_forex.position_id)

        assert buy_position_forex.position_id not in partial_manager.partial_closes
        assert buy_position_forex.position_id not in partial_manager.remaining_volume


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_tracked_positions_count(self, partial_manager, buy_position_forex):
        """Test getting tracked positions count."""
        assert partial_manager.get_tracked_positions_count() == 0

        partial_manager.initialize_position(buy_position_forex)
        assert partial_manager.get_tracked_positions_count() == 1

    def test_string_representation(self, partial_manager):
        """Test string representation."""
        str_repr = str(partial_manager)
        assert "PartialCloseManager" in str_repr
        assert "0 positions tracked" in str_repr

    def test_get_next_level_auto_initialize(self, partial_manager, buy_position_forex):
        """Test get_next_level auto-initializes position if not tracked."""
        # Position not initialized yet
        assert buy_position_forex.position_id not in partial_manager.partial_closes

        # Should auto-initialize and return level
        next_level = partial_manager.get_next_level(buy_position_forex)

        assert next_level is not None
        assert buy_position_forex.position_id in partial_manager.partial_closes

    def test_get_next_level_sell_position(self, partial_manager):
        """Test get_next_level for SELL position calculates TP distance correctly."""
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

        # TP distance: 1.1000 - 1.0850 = 0.0150 = 150 pips
        # Level 1: 50% of TP = 75 pips
        next_level = partial_manager.get_next_level(sell_position)

        assert next_level is not None
        assert next_level.level == 1
        assert next_level.distance_pips == pytest.approx(75.0, abs=0.1)

    def test_should_close_partial_closed_position(self, partial_manager, buy_position_forex):
        """Test should_close_partial returns False for closed position."""
        buy_position_forex.status = PositionStatus.CLOSED
        buy_position_forex.current_profit_pips = 100.0

        assert partial_manager.should_close_partial(buy_position_forex) is False

    def test_should_close_partial_volume_too_small(self, partial_manager, buy_position_forex):
        """Test should_close_partial returns False when close volume is too small."""
        partial_manager.initialize_position(buy_position_forex)
        # Use very small volume that would result in close volume < 0.01
        buy_position_forex.volume = 0.01  # Very small position
        partial_manager.remaining_volume[buy_position_forex.position_id] = 0.01
        buy_position_forex.current_profit_pips = 100.0  # Above threshold

        # Close volume would be 0.01 * 0.25 = 0.0025 < 0.01 minimum
        assert partial_manager.should_close_partial(buy_position_forex) is False

    def test_calculate_close_volume_commodities(self, partial_manager):
        """Test calculate_close_volume rounds correctly for commodities."""
        position = Position(
            position_id="pos_gold_001",
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
        partial_manager.initialize_position(position)
        partial_manager.remaining_volume[position.position_id] = 0.75

        level = PartialCloseLevel(2, 40.0, 0.50)
        close_volume = partial_manager.calculate_close_volume(position, level)

        # Should round to 1 decimal for commodities
        assert close_volume == pytest.approx(0.4, abs=0.01)

    def test_calculate_close_volume_crypto(self, partial_manager):
        """Test calculate_close_volume rounds correctly for crypto."""
        position = Position(
            position_id="pos_crypto_001",
            symbol="BTCUSD",
            position_type=PositionType.BUY,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            volume=1.0,
            pip_size=1.0,
            pip_value_per_lot=1.0,
            status=PositionStatus.OPEN,
        )
        partial_manager.initialize_position(position)
        partial_manager.remaining_volume[position.position_id] = 0.75

        level = PartialCloseLevel(2, 40.0, 0.50)
        close_volume = partial_manager.calculate_close_volume(position, level)

        # Should round to 3 decimals for crypto
        assert close_volume == pytest.approx(0.375, abs=0.001)

    def test_execute_partial_close_volume_exceeds_remaining(
        self, partial_manager, buy_position_forex
    ):
        """Test execute_partial_close adjusts when close volume exceeds remaining."""
        partial_manager.initialize_position(buy_position_forex)
        # Set remaining volume to be less than calculated close volume
        # Use a scenario where calculated volume (25% of remaining) would exceed remaining
        # Set remaining to 0.1, but force calculated volume to be higher
        partial_manager.remaining_volume[buy_position_forex.position_id] = 0.1
        buy_position_forex.current_profit_pips = 100.0

        # Manually set a level that would calculate to more than remaining
        # We need to mock the calculate_close_volume to return > remaining
        from unittest.mock import patch

        with patch.object(partial_manager, "calculate_close_volume", return_value=0.15):
            result = partial_manager.execute_partial_close(buy_position_forex, close_price=1.1100)

            # Should adjust to remaining volume (0.1)
            assert result["close_volume"] == 0.1
            assert result["remaining_volume"] == 0.0

    def test_execute_partial_close_volume_too_small_raises_error(
        self, partial_manager, buy_position_forex
    ):
        """Test execute_partial_close raises error when volume too small."""
        partial_manager.initialize_position(buy_position_forex)
        # Set very small remaining volume
        partial_manager.remaining_volume[buy_position_forex.position_id] = 0.005  # < 0.01 minimum
        buy_position_forex.current_profit_pips = 100.0

        with pytest.raises(ValueError, match="Cannot partial close"):
            partial_manager.execute_partial_close(buy_position_forex, close_price=1.1100)

    def test_get_partial_close_levels_sell_position(self, partial_manager):
        """Test get_partial_close_levels for SELL position calculates correctly."""
        sell_position = Position(
            position_id="pos_sell_001",
            symbol="EURUSD",
            position_type=PositionType.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,  # TP below entry
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,
        )

        # TP distance: 1.1000 - 1.0850 = 0.0150 = 150 pips
        levels = partial_manager.get_partial_close_levels("EURUSD", sell_position)

        assert len(levels) == 2
        assert levels[0].distance_pips == pytest.approx(75.0, abs=0.1)  # 50% of 150
        assert levels[1].distance_pips == pytest.approx(120.0, abs=0.1)  # 80% of 150
