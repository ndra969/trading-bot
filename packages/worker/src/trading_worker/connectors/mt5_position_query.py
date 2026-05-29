"""
MT5 Position Query

Handles MT5 position tracking and monitoring (read operations only).
For position lifecycle management, see trading_worker.position.position_manager.
"""

from datetime import datetime
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


class MT5PositionQuery:
    """
    MT5 Position Manager.

    Provides position tracking, monitoring, and profit/loss calculations.
    """

    def __init__(self, mt5_connector, symbol_manager):
        """
        Initialize Position Manager.

        Args:
            mt5_connector: MT5Connector instance
            symbol_manager: SymbolManager instance
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available")

        self.connector = mt5_connector
        self.symbol_manager = symbol_manager

    def get_all_positions(self) -> list[dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            List of position dictionaries

        Raises:
            MT5ConnectionError: If not connected
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            positions = mt5.positions_get()
            if positions is None:
                return []

            return [pos._asdict() for pos in positions]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_positions_by_symbol(self, symbol: str) -> list[dict[str, Any]]:
        """
        Get positions for specific symbol.

        Args:
            symbol: Symbol name

        Returns:
            List of position dictionaries
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None:
                return []

            return [pos._asdict() for pos in positions]
        except Exception as e:
            logger.error(f"Error getting positions for {symbol}: {e}")
            return []

    def get_position_by_ticket(self, ticket: int) -> dict[str, Any] | None:
        """
        Get position by ticket number.

        Args:
            ticket: Position ticket

        Returns:
            Position dictionary or None
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions and len(positions) > 0:
                return positions[0]._asdict()
            return None
        except Exception as e:
            logger.error(f"Error getting position {ticket}: {e}")
            return None

    def get_position_count(self) -> int:
        """
        Get total number of open positions.

        Returns:
            Number of positions
        """
        positions = self.get_all_positions()
        return len(positions)

    def get_position_count_by_symbol(self, symbol: str) -> int:
        """
        Get number of positions for symbol.

        Args:
            symbol: Symbol name

        Returns:
            Number of positions
        """
        positions = self.get_positions_by_symbol(symbol)
        return len(positions)

    def calculate_position_profit(self, ticket: int) -> float:
        """
        Calculate current profit/loss for position.

        Args:
            ticket: Position ticket

        Returns:
            Profit/loss in account currency
        """
        position = self.get_position_by_ticket(ticket)
        if position is None:
            return 0.0

        return position.get("profit", 0.0)

    def calculate_position_pips(self, ticket: int) -> float:
        """
        Calculate profit/loss in pips.

        Args:
            ticket: Position ticket

        Returns:
            Profit/loss in pips
        """
        position = self.get_position_by_ticket(ticket)
        if position is None:
            return 0.0

        # Get symbol info
        symbol = position.get("symbol", "")
        symbol_info = self.symbol_manager.get_symbol_info(symbol)
        point = symbol_info.get("point", 0.00001)

        # Calculate pip difference
        entry_price = position.get("price_open", 0.0)
        current_price = position.get("price_current", 0.0)
        position_type = position.get("type", 0)

        if position_type == 0:  # BUY
            pip_diff = (current_price - entry_price) / point
        else:  # SELL
            pip_diff = (entry_price - current_price) / point

        return pip_diff

    def get_total_profit(self) -> float:
        """
        Get total profit/loss from all positions.

        Returns:
            Total profit/loss
        """
        positions = self.get_all_positions()
        return sum(pos.get("profit", 0.0) for pos in positions)

    def get_position_summary(self) -> dict[str, Any]:
        """
        Get summary of all positions.

        Returns:
            Dictionary with position summary
        """
        positions = self.get_all_positions()

        buy_positions = [p for p in positions if p.get("type") == 0]
        sell_positions = [p for p in positions if p.get("type") == 1]

        return {
            "total_positions": len(positions),
            "buy_positions": len(buy_positions),
            "sell_positions": len(sell_positions),
            "total_profit": self.get_total_profit(),
            "total_volume": sum(p.get("volume", 0.0) for p in positions),
            "symbols": list({p.get("symbol") for p in positions}),
        }

    def get_position_details(self, ticket: int) -> dict[str, Any]:
        """
        Get detailed position information.

        Args:
            ticket: Position ticket

        Returns:
            Dictionary with position details
        """
        position = self.get_position_by_ticket(ticket)
        if position is None:
            return {}

        symbol = position.get("symbol", "")

        return {
            "ticket": ticket,
            "symbol": symbol,
            "type": "BUY" if position.get("type") == 0 else "SELL",
            "volume": position.get("volume", 0.0),
            "price_open": position.get("price_open", 0.0),
            "price_current": position.get("price_current", 0.0),
            "sl": position.get("sl", 0.0),
            "tp": position.get("tp", 0.0),
            "profit": position.get("profit", 0.0),
            "profit_pips": self.calculate_position_pips(ticket),
            "swap": position.get("swap", 0.0),
            "comment": position.get("comment", ""),
            "time_open": datetime.fromtimestamp(position.get("time", 0)),
        }

    def is_position_profitable(self, ticket: int, threshold: float = 0.0) -> bool:
        """
        Check if position is profitable above threshold.

        Args:
            ticket: Position ticket
            threshold: Minimum profit threshold

        Returns:
            True if position profit exceeds threshold
        """
        profit = self.calculate_position_profit(ticket)
        return profit > threshold
