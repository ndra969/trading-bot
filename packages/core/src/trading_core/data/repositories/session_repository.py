"""
Session Repository for Trading Sessions.

Provides CRUD operations and session management for TradingSession model.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError

from ...utils.logger import get_logger
from ..database import get_session
from ..models import TradingSession

logger = get_logger(__name__)


class SessionRepository:
    """Repository for managing TradingSession database operations."""

    def __init__(self):
        """Initialize SessionRepository."""
        self.logger = get_logger(self.__class__.__name__)

    async def create(self, session_data: dict) -> TradingSession:
        """
        Create a new trading session.

        Args:
            session_data: Dictionary with session data

        Returns:
            Created TradingSession instance

        Raises:
            ValueError: If session with same ID already exists
        """
        async with get_session() as session:
            new_session = TradingSession(**session_data)
            session.add(new_session)

            try:
                await session.commit()
                await session.refresh(new_session)
                self.logger.info(
                    f"Created session: {new_session.session_id} "
                    f"(account={new_session.account_id}, type={new_session.trading_type})"
                )
                return new_session
            except IntegrityError as e:
                await session.rollback()
                self.logger.error(f"Duplicate session_id: {e}")
                raise ValueError("Session with this ID already exists.") from e

    async def get_by_id(self, db_id: int) -> TradingSession | None:
        """
        Get session by database ID.

        Args:
            db_id: Database primary key ID

        Returns:
            TradingSession or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.id == db_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> TradingSession | None:
        """
        Get session by session_id.

        Args:
            session_id: Unique session identifier

        Returns:
            TradingSession or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.session_id == session_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_active_sessions(self) -> list[TradingSession]:
        """
        Get all active sessions.

        Returns:
            List of active TradingSession instances
        """
        async with get_session() as session:
            stmt = (
                select(TradingSession)
                .where(TradingSession.status == "ACTIVE")
                .order_by(desc(TradingSession.start_time))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_sessions_by_account(
        self, account_id: int, limit: int = 100
    ) -> list[TradingSession]:
        """
        Get sessions for specific account.

        Args:
            account_id: Account ID to filter by
            limit: Maximum number of sessions to return

        Returns:
            List of TradingSession instances
        """
        async with get_session() as session:
            stmt = (
                select(TradingSession)
                .where(TradingSession.account_id == account_id)
                .order_by(desc(TradingSession.start_time))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_sessions_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        account_id: int | None = None,
    ) -> list[TradingSession]:
        """
        Get sessions within date range.

        Args:
            start_date: Start date
            end_date: End date
            account_id: Optional account filter

        Returns:
            List of TradingSession instances
        """
        async with get_session() as session:
            conditions = [
                TradingSession.start_time >= start_date,
                TradingSession.start_time <= end_date,
            ]

            if account_id:
                conditions.append(TradingSession.account_id == account_id)

            stmt = (
                select(TradingSession)
                .where(and_(*conditions))
                .order_by(desc(TradingSession.start_time))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_backtest_sessions(self) -> list[TradingSession]:
        """
        Get all backtest sessions.

        Returns:
            List of backtest TradingSession instances
        """
        async with get_session() as session:
            stmt = (
                select(TradingSession)
                .where(TradingSession.is_backtest)
                .order_by(desc(TradingSession.start_time))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update(self, db_id: int, update_data: dict) -> TradingSession | None:
        """
        Update session data.

        Args:
            db_id: Database primary key ID
            update_data: Dictionary with fields to update

        Returns:
            Updated TradingSession or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.id == db_id)
            result = await session.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                return None

            # Update fields
            for key, value in update_data.items():
                if hasattr(db_session, key):
                    setattr(db_session, key, value)

            db_session.updated_at = datetime.now(UTC).replace(tzinfo=None)

            try:
                await session.commit()
                await session.refresh(db_session)
                self.logger.info(f"Updated session {db_session.session_id}")
                return db_session
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating session {db_id}: {e}")
                raise

    async def update_aggregations(
        self,
        session_id: str,
        pnl: float,
        is_winner: bool,
        gross_profit: float = 0.0,
        gross_loss: float = 0.0,
    ) -> bool:
        """
        Update session aggregations when a position closes.

        Args:
            session_id: Session ID to update
            pnl: Position P&L
            is_winner: Whether position was a winner
            gross_profit: Gross profit if winner
            gross_loss: Gross loss if loser

        Returns:
            True if successful, False otherwise
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.session_id == session_id)
            result = await session.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                self.logger.warning(f"Session {session_id} not found for aggregation update")
                return False

            # Use model method to update aggregations
            db_session.update_aggregations(pnl, is_winner, gross_profit, gross_loss)

            try:
                await session.commit()
                self.logger.debug(
                    f"Updated aggregations for session {session_id}: "
                    f"trades={db_session.total_trades}, win_rate={db_session.win_rate:.1f}%"
                )
                return True
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error updating aggregations for session {session_id}: {e}")
                return False

    async def close_abandoned_sessions(self, account_id: int, ending_balance: float) -> int:
        """Mark all ACTIVE sessions for an account as CLOSED.

        Used at bot startup to clean up sessions left ACTIVE by previous
        crashes/kills that bypassed graceful shutdown. Sets end_time =
        updated_at (the last time the session was touched) so duration
        reflects when the session actually stopped being updated.

        Args:
            account_id: Account whose stale sessions to close.
            ending_balance: Balance to record as ending_balance (best
                available — usually the current account balance).

        Returns:
            Number of sessions closed.
        """
        async with get_session() as db:
            stmt = select(TradingSession).where(
                and_(
                    TradingSession.account_id == account_id,
                    TradingSession.status == "ACTIVE",
                )
            )
            result = await db.execute(stmt)
            stale_sessions = list(result.scalars().all())

            if not stale_sessions:
                return 0

            for s in stale_sessions:
                s.status = "CLOSED"
                # Use last-known-update as end_time — accurate signal of
                # when the session actually stopped progressing.
                s.end_time = s.updated_at
                s.ending_balance = ending_balance

            try:
                await db.commit()
                self.logger.info(
                    f"Closed {len(stale_sessions)} abandoned ACTIVE sessions "
                    f"for account {account_id}"
                )
                return len(stale_sessions)
            except Exception as e:
                await db.rollback()
                self.logger.error(f"Error closing abandoned sessions: {e}")
                return 0

    async def close_session(self, session_id: str, ending_balance: float) -> bool:
        """
        Close a trading session.

        Args:
            session_id: Session ID to close
            ending_balance: Final account balance

        Returns:
            True if successful, False otherwise
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.session_id == session_id)
            result = await session.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                self.logger.warning(f"Session {session_id} not found")
                return False

            # Use model method to close session
            db_session.close_session(ending_balance)

            try:
                await session.commit()
                self.logger.info(
                    f"Closed session {session_id}: "
                    f"P&L=${db_session.total_pnl_usd:.2f}, "
                    f"trades={db_session.total_trades}, "
                    f"win_rate={db_session.win_rate:.1f}%"
                )
                return True
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error closing session {session_id}: {e}")
                return False

    async def delete(self, db_id: int) -> bool:
        """
        Delete a trading session.

        Args:
            db_id: Database primary key ID

        Returns:
            True if deleted, False if not found
        """
        async with get_session() as session:
            stmt = select(TradingSession).where(TradingSession.id == db_id)
            result = await session.execute(stmt)
            db_session = result.scalar_one_or_none()

            if not db_session:
                return False

            try:
                await session.delete(db_session)
                await session.commit()
                self.logger.info(f"Deleted session {db_session.session_id}")
                return True
            except Exception as e:
                await session.rollback()
                self.logger.error(f"Error deleting session {db_id}: {e}")
                raise

    async def get_session_performance(self, session_id: str) -> dict | None:
        """
        Get session performance summary.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with performance metrics or None if not found
        """
        db_session = await self.get_by_session_id(session_id)
        if not db_session:
            return None

        return {
            "session_id": db_session.session_id,
            "status": db_session.status,
            "trading_type": db_session.trading_type,
            "total_pnl": db_session.total_pnl_usd,
            "total_trades": db_session.total_trades,
            "win_rate": db_session.win_rate,
            "profit_factor": db_session.profit_factor,
            "gross_profit": db_session.gross_profit,
            "gross_loss": db_session.gross_loss,
            "average_win": db_session.average_win,
            "average_loss": db_session.average_loss,
            "max_drawdown": db_session.max_drawdown,
            "duration_hours": db_session.calculate_session_duration(),
        }

    async def calculate_session_stats(self, account_id: int) -> dict:
        """
        Calculate aggregate statistics for account's sessions.

        Args:
            account_id: Account ID

        Returns:
            Dictionary with aggregate statistics
        """
        async with get_session() as session:
            # Total sessions
            total_stmt = select(func.count(TradingSession.id)).where(
                TradingSession.account_id == account_id
            )
            total_result = await session.execute(total_stmt)
            total_sessions = total_result.scalar() or 0

            # Active sessions
            active_stmt = select(func.count(TradingSession.id)).where(
                and_(
                    TradingSession.account_id == account_id,
                    TradingSession.status == "ACTIVE",
                )
            )
            active_result = await session.execute(active_stmt)
            active_sessions = active_result.scalar() or 0

            # Total P&L
            pnl_stmt = select(func.sum(TradingSession.total_pnl_usd)).where(
                TradingSession.account_id == account_id
            )
            pnl_result = await session.execute(pnl_stmt)
            total_pnl = pnl_result.scalar() or 0.0

            # Total trades
            trades_stmt = select(func.sum(TradingSession.total_trades)).where(
                TradingSession.account_id == account_id
            )
            trades_result = await session.execute(trades_stmt)
            total_trades = trades_result.scalar() or 0

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_pnl": total_pnl,
                "total_trades": total_trades,
            }
