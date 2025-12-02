"""Foundation Engine - Coordinates foundation strategy."""

from typing import Any

import pandas as pd

from trading_bot.strategies.foundation.supply_demand import SupplyDemandStrategy
from trading_bot.strategies.foundation.zone_detector import DetectedZone
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class FoundationEngine:
    """
    Foundation strategy engine.

    Coordinates all foundation strategy components.
    """

    def __init__(self, config: dict[str, Any] = None, use_database: bool = True):
        """
        Initialize foundation engine.

        Args:
            config: Engine configuration
            use_database: Whether to persist zones to database
        """
        self.config = config or {}

        # Initialize S&D strategy
        self.strategy = SupplyDemandStrategy(
            self.config.get("supply_demand", {}), use_database=use_database
        )

        logger.info(f"FoundationEngine initialized (database: {use_database})")

    async def analyze_symbol(
        self, symbol: str, data: pd.DataFrame, timeframe: str = "H1"
    ) -> list[DetectedZone]:
        """
        Analyze a symbol using foundation strategy.

        Args:
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Timeframe for zones

        Returns:
            List of detected zones
        """
        logger.debug(f"Analyzing {symbol} with foundation strategy")
        return await self.strategy.analyze(symbol, data, timeframe)

    async def load_zones(self, symbol: str) -> None:
        """Load zones from database for a symbol."""
        await self.strategy.load_zones(symbol)

    def get_zones(self, symbol: str) -> list[DetectedZone]:
        """Get detected zones for a symbol."""
        return self.strategy.get_zones(symbol)
