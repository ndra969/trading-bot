"""
Unit tests for SessionRepository.

Tests CRUD operations and session management.
"""

from datetime import UTC, datetime, timedelta

import pytest
from trading_core.data.repositories import SessionRepository


class TestSessionRepository:
    """Test SessionRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, setup_test_database):
        """Test creating a new session successfully."""
        # Create account first
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        # Create session
        repo = SessionRepository()
        session_data = {
            "session_id": "sess_test_001",
            "account_id": account.account_id,
            "trading_type": "day_trading",
            "starting_balance": 1000.0,
        }

        session = await repo.create(session_data)

        assert session is not None
        assert session.session_id == "sess_test_001"
        assert session.account_id == 12345
        assert session.trading_type == "day_trading"
        assert session.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_create_session_duplicate_id_error(self, setup_test_database):
        """Test creating session with duplicate ID raises error."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        session_data = {
            "session_id": "sess_duplicate",
            "account_id": account.account_id,
            "trading_type": "day_trading",
        }

        # Create first session
        await repo.create(session_data)

        # Try to create duplicate
        with pytest.raises(ValueError, match="Session with this ID already exists"):
            await repo.create(session_data)

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, setup_test_database):
        """Test getting session by database ID."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_test_002",
                "account_id": account.account_id,
                "trading_type": "scalping",
            }
        )

        # Get by ID
        session = await repo.get_by_id(created.id)

        assert session is not None
        assert session.session_id == "sess_test_002"
        assert session.trading_type == "scalping"

    @pytest.mark.asyncio
    async def test_get_session_by_session_id(self, setup_test_database):
        """Test getting session by session_id."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        await repo.create(
            {
                "session_id": "sess_test_003",
                "account_id": account.account_id,
                "trading_type": "swing_trading",
            }
        )

        # Get by session_id
        session = await repo.get_by_session_id("sess_test_003")

        assert session is not None
        assert session.session_id == "sess_test_003"
        assert session.trading_type == "swing_trading"

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, setup_test_database):
        """Test getting all active sessions."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()

        # Create 2 active sessions
        await repo.create(
            {
                "session_id": "sess_active_1",
                "account_id": account.account_id,
                "status": "ACTIVE",
            }
        )
        await repo.create(
            {
                "session_id": "sess_active_2",
                "account_id": account.account_id,
                "status": "ACTIVE",
            }
        )

        # Create 1 closed session
        await repo.create(
            {
                "session_id": "sess_closed_1",
                "account_id": account.account_id,
                "status": "CLOSED",
            }
        )

        # Get active sessions
        active_sessions = await repo.get_active_sessions()

        assert len(active_sessions) == 2
        assert all(s.status == "ACTIVE" for s in active_sessions)

    @pytest.mark.asyncio
    async def test_get_sessions_by_account(self, setup_test_database):
        """Test getting sessions for specific account."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account1 = await account_repo.create(
            {
                "account_id": 11111,
                "broker_name": "Broker1",
                "account_number": "11111",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )
        account2 = await account_repo.create(
            {
                "account_id": 22222,
                "broker_name": "Broker2",
                "account_number": "22222",
                "account_type": "DEMO",
                "balance": 2000.0,
            }
        )

        repo = SessionRepository()

        # Create sessions for account1
        await repo.create(
            {
                "session_id": "sess_acc1_1",
                "account_id": account1.account_id,
            }
        )
        await repo.create(
            {
                "session_id": "sess_acc1_2",
                "account_id": account1.account_id,
            }
        )

        # Create session for account2
        await repo.create(
            {
                "session_id": "sess_acc2_1",
                "account_id": account2.account_id,
            }
        )

        # Get sessions for account1
        sessions = await repo.get_sessions_by_account(account1.account_id)

        assert len(sessions) == 2
        assert all(s.account_id == account1.account_id for s in sessions)

    @pytest.mark.asyncio
    async def test_update_session_aggregations(self, setup_test_database):
        """Test updating session aggregations."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        await repo.create(
            {
                "session_id": "sess_test_004",
                "account_id": account.account_id,
            }
        )

        # Update aggregations
        success = await repo.update_aggregations(
            session_id="sess_test_004",
            pnl=50.0,
            is_winner=True,
            gross_profit=50.0,
        )

        assert success is True

        # Verify updates
        session = await repo.get_by_session_id("sess_test_004")
        assert session.total_trades == 1
        assert session.winning_trades == 1
        assert session.total_pnl_usd == 50.0
        assert session.win_rate == 100.0

    @pytest.mark.asyncio
    async def test_close_session(self, setup_test_database):
        """Test closing a session."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        await repo.create(
            {
                "session_id": "sess_test_005",
                "account_id": account.account_id,
                "status": "ACTIVE",
                "starting_balance": 1000.0,
            }
        )

        # Close session
        success = await repo.close_session("sess_test_005", ending_balance=1200.0)

        assert success is True

        # Verify closure
        session = await repo.get_by_session_id("sess_test_005")
        assert session.status == "CLOSED"
        assert session.end_time is not None
        assert session.ending_balance == 1200.0

    @pytest.mark.asyncio
    async def test_get_session_performance(self, setup_test_database):
        """Test getting session performance summary."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        await repo.create(
            {
                "session_id": "sess_test_006",
                "account_id": account.account_id,
                "total_pnl_usd": 150.0,
                "total_trades": 10,
                "win_rate": 60.0,
            }
        )

        # Get performance
        perf = await repo.get_session_performance("sess_test_006")

        assert perf is not None
        assert perf["session_id"] == "sess_test_006"
        assert perf["total_pnl"] == 150.0
        assert perf["total_trades"] == 10
        assert perf["win_rate"] == 60.0

    @pytest.mark.asyncio
    async def test_calculate_session_stats(self, setup_test_database):
        """Test calculating aggregate session statistics."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()

        # Create multiple sessions
        await repo.create(
            {
                "session_id": "sess_stat_1",
                "account_id": account.account_id,
                "status": "ACTIVE",
                "total_pnl_usd": 50.0,
                "total_trades": 5,
            }
        )
        await repo.create(
            {
                "session_id": "sess_stat_2",
                "account_id": account.account_id,
                "status": "CLOSED",
                "total_pnl_usd": 100.0,
                "total_trades": 10,
            }
        )

        # Calculate stats
        stats = await repo.calculate_session_stats(account.account_id)

        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 1
        assert stats["total_pnl"] == 150.0
        assert stats["total_trades"] == 15

    @pytest.mark.asyncio
    async def test_get_sessions_by_date_range(self, setup_test_database):
        """Test getting sessions within date range."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()

        # Create sessions with different dates
        now = datetime.now(UTC).replace(tzinfo=None)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create session in range
        await repo.create(
            {
                "session_id": "sess_date_1",
                "account_id": account.account_id,
                "start_time": now,
            }
        )

        # Create session outside range
        await repo.create(
            {
                "session_id": "sess_date_2",
                "account_id": account.account_id,
                "start_time": yesterday - timedelta(days=1),
            }
        )

        # Get sessions in range
        sessions = await repo.get_sessions_by_date_range(
            start_date=yesterday,
            end_date=tomorrow,
        )

        assert len(sessions) >= 1
        assert any(s.session_id == "sess_date_1" for s in sessions)

    @pytest.mark.asyncio
    async def test_get_sessions_by_date_range_with_account(self, setup_test_database):
        """Test getting sessions by date range with account filter."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        now = datetime.now(UTC).replace(tzinfo=None)

        await repo.create(
            {
                "session_id": "sess_date_acc",
                "account_id": account.account_id,
                "start_time": now,
            }
        )

        sessions = await repo.get_sessions_by_date_range(
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            account_id=account.account_id,
        )

        assert len(sessions) >= 1
        assert all(s.account_id == account.account_id for s in sessions)

    @pytest.mark.asyncio
    async def test_get_backtest_sessions(self, setup_test_database):
        """Test getting backtest sessions."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()

        # Create backtest session
        await repo.create(
            {
                "session_id": "sess_backtest_1",
                "account_id": account.account_id,
                "is_backtest": True,
            }
        )

        # Create regular session
        await repo.create(
            {
                "session_id": "sess_regular_1",
                "account_id": account.account_id,
                "is_backtest": False,
            }
        )

        # Get backtest sessions
        backtest_sessions = await repo.get_backtest_sessions()

        assert len(backtest_sessions) >= 1
        assert all(s.is_backtest for s in backtest_sessions)

    @pytest.mark.asyncio
    async def test_update_session(self, setup_test_database):
        """Test updating session data."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_update_1",
                "account_id": account.account_id,
                "trading_type": "day_trading",
            }
        )

        # Update session
        updated = await repo.update(
            created.id,
            {
                "trading_type": "scalping",
                "description": "Updated session",
            },
        )

        assert updated is not None
        assert updated.trading_type == "scalping"

    @pytest.mark.asyncio
    async def test_update_session_not_found(self, setup_test_database):
        """Test updating non-existent session returns None."""
        repo = SessionRepository()

        updated = await repo.update(99999, {"trading_type": "scalping"})

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_session(self, setup_test_database):
        """Test deleting a session."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_delete_1",
                "account_id": account.account_id,
            }
        )

        # Delete session
        deleted = await repo.delete(created.id)

        assert deleted is True

        # Verify deleted
        session = await repo.get_by_id(created.id)
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, setup_test_database):
        """Test deleting non-existent session returns False."""
        repo = SessionRepository()

        deleted = await repo.delete(99999)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_update_aggregations_session_not_found(self, setup_test_database):
        """Test updating aggregations for non-existent session."""
        repo = SessionRepository()

        success = await repo.update_aggregations(
            session_id="nonexistent",
            pnl=50.0,
            is_winner=True,
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_close_session_not_found(self, setup_test_database):
        """Test closing non-existent session."""
        repo = SessionRepository()

        success = await repo.close_session("nonexistent", ending_balance=1000.0)

        assert success is False

    @pytest.mark.asyncio
    async def test_get_session_performance_not_found(self, setup_test_database):
        """Test getting performance for non-existent session."""
        repo = SessionRepository()

        perf = await repo.get_session_performance("nonexistent")

        assert perf is None

    @pytest.mark.asyncio
    async def test_update_session_error_handling(self, setup_test_database):
        """Test update error handling path."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import SQLAlchemyError
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_error_update",
                "account_id": account.account_id,
            }
        )

        # Create mock session that raises on commit
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: created))
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
        mock_session.rollback = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Create async context manager mock
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        # Patch get_session
        with patch(
            "trading_core.data.repositories.session_repository.get_session", mock_get_session
        ):
            # Should raise exception
            with pytest.raises(SQLAlchemyError):
                await repo.update(created.id, {"trading_type": "scalping"})

    @pytest.mark.asyncio
    async def test_update_aggregations_error_handling(self, setup_test_database):
        """Test update_aggregations error handling path."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import SQLAlchemyError
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_error_agg",
                "account_id": account.account_id,
            }
        )

        # Create mock session that raises on commit
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: created))
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
        mock_session.rollback = AsyncMock()

        # Create async context manager mock
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        # Patch get_session
        with patch(
            "trading_core.data.repositories.session_repository.get_session", mock_get_session
        ):
            # Should return False on error
            result = await repo.update_aggregations(
                session_id="sess_error_agg",
                pnl=50.0,
                is_winner=True,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_close_session_error_handling(self, setup_test_database):
        """Test close_session error handling path."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import SQLAlchemyError
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_error_close",
                "account_id": account.account_id,
            }
        )

        # Create mock session that raises on commit
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: created))
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
        mock_session.rollback = AsyncMock()

        # Create async context manager mock
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        # Patch get_session
        with patch(
            "trading_core.data.repositories.session_repository.get_session", mock_get_session
        ):
            # Should return False on error
            result = await repo.close_session("sess_error_close", ending_balance=1000.0)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_session_error_handling(self, setup_test_database):
        """Test delete error handling path."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import SQLAlchemyError
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        account = await account_repo.create(
            {
                "account_id": 12345,
                "broker_name": "TestBroker",
                "account_number": "12345",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        created = await repo.create(
            {
                "session_id": "sess_error_delete",
                "account_id": account.account_id,
            }
        )

        # Create mock session that raises on delete
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: created))
        mock_session.delete = AsyncMock(side_effect=SQLAlchemyError("Database error"))
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        # Create async context manager mock
        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        # Patch get_session
        with patch(
            "trading_core.data.repositories.session_repository.get_session", mock_get_session
        ):
            # Should raise exception
            with pytest.raises(SQLAlchemyError):
                await repo.delete(created.id)


class TestCloseAbandonedSessions:
    """Verify startup cleanup of sessions left ACTIVE by previous crashes."""

    @pytest.mark.asyncio
    async def test_closes_only_active_sessions_for_account(self, setup_test_database):
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        acc1 = await account_repo.create(
            {
                "account_id": 11111,
                "broker_name": "TestBroker",
                "account_number": "11111",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )
        acc2 = await account_repo.create(
            {
                "account_id": 22222,
                "broker_name": "TestBroker",
                "account_number": "22222",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        # Account 1: 2 abandoned ACTIVE + 1 already CLOSED
        s1 = await repo.create(
            {"session_id": "abandoned_1", "account_id": acc1.account_id, "status": "ACTIVE"}
        )
        s2 = await repo.create(
            {"session_id": "abandoned_2", "account_id": acc1.account_id, "status": "ACTIVE"}
        )
        s3 = await repo.create(
            {"session_id": "already_closed", "account_id": acc1.account_id, "status": "ACTIVE"}
        )
        await repo.close_session("already_closed", 1100.0)
        # Account 2: 1 ACTIVE that must NOT be touched
        s4 = await repo.create(
            {"session_id": "other_account", "account_id": acc2.account_id, "status": "ACTIVE"}
        )

        closed_count = await repo.close_abandoned_sessions(
            account_id=acc1.account_id, ending_balance=1050.0
        )

        assert closed_count == 2

        # Both account-1 ACTIVE sessions now CLOSED
        s1_after = await repo.get_by_session_id("abandoned_1")
        s2_after = await repo.get_by_session_id("abandoned_2")
        assert s1_after.status == "CLOSED"
        assert s2_after.status == "CLOSED"
        assert s1_after.end_time is not None
        assert s1_after.ending_balance == 1050.0

        # Account-2 session untouched
        s4_after = await repo.get_by_session_id("other_account")
        assert s4_after.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_no_abandoned_sessions_returns_zero(self, setup_test_database):
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        acc = await account_repo.create(
            {
                "account_id": 33333,
                "broker_name": "TestBroker",
                "account_number": "33333",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        closed_count = await repo.close_abandoned_sessions(
            account_id=acc.account_id, ending_balance=1000.0
        )

        assert closed_count == 0

    @pytest.mark.asyncio
    async def test_end_time_set_to_updated_at(self, setup_test_database):
        """end_time should reflect when session was last touched, not now()."""
        from trading_core.data.repositories import AccountRepository

        account_repo = AccountRepository()
        acc = await account_repo.create(
            {
                "account_id": 44444,
                "broker_name": "TestBroker",
                "account_number": "44444",
                "account_type": "DEMO",
                "balance": 1000.0,
            }
        )

        repo = SessionRepository()
        session = await repo.create(
            {
                "session_id": "stale_session",
                "account_id": acc.account_id,
                "status": "ACTIVE",
            }
        )
        original_updated_at = session.updated_at

        await repo.close_abandoned_sessions(account_id=acc.account_id, ending_balance=1000.0)

        closed_session = await repo.get_by_session_id("stale_session")
        assert closed_session.end_time == original_updated_at
