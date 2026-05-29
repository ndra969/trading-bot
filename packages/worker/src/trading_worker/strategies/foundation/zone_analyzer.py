"""Zone Analyzer - Analyzes zone strength and quality."""

from trading_core.utils.logger import get_logger

from trading_worker.strategies.foundation.zone_detector import DetectedZone

logger = get_logger(__name__)


class ZoneAnalyzer:
    """Analyzes detected zones for trading opportunities."""

    def __init__(self, config: dict = None):
        """Initialize zone analyzer."""
        self.config = config or {}
        self.min_zone_strength = self.config.get("min_zone_strength", 60.0)
        logger.info(f"ZoneAnalyzer initialized with min_strength={self.min_zone_strength}")

    def analyze_zones(self, zones: list[DetectedZone]) -> list[DetectedZone]:
        """
        Analyze zones and return high-quality zones.

        Args:
            zones: List of detected zones

        Returns:
            Filtered list of high-quality zones
        """
        if not zones:
            return []

        # Filter by strength
        quality_zones = [z for z in zones if z.strength >= self.min_zone_strength]

        # Sort by strength
        quality_zones.sort(key=lambda z: z.strength, reverse=True)

        logger.debug(f"Analyzed {len(zones)} zones, {len(quality_zones)} meet quality threshold")
        return quality_zones
