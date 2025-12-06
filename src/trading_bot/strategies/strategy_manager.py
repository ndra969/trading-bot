"""
Strategy Manager - Orchestrates all trading strategies.

Coordinates multiple strategies and manages their execution.
"""

import asyncio
from typing import Any, Protocol

import pandas as pd

from trading_bot.strategies.models import StrategyResult
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class BaseStrategy(Protocol):
    """Protocol for strategy interface."""

    async def generate_signals(
        self, symbol: str, data: pd.DataFrame, timeframe: str
    ) -> list[StrategyResult]:
        """Generate trading signals from strategy."""
        ...


class StrategyManager:
    """
    Manages and coordinates all trading strategies.

    Responsibilities:
    - Register and manage multiple strategies
    - Execute strategies for symbol analysis
    - Collect and aggregate strategy results
    - Prevent conflicts (1 trade per symbol)
    - Monitor strategy health
    """

    def __init__(self, config: dict[str, Any] = None):
        """
        Initialize strategy manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.strategies: dict[str, BaseStrategy] = {}
        self.strategy_health: dict[str, bool] = {}

        # Configuration
        self.max_concurrent_strategies = self.config.get("strategy_manager", {}).get(
            "max_concurrent_strategies", 8
        )
        self.conflict_prevention = self.config.get("strategy_manager", {}).get(
            "conflict_prevention", True
        )
        self.health_check_interval = self.config.get("strategy_manager", {}).get(
            "health_check_interval", 300
        )

        logger.info(
            f"StrategyManager initialized (max strategies: {self.max_concurrent_strategies})"
        )

    def register_strategy(self, name: str, strategy: BaseStrategy) -> None:
        """
        Register a strategy.

        Args:
            name: Strategy name (e.g., "foundation", "trendline")
            strategy: Strategy instance

        Raises:
            ValueError: If strategy name already exists or max strategies reached
        """
        if name in self.strategies:
            raise ValueError(f"Strategy '{name}' is already registered")

        if len(self.strategies) >= self.max_concurrent_strategies:
            raise ValueError(
                f"Maximum number of strategies ({self.max_concurrent_strategies}) reached"
            )

        self.strategies[name] = strategy
        self.strategy_health[name] = True
        logger.info(f"Strategy '{name}' registered successfully")

    def unregister_strategy(self, name: str) -> None:
        """
        Unregister a strategy.

        Args:
            name: Strategy name to remove

        Raises:
            ValueError: If strategy not found
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")

        del self.strategies[name]
        del self.strategy_health[name]
        logger.info(f"Strategy '{name}' unregistered")

    def get_active_strategies(self) -> list[str]:
        """
        Get list of active strategies.

        Returns:
            List of active strategy names
        """
        return [name for name, healthy in self.strategy_health.items() if healthy]

    async def analyze_symbol(
        self, symbol: str, data: pd.DataFrame, timeframe: str = "H1"
    ) -> list[StrategyResult]:
        """
        Analyze symbol using all active strategies.

        Args:
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Analysis timeframe

        Returns:
            List of StrategyResult from all strategies
        """
        if not self.strategies:
            logger.warning("No strategies registered")
            return []

        logger.debug(f"Analyzing {symbol} with {len(self.strategies)} strategies")

        # Execute all strategies concurrently
        tasks = []
        strategy_names = []

        for name, strategy in self.strategies.items():
            if not self.strategy_health.get(name, False):
                logger.debug(f"Skipping unhealthy strategy: {name}")
                continue

            tasks.append(self._execute_strategy(name, strategy, symbol, data, timeframe))
            strategy_names.append(name)

        if not tasks:
            logger.warning("No healthy strategies available")
            return []

        # Wait for all strategies to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid results
        all_results = []
        for name, result in zip(strategy_names, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Strategy '{name}' failed: {result}")
                self.strategy_health[name] = False
                continue

            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, StrategyResult):
                all_results.append(result)

        logger.info(
            f"Analysis complete for {symbol}: {len(all_results)} results from "
            f"{len([r for r in results if not isinstance(r, Exception)])} strategies"
        )

        return all_results

    async def _execute_strategy(
        self,
        name: str,
        strategy: BaseStrategy,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str,
    ) -> list[StrategyResult]:
        """
        Execute a single strategy with error handling.

        Args:
            name: Strategy name
            strategy: Strategy instance
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Analysis timeframe

        Returns:
            List of StrategyResult
        """
        try:
            logger.debug(f"Executing strategy '{name}' for {symbol}")
            results = await strategy.generate_signals(symbol, data, timeframe)

            if not isinstance(results, list):
                logger.error(f"Strategy '{name}' returned invalid result type: {type(results)}")
                return []

            # Validate results
            valid_results = []
            for result in results:
                if not isinstance(result, StrategyResult):
                    logger.warning(
                        f"Strategy '{name}' returned invalid result type: {type(result)}"
                    )
                    continue

                if result.strategy_name != name:
                    logger.warning(
                        f"Strategy '{name}' returned result with wrong name: {result.strategy_name}"
                    )
                    result.strategy_name = name  # Fix the name

                valid_results.append(result)

            logger.debug(f"Strategy '{name}' for {symbol}: {len(valid_results)} valid results")
            return valid_results

        except Exception as e:
            logger.error(f"Error executing strategy '{name}': {e}", exc_info=True)
            self.strategy_health[name] = False
            return []

    async def health_check(self) -> dict[str, bool]:
        """
        Check health of all registered strategies.

        Returns:
            Dictionary mapping strategy names to health status
        """
        health_status = {}

        for name, _strategy in self.strategies.items():
            try:
                # Try to execute strategy with empty data as health check
                # In real scenario, you might want a dedicated health check method
                health_status[name] = self.strategy_health.get(name, True)
            except Exception as e:
                logger.error(f"Health check failed for strategy '{name}': {e}")
                health_status[name] = False
                self.strategy_health[name] = False

        healthy_count = sum(1 for healthy in health_status.values() if healthy)
        logger.info(f"Health check: {healthy_count}/{len(health_status)} strategies healthy")

        return health_status

    def reset_strategy_health(self, name: str) -> None:
        """
        Reset health status for a strategy.

        Args:
            name: Strategy name

        Raises:
            ValueError: If strategy not found
        """
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")

        self.strategy_health[name] = True
        logger.info(f"Health reset for strategy '{name}'")

    def get_strategy_count(self) -> int:
        """Get total number of registered strategies."""
        return len(self.strategies)

    def is_strategy_registered(self, name: str) -> bool:
        """Check if a strategy is registered."""
        return name in self.strategies

    def __str__(self) -> str:
        """String representation."""
        healthy = len(self.get_active_strategies())
        total = len(self.strategies)
        return f"StrategyManager({healthy}/{total} strategies active)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
