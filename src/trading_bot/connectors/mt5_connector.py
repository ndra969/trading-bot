"""
MetaTrader5 Connector

Core connector for MetaTrader5 platform integration.
Handles connection, initialization, and health monitoring.
"""

import time
from typing import Any

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from ..exceptions import (
    MT5ConnectionError,
    MT5TerminalNotRunningError,
    MT5VersionIncompatibleError,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MT5Connector:
    """
    MetaTrader5 platform connector.

    Manages connection lifecycle, health monitoring, and basic MT5 operations.
    """

    MIN_VERSION = (5, 0, 0)  # Minimum required MT5 version

    def __init__(
        self,
        terminal_path: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize MT5 connector.

        Args:
            terminal_path: Path to MT5 terminal (auto-detect if None)
            login: Trading account login
            password: Trading account password
            server: MT5 server name
            timeout: Connection timeout in seconds
            retry_attempts: Number of connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        if not MT5_AVAILABLE:
            raise ImportError(
                "MetaTrader5 package not available. " "Install it with: pip install MetaTrader5"
            )

        self.terminal_path = terminal_path
        self.login = login
        self.password = password
        self.server = server
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        self._is_connected = False
        self._terminal_info: dict[str, Any] | None = None
        self._account_info: dict[str, Any] | None = None

    def initialize(self) -> bool:
        """
        Initialize MT5 terminal connection.

        Returns:
            True if initialization successful

        Raises:
            MT5ConnectionError: If initialization fails
            MT5TerminalNotRunningError: If terminal is not running
            MT5VersionIncompatibleError: If MT5 version is incompatible
        """
        logger.info("Initializing MT5 connection...")

        for attempt in range(1, self.retry_attempts + 1):
            try:
                # Initialize MT5 terminal
                if self.terminal_path:
                    initialized = mt5.initialize(path=self.terminal_path, timeout=self.timeout)
                else:
                    initialized = mt5.initialize(timeout=self.timeout)

                if not initialized:
                    error_code, error_msg = mt5.last_error()
                    raise MT5ConnectionError(
                        f"MT5 initialization failed: {error_msg} (code: {error_code})"
                    )

                # Check terminal info
                self._terminal_info = mt5.terminal_info()._asdict() if mt5.terminal_info() else {}

                # Check if terminal is running
                if not self._terminal_info or not self._terminal_info.get("connected"):
                    mt5.shutdown()
                    raise MT5TerminalNotRunningError()

                # Check version compatibility
                version = mt5.version()
                if version and version[:3] < self.MIN_VERSION:
                    mt5.shutdown()
                    raise MT5VersionIncompatibleError(
                        version=".".join(map(str, version)),
                        min_version=".".join(map(str, self.MIN_VERSION)),
                    )

                # Login if credentials provided
                if self.login and self.password and self.server:
                    login_success = mt5.login(
                        login=self.login,
                        password=self.password,
                        server=self.server,
                        timeout=self.timeout,
                    )

                    if not login_success:
                        error_code, error_msg = mt5.last_error()
                        mt5.shutdown()
                        raise MT5ConnectionError(
                            f"MT5 login failed: {error_msg} (code: {error_code})"
                        )

                # Get account info
                self._account_info = mt5.account_info()._asdict() if mt5.account_info() else {}

                self._is_connected = True
                logger.info(f"MT5 connected successfully (attempt {attempt}/{self.retry_attempts})")
                logger.info(f"Terminal: {self._terminal_info.get('name', 'Unknown')}")
                logger.info(f"Account: {self._account_info.get('login', 'Unknown')}")

                return True

            except (MT5ConnectionError, MT5TerminalNotRunningError, MT5VersionIncompatibleError):
                raise
            except Exception as e:
                logger.warning(f"Connection attempt {attempt}/{self.retry_attempts} failed: {e}")

                if attempt < self.retry_attempts:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise MT5ConnectionError(
                        f"Failed to connect after {self.retry_attempts} attempts: {e}"
                    ) from e

        return False

    def shutdown(self) -> None:
        """Shutdown MT5 connection gracefully."""
        if self._is_connected:
            mt5.shutdown()
            self._is_connected = False
            logger.info("MT5 connection closed")

    def is_connected(self) -> bool:
        """
        Check if MT5 is connected.

        Returns:
            True if connected and terminal is responsive
        """
        if not self._is_connected:
            return False

        try:
            # Check if terminal is still responsive
            terminal_info = mt5.terminal_info()
            return terminal_info is not None and terminal_info.connected
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            return False

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check on MT5 connection.

        Returns:
            Dictionary with health check results
        """
        health = {
            "connected": False,
            "terminal_running": False,
            "trade_allowed": False,
            "terminal_info": {},
            "account_info": {},
        }

        if not self._is_connected:
            return health

        try:
            # Check terminal
            terminal_info = mt5.terminal_info()
            if terminal_info:
                health["terminal_running"] = True
                health["connected"] = terminal_info.connected
                health["trade_allowed"] = terminal_info.trade_allowed
                health["terminal_info"] = terminal_info._asdict()

            # Check account
            account_info = mt5.account_info()
            if account_info:
                health["account_info"] = account_info._asdict()

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        return health

    def place_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
        comment: str = "",
        magic: int = 0,
    ) -> dict[str, Any] | None:
        """
        Place a trade order.

        Args:
            symbol: Trading symbol
            order_type: 'BUY' or 'SELL'
            volume: Lot size
            price: Entry price (for pending orders, current price for market)
            sl: Stop Loss price
            tp: Take Profit price
            comment: Order comment
            magic: Magic number

        Returns:
            Dictionary with order result or None if failed
        """
        if not self._is_connected:
            logger.error("Cannot place order: MT5 not connected")
            return None

        try:
            # Prepare request
            action = mt5.TRADE_ACTION_DEAL  # Market execution

            type_op = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL

            request = {
                "action": action,
                "symbol": symbol,
                "volume": volume,
                "type": type_op,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,  # Slippage tolerance
                "magic": magic,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send order
            result = mt5.order_send(request)

            if result is None:
                logger.error("Order failed: result is None")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.comment} (code: {result.retcode})")
                return None

            logger.info(f"Order placed successfully: {result.order}")
            return result._asdict()

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    @property
    def terminal_info(self) -> dict[str, Any]:
        """Get terminal information."""
        return self._terminal_info or {}

    @property
    def account_info(self) -> dict[str, Any]:
        """Get account information."""
        return self._account_info or {}

    @property
    def version(self) -> tuple | None:
        """Get MT5 version."""
        try:
            return mt5.version()
        except Exception:
            return None

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
