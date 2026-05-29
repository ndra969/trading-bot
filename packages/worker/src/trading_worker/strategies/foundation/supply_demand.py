"""Supply & Demand Strategy - Main foundation strategy."""

from datetime import datetime

import pandas as pd
from trading_core.utils.logger import get_logger

from trading_worker.strategies.foundation.zone_analyzer import ZoneAnalyzer
from trading_worker.strategies.foundation.zone_detector import DetectedZone, ZoneDetector
from trading_worker.strategies.foundation.zone_manager import ZoneManager

logger = get_logger(__name__)


class SupplyDemandStrategy:
    """
    Supply & Demand trading strategy.

    Detects and trades based on supply/demand zones.
    """

    def __init__(self, config: dict = None, use_database: bool = True):
        """
        Initialize S&D strategy.

        Args:
            config: Strategy configuration
            use_database: Whether to persist zones to database
        """
        self.config = config or {}

        # ZoneDetector expects a flat config: zone_detection params at the top
        # plus scoring_weights as a nested dict. Merge them here so the YAML
        # nesting stays semantically meaningful while the detector still gets
        # the shape it expects.
        detector_config = {
            **self.config.get("zone_detection", {}),
            "scoring_weights": self.config.get("scoring_weights", {}),
        }

        # Initialize components
        self.detector = ZoneDetector(detector_config)
        self.manager = ZoneManager(
            config=self.config.get("zone_management", {}), use_database=use_database
        )
        self.analyzer = ZoneAnalyzer(self.config.get("analysis", {}))

        logger.info(f"SupplyDemandStrategy initialized (database: {use_database})")

    async def analyze(
        self,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str = "H1",
        reference_time: datetime | None = None,
    ) -> list[DetectedZone]:
        """
        Analyze market data for supply/demand zones.

        Args:
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Timeframe for zones
            reference_time: Reference time for zone age calculation (for backtest)

        Returns:
            List of detected high-quality zones
        """
        try:
            # Detect zones with reference time (for backtest mode)
            zones = self.detector.detect_zones(data, reference_time=reference_time)

            # Store zones (async - saves to database)
            await self.manager.add_zones(symbol, zones, timeframe)

            # Analyze and filter quality zones
            quality_zones = self.analyzer.analyze_zones(zones)

            logger.info(f"{symbol}: Detected {len(zones)} zones, {len(quality_zones)} high-quality")
            return quality_zones

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return []

    async def load_zones(self, symbol: str) -> None:
        """Load zones from database for a symbol."""
        await self.manager.load_zones_from_db(symbol)

    def get_zones(self, symbol: str) -> list[DetectedZone]:
        """Get all zones for a symbol."""
        return self.manager.get_zones(symbol)
