"""Tests for PositionTracker."""

from datetime import datetime

import pytest

from trading_bot.position.position_models import Position, PositionStatus, PositionType
from trading_bot.position.position_tracker import PositionTracker


@pytest.fixture
def tracker():
    """Create a PositionTracker instance."""
    return PositionTracker()


@pytest.fixture
def buy_position():
    """Create a BUY position."""
    return Position(
        position_id="pos_001",
        symbol="EURUSD",
        position_type=PositionType.BUY,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit=1.1150,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.PENDING,
    )


@pytest.fixture
def sell_position():
    """Create a SELL position."""
    return Position(
        position_id="pos_002",
        symbol="GBPUSD",
        position_type=PositionType.SELL,
        entry_price=1.2500,
        stop_loss=1.2550,
        take_profit=1.2350,
        volume=1.0,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        status=PositionStatus.PENDING,
    )


class TestPositionTrackerInitialization:
    """Test PositionTracker initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        tracker = PositionTracker()
        assert tracker.pip_calculator is not None


class TestOpenPosition:
    """Test opening positions."""

    def test_open_pending_position(self, tracker, buy_position):
        """Test opening a pending position."""
        tracker.open_position(buy_position)

        assert buy_position.status == PositionStatus.OPEN
        assert buy_position.open_time is not None
        assert buy_position.current_price == buy_position.entry_price
        assert buy_position.current_profit_pips == 0.0
        assert buy_position.current_pnl_usd == 0.0
        assert buy_position.risk_amount_usd > 0
        assert buy_position.potential_profit_usd > 0

    def test_open_position_calculates_risk_amount(self, tracker, buy_position):
        """Test that opening position calculates risk amount."""
        tracker.open_position(buy_position)

        # Risk = 50 pips * $10 = $500
        assert buy_position.risk_amount_usd == pytest.approx(500.0, abs=1.0)

    def test_open_position_calculates_potential_profit(self, tracker, buy_position):
        """Test that opening position calculates potential profit."""
        tracker.open_position(buy_position)

        # Potential = 150 pips * $10 = $1500
        assert buy_position.potential_profit_usd == pytest.approx(1500.0, abs=1.0)

    def test_open_already_open_position(self, tracker, buy_position):
        """Test that opening an already open position does nothing."""
        buy_position.status = PositionStatus.OPEN
        open_time = datetime(2024, 1, 1, 10, 0, 0)
        buy_position.open_time = open_time

        tracker.open_position(buy_position)

        # Should not change open_time
        assert buy_position.open_time == open_time


class TestUpdatePositionPrice:
    """Test updating position price."""

    def test_update_price_buy_profit(self, tracker, buy_position):
        """Test updating BUY position in profit."""
        tracker.open_position(buy_position)

        # Price moves up 50 pips
        tracker.update_position_price(buy_position, 1.1050)

        assert buy_position.current_price == 1.1050
        assert buy_position.current_profit_pips == pytest.approx(50.0, abs=0.1)
        assert buy_position.current_pnl_usd == pytest.approx(500.0, abs=1.0)

    def test_update_price_buy_loss(self, tracker, buy_position):
        """Test updating BUY position in loss."""
        tracker.open_position(buy_position)

        # Price moves down 30 pips
        tracker.update_position_price(buy_position, 1.0970)

        assert buy_position.current_price == 1.0970
        assert buy_position.current_profit_pips == pytest.approx(-30.0, abs=0.1)
        assert buy_position.current_pnl_usd == pytest.approx(-300.0, abs=1.0)

    def test_update_price_sell_profit(self, tracker, sell_position):
        """Test updating SELL position in profit."""
        tracker.open_position(sell_position)

        # Price moves down 50 pips
        tracker.update_position_price(sell_position, 1.2450)

        assert sell_position.current_price == 1.2450
        assert sell_position.current_profit_pips == pytest.approx(50.0, abs=0.1)
        assert sell_position.current_pnl_usd == pytest.approx(500.0, abs=1.0)

    def test_update_price_sell_loss(self, tracker, sell_position):
        """Test updating SELL position in loss."""
        tracker.open_position(sell_position)

        # Price moves up 30 pips
        tracker.update_position_price(sell_position, 1.2530)

        assert sell_position.current_price == 1.2530
        assert sell_position.current_profit_pips == pytest.approx(-30.0, abs=0.1)
        assert sell_position.current_pnl_usd == pytest.approx(-300.0, abs=1.0)

    def test_update_price_closed_position(self, tracker, buy_position):
        """Test that updating closed position does nothing."""
        buy_position.status = PositionStatus.CLOSED
        buy_position.current_profit_pips = 50.0

        tracker.update_position_price(buy_position, 1.1050)

        # Should not update
        assert buy_position.current_profit_pips == 50.0


class TestClosePosition:
    """Test closing positions."""

    def test_close_position_with_profit(self, tracker, buy_position):
        """Test closing position with profit."""
        tracker.open_position(buy_position)

        # Close at profit
        tracker.close_position(buy_position, 1.1050)

        assert buy_position.status == PositionStatus.CLOSED
        assert buy_position.close_time is not None
        assert buy_position.close_price == 1.1050
        assert buy_position.current_profit_pips == pytest.approx(50.0, abs=0.1)
        assert buy_position.current_pnl_usd == pytest.approx(500.0, abs=1.0)

    def test_close_position_with_loss(self, tracker, buy_position):
        """Test closing position with loss."""
        tracker.open_position(buy_position)

        # Close at loss
        tracker.close_position(buy_position, 1.0970)

        assert buy_position.status == PositionStatus.CLOSED
        assert buy_position.current_profit_pips == pytest.approx(-30.0, abs=0.1)
        assert buy_position.current_pnl_usd == pytest.approx(-300.0, abs=1.0)

    def test_close_pending_position(self, tracker, buy_position):
        """Test that closing pending position does nothing."""
        assert buy_position.status == PositionStatus.PENDING

        tracker.close_position(buy_position, 1.1050)

        # Should remain pending
        assert buy_position.status == PositionStatus.PENDING
        assert buy_position.close_time is None


class TestCheckStopLoss:
    """Test stop loss checking."""

    def test_check_stop_loss_buy_hit(self, tracker, buy_position):
        """Test stop loss hit for BUY position."""
        tracker.open_position(buy_position)
        tracker.update_position_price(buy_position, 1.0945)  # Below SL

        assert tracker.check_stop_loss(buy_position) is True

    def test_check_stop_loss_buy_not_hit(self, tracker, buy_position):
        """Test stop loss not hit for BUY position."""
        tracker.open_position(buy_position)
        tracker.update_position_price(buy_position, 1.1050)  # Above SL

        assert tracker.check_stop_loss(buy_position) is False

    def test_check_stop_loss_sell_hit(self, tracker, sell_position):
        """Test stop loss hit for SELL position."""
        tracker.open_position(sell_position)
        tracker.update_position_price(sell_position, 1.2555)  # Above SL

        assert tracker.check_stop_loss(sell_position) is True

    def test_check_stop_loss_sell_not_hit(self, tracker, sell_position):
        """Test stop loss not hit for SELL position."""
        tracker.open_position(sell_position)
        tracker.update_position_price(sell_position, 1.2450)  # Below SL

        assert tracker.check_stop_loss(sell_position) is False

    def test_check_stop_loss_closed_position(self, tracker, buy_position):
        """Test stop loss check for closed position."""
        buy_position.status = PositionStatus.CLOSED
        assert tracker.check_stop_loss(buy_position) is False


class TestCheckTakeProfit:
    """Test take profit checking."""

    def test_check_take_profit_buy_hit(self, tracker, buy_position):
        """Test take profit hit for BUY position."""
        tracker.open_position(buy_position)
        tracker.update_position_price(buy_position, 1.1155)  # Above TP

        assert tracker.check_take_profit(buy_position) is True

    def test_check_take_profit_buy_not_hit(self, tracker, buy_position):
        """Test take profit not hit for BUY position."""
        tracker.open_position(buy_position)
        tracker.update_position_price(buy_position, 1.1050)  # Below TP

        assert tracker.check_take_profit(buy_position) is False

    def test_check_take_profit_sell_hit(self, tracker, sell_position):
        """Test take profit hit for SELL position."""
        tracker.open_position(sell_position)
        tracker.update_position_price(sell_position, 1.2345)  # Below TP

        assert tracker.check_take_profit(sell_position) is True

    def test_check_take_profit_sell_not_hit(self, tracker, sell_position):
        """Test take profit not hit for SELL position."""
        tracker.open_position(sell_position)
        tracker.update_position_price(sell_position, 1.2450)  # Above TP

        assert tracker.check_take_profit(sell_position) is False

    def test_check_take_profit_not_open(self, tracker, buy_position):
        """Test take profit check for non-open position returns False."""
        buy_position.status = PositionStatus.PENDING
        buy_position.current_price = None

        assert tracker.check_take_profit(buy_position) is False

    def test_check_take_profit_current_price_none(self, tracker, buy_position):
        """Test take profit check when current_price is None returns False."""
        tracker.open_position(buy_position)
        buy_position.current_price = None

        assert tracker.check_take_profit(buy_position) is False


class TestGetPositionSummary:
    """Test position summary."""

    def test_get_position_summary(self, tracker, buy_position):
        """Test getting position summary."""
        tracker.open_position(buy_position)
        tracker.update_position_price(buy_position, 1.1050)

        summary = tracker.get_position_summary(buy_position)

        assert summary["position_id"] == "pos_001"
        assert summary["symbol"] == "EURUSD"
        assert summary["type"] == "BUY"
        assert summary["status"] == "OPEN"
        assert summary["profit_pips"] == pytest.approx(50.0, abs=0.1)
        assert summary["pnl_usd"] == pytest.approx(500.0, abs=1.0)
        assert "risk_usd" in summary
        assert "duration_seconds" in summary
