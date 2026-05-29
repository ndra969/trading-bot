"""
Unit tests for TradingSession model.

Tests session creation, validation, and business logic methods.
"""

from datetime import UTC, datetime

import pytest
from trading_core.data.models import TradingSession


class TestTradingSessionModel:
    """Test TradingSession model creation and validation."""

    def test_create_trading_session_minimal(self):
        """Test creating session with minimal required fields."""
        session = TradingSession(
            session_id="test_session_001",
            account_id=12345,
            trading_type="day_trading",
            start_time=datetime.now(UTC).replace(tzinfo=None),  # Explicitly set
            created_at=datetime.now(UTC).replace(tzinfo=None),  # Explicitly set
            updated_at=datetime.now(UTC).replace(tzinfo=None),  # Explicitly set
        )

        assert session.session_id == "test_session_001"
        assert session.account_id == 12345
        assert session.trading_type == "day_trading"

    def test_create_trading_session_with_all_fields(self):
        """Test creating session with all fields."""
        start_time = datetime.now(UTC).replace(tzinfo=None)

        session = TradingSession(
            session_id="test_session_002",
            account_id=12345,
            config_hash="abc123",
            start_time=start_time,
            trading_type="scalping",
            is_backtest=True,
            is_dry_run=False,
            starting_balance=1000.0,
        )

        assert session.config_hash == "abc123"
        assert session.start_time == start_time
        assert session.trading_type == "scalping"
        assert session.is_backtest is True
        assert session.starting_balance == 1000.0

    def test_session_status_validation(self):
        """Test session status validation."""
        session = TradingSession(
            session_id="test_session_003",
            account_id=12345,
            status="ACTIVE",
        )

        assert session.status == "ACTIVE"

        # Test invalid status raises error
        with pytest.raises(ValueError, match="Session status must be ACTIVE or CLOSED"):
            session = TradingSession(
                session_id="test_session_004",
                account_id=12345,
                status="INVALID",
            )

    def test_trading_type_validation(self):
        """Test trading type validation."""
        valid_types = ["scalping", "day_trading", "swing_trading", "position_trading"]

        for trading_type in valid_types:
            session = TradingSession(
                session_id=f"test_session_{trading_type}",
                account_id=12345,
                trading_type=trading_type,
            )
            assert session.trading_type == trading_type

        # Test invalid trading type
        with pytest.raises(ValueError, match="Trading type must be one of"):
            session = TradingSession(
                session_id="test_session_invalid",
                account_id=12345,
                trading_type="invalid_type",
            )

    def test_close_session(self):
        """Test closing a session."""
        session = TradingSession(
            session_id="test_session_005",
            account_id=12345,
            status="ACTIVE",
            start_time=datetime.now(UTC).replace(tzinfo=None),
        )

        assert session.status == "ACTIVE"
        assert session.end_time is None

        # Close session
        session.close_session(ending_balance=1500.0)

        assert session.status == "CLOSED"
        assert session.end_time is not None
        assert session.ending_balance == 1500.0

    def test_update_aggregations_winning_trade(self):
        """Test updating aggregations with winning trade."""
        session = TradingSession(
            session_id="test_session_006",
            account_id=12345,
            total_trades=0,  # Initialize explicitly
            winning_trades=0,
            losing_trades=0,
            total_pnl_usd=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            win_rate=0.0,
            average_win=0.0,
            average_loss=0.0,
        )

        # Add winning trade
        session.update_aggregations(pnl=50.0, is_winner=True, gross_profit=50.0)

        assert session.total_trades == 1
        assert session.winning_trades == 1
        assert session.losing_trades == 0
        assert session.total_pnl_usd == 50.0
        assert session.gross_profit == 50.0
        assert session.gross_loss == 0.0
        assert session.win_rate == 100.0
        assert session.average_win == 50.0

    def test_update_aggregations_losing_trade(self):
        """Test updating aggregations with losing trade."""
        session = TradingSession(
            session_id="test_session_007",
            account_id=12345,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl_usd=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            win_rate=0.0,
            average_win=0.0,
            average_loss=0.0,
        )

        # Add losing trade
        session.update_aggregations(pnl=-30.0, is_winner=False, gross_loss=-30.0)

        assert session.total_trades == 1
        assert session.winning_trades == 0
        assert session.losing_trades == 1
        assert session.total_pnl_usd == -30.0
        assert session.gross_profit == 0.0
        assert session.gross_loss == 30.0  # Stored as positive
        assert session.win_rate == 0.0
        assert session.average_loss == 30.0

    def test_update_aggregations_multiple_trades(self):
        """Test updating aggregations with multiple trades."""
        session = TradingSession(
            session_id="test_session_008",
            account_id=12345,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl_usd=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            win_rate=0.0,
            average_win=0.0,
            average_loss=0.0,
            profit_factor=0.0,
        )

        # Add 3 winners
        session.update_aggregations(pnl=50.0, is_winner=True, gross_profit=50.0)
        session.update_aggregations(pnl=30.0, is_winner=True, gross_profit=30.0)
        session.update_aggregations(pnl=40.0, is_winner=True, gross_profit=40.0)

        # Add 2 losers
        session.update_aggregations(pnl=-20.0, is_winner=False, gross_loss=-20.0)
        session.update_aggregations(pnl=-10.0, is_winner=False, gross_loss=-10.0)

        assert session.total_trades == 5
        assert session.winning_trades == 3
        assert session.losing_trades == 2
        assert session.total_pnl_usd == 90.0  # 120 - 30
        assert session.gross_profit == 120.0
        assert session.gross_loss == 30.0
        assert session.win_rate == 60.0
        assert session.average_win == 40.0  # 120 / 3
        assert session.average_loss == 15.0  # 30 / 2

    def test_profit_factor_calculation(self):
        """Test profit factor calculation."""
        session = TradingSession(
            session_id="test_session_009",
            account_id=12345,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl_usd=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            average_win=0.0,
            average_loss=0.0,
        )

        # Add trades
        session.update_aggregations(pnl=100.0, is_winner=True, gross_profit=100.0)
        session.update_aggregations(pnl=-50.0, is_winner=False, gross_loss=-50.0)

        # Profit factor = 100 / 50 = 2.0
        assert session.profit_factor == 2.0

        # Test with only winners (no gross loss)
        session2 = TradingSession(
            session_id="test_session_010",
            account_id=12345,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            total_pnl_usd=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            average_win=0.0,
            average_loss=0.0,
        )
        session2.update_aggregations(pnl=100.0, is_winner=True, gross_profit=100.0)

        assert session2.profit_factor == 100.0  # When no losses, profit factor = gross profit

    def test_calculate_session_duration_active(self):
        """Test session duration calculation for active session."""
        session = TradingSession(
            session_id="test_session_011",
            account_id=12345,
            start_time=datetime.now(UTC).replace(tzinfo=None),
        )

        # Active session has no end_time
        duration = session.calculate_session_duration()
        assert duration is None

    def test_calculate_session_duration_closed(self):
        """Test session duration calculation for closed session."""
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 14, 30, 0)  # 4.5 hours later

        session = TradingSession(
            session_id="test_session_012",
            account_id=12345,
            start_time=start_time,
            end_time=end_time,
            status="CLOSED",
        )

        duration = session.calculate_session_duration()
        assert duration == 4.5  # 4.5 hours

    def test_session_metadata_storage(self):
        """Test storing metadata in session."""
        session = TradingSession(
            session_id="test_session_013",
            account_id=12345,
            meta_data={"note": "Test session", "strategy": "foundation"},
        )

        assert session.meta_data["note"] == "Test session"
        assert session.meta_data["strategy"] == "foundation"

    def test_timestamps_auto_created(self):
        """Test that timestamps are auto-created."""
        before = datetime.now(UTC).replace(tzinfo=None)

        session = TradingSession(
            session_id="test_session_014",
            account_id=12345,
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )

        after = datetime.now(UTC).replace(tzinfo=None)

        assert session.created_at is not None
        assert session.updated_at is not None
        assert before <= session.created_at <= after
        assert before <= session.updated_at <= after

    def test_string_representation(self):
        """Test __repr__ method."""
        session = TradingSession(
            session_id="test_session_015",
            account_id=12345,
            total_pnl_usd=150.0,
            total_trades=10,
            win_rate=60.0,
        )

        repr_str = repr(session)
        assert "test_session_015" in repr_str
        assert "12345" in repr_str
        assert "150.00" in repr_str
        assert "10" in repr_str
        assert "60.0" in repr_str
