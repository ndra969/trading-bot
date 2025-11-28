"""
Order Manager

Handles MT5 order operations including execution, modification, and cancellation.
"""

from enum import Enum
from typing import Any

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from ..exceptions import MT5ConnectionError, MT5OrderError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OrderType(Enum):
    """Order type enumeration."""

    BUY = mt5.ORDER_TYPE_BUY if MT5_AVAILABLE else 0
    SELL = mt5.ORDER_TYPE_SELL if MT5_AVAILABLE else 1
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT if MT5_AVAILABLE else 2
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT if MT5_AVAILABLE else 3
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP if MT5_AVAILABLE else 4
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP if MT5_AVAILABLE else 5


class OrderManager:
    """
    MT5 Order Manager.

    Provides order execution, modification, and management functionality.
    """

    def __init__(self, mt5_connector, symbol_manager):
        """
        Initialize Order Manager.

        Args:
            mt5_connector: MT5Connector instance
            symbol_manager: SymbolManager instance
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available")

        self.connector = mt5_connector
        self.symbol_manager = symbol_manager

    def send_market_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        sl: float | None = None,
        tp: float | None = None,
        deviation: int = 10,
        comment: str = "",
    ) -> dict[str, Any]:
        """
        Send market order (buy/sell immediately).

        Args:
            symbol: Symbol to trade
            order_type: "BUY" or "SELL"
            volume: Trade volume (lots)
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            deviation: Maximum price deviation in points
            comment: Order comment

        Returns:
            Dictionary with order result

        Raises:
            MT5OrderError: If order execution fails
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        # Validate symbol
        self.symbol_manager.validate_symbol(symbol)

        # Get symbol info
        symbol_info = self.symbol_manager.get_symbol_info(symbol)

        # Validate volume
        volume_min = symbol_info.get("volume_min", 0.01)
        volume_max = symbol_info.get("volume_max", 100.0)
        symbol_info.get("volume_step", 0.01)

        if volume < volume_min:
            raise MT5OrderError(f"Volume {volume} below minimum {volume_min}", 10013)
        if volume > volume_max:
            raise MT5OrderError(f"Volume {volume} exceeds maximum {volume_max}", 10014)

        # Determine order type
        if order_type.upper() == "BUY":
            trade_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.get("ask", 0.0)
        elif order_type.upper() == "SELL":
            trade_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.get("bid", 0.0)
        else:
            raise MT5OrderError(f"Invalid order type: {order_type}", 10015)

        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": trade_type,
            "price": price,
            "deviation": deviation,
            "magic": 234000,  # Magic number for identification
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Add SL/TP if provided
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp

        # Send order
        try:
            result = mt5.order_send(request)

            if result is None:
                error_code, error_msg = mt5.last_error()
                raise MT5OrderError(f"Order send failed: {error_msg}", error_code)

            result_dict = result._asdict()

            # Check result
            if result_dict.get("retcode") != mt5.TRADE_RETCODE_DONE:
                retcode = result_dict.get("retcode", 0)
                comment = result_dict.get("comment", "Unknown error")
                raise MT5OrderError(f"Order rejected: {comment}", retcode)

            logger.info(f"Market order executed: {order_type} {volume} {symbol} @ {price}")
            return result_dict

        except MT5OrderError:
            raise
        except Exception as e:
            logger.error(f"Error sending order: {e}")
            raise MT5OrderError(str(e), 10000) from e

    def send_pending_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "",
    ) -> dict[str, Any]:
        """
        Send pending order (limit/stop).

        Args:
            symbol: Symbol to trade
            order_type: "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
            volume: Trade volume (lots)
            price: Order price
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Order comment

        Returns:
            Dictionary with order result

        Raises:
            MT5OrderError: If order placement fails
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        # Validate symbol
        self.symbol_manager.validate_symbol(symbol)

        # Determine order type
        order_type_map = {
            "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
            "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
            "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
            "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
        }

        if order_type.upper() not in order_type_map:
            raise MT5OrderError(f"Invalid pending order type: {order_type}", 10015)

        trade_type = order_type_map[order_type.upper()]

        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": trade_type,
            "price": price,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        # Add SL/TP if provided
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp

        # Send order
        try:
            result = mt5.order_send(request)

            if result is None:
                error_code, error_msg = mt5.last_error()
                raise MT5OrderError(f"Pending order failed: {error_msg}", error_code)

            result_dict = result._asdict()

            if result_dict.get("retcode") != mt5.TRADE_RETCODE_DONE:
                retcode = result_dict.get("retcode", 0)
                comment = result_dict.get("comment", "Unknown error")
                raise MT5OrderError(f"Pending order rejected: {comment}", retcode)

            logger.info(f"Pending order placed: {order_type} {volume} {symbol} @ {price}")
            return result_dict

        except MT5OrderError:
            raise
        except Exception as e:
            logger.error(f"Error sending pending order: {e}")
            raise MT5OrderError(str(e), 10000) from e

    def modify_position(
        self,
        ticket: int,
        sl: float | None = None,
        tp: float | None = None,
    ) -> dict[str, Any]:
        """
        Modify position SL/TP.

        Args:
            ticket: Position ticket number
            sl: New stop loss (None to keep current)
            tp: New take profit (None to keep current)

        Returns:
            Dictionary with modification result

        Raises:
            MT5OrderError: If modification fails
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        # Get position info
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Position {ticket} not found", 10016)

        position = position[0]

        # Prepare modification request
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "sl": sl if sl is not None else position.sl,
            "tp": tp if tp is not None else position.tp,
        }

        # Send modification
        try:
            result = mt5.order_send(request)

            if result is None:
                error_code, error_msg = mt5.last_error()
                raise MT5OrderError(f"Position modification failed: {error_msg}", error_code)

            result_dict = result._asdict()

            if result_dict.get("retcode") != mt5.TRADE_RETCODE_DONE:
                retcode = result_dict.get("retcode", 0)
                comment = result_dict.get("comment", "Unknown error")
                raise MT5OrderError(f"Modification rejected: {comment}", retcode)

            logger.info(f"Position {ticket} modified: SL={sl}, TP={tp}")
            return result_dict

        except MT5OrderError:
            raise
        except Exception as e:
            logger.error(f"Error modifying position: {e}")
            raise MT5OrderError(str(e), 10000) from e

    def close_position(
        self,
        ticket: int,
        volume: float | None = None,
        deviation: int = 10,
    ) -> dict[str, Any]:
        """
        Close position (full or partial).

        Args:
            ticket: Position ticket number
            volume: Volume to close (None for full closure)
            deviation: Maximum price deviation

        Returns:
            Dictionary with close result

        Raises:
            MT5OrderError: If close fails
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        # Get position info
        position = mt5.positions_get(ticket=ticket)
        if not position:
            raise MT5OrderError(f"Position {ticket} not found", 10016)

        position = position[0]

        # Determine close volume
        close_volume = volume if volume is not None else position.volume

        # Determine close type (opposite of position type)
        if position.type == mt5.POSITION_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
        else:
            close_type = mt5.ORDER_TYPE_BUY

        # Get current price
        symbol_info = self.symbol_manager.get_symbol_info(position.symbol)
        if close_type == mt5.ORDER_TYPE_BUY:
            price = symbol_info.get("ask", 0.0)
        else:
            price = symbol_info.get("bid", 0.0)

        # Prepare close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": close_volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": deviation,
            "magic": 234000,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send close request
        try:
            result = mt5.order_send(request)

            if result is None:
                error_code, error_msg = mt5.last_error()
                raise MT5OrderError(f"Position close failed: {error_msg}", error_code)

            result_dict = result._asdict()

            if result_dict.get("retcode") != mt5.TRADE_RETCODE_DONE:
                retcode = result_dict.get("retcode", 0)
                comment = result_dict.get("comment", "Unknown error")
                raise MT5OrderError(f"Close rejected: {comment}", retcode)

            logger.info(f"Position {ticket} closed: {close_volume} lots @ {price}")
            return result_dict

        except MT5OrderError:
            raise
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise MT5OrderError(str(e), 10000) from e
