"""
Base executor abstract class for all trading type executors.

This module defines the abstract interface that all trading executors must implement.
Each trading type (day_trading, swing_trading, scalping, position_trading) has its
own executor with specific logic for:
- Timeframe selection
- Technical indicator usage
- Entry/exit conditions
- Position management
"""

from abc import ABC, abstractmethod
from typing import Any

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class TradingTypeExecutor(ABC):
    """
    Abstract base class for trading type executors.

    Each executor implements a specific trading style (intraday, swing, scalping, etc.)
    with unique characteristics:
    - Timeframes used for analysis
    - Technical indicators and their parameters
    - Entry signal generation logic
    - Risk management rules
    - Position holding duration

    Attributes:
        config: Configuration dictionary for this executor
        foundation_engine: Foundation strategy engine for zone detection
        position_manager: Position manager for trade operations

    Example:
        >>> executor = IntradayExecutor(config, foundation_engine, position_manager)
        >>> await executor.initialize()
        >>> await executor.execute_trading_loop(['XAUUSD', 'EURUSD'])
    """

    def __init__(
        self, config: dict[str, Any], foundation_engine: Any, position_manager: Any
    ) -> None:
        """
        Initialize the trading executor.

        Args:
            config: Configuration dictionary containing trading parameters
            foundation_engine: Foundation strategy engine instance
            position_manager: Position manager instance for trade operations
        """
        self.config = config
        self.foundation_engine = foundation_engine
        self.position_manager = position_manager

        logger.debug(f"{self.__class__.__name__} initialized")

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize executor-specific components.

        This method is called once during executor startup and should:
        - Initialize any required data structures
        - Set up caching mechanisms
        - Validate configuration
        - Prepare technical indicators

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        pass

    @abstractmethod
    async def execute_trading_loop(self, symbols: list[str]) -> None:
        """
        Execute the main trading loop for the given symbols.

        This method implements the core trading logic:
        1. Scan symbols for opportunities
        2. Generate entry signals
        3. Open/close positions via position_manager
        4. Apply risk management rules
        5. Wait for next analysis cycle

        Args:
            symbols: List of symbol names to trade (e.g., ['XAUUSD', 'EURUSD'])

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        pass

    @abstractmethod
    async def analyze_symbol(self, symbol: str, current_time: Any) -> dict[str, Any] | None:
        """
        Analyze a single symbol for trading opportunities.

        This method should:
        1. Get/refresh zones if needed
        2. Check if price is at a zone
        3. Apply trend filters
        4. Validate entry conditions
        5. Generate signal if all conditions met

        Args:
            symbol: Symbol name to analyze (e.g., 'XAUUSD')
            current_time: Current datetime for analysis

        Returns:
            Signal dictionary if entry conditions are met, None otherwise

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        pass

    @abstractmethod
    def get_timeframes(self) -> dict[str, str]:
        """
        Get the timeframes used by this executor.

        Returns a dictionary with timeframe names used for analysis:
        - zone_timeframe: Higher timeframe for zone detection
        - entry_timeframe: Lower timeframe for entry signals
        - trend_timeframe: Timeframe for trend analysis

        Returns:
            Dictionary mapping timeframe names to timeframe values

        Example:
            >>> executor.get_timeframes()
            {
                'zone_timeframe': 'H1',
                'entry_timeframe': 'M30',
                'trend_timeframe': 'H1'
            }

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        pass

    @abstractmethod
    def get_technical_indicators(self) -> dict[str, dict[str, Any]]:
        """
        Get the technical indicators configuration used by this executor.

        Returns a dictionary with indicator parameters for this trading type.
        Each trading type may use different indicators or parameters.

        Returns:
            Dictionary with indicator configurations

        Example:
            >>> executor.get_technical_indicators()
            {
                'ema': {'fast': 20, 'slow': 50, 'trend': 200},
                'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
                'breakeven': {'trigger_r': 0.7, 'offset_pips': 2.0}
            }

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        pass
