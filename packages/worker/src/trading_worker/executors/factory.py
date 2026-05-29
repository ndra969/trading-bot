"""
Factory for creating trading type executors.

This module provides a factory pattern for creating executor instances
based on the configured trading type (day_trading, swing_trading, etc.).

The factory encapsulates the logic for:
- Mapping trading types to executor classes
- Validating trading type configuration
- Instantiating executors with proper dependencies
"""

from typing import Any

from trading_core.utils.logger import get_logger

from trading_worker.executors.base_executor import TradingTypeExecutor
from trading_worker.executors.intraday_executor import IntradayExecutor

logger = get_logger(__name__)


class TradingTypeFactory:
    """
    Factory for creating trading type executor instances.

    This class implements the Factory pattern to decouple the trading bot
    from specific executor implementations. New trading types can be added
    by updating the executor mapping without changing the bot code.

    Supported trading types:
    - day_trading: IntradayExecutor (H1 zones, M30 entries)
    - swing_trading: SwingExecutor (TODO - Phase 3)
    - scalping: ScalpingExecutor (TODO - Phase 4)
    - position_trading: PositionExecutor (TODO - Future)

    Example:
        >>> executor = TradingTypeFactory.create_executor(
        ...     trading_type="day_trading",
        ...     config=config,
        ...     foundation_engine=foundation_engine,
        ...     position_manager=position_manager
        ... )
        >>> await executor.initialize()
    """

    # Mapping of trading types to executor classes
    # Add new trading types here as they are implemented
    _EXECUTORS: dict[str, type[TradingTypeExecutor]] = {
        "day_trading": IntradayExecutor,
        # Future implementations:
        # "swing_trading": SwingExecutor,
        # "scalping": ScalpingExecutor,
        # "position_trading": PositionExecutor,
    }

    @staticmethod
    def create_executor(
        trading_type: str,
        config: dict[str, Any],
        foundation_engine: Any,
        position_manager: Any,
    ) -> TradingTypeExecutor:
        """
        Create an executor instance for the specified trading type.

        This method validates the trading type, retrieves the corresponding
        executor class, and instantiates it with the provided dependencies.

        Args:
            trading_type: The trading type (e.g., 'day_trading', 'swing_trading')
            config: Configuration dictionary for the executor
            foundation_engine: Foundation strategy engine instance
            position_manager: Position manager instance

        Returns:
            An instance of the appropriate executor class

        Raises:
            ValueError: If the trading type is not supported

        Example:
            >>> executor = TradingTypeFactory.create_executor(
            ...     trading_type="day_trading",
            ...     config=my_config,
            ...     foundation_engine=my_engine,
            ...     position_manager=my_manager
            ... )
            >>> isinstance(executor, IntradayExecutor)
            True
        """
        # Validate trading type
        executor_class = TradingTypeFactory._EXECUTORS.get(trading_type)

        if executor_class is None:
            # Build helpful error message with supported types
            supported_types = ", ".join(TradingTypeFactory._EXECUTORS.keys())
            error_message = (
                f"Unsupported trading type: '{trading_type}'. "
                f"Supported types: {supported_types}"
            )
            logger.error(error_message)
            raise ValueError(error_message)

        # Create executor instance
        logger.info(f"Creating {executor_class.__name__} for trading type: {trading_type}")

        executor = executor_class(
            config=config,
            foundation_engine=foundation_engine,
            position_manager=position_manager,
        )

        logger.info(f"Successfully created {executor_class.__name__}")

        return executor

    @classmethod
    def get_supported_trading_types(cls) -> list[str]:
        """
        Get list of supported trading types.

        Returns:
            List of trading type names that can be used with create_executor()

        Example:
            >>> TradingTypeFactory.get_supported_trading_types()
            ['day_trading']
        """
        return list(cls._EXECUTORS.keys())

    @classmethod
    def is_trading_type_supported(cls, trading_type: str) -> bool:
        """
        Check if a trading type is supported.

        Args:
            trading_type: The trading type to check

        Returns:
            True if the trading type is supported, False otherwise

        Example:
            >>> TradingTypeFactory.is_trading_type_supported("day_trading")
            True
            >>> TradingTypeFactory.is_trading_type_supported("swing_trading")
            False
        """
        return trading_type in cls._EXECUTORS
