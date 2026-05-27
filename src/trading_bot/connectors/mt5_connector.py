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
                "MetaTrader5 package not available. Install it with: pip install MetaTrader5"
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

                # Verify we actually attached to the requested terminal. MT5's python
                # lib will silently hand back an already-running terminal even when a
                # different `path=` is requested (single-instance-per-process quirk).
                # Without this check, --config test (Broker A) would silently end up
                # on Broker B if dev was running. Fail loudly instead.
                if self.terminal_path:
                    self._verify_terminal_path()

                # Check version compatibility
                version = mt5.version()
                if version and version[:3] < self.MIN_VERSION:
                    mt5.shutdown()
                    raise MT5VersionIncompatibleError(
                        version=".".join(map(str, version)),
                        min_version=".".join(map(str, self.MIN_VERSION)),
                    )

                # Login only if all three credentials are present. mt5.login()
                # rejects password=None with "Invalid password argument", so we
                # can't use it to force a session switch without a real password.
                # Without explicit login(), we rely on terminal_path verification
                # above to fail loudly when MT5 attaches to the wrong terminal.
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

                # Log server information for debugging
                account_info_obj = mt5.account_info()
                if account_info_obj:
                    server_used = (
                        account_info_obj.server
                        if hasattr(account_info_obj, "server")
                        else "Unknown"
                    )
                    logger.info(f"MT5 Server: {server_used} (from account info)")
                    if self.server:
                        logger.info(f"Config Server: {self.server} (from config/env)")
                        if server_used.lower() != self.server.lower():
                            logger.warning(
                                f"⚠️ Server mismatch: Config specifies '{self.server}' but MT5 is using '{server_used}'. "
                                f"This may happen if MT5 terminal was already logged in to a different server."
                            )
                    else:
                        logger.info(
                            f"⚠️ No server specified in config - MT5 using existing connection: {server_used}"
                        )

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

    def _verify_terminal_path(self) -> None:
        """Ensure the attached MT5 terminal matches the requested terminal_path.

        Raises MT5ConnectionError (after mt5.shutdown()) if the terminal we
        actually connected to isn't under the requested path. Compares
        canonical paths via Path.resolve() to handle slashes/case differences.
        """
        from pathlib import Path

        actual = self._terminal_info.get("path") if self._terminal_info else None
        if not actual:
            return  # Terminal didn't expose its path — can't verify, allow

        try:
            requested = Path(self.terminal_path).resolve()
            actual_dir = Path(actual).resolve()
            # actual is a directory; requested may be either a directory or terminal64.exe
            if requested.is_file():
                requested = requested.parent
            same = actual_dir == requested
        except Exception as e:
            logger.warning(f"Could not normalize terminal paths for verification: {e}")
            return  # Best-effort — don't block on filesystem oddities

        if not same:
            mt5.shutdown()
            raise MT5ConnectionError(
                f"MT5 attached to wrong terminal. Requested: {self.terminal_path}, "
                f"actual: {actual}. Another MT5 instance is likely already running. "
                f"Close it (or set MT5_PASSWORD to force-switch) and retry."
            )
        logger.debug(f"MT5 terminal path verified: {actual}")

    def shutdown(self) -> None:
        """Shutdown MT5 connection gracefully."""
        if self._is_connected:
            mt5.shutdown()
            self._is_connected = False
            logger.info("MT5 connection closed")

    def is_connected(self) -> bool:
        """
        Check if MT5 is connected and on correct server.

        Returns:
            True if connected and terminal is responsive
        """
        if not self._is_connected:
            logger.debug("MT5 is_connected() check: _is_connected=False")
            return False

        try:
            # Check if terminal is still responsive
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.warning("MT5 is_connected() check: terminal_info is None")
                return False

            is_terminal_connected = terminal_info.connected
            if not is_terminal_connected:
                logger.warning(
                    f"MT5 is_connected() check: terminal_info.connected=False "
                    f"(terminal_running={terminal_info.connected}, trade_allowed={getattr(terminal_info, 'trade_allowed', 'unknown')})"
                )
                return False

            # CRITICAL: Check if server changed (prevent auto-switch to test server)
            if self.server:
                account_info = mt5.account_info()
                if account_info and hasattr(account_info, "server"):
                    current_server = account_info.server
                    if current_server.lower() != self.server.lower():
                        logger.error(
                            f"🚨 SERVER MISMATCH DETECTED! "
                            f"Expected: '{self.server}', Current: '{current_server}'. "
                            f"MT5 may have auto-switched servers. Marking as disconnected."
                        )
                        self._is_connected = False
                        return False

            return is_terminal_connected
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
            "server_match": True,
            "expected_server": self.server,
            "current_server": None,
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

            # Check account and server
            account_info = mt5.account_info()
            if account_info:
                health["account_info"] = account_info._asdict()
                if hasattr(account_info, "server"):
                    health["current_server"] = account_info.server
                    # Check server mismatch
                    if self.server and account_info.server.lower() != self.server.lower():
                        health["server_match"] = False
                        logger.warning(
                            f"⚠️ Server mismatch in health check: "
                            f"Expected '{self.server}', Current '{account_info.server}'"
                        )

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        return health

    def _get_error_description(self, retcode: int) -> str:
        """
        Get human-readable error description for MT5 return codes.

        Args:
            retcode: MT5 return code

        Returns:
            Human-readable error description
        """
        error_codes = {
            10004: "Requote",
            10006: "Request rejected",
            10007: "Request canceled by trader",
            10008: "Order placed",
            10009: "Request completed",
            10010: "Only part of the request was completed",
            10011: "Request processing error",
            10012: "Request canceled by timeout",
            10013: "Invalid request",
            10014: "Invalid volume in the request",
            10015: "Invalid price in the request",
            10016: "Invalid stops in the request",
            10017: "Trade is disabled",
            10018: "Market is closed",
            10019: "There is not enough money to complete the request",
            10020: "Prices changed",
            10021: "There are no quotes to process the request",
            10025: "No changes",
            10027: "Off quotes",
            10028: "Broker is busy",
            10029: "Order expired",
            10030: "Invalid order",
            10031: "Invalid volume",
            10032: "Invalid price",
            10033: "Invalid stops",
            10034: "Trade is disabled",
            10035: "Market is closed",
            10036: "There is not enough money",
            10038: "Requote",
            10039: "Order is locked",
            10040: "Long positions only allowed",
            10041: "Too many requests",
        }

        return error_codes.get(retcode, f"Unknown error code: {retcode}")

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
    ) -> dict[str, Any]:
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
            Dictionary with order result. On success, contains order details.
            On failure, contains:
                - success: False
                - error: Error message
                - error_code: MT5 error code
                - error_description: Human-readable error description
        """
        if not self._is_connected:
            logger.error("Cannot place order: MT5 not connected")
            return {
                "success": False,
                "error": "MT5 not connected",
                "error_code": 0,
                "error_description": "MT5 connection not established",
            }

        try:
            # Prepare request
            action = mt5.TRADE_ACTION_DEAL  # Market execution

            type_op = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL

            # Check symbol filling modes
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                error_msg = f"Symbol {symbol} not found"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": 0,
                    "error_description": "Symbol not found in MT5",
                }

            # Determine appropriate filling mode
            filling_mode = mt5.ORDER_FILLING_FOK  # Default fallback

            # Check filling modes supported by the symbol
            # SYMBOL_FILLING_FOK = 1
            # SYMBOL_FILLING_IOC = 2

            # It's safer to rely on what the symbol actually supports
            if symbol_info.filling_mode & 1:  # 1 = SYMBOL_FILLING_FOK
                filling_mode = mt5.ORDER_FILLING_FOK
            elif symbol_info.filling_mode & 2:  # 2 = SYMBOL_FILLING_IOC
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                # If neither FOK nor IOC is explicitly flagged, try RETURN (common for some market execution)
                pass

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
                "type_filling": filling_mode,
            }

            # Send order
            result = mt5.order_send(request)

            if result is None:
                error_code, error_msg = mt5.last_error()
                error_description = (
                    self._get_error_description(error_code) if error_code else "Unknown error"
                )
                logger.error(f"Order failed: {error_msg} (code: {error_code})")
                return {
                    "success": False,
                    "error": error_msg or "Order send returned None",
                    "error_code": error_code,
                    "error_description": error_description,
                }

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_description = self._get_error_description(result.retcode)
                error_msg = result.comment or error_description
                logger.error(f"Order failed: {error_msg} (code: {result.retcode})")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_code": result.retcode,
                    "error_description": error_description,
                }

            logger.info(f"Order placed successfully: {result.order}")
            order_dict = result._asdict()
            order_dict["success"] = True
            return order_dict

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error placing order: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_code": 10000,
                "error_description": "Exception occurred during order placement",
            }

    def get_positions(self, symbol: str = None) -> list[dict[str, Any]]:
        """
        Get open positions.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of position dictionaries
        """
        if not self._is_connected:
            logger.error("Cannot get positions: MT5 not connected")
            return []

        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()

            if positions is None:
                return []

            return [p._asdict() for p in positions]

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
    ) -> dict[str, Any]:
        """
        Modify position SL/TP.

        Args:
            ticket: Position ticket
            sl: New Stop Loss
            tp: New Take Profit

        Returns:
            Dictionary with modification result:
            {
                "success": bool,  # True if modification successful
                "modified": bool,  # True if actual modification was made (False if no changes needed)
                "sl_changed": bool,  # True if SL was changed
                "tp_changed": bool,  # True if TP was changed
                "message": str,  # Status message
            }
        """
        if not self._is_connected:
            logger.error("Cannot modify position: MT5 not connected")
            return {
                "success": False,
                "modified": False,
                "sl_changed": False,
                "tp_changed": False,
                "message": "MT5 not connected",
            }

        try:
            # Get current position to check if changes are needed
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                logger.error(f"Position {ticket} not found")
                return {
                    "success": False,
                    "modified": False,
                    "sl_changed": False,
                    "tp_changed": False,
                    "message": f"Position {ticket} not found",
                }

            current_position = positions[0]
            current_sl = current_position.sl
            current_tp = current_position.tp
            symbol = current_position.symbol

            # Calculate tolerance based on symbol's pip size
            # Get symbol info to determine pip size
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                point = symbol_info.point  # Minimum price change (pip size)
                # Use 0.5 pip tolerance (half of minimum price change)
                tolerance = point * 0.5
            else:
                # Fallback: determine tolerance based on price magnitude
                # Forex major: ~1.0-2.0 range -> pip_size = 0.0001
                # Forex JPY: ~100-200 range -> pip_size = 0.01
                # Commodities: ~1000-2000 range -> pip_size = 0.1
                # Crypto: >10000 range -> pip_size = 1.0
                if abs(current_sl) < 10:
                    tolerance = 0.0001  # Forex major (EURUSD, GBPUSD, etc.)
                elif abs(current_sl) < 1000:
                    tolerance = 0.01  # Forex JPY (USDJPY, etc.)
                elif abs(current_sl) < 10000:
                    tolerance = 0.1  # Commodities (XAUUSD, etc.)
                else:
                    tolerance = 1.0  # Crypto (BTCUSD, etc.)

            # Check if SL needs to change (with tolerance for floating point)
            sl_changed = False
            if sl is not None:
                if abs(sl - current_sl) > tolerance:
                    sl_changed = True
                else:
                    logger.debug(
                        f"SL unchanged: {current_sl:.5f} ≈ {sl:.5f} (tolerance: {tolerance:.5f}, diff: {abs(sl - current_sl):.5f})"
                    )

            # Check if TP needs to change
            tp_changed = False
            if tp is not None:
                if abs(tp - current_tp) > tolerance:
                    tp_changed = True
                else:
                    logger.debug(
                        f"TP unchanged: {current_tp:.5f} ≈ {tp:.5f} (tolerance: {tolerance:.5f}, diff: {abs(tp - current_tp):.5f})"
                    )

            # If no changes needed, return success but not modified
            if not sl_changed and not tp_changed:
                logger.debug(
                    f"No changes needed for position {ticket} (SL: {current_sl:.5f}, TP: {current_tp:.5f})"
                )
                return {
                    "success": True,
                    "modified": False,
                    "sl_changed": False,
                    "tp_changed": False,
                    "message": "No changes needed",
                }

            # Prepare request (use current values if not changing)
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "sl": sl if sl is not None else current_sl,
                "tp": tp if tp is not None else current_tp,
            }

            result = mt5.order_send(request)

            if result is None:
                logger.error("Modify failed: result is None")
                return {
                    "success": False,
                    "modified": False,
                    "sl_changed": sl_changed,
                    "tp_changed": tp_changed,
                    "message": "MT5 order_send returned None",
                }

            # Handle "No changes" error (10025) - treat as success but not modified
            if result.retcode == 10025:
                logger.debug(
                    f"MT5 reports no changes (code: 10025) for ticket {ticket} - treating as success"
                )
                return {
                    "success": True,
                    "modified": False,
                    "sl_changed": sl_changed,
                    "tp_changed": tp_changed,
                    "message": "MT5 reported no changes needed",
                }

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Modify failed: {result.comment} (code: {result.retcode})")
                return {
                    "success": False,
                    "modified": False,
                    "sl_changed": sl_changed,
                    "tp_changed": tp_changed,
                    "message": f"MT5 error: {result.comment} (code: {result.retcode})",
                }

            # Successfully modified
            logger.info(
                f"Position {ticket} modified: SL={sl if sl_changed else 'unchanged'}, TP={tp if tp_changed else 'unchanged'}"
            )
            return {
                "success": True,
                "modified": True,
                "sl_changed": sl_changed,
                "tp_changed": tp_changed,
                "message": "Successfully modified",
            }

        except Exception as e:
            logger.error(f"Error modifying position: {e}")
            return {
                "success": False,
                "modified": False,
                "sl_changed": False,
                "tp_changed": False,
                "message": f"Exception: {str(e)}",
            }

    def close_position(
        self,
        ticket: int,
        volume: float | None = None,
        comment: str = "",
    ) -> dict[str, Any] | None:
        """
        Close a position (full or partial).

        Args:
            ticket: Position ticket
            volume: Volume to close (None for full close)
            comment: Closing comment

        Returns:
            Result dictionary or None if failed
        """
        if not self._is_connected:
            logger.error("Cannot close position: MT5 not connected")
            return None

        try:
            # Get position details to know symbol and type
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                logger.error(f"Position {ticket} not found")
                return None

            position = positions[0]
            symbol = position.symbol

            # Determine close type (Opposite of position type)
            # If BUY (0), close with SELL (1). If SELL (1), close with BUY (0).
            # But order_send uses ORDER_TYPE_SELL to close BUY, and vice versa.
            close_type = (
                mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            )

            # Determine price (Bid for SELL close, Ask for BUY close)
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"Tick data not found for {symbol}")
                return None

            price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

            # Volume to close
            close_volume = volume if volume is not None else position.volume

            # Check filling mode (reuse logic from place_order if possible, or just try FOK/IOC)
            symbol_info = mt5.symbol_info(symbol)
            filling_mode = mt5.ORDER_FILLING_FOK
            if symbol_info:
                if symbol_info.filling_mode & 1:
                    filling_mode = mt5.ORDER_FILLING_FOK
                elif symbol_info.filling_mode & 2:
                    filling_mode = mt5.ORDER_FILLING_IOC

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": symbol,
                "volume": close_volume,
                "type": close_type,
                "price": price,
                "deviation": 20,
                "magic": position.magic,
                "comment": comment or f"Close {ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }

            result = mt5.order_send(request)

            if result is None:
                logger.error("Close failed: result is None")
                return None

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close failed: {result.comment} (code: {result.retcode})")
                return None

            logger.info(f"Position {ticket} closed successfully: {result.order}")
            return result._asdict()

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None

    def get_history_deal(self, ticket: int) -> dict[str, Any] | None:
        """
        Get deal history for a ticket (closing deal only).

        Args:
            ticket: Position ticket

        Returns:
            Closing deal details or None if not found
        """
        if not self._is_connected:
            return None

        try:
            # Get deals for this position (limit to recent deals only)
            # Use position ID to get deals, but limit to last 10 deals to avoid heavy query
            from datetime import datetime, timedelta

            # Only query deals from last 24 hours to limit query size
            date_from = datetime.now() - timedelta(days=1)

            deals = mt5.history_deals_get(position=ticket, date_from=date_from)

            if deals is None or len(deals) == 0:
                return None

            # Filter for closing deals only (DEAL_TYPE_BALANCE or deals with opposite type)
            # The last deal is usually the closing deal
            closing_deal = None
            for deal in reversed(deals):  # Start from most recent
                # Closing deals typically have DEAL_ENTRY_OUT or are balance deals
                if deal.entry == mt5.DEAL_ENTRY_OUT:
                    closing_deal = deal
                    break

            # If no OUT deal found, use the last deal
            if closing_deal is None:
                closing_deal = deals[-1]

            return closing_deal._asdict()

        except Exception as e:
            logger.error(f"Error getting history deal for ticket {ticket}: {e}")
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

    def __exit__(self, *_exc_info):
        """Context manager exit (exception info unused — always shut down)."""
        self.shutdown()
