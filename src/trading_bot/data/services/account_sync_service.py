"""
Account Sync Service - Synchronize MT5 account data.

Handles fetching account information from MetaTrader5 and updating
the database with current balance, equity, and other account details.
"""

from datetime import UTC, datetime
from typing import Any

from trading_bot.connectors.mt5_connector import MT5Connector
from trading_bot.data.models import TradingAccount
from trading_bot.data.repositories import AccountRepository
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class AccountSyncService:
    """
    Service for synchronizing MT5 account data.

    Responsibilities:
    - Fetch account info from MT5
    - Update account balance and equity
    - Track sync status and errors
    - Handle connection failures gracefully
    """

    def __init__(
        self, repository: AccountRepository | None = None, mt5_connector: MT5Connector | None = None
    ):
        """
        Initialize account sync service.

        Args:
            repository: Optional AccountRepository instance (for testing)
            mt5_connector: Optional MT5Connector instance (for testing)
        """
        self.repository = repository or AccountRepository()
        self.mt5_connector = mt5_connector
        self._last_sync_status: dict[str, Any] = {
            "last_sync_time": None,
            "accounts_synced": 0,
            "accounts_failed": 0,
            "errors": [],
        }

    async def ensure_account_exists(self, mt5_connector: MT5Connector) -> TradingAccount | None:
        """
        Ensure current MT5 account exists in database.
        If not exists, create it from MT5 account info.
        If exists, update balance and equity.

        Args:
            mt5_connector: MT5Connector instance with active connection

        Returns:
            TradingAccount instance or None if failed
        """
        try:
            if not mt5_connector.is_connected():
                logger.warning("MT5 not connected - cannot ensure account exists")
                return None

            # Get MT5 account info
            account_info_dict = mt5_connector.account_info
            if not account_info_dict:
                logger.error("Failed to get MT5 account info")
                return None

            account_id = account_info_dict.get("login")
            if not account_id:
                logger.error("MT5 account info missing login ID")
                return None

            # Check if account exists in DB
            account = await self.repository.get_by_account_id(account_id)

            if account:
                # Account exists - update balance and equity
                await self.repository.update_balance(
                    account.id,
                    account_info_dict.get("balance", 0.0),
                    account_info_dict.get("equity"),
                )
                logger.info(f"✅ Account {account_id} already exists - updated balance/equity")
                return account
            else:
                # Account doesn't exist - create new
                # Determine account type from trade_mode
                trade_mode = account_info_dict.get("trade_mode", 0)
                # MT5 trade modes: 0=DEMO, 1=CONTEST, 2=REAL
                account_type = (
                    "DEMO" if trade_mode == 0 else ("LIVE" if trade_mode == 2 else "DEMO")
                )

                # Get broker name from server or company
                server = account_info_dict.get("server", "Unknown")
                company = account_info_dict.get("company", "Unknown")
                broker_name = (
                    company
                    if company != "Unknown"
                    else server.split("-")[0]
                    if "-" in server
                    else server
                )

                account_data = {
                    "account_id": account_id,
                    "broker_name": broker_name,
                    "account_number": str(account_id),  # Use account_id as account_number
                    "account_type": account_type,
                    "balance": account_info_dict.get("balance", 0.0),
                    "equity": account_info_dict.get("equity"),
                    "leverage": account_info_dict.get("leverage", 100),
                    "currency": account_info_dict.get("currency", "USD"),
                    "is_active": True,
                }

                account = await self.repository.create(account_data)
                equity_str = f"{account.equity:.2f}" if account.equity else "0.00"
                logger.info(
                    f"✅ Created new account {account_id} ({broker_name}, {account_type}): "
                    f"Balance=${account.balance:.2f}, Equity=${equity_str}"
                )
                return account

        except Exception as e:
            logger.error(f"Error ensuring account exists: {e}")
            return None

    async def sync_account(self, account_id: int) -> bool:
        """
        Sync single account from MT5.

        Args:
            account_id: MT5 account ID to sync

        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Check if account exists in DB
            account = await self.repository.get_by_account_id(account_id)
            if not account:
                logger.warning(f"Account {account_id} not found in database")
                return False

            # Get MT5 account info - use provided connector or create new
            if self.mt5_connector and self.mt5_connector.is_connected():
                account_info = self.mt5_connector.account_info
            else:
                mt5_connector = MT5Connector()
                if not mt5_connector.is_connected():
                    logger.error(f"MT5 not connected for account {account_id}")
                    return False
                account_info = mt5_connector.account_info

            if not account_info:
                logger.error(f"Failed to get MT5 account info for {account_id}")
                return False

            # Verify account ID matches
            if account_info.get("login") != account_id:
                logger.error(
                    f"Account ID mismatch: DB={account_id}, MT5={account_info.get('login')}"
                )
                return False

            # Update account balance and equity
            await self.repository.update_balance(
                account.id, account_info.get("balance", 0.0), account_info.get("equity")
            )

            equity_value = (
                account_info.get("equity", 0.0) if account_info.get("equity") is not None else 0.0
            )
            logger.info(
                f"Synced account {account_id}: "
                f"Balance=${account_info.get('balance', 0.0):.2f}, "
                f"Equity=${equity_value:.2f}"
            )

            # Update sync status
            self._last_sync_status["accounts_synced"] += 1

            return True

        except Exception as e:
            logger.error(f"Error syncing account {account_id}: {e}")
            self._last_sync_status["accounts_failed"] += 1
            self._last_sync_status["errors"].append({"account_id": account_id, "error": str(e)})
            return False

    async def sync_all_active_accounts(self) -> dict[str, int]:
        """
        Sync all active accounts from MT5.

        Returns:
            Dictionary with sync results: {total, success, failed}
        """
        # Reset sync status
        self._last_sync_status = {
            "last_sync_time": datetime.now(UTC),
            "accounts_synced": 0,
            "accounts_failed": 0,
            "errors": [],
        }

        # Get all active accounts
        active_accounts = await self.repository.get_active_accounts()

        if not active_accounts:
            logger.info("No active accounts to sync")
            return {"total": 0, "success": 0, "failed": 0}

        logger.info(f"Starting sync for {len(active_accounts)} active accounts")

        success_count = 0
        failed_count = 0

        for account in active_accounts:
            result = await self.sync_account(account.account_id)
            if result:
                success_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Sync completed: {success_count} success, {failed_count} failed "
            f"out of {len(active_accounts)} total"
        )

        return {
            "total": len(active_accounts),
            "success": success_count,
            "failed": failed_count,
        }

    async def check_connection_status(self) -> bool:
        """
        Check MT5 connection status.

        Returns:
            True if connected, False otherwise
        """
        try:
            mt5_connector = MT5Connector()
            return mt5_connector.is_connected()
        except Exception as e:
            logger.error(f"Error checking MT5 connection: {e}")
            return False

    def get_last_sync_status(self) -> dict[str, Any]:
        """
        Get status of last sync operation.

        Returns:
            Dictionary with sync status information
        """
        return self._last_sync_status.copy()
