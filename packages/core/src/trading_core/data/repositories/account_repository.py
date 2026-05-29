"""
Account Repository - CRUD operations for TradingAccount model.

Implements repository pattern for clean data access.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trading_core.data.database import get_session
from trading_core.data.models import TradingAccount
from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class AccountRepository:
    """Repository for TradingAccount CRUD operations."""

    def __init__(self, session: AsyncSession | None = None):
        """
        Initialize account repository.

        Args:
            session: Optional database session (for testing)
        """
        self.session = session

    async def create(self, account_data: dict) -> TradingAccount:
        """
        Create a new trading account.

        Args:
            account_data: Dictionary with account fields

        Returns:
            Created TradingAccount instance

        Raises:
            IntegrityError: If account with same account_id already exists
        """
        async with get_session() as session:
            account = TradingAccount(**account_data)
            session.add(account)
            await session.commit()
            await session.refresh(account)
            logger.info(f"Created account: {account.account_id} ({account.broker_name})")
            return account

    async def get_by_id(self, account_pk: int) -> TradingAccount | None:
        """
        Get account by primary key ID.

        Args:
            account_pk: Primary key ID

        Returns:
            TradingAccount or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.id == account_pk)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_account_id(self, account_id: int) -> TradingAccount | None:
        """
        Get account by MT5 account_id.

        Args:
            account_id: MT5 login ID

        Returns:
            TradingAccount or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.account_id == account_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_broker_and_number(
        self, broker_name: str, account_number: str
    ) -> TradingAccount | None:
        """
        Get account by broker name and account number.

        Args:
            broker_name: Broker name (e.g., "Exness")
            account_number: Account number

        Returns:
            TradingAccount or None if not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(
                TradingAccount.broker_name == broker_name,
                TradingAccount.account_number == account_number,
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_active_accounts(self) -> list[TradingAccount]:
        """
        Get all active accounts.

        Returns:
            List of active TradingAccount instances
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.is_active)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def list_accounts(self, limit: int = 100, offset: int = 0) -> list[TradingAccount]:
        """
        List accounts with pagination.

        Args:
            limit: Maximum number of accounts to return
            offset: Number of accounts to skip

        Returns:
            List of TradingAccount instances
        """
        async with get_session() as session:
            stmt = select(TradingAccount).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_balance(
        self, account_pk: int, balance: float, equity: float | None = None
    ) -> TradingAccount:
        """
        Update account balance and equity.

        Args:
            account_pk: Primary key ID
            balance: New balance
            equity: New equity (optional)

        Returns:
            Updated TradingAccount instance

        Raises:
            ValueError: If account not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.id == account_pk)
            result = await session.execute(stmt)
            account = result.scalars().first()

            if not account:
                raise ValueError(f"Account with ID {account_pk} not found")

            account.update_balance(balance, equity)
            await session.commit()
            await session.refresh(account)
            logger.info(f"Updated balance for account {account.account_id}: ${balance}")
            return account

    async def deactivate(self, account_pk: int) -> TradingAccount:
        """
        Deactivate an account.

        Args:
            account_pk: Primary key ID

        Returns:
            Deactivated TradingAccount instance

        Raises:
            ValueError: If account not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.id == account_pk)
            result = await session.execute(stmt)
            account = result.scalars().first()

            if not account:
                raise ValueError(f"Account with ID {account_pk} not found")

            account.deactivate()
            await session.commit()
            await session.refresh(account)
            logger.info(f"Deactivated account {account.account_id}")
            return account

    async def delete(self, account_pk: int) -> bool:
        """
        Delete an account (for testing cleanup).

        Args:
            account_pk: Primary key ID

        Returns:
            True if deleted, False if not found
        """
        async with get_session() as session:
            stmt = select(TradingAccount).where(TradingAccount.id == account_pk)
            result = await session.execute(stmt)
            account = result.scalars().first()

            if not account:
                return False

            await session.delete(account)
            await session.commit()
            logger.debug(f"Deleted account {account.account_id}")
            return True
