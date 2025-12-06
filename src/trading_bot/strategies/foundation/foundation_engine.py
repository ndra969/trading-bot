"""Foundation Engine - Coordinates foundation strategy."""

from typing import Any

import pandas as pd

from trading_bot.strategies.foundation.supply_demand import SupplyDemandStrategy
from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_bot.strategies.models import SignalDirection, StrategyResult
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

    async def generate_signals(
        self, symbol: str, data: pd.DataFrame, timeframe: str = "H1"
    ) -> list[StrategyResult]:
        """
        Generate trading signals from foundation strategy.

        Args:
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Analysis timeframe

        Returns:
            List of StrategyResult objects
        """
        logger.debug(f"Generating signals for {symbol}")

        # First analyze and detect zones
        zones = await self.analyze_symbol(symbol, data, timeframe)

        if not zones:
            logger.debug(f"{symbol}: No zones detected")
            return []

        # Get current price from data
        if data.empty:
            logger.warning(f"{symbol}: Empty data, cannot generate signals")
            return []

        current_price = float(data["close"].iloc[-1])

        # Generate signals from zones
        results = []
        for zone in zones:
            # Check if price is at/near zone
            if self._is_price_at_zone(current_price, zone):
                result = self._create_signal_from_zone(symbol, zone, current_price, timeframe, data)
                if result:
                    results.append(result)

        logger.debug(f"{symbol}: Generated {len(results)} signals from {len(zones)} zones")
        return results

    def _is_price_at_zone(self, current_price: float, zone: DetectedZone) -> bool:
        """
        Check if current price is at or near a zone.

        Args:
            current_price: Current market price
            zone: Detected zone

        Returns:
            True if price is at zone
        """
        # Price is "at zone" if it's within the zone boundaries
        # or within 20% of the zone size above/below the zone
        zone_size = zone.upper_bound - zone.lower_bound
        tolerance = zone_size * 0.2

        # Check if price is within zone boundaries (with tolerance)
        return zone.lower_bound - tolerance <= current_price <= zone.upper_bound + tolerance

    def _is_demand_zone(self, zone: DetectedZone, data: pd.DataFrame) -> bool:
        """
        Determine if zone is a demand zone (price likely to bounce up).

        Args:
            zone: Detected zone
            data: OHLCV data

        Returns:
            True if zone is demand zone
        """
        # Simple heuristic: if zone is rejection type and price moved up after,
        # it's likely a demand zone. Otherwise, check price action after zone.
        if zone.zone_type == ZoneType.REJECTION:
            # For rejection zones, check if price was rejected upward
            # (demand zone = price rejected from below, then moved up)
            return True  # Rejection zones are typically demand zones
        elif zone.zone_type == ZoneType.BREAKOUT_ORIGIN:
            # Breakout origin zones can be either, but if price broke upward,
            # it's likely a demand zone
            if not data.empty:
                # Check if price after zone is higher
                zone_end_idx = len(data) - 1
                if zone_end_idx > 0:
                    price_after = data["close"].iloc[-1]
                    return price_after > zone.upper_bound
        # Default: assume demand zone for consolidation
        return True

    def _create_signal_from_zone(
        self,
        symbol: str,
        zone: DetectedZone,
        current_price: float,
        timeframe: str,
        data: pd.DataFrame,
    ) -> StrategyResult | None:
        """
        Create a trading signal from a zone.

        Args:
            symbol: Trading symbol
            zone: Detected zone
            current_price: Current market price
            timeframe: Analysis timeframe
            data: OHLCV data for context

        Returns:
            StrategyResult or None if signal cannot be created
        """
        try:
            # Determine if zone is demand or supply
            is_demand = self._is_demand_zone(zone, data)

            if is_demand:
                # Demand zone = BUY signal (price likely to bounce up)
                direction = SignalDirection.BUY
                entry_price = zone.upper_bound  # Enter at top of demand zone
                stop_loss = (
                    zone.lower_bound - (zone.upper_bound - zone.lower_bound) * 0.1
                )  # 10% below zone
                take_profit = entry_price + (entry_price - stop_loss) * 3.0  # 1:3 R:R
            else:
                # Supply zone = SELL signal (price likely to bounce down)
                direction = SignalDirection.SELL
                entry_price = zone.lower_bound  # Enter at bottom of supply zone
                stop_loss = (
                    zone.upper_bound + (zone.upper_bound - zone.lower_bound) * 0.1
                )  # 10% above zone
                take_profit = entry_price - (stop_loss - entry_price) * 3.0  # 1:3 R:R

            # Validate prices
            if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
                logger.warning(f"{symbol}: Invalid prices for zone signal")
                return None

            # Generate zone_id from zone properties (same format as ZoneManager)
            zone_id = (
                f"{symbol}_{zone.zone_type.value}_{zone.lower_bound:.5f}_{zone.upper_bound:.5f}"
            )

            # Create result
            result = StrategyResult(
                strategy_name="foundation",
                symbol=symbol,
                score=zone.strength,  # Use zone strength as score
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=timeframe,
                metadata={
                    "zone_id": zone_id,
                    "zone_type": zone.zone_type.value,
                    "zone_strength": zone.strength,
                    "zone_touches": zone.touches,
                },
            )

            logger.debug(
                f"Created signal: {direction.value} {symbol} @ {entry_price:.5f} "
                f"(zone strength: {zone.strength:.1f})"
            )

            return result

        except Exception as e:
            logger.error(f"Error creating signal from zone: {e}")
            return None
