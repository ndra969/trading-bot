"""
Data Manager

Handles MT5 market data retrieval including OHLCV and tick data.
"""

from datetime import datetime
from typing import Any

import pandas as pd

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from ..exceptions import MT5ConnectionError, MT5DataError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataManager:
    """
    MT5 Data Manager.

    Provides market data retrieval including OHLCV bars and tick data.
    """

    # Timeframe mapping
    TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
        "M5": mt5.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
        "M15": mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
        "M30": mt5.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
        "H1": mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
        "H4": mt5.TIMEFRAME_H4 if MT5_AVAILABLE else 240,
        "D1": mt5.TIMEFRAME_D1 if MT5_AVAILABLE else 1440,
        "W1": mt5.TIMEFRAME_W1 if MT5_AVAILABLE else 10080,
        "MN1": mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else 43200,
    }

    def __init__(self, mt5_connector, symbol_manager):
        """
        Initialize Data Manager.

        Args:
            mt5_connector: MT5Connector instance
            symbol_manager: SymbolManager instance
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available")

        self.connector = mt5_connector
        self.symbol_manager = symbol_manager

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "H1",
        count: int = 100,
        start_pos: int = 0,
    ) -> pd.DataFrame:
        """
        Get OHLCV data for symbol.

        Args:
            symbol: Symbol name
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
            count: Number of bars to retrieve
            start_pos: Start position (0 = most recent)

        Returns:
            DataFrame with OHLCV data

        Raises:
            MT5DataError: If data retrieval fails
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        # Validate symbol
        self.symbol_manager.validate_symbol(symbol)

        # Get timeframe constant
        if timeframe not in self.TIMEFRAMES:
            raise MT5DataError(
                f"Invalid timeframe: {timeframe}", symbol=symbol, timeframe=timeframe
            )

        mt5_timeframe = self.TIMEFRAMES[timeframe]

        try:
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, start_pos, count)

            if rates is None or len(rates) == 0:
                error_code, error_msg = mt5.last_error()
                raise MT5DataError(
                    f"No data available: {error_msg}", symbol=symbol, timeframe=timeframe
                )

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Rename columns for clarity
            df = df.rename(
                columns={
                    "time": "timestamp",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "tick_volume": "volume",
                    "spread": "spread",
                    "real_volume": "real_volume",
                }
            )

            # Set timestamp as index for zone detection compatibility
            df = df.set_index("timestamp")

            logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
            return df

        except MT5DataError:
            raise
        except Exception as e:
            logger.error(f"Error getting OHLCV data: {e}")
            raise MT5DataError(str(e), symbol=symbol, timeframe=timeframe) from e

    def get_ohlcv_range(
        self,
        symbol: str,
        timeframe: str,
        date_from: datetime,
        date_to: datetime,
    ) -> pd.DataFrame:
        """
        Get OHLCV data for date range.

        Args:
            symbol: Symbol name
            timeframe: Timeframe
            date_from: Start date
            date_to: End date

        Returns:
            DataFrame with OHLCV data
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        self.symbol_manager.validate_symbol(symbol)

        if timeframe not in self.TIMEFRAMES:
            raise MT5DataError(
                f"Invalid timeframe: {timeframe}", symbol=symbol, timeframe=timeframe
            )

        mt5_timeframe = self.TIMEFRAMES[timeframe]

        try:
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, date_from, date_to)

            if rates is None or len(rates) == 0:
                raise MT5DataError(
                    "No data available for date range", symbol=symbol, timeframe=timeframe
                )

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            df = df.rename(
                columns={
                    "time": "timestamp",
                    "tick_volume": "volume",
                }
            )

            # Set timestamp as index for zone detection compatibility
            df = df.set_index("timestamp")

            logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe}")
            return df

        except MT5DataError:
            raise
        except Exception as e:
            logger.error(f"Error getting OHLCV range: {e}")
            raise MT5DataError(str(e), symbol=symbol, timeframe=timeframe) from e

    def get_last_tick(self, symbol: str) -> dict[str, Any]:
        """
        Get last tick for symbol.

        Args:
            symbol: Symbol name

        Returns:
            Dictionary with tick data
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        self.symbol_manager.validate_symbol(symbol)

        try:
            tick = mt5.symbol_info_tick(symbol)

            if tick is None:
                raise MT5DataError("No tick data available", symbol=symbol)

            return tick._asdict()

        except MT5DataError:
            raise
        except Exception as e:
            logger.error(f"Error getting tick: {e}")
            raise MT5DataError(str(e), symbol=symbol) from e

    def get_ticks(
        self,
        symbol: str,
        count: int = 100,
        flags: int = None,
    ) -> pd.DataFrame:
        """
        Get tick data.

        Args:
            symbol: Symbol name
            count: Number of ticks
            flags: Tick flags (mt5.COPY_TICKS_ALL, mt5.COPY_TICKS_INFO, mt5.COPY_TICKS_TRADE)

        Returns:
            DataFrame with tick data
        """
        if not self.connector.is_connected():
            raise MT5ConnectionError("MT5 not connected")

        self.symbol_manager.validate_symbol(symbol)

        if flags is None:
            flags = mt5.COPY_TICKS_ALL

        try:
            ticks = mt5.copy_ticks_from_pos(symbol, 0, count, flags)

            if ticks is None or len(ticks) == 0:
                raise MT5DataError("No tick data available", symbol=symbol)

            df = pd.DataFrame(ticks)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            logger.info(f"Retrieved {len(df)} ticks for {symbol}")
            return df

        except MT5DataError:
            raise
        except Exception as e:
            logger.error(f"Error getting ticks: {e}")
            raise MT5DataError(str(e), symbol=symbol) from e

    def get_current_price(self, symbol: str) -> tuple[float, float]:
        """
        Get current bid/ask prices.

        Args:
            symbol: Symbol name

        Returns:
            Tuple of (bid, ask)
        """
        tick = self.get_last_tick(symbol)
        return (tick.get("bid", 0.0), tick.get("ask", 0.0))
