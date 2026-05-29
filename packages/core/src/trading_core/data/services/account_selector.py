"""
Account Selector Service - Multi-account trading support.

Handles account selection and switching for trading operations.
"""

from trading_core.data.repositories import AccountRepository
from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class AccountSelector:
    """
    Service for selecting and managing active trading accounts.

    Responsibilities:
    - Get active account for trading
    - Switch between accounts
    - Track current active account
    - List all available accounts
    """

    def __init__(self, repository: AccountRepository | None = None):
        """
        Initialize account selector.

        Args:
            repository: Optional AccountRepository instance (for testing)
        """
        self.repository = repository or AccountRepository()
        self._current_account_id: int | None = None

    async def get_active_account(self):
        """
        Get the currently active account for trading.

        Returns:
            TradingAccount instance or None if no active account
        """
        # If we have a cached current account, try to get it
        if self._current_account_id:
            account = await self.repository.get_by_account_id(self._current_account_id)
            if account and account.is_active:
                return account
            # Account was deactivated or not found, clear cache
            self._current_account_id = None

        # Get first active account from repository
        active_accounts = await self.repository.get_active_accounts()

        if not active_accounts:
            logger.warning("No active accounts found")
            return None

        # Use first active account as default
        account = active_accounts[0]
        self._current_account_id = account.account_id

        logger.info(f"Selected active account: {account.account_id} ({account.broker_name})")

        return account

    async def switch_account(self, account_id: int) -> bool:
        """
        Switch to a different active account.

        Args:
            account_id: MT5 account ID to switch to

        Returns:
            True if switch successful, False if account not found or inactive
        """
        account = await self.repository.get_by_account_id(account_id)

        if not account:
            logger.warning(f"Account {account_id} not found")
            return False

        if not account.is_active:
            logger.warning(f"Account {account_id} is not active")
            return False

        self._current_account_id = account_id

        logger.info(f"Switched to account: {account_id} ({account.broker_name})")

        return True

    async def get_account_by_id(self, account_id: int):
        """
        Get account by MT5 account ID.

        Args:
            account_id: MT5 account ID

        Returns:
            TradingAccount instance or None if not found
        """
        return await self.repository.get_by_account_id(account_id)

    async def get_all_active_accounts(self):
        """
        Get all active accounts.

        Returns:
            List of active TradingAccount instances
        """
        return await self.repository.get_active_accounts()

    def get_current_account_id(self) -> int | None:
        """
        Get current account ID (cached).

        Returns:
            Current account ID or None
        """
        return self._current_account_id
