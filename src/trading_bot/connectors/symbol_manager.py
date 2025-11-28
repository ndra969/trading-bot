"""
Symbol Manager

Handles MT5 symbol operations including discovery, validation, and information retrieval.
"""

from typing import Any

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from ..exceptions import MT5ConnectionError, MT5SymbolError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SymbolManager:
    """
    MT5 Symbol Manager.

    Provides symbol discovery, validation, and information retrieval.
    """

    def __init__(self, mt5_connector):
        """
        Initialize Symbol Manager.

        Args:
            mt5_connector: MT5Connector instance
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available")

        self.connector = mt5_connector

    def get_all_symbols(self) -> list[str]:
        """
        Get all available symbols.

        Returns:
            List of symbol names

        Raises:
            MT5ConnectionError: If not connected to MT5
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            symbols = mt5.symbols_get()
            if symbols is None:
                return []

            return [symbol.name for symbol in symbols]
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []

    def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        """
        Get detailed symbol information.

        Args:
            symbol: Symbol name

        Returns:
            Dictionary with symbol details

        Raises:
            MT5SymbolError: If symbol not found
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                raise MT5SymbolError(symbol, "Symbol not found or not available")

            return symbol_info._asdict()
        except MT5SymbolError:
            raise
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            raise MT5SymbolError(symbol, str(e)) from e

    def is_symbol_available(self, symbol: str) -> bool:
        """
        Check if symbol is available for trading.

        Args:
            symbol: Symbol name

        Returns:
            True if symbol is available
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            return symbol_info.get("visible", False)
        except Exception:
            return False

    def is_trading_allowed(self, symbol: str) -> bool:
        """
        Check if trading is allowed for symbol.

        Args:
            symbol: Symbol name

        Returns:
            True if trading is allowed
        """
        try:
            symbol_info = self.get_symbol_info(symbol)
            return symbol_info.get("trade_mode", 0) != 0  # 0 = DISABLED
        except Exception:
            return False

    def get_symbol_specs(self, symbol: str) -> dict[str, Any]:
        """
        Get symbol specifications (contract details).

        Args:
            symbol: Symbol name

        Returns:
            Dictionary with symbol specifications
        """
        symbol_info = self.get_symbol_info(symbol)

        return {
            "symbol": symbol,
            "description": symbol_info.get("description", ""),
            "digits": symbol_info.get("digits", 5),
            "point": symbol_info.get("point", 0.00001),
            "tick_size": symbol_info.get("trade_tick_size", 0.00001),
            "tick_value": symbol_info.get("trade_tick_value", 1.0),
            "contract_size": symbol_info.get("trade_contract_size", 100000.0),
            "volume_min": symbol_info.get("volume_min", 0.01),
            "volume_max": symbol_info.get("volume_max", 100.0),
            "volume_step": symbol_info.get("volume_step", 0.01),
            "swap_long": symbol_info.get("swap_long", 0.0),
            "swap_short": symbol_info.get("swap_short", 0.0),
            "currency_base": symbol_info.get("currency_base", ""),
            "currency_profit": symbol_info.get("currency_profit", ""),
            "currency_margin": symbol_info.get("currency_margin", ""),
        }

    def get_bid_ask(self, symbol: str) -> tuple[float, float]:
        """
        Get current bid and ask prices.

        Args:
            symbol: Symbol name

        Returns:
            Tuple of (bid, ask) prices
        """
        symbol_info = self.get_symbol_info(symbol)
        bid = symbol_info.get("bid", 0.0)
        ask = symbol_info.get("ask", 0.0)
        return (bid, ask)

    def get_spread(self, symbol: str) -> float:
        """
        Get current spread in points.

        Args:
            symbol: Symbol name

        Returns:
            Spread in points
        """
        symbol_info = self.get_symbol_info(symbol)
        return symbol_info.get("spread", 0.0)

    def select_symbol(self, symbol: str, enable: bool = True) -> bool:
        """
        Enable or disable symbol in Market Watch.

        Args:
            symbol: Symbol name
            enable: True to enable, False to disable

        Returns:
            True if operation successful
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        try:
            result = mt5.symbol_select(symbol, enable)
            if result:
                logger.info(
                    f"Symbol {symbol} {'enabled' if enable else 'disabled'} in Market Watch"
                )
            return result
        except Exception as e:
            logger.error(f"Error selecting symbol {symbol}: {e}")
            return False

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol for trading.

        Args:
            symbol: Symbol name

        Returns:
            True if symbol is valid and tradable

        Raises:
            MT5SymbolError: If symbol validation fails
        """
        # Check if symbol exists
        if not self.is_symbol_available(symbol):
            raise MT5SymbolError(symbol, "Symbol not available")

        # Check if trading allowed
        if not self.is_trading_allowed(symbol):
            raise MT5SymbolError(symbol, "Trading not allowed for this symbol")

        # Ensure symbol is in Market Watch
        self.select_symbol(symbol, True)

        logger.info(f"Symbol {symbol} validated successfully")
        return True
