"""Tests for position data models."""

from datetime import datetime

import pytest

from trading_bot.position.position_models import (
    Position,
    PositionStatus,
    PositionType,
)


class TestPositionType:
    """Test PositionType enum."""

    def test_position_type_values(self):
        """Test PositionType enum values."""
        assert PositionType.BUY.value == "BUY"
        assert PositionType.SELL.value == "SELL"


class TestPositionStatus:
    """Test PositionStatus enum."""

    def test_position_status_values(self):
        """Test PositionStatus enum values."""
        assert PositionStatus.PENDING.value == "PENDING"
        assert PositionStatus.OPEN.value == "OPEN"
        assert PositionStatus.CLOSED.value == "CLOSED"
        assert PositionStatus.CANCELLED.value == "CANCELLED"


class TestPositionInitialization:
    """Test Position initialization."""

    def test_position_initialization_buy(self):
        """Test BUY position initialization."""
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
        )

        assert position.position_id == "pos_001"
        assert position.symbol == "EURUSD"
        assert position.position_type == PositionType.BUY
        assert position.entry_price == 1.1000
        assert position.stop_loss == 1.0950
        assert position.take_profit == 1.1150
        assert position.volume == 1.0
        assert position.status == PositionStatus.PENDING

    def test_position_initialization_sell(self):
        """Test SELL position initialization."""
        position = Position(
            position_id="pos_002",
            symbol="GBPUSD",
            position_type=PositionType.SELL,
            entry_price=1.2500,
            stop_loss=1.2550,
            take_profit=1.2350,
            volume=0.5,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )

        assert position.position_type == PositionType.SELL
        assert position.stop_loss > position.entry_price
        assert position.take_profit < position.entry_price


class TestPositionValidation:
    """Test Position validation."""

    def test_buy_position_invalid_stop_loss(self):
        """Test BUY position with invalid stop loss (above entry)."""
        with pytest.raises(ValueError, match="stop_loss must be below entry_price"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=1.1050,  # Invalid: above entry
                take_profit=1.1150,
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_buy_position_invalid_take_profit(self):
        """Test BUY position with invalid take profit (below entry)."""
        with pytest.raises(ValueError, match="take_profit must be above entry_price"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.0980,  # Invalid: below entry
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_sell_position_invalid_stop_loss(self):
        """Test SELL position with invalid stop loss (below entry)."""
        with pytest.raises(ValueError, match="stop_loss must be above entry_price"):
            Position(
                position_id="pos_002",
                symbol="EURUSD",
                position_type=PositionType.SELL,
                entry_price=1.1000,
                stop_loss=1.0950,  # Invalid: below entry
                take_profit=1.0850,
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_sell_position_invalid_take_profit(self):
        """Test SELL position with invalid take profit (above entry)."""
        with pytest.raises(ValueError, match="take_profit must be below entry_price"):
            Position(
                position_id="pos_002",
                symbol="EURUSD",
                position_type=PositionType.SELL,
                entry_price=1.1000,
                stop_loss=1.1050,
                take_profit=1.1020,  # Invalid: above entry
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_position_invalid_entry_price(self):
        """Test position with invalid entry price."""
        with pytest.raises(ValueError, match="Entry price must be positive"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=0.0,  # Invalid
                stop_loss=1.0950,
                take_profit=1.1150,
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_position_invalid_volume(self):
        """Test position with invalid volume."""
        with pytest.raises(ValueError, match="Volume must be positive"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                volume=0.0,  # Invalid
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_position_invalid_stop_loss_zero(self):
        """Test position with invalid stop loss (zero)."""
        with pytest.raises(ValueError, match="Stop loss must be positive"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=0.0,  # Invalid
                take_profit=1.1150,
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_position_invalid_take_profit_zero(self):
        """Test position with invalid take profit (zero)."""
        with pytest.raises(ValueError, match="Take profit must be positive"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=0.0,  # Invalid
                volume=1.0,
                pip_size=0.0001,
                pip_value_per_lot=10.0,
            )

    def test_position_invalid_pip_size_zero(self):
        """Test position with invalid pip size (zero)."""
        with pytest.raises(ValueError, match="Pip size must be positive"):
            Position(
                position_id="pos_001",
                symbol="EURUSD",
                position_type=PositionType.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                volume=1.0,
                pip_size=0.0,  # Invalid
                pip_value_per_lot=10.0,
            )

    def test_position_string_to_enum_conversion(self):
        """Test position converts string position_type and status to enum."""
        position = Position(
            position_id="pos_001",
            symbol="EURUSD",
            position_type="BUY",  # String instead of enum
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status="OPEN",  # String instead of enum
        )

        assert isinstance(position.position_type, PositionType)
        assert position.position_type == PositionType.BUY
        assert isinstance(position.status, PositionStatus)
        assert position.status == PositionStatus.OPEN

    def test_risk_reward_ratio_zero_risk(self):
        """Test risk/reward ratio when risk is zero or negative."""
        position = Position(
            position_id="pos_001",
            symbol="EURUSD",
            position_type=PositionType.BUY,
            entry_price=1.1000,
            stop_loss=1.1000,  # SL equals entry (zero risk)
            take_profit=1.1150,
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
            status=PositionStatus.OPEN,  # OPEN allows SL = entry
        )

        # Should return 0.0 when risk <= 0
        assert position.risk_reward_ratio == 0.0


class TestPositionProperties:
    """Test Position properties."""

    def test_is_open_property(self):
        """Test is_open property."""
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
        assert position.is_open is True

        position.status = PositionStatus.CLOSED
        assert position.is_open is False

    def test_is_closed_property(self):
        """Test is_closed property."""
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
            status=PositionStatus.CLOSED,
        )
        assert position.is_closed is True

        position.status = PositionStatus.OPEN
        assert position.is_closed is False

    def test_risk_reward_ratio_buy(self):
        """Test risk/reward ratio for BUY position."""
        position = Position(
            position_id="pos_001",
            symbol="EURUSD",
            position_type=PositionType.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 pips risk
            take_profit=1.1150,  # 150 pips reward
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )
        assert position.risk_reward_ratio == pytest.approx(3.0, abs=0.01)

    def test_risk_reward_ratio_sell(self):
        """Test risk/reward ratio for SELL position."""
        position = Position(
            position_id="pos_002",
            symbol="EURUSD",
            position_type=PositionType.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,  # 50 pips risk
            take_profit=1.0850,  # 150 pips reward
            volume=1.0,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )
        assert position.risk_reward_ratio == pytest.approx(3.0, abs=0.01)

    def test_duration_seconds(self):
        """Test position duration calculation."""
        open_time = datetime(2024, 1, 1, 10, 0, 0)
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
            open_time=open_time,
        )

        # No close time, should calculate from now
        assert position.duration_seconds is not None
        assert position.duration_seconds > 0


class TestPositionMethods:
    """Test Position methods."""

    def test_to_dict(self):
        """Test position to_dict conversion."""
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
        )

        data = position.to_dict()
        assert data["position_id"] == "pos_001"
        assert data["symbol"] == "EURUSD"
        assert data["position_type"] == "BUY"
        assert data["entry_price"] == 1.1000
        assert data["volume"] == 1.0
        assert data["status"] == "PENDING"
        assert "risk_reward_ratio" in data

    def test_string_representation(self):
        """Test position string representation."""
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
        )

        str_repr = str(position)
        assert "BUY" in str_repr
        assert "EURUSD" in str_repr
        assert "1.10000" in str_repr
        assert "PENDING" in str_repr
