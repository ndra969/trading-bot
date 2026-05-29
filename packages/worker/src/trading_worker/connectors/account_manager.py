"""
Account Manager

Handles MT5 account operations including balance, equity, margin monitoring.
"""

from typing import Any

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_core.utils.logger import get_logger

from ..exceptions import MT5ConnectionError

logger = get_logger(__name__)


class AccountManager:
    """
    MT5 Account Manager.

    Provides account information, balance monitoring, and margin tracking.
    """

    def __init__(self, mt5_connector):
        """
        Initialize Account Manager.

        Args:
            mt5_connector: MT5Connector instance
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available")

        self.connector = mt5_connector

    def get_account_info(self) -> dict[str, Any]:
        """
        Get complete account information.

        Returns:
            Dictionary with account details

        Raises:
            MT5ConnectionError: If not connected to MT5
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            account_info = mt5.account_info()
            if account_info is None:
                error_code, error_msg = mt5.last_error()
                raise MT5ConnectionError(
                    f"Failed to get account info: {error_msg} (code: {error_code})"
                )

            return account_info._asdict()
        except MT5ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise MT5ConnectionError(f"Failed to retrieve account info: {e}") from e

    def get_balance(self) -> float:
        """
        Get current account balance.

        Returns:
            Account balance
        """
        account_info = self.get_account_info()
        return account_info.get("balance", 0.0)

    def get_equity(self) -> float:
        """
        Get current account equity.

        Returns:
            Account equity
        """
        account_info = self.get_account_info()
        return account_info.get("equity", 0.0)

    def get_margin(self) -> float:
        """
        Get used margin.

        Returns:
            Used margin
        """
        account_info = self.get_account_info()
        return account_info.get("margin", 0.0)

    def get_free_margin(self) -> float:
        """
        Get free margin available for trading.

        Returns:
            Free margin
        """
        account_info = self.get_account_info()
        return account_info.get("margin_free", 0.0)

    def get_margin_level(self) -> float:
        """
        Get margin level percentage.

        Returns:
            Margin level (0.0 if no open positions)
        """
        account_info = self.get_account_info()
        return account_info.get("margin_level", 0.0)

    def get_profit(self) -> float:
        """
        Get current profit/loss from open positions.

        Returns:
            Current profit/loss
        """
        account_info = self.get_account_info()
        return account_info.get("profit", 0.0)

    def get_leverage(self) -> int:
        """
        Get account leverage.

        Returns:
            Account leverage (e.g., 100 for 1:100)
        """
        account_info = self.get_account_info()
        return account_info.get("leverage", 1)

    def get_currency(self) -> str:
        """
        Get account currency.

        Returns:
            Account currency (e.g., "USD")
        """
        account_info = self.get_account_info()
        return account_info.get("currency", "USD")

    def get_server(self) -> str:
        """
        Get broker server name.

        Returns:
            Server name
        """
        account_info = self.get_account_info()
        return account_info.get("server", "Unknown")

    def get_company(self) -> str:
        """
        Get broker company name.

        Returns:
            Company name
        """
        account_info = self.get_account_info()
        return account_info.get("company", "Unknown")

    def is_trade_allowed(self) -> bool:
        """
        Check if trading is allowed on account.

        Returns:
            True if trading is allowed
        """
        account_info = self.get_account_info()
        return account_info.get("trade_allowed", False)

    def get_account_type(self) -> str:
        """
        Get account type (demo, real).

        Returns:
            Account type
        """
        account_info = self.get_account_info()
        trade_mode = account_info.get("trade_mode", 0)

        # MT5 trade modes: 0=DEMO, 1=CONTEST, 2=REAL
        if trade_mode == 0:
            return "DEMO"
        elif trade_mode == 1:
            return "CONTEST"
        elif trade_mode == 2:
            return "REAL"
        else:
            return "UNKNOWN"

    def get_summary(self) -> dict[str, Any]:
        """
        Get account summary with key metrics.

        Returns:
            Dictionary with account summary
        """
        return {
            "balance": self.get_balance(),
            "equity": self.get_equity(),
            "margin": self.get_margin(),
            "free_margin": self.get_free_margin(),
            "margin_level": self.get_margin_level(),
            "profit": self.get_profit(),
            "leverage": self.get_leverage(),
            "currency": self.get_currency(),
            "server": self.get_server(),
            "company": self.get_company(),
            "trade_allowed": self.is_trade_allowed(),
            "account_type": self.get_account_type(),
        }
