"""Foundation Engine - Coordinates foundation strategy."""

from datetime import datetime
from typing import Any

import pandas as pd

from trading_bot.strategies.enhancement.breakout_analyzer import BreakoutAnalyzer
from trading_bot.strategies.enhancement.fibonacci_analyzer import FibonacciAnalyzer
from trading_bot.strategies.enhancement.ma_analyzer import MovingAverageAnalyzer
from trading_bot.strategies.enhancement.price_action_analyzer import PriceActionAnalyzer
from trading_bot.strategies.enhancement.rsi_analyzer import RSIAnalyzer
from trading_bot.strategies.enhancement.structure_analyzer import MarketStructureAnalyzer
from trading_bot.strategies.enhancement.trendline_analyzer import TrendlineAnalyzer
from trading_bot.strategies.foundation.supply_demand import SupplyDemandStrategy
from trading_bot.strategies.foundation.zone_detector import DetectedZone
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

        # Initialize Enhancement Analyzers
        self.rsi_analyzer = RSIAnalyzer(self.config)
        self.ma_analyzer = MovingAverageAnalyzer(self.config)
        self.trendline_analyzer = TrendlineAnalyzer(self.config)
        self.price_action_analyzer = PriceActionAnalyzer(self.config)
        self.fibonacci_analyzer = FibonacciAnalyzer(self.config)
        self.structure_analyzer = MarketStructureAnalyzer(self.config)
        self.breakout_analyzer = BreakoutAnalyzer(self.config)

        logger.info(f"FoundationEngine initialized (database: {use_database})")

    async def analyze_symbol(
        self,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str = "H1",
        reference_time: datetime | None = None,
    ) -> list[DetectedZone]:
        """
        Analyze a symbol using foundation strategy.

        Args:
            symbol: Trading symbol
            data: OHLCV DataFrame
            timeframe: Timeframe for zones
            reference_time: Reference time for zone age calculation (for backtest)

        Returns:
            List of detected zones
        """
        logger.debug(f"Analyzing {symbol} with foundation strategy")
        return await self.strategy.analyze(symbol, data, timeframe, reference_time=reference_time)

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

        # Log analysis context
        if zones:
            nearest_zone = min(
                zones,
                key=lambda z: min(
                    abs(current_price - z.upper_bound), abs(current_price - z.lower_bound)
                ),
            )
            dist_to_nearest = min(
                abs(current_price - nearest_zone.upper_bound),
                abs(current_price - nearest_zone.lower_bound),
            )
            is_in_zone = nearest_zone.lower_bound <= current_price <= nearest_zone.upper_bound

            logger.info(
                f"{symbol}: Price {current_price:.5f} | Nearest Zone: {nearest_zone.zone_type.value} "
                f"({nearest_zone.lower_bound:.5f}-{nearest_zone.upper_bound:.5f}) | "
                f"Dist: {dist_to_nearest:.1f} | In Zone: {is_in_zone}"
            )

        # Generate signals from zones
        results = []
        for zone in zones:
            # Check if price is at/near zone
            if self._is_price_at_zone(current_price, zone):
                result = await self._create_signal_from_zone(
                    symbol, zone, current_price, timeframe, data
                )
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

    def _is_demand_zone(self, zone: DetectedZone, current_price: float) -> bool:
        """
        Determine if zone is a demand zone (support) or supply zone (resistance).

        Args:
            zone: Detected zone
            current_price: Current market price

        Returns:
            True if zone is a Demand zone (Buy side), False if Supply (Sell side)
        """
        midpoint = (zone.upper_bound + zone.lower_bound) / 2

        # If price is approaching from above, it's a DEMAND zone (Support)
        # If price is approaching from below, it's a SUPPLY zone (Resistance)
        return current_price > midpoint

    async def _create_signal_from_zone(
        self,
        symbol: str,
        zone: DetectedZone,
        current_price: float,
        timeframe: str,
        data: pd.DataFrame,
        h1_trend_bias: str = None,  # Added Phase 5.24: "BULLISH", "BEARISH", or None
    ) -> StrategyResult | None:
        """
        Create a trading signal from a zone with enhancement layers.

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
            # Determine if zone is demand or supply (Fixed Phase 5.6)
            is_demand = self._is_demand_zone(zone, current_price)
            zone_type_str = "DEMAND" if is_demand else "SUPPLY"

            # Get R:R ratio from config (default 2.0 for 1:2)
            rr_ratio = (
                self.config.get("signal_generation", {})
                .get("risk_reward", {})
                .get("default_take_profit_ratio", 2.0)
            )

            # Determine asset class for SL buffer adjustment
            from trading_bot.position.pip_calculator import PipCalculator

            pip_calc = PipCalculator()
            asset_class = pip_calc._determine_asset_class(symbol)
            pip_size = pip_calc.get_pip_size(symbol)

            min_sl_distance = 0.0

            zone_height = zone.upper_bound - zone.lower_bound
            zone_height_pips = zone_height / pip_size

            # ═══════════════════════════════════════════════════════
            # QUALITY FILTERS FOR COMMODITIES (Gold)
            # Skip low-quality setups to improve expectancy
            # ═══════════════════════════════════════════════════════
            if asset_class == "commodities":
                # Filter 1: Zone Width (Precision Filter)
                # RELAXED: Increased max zone width to 500 pips for XAUUSD backtest
                # Gold can have larger zones due to volatility, allow more flexibility
                max_acceptable_zone_width = 500.0  # pips (increased from 350.0)
                if zone_height_pips > max_acceptable_zone_width:
                    logger.warning(
                        f"{symbol}: REJECTED - Zone too wide ({zone_height_pips:.1f} pips > {max_acceptable_zone_width} pips). "
                        f"Wide zones lack precision and increase risk."
                    )
                    return None

                # Filter 2: Zone Strength (Quality Filter)
                # RELAXED: Lowered min strength to 0.4 to allow more setups
                # Only trade moderately strong zones. Min strength 0.4 (was 0.5)
                min_zone_strength = 0.4  # Reduced from 0.5
                if zone.strength < min_zone_strength:
                    logger.warning(
                        f"{symbol}: REJECTED - Zone strength too low ({zone.strength:.2f} < {min_zone_strength}). "
                        f"Only trade reasonably tested zones."
                    )
                    return None

            # Crypto needs much wider SL buffer due to high volatility
            # Initialize minimum SL distance pips (will be set per asset class below)
            min_sl_distance_pips = 0.0

            if asset_class == "crypto":
                # For crypto: Use 50% buffer (reduced from 150%) with cap
                # Cap max zone height to prevent excessive SL (e.g. 10000 points)
                max_zone_height_pips = 10000.0
                max_zone_height = max_zone_height_pips * pip_size

                if zone_height > max_zone_height:
                    logger.warning(
                        f"{symbol}: Zone height {zone_height_pips:.1f} pips exceeds maximum {max_zone_height_pips} pips. "
                        f"Capping zone height for SL calculation."
                    )
                    effective_zone_height = max_zone_height
                    sl_buffer = effective_zone_height * 0.5
                else:
                    sl_buffer = zone_height * 0.5

                # Ensure minimum buffer (1000 points)
                min_buffer_points = 1000.0
                sl_buffer = max(sl_buffer, min_buffer_points)

            elif asset_class == "forex_major":
                # For forex major: 50% of zone height, but with maximum limits
                # Maximum zone height: 30 pips (0.0030 for EURUSD) - more conservative
                # This prevents TP from being too far when zone is large
                max_zone_height_pips = 30.0
                max_zone_height = max_zone_height_pips * pip_size

                # If zone is too large, cap it and use smaller buffer
                if zone_height > max_zone_height:
                    logger.warning(
                        f"{symbol}: Zone height {zone_height_pips:.1f} pips exceeds maximum {max_zone_height_pips} pips. "
                        f"Capping zone height for SL calculation."
                    )
                    # Use capped zone height for buffer calculation
                    effective_zone_height = max_zone_height
                    sl_buffer = effective_zone_height * 0.5
                else:
                    # Normal zone, use 50% buffer
                    sl_buffer = zone_height * 0.5

                # Get minimum SL distance from config (default: 15 pips)
                min_sl_distance_pips = (
                    self.config.get("signal_generation", {})
                    .get("risk_reward", {})
                    .get("min_stop_loss_distance", {})
                    .get("forex_major", 15.0)
                )
                min_sl_distance = min_sl_distance_pips * pip_size

                # Ensure SL buffer is at least minimum distance
                if sl_buffer < min_sl_distance:
                    sl_buffer = min_sl_distance
                    logger.debug(
                        f"{symbol}: Using minimum SL buffer {min_sl_distance_pips} pips (150 points for 5-digit broker)"
                    )
            elif asset_class == "forex_jpy":
                # For JPY pairs: Similar to major but with JPY pip size
                # Maximum zone height: 30 pips (more conservative)
                max_zone_height_pips = 30.0
                max_zone_height = max_zone_height_pips * pip_size

                if zone_height > max_zone_height:
                    logger.warning(
                        f"{symbol}: Zone height {zone_height_pips:.1f} pips exceeds maximum {max_zone_height_pips} pips. "
                        f"Capping zone height for SL calculation."
                    )
                    effective_zone_height = max_zone_height
                    sl_buffer = effective_zone_height * 0.5
                else:
                    sl_buffer = zone_height * 0.5

                # Get minimum SL distance from config (default: 15 pips)
                min_sl_distance_pips = (
                    self.config.get("signal_generation", {})
                    .get("risk_reward", {})
                    .get("min_stop_loss_distance", {})
                    .get("forex_jpy", 15.0)
                )
                min_sl_distance = min_sl_distance_pips * pip_size
                if sl_buffer < min_sl_distance:
                    sl_buffer = min_sl_distance
                    logger.debug(
                        f"{symbol}: Using minimum SL buffer {min_sl_distance_pips} pips (150 points for 5-digit broker)"
                    )
            else:
                # For commodities: Cap logic added
                # FIX: Increased max zone height for SL calculation to handle larger zones
                # Gold can have large zones, but we still need reasonable SL
                max_zone_height_pips = 200.0  # Increased from 100.0 to 200.0 pips ($20.00)
                max_zone_height = max_zone_height_pips * pip_size

                # Boost RR for commodities to allow runners, but keep realistic for backtest
                rr_ratio = 2.0  # Restored to 2.0 (Intraday Phase 5.21)
                min_rr = 1.5  # Restored to 1.5

                if zone_height > max_zone_height:
                    logger.warning(
                        f"{symbol}: Zone height {zone_height_pips:.1f} pips exceeds maximum {max_zone_height_pips} pips. "
                        f"Capping zone height for SL calculation."
                    )
                    effective_zone_height = max_zone_height
                    sl_buffer = effective_zone_height * 0.5  # Restored to 0.5 (Intraday)
                else:
                    sl_buffer = zone_height * 0.5  # Restored to 0.5 (Intraday)

                # Get minimum SL distance from config (default: 50 pips for commodities)
                # RELAXED: Reduced to 40 pips to allow more setups
                min_sl_distance_pips = (
                    self.config.get("signal_generation", {})
                    .get("risk_reward", {})
                    .get("min_stop_loss_distance", {})
                    .get("commodities", 40.0)  # Reduced from 50.0 to 40.0 for more flexibility
                )
                min_sl_distance = min_sl_distance_pips * pip_size
                if sl_buffer < min_sl_distance:
                    sl_buffer = min_sl_distance
                    logger.debug(f"{symbol}: Using minimum SL buffer {min_sl_distance_pips} pips")

            # -------------------------------------------------------------------------
            # ENTRY & RISK CALCULATION FIX
            # -------------------------------------------------------------------------
            # OLD LOGIC (Flawed):
            # Used zone boundary (upper/lower) as entry_price for calculation,
            # but execution happened at current_price.
            # This caused TP/SL to be fixed relative to zone, ignoring actual entry deviation.
            #
            # NEW LOGIC:
            # 1. Use CURRENT PRICE as entry (since we execute at market)
            # 2. SL is fixed at zone boundary + buffer
            # 3. TP is calculated relative to ACTUAL entry to maintain constant RR
            # -------------------------------------------------------------------------

            if is_demand:
                direction = SignalDirection.BUY

                # === TREND FILTER (PHASE 5.5: Soft Gate - Handled by MA Layer) ===
                # We no longer block entries based on trend EMA here to allow reversals.
                # Trend alignment still contributes to 'MA' score (8 points).

                # === VOLUME BURST VALIDATION (Commodities) ===
                if asset_class == "commodities" and len(data) >= 20:
                    avg_volume = data["volume"].tail(20).mean()
                    current_volume = data["volume"].iloc[-1]

                    # Adaptive Volume (Phase 5.22): More lenient for trend-following
                    # FIX: Melonggarkan threshold untuk XAUUSD MTF backtest
                    # RELAXED: Further reduced volume threshold to allow more setups
                    vol_threshold = 0.6  # Default: 0.6x (reduced from 0.8x for backtest)
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        is_with_trend = (
                            direction == SignalDirection.BUY and current_price > ema_20
                        ) or (direction == SignalDirection.SELL and current_price < ema_20)
                        if is_with_trend:
                            vol_threshold = (
                                0.5  # Lebih longgar untuk trend-following (reduced from 0.6)
                            )

                    if current_volume < avg_volume * vol_threshold:
                        logger.debug(
                            f"{symbol}: REJECTED - No volume burst (Vol: {current_volume} < {avg_volume:.0f} * {vol_threshold})"
                        )
                        return None

                # === CANDLE SENTIMENT GATE (Commodities) ===
                if asset_class == "commodities" and len(data) >= 1:
                    last_open = data["open"].iloc[-1]
                    last_close = data["close"].iloc[-1]
                    last_high = data["high"].iloc[-1]
                    last_low = data["low"].iloc[-1]
                    last_range = last_high - last_low
                    last_body = abs(last_close - last_open)

                    # Prevent buying a "Falling Knife"
                    # RELAXED: Only reject if body is > 70% of range (was 60%)
                    if last_close < last_open and last_range > 0:
                        body_ratio = last_body / last_range
                        if body_ratio > 0.7:  # Relaxed from 0.6 to 0.7
                            logger.warning(
                                f"{symbol}: REJECTED - Falling knife detected (Bearish Body Ratio: {body_ratio:.2f})"
                            )
                            return None

                # === FLASH CRASH PROTECTION (Volatility Filter) ===
                if asset_class == "commodities" and len(data) >= 14:
                    # Calculate ATR(14) equivalent (moving range)
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # FIX: Melonggarkan volatility threshold (dari 2.0x menjadi 2.5x)
                    # If current candle is > 2.5x the average volatility, skip (Panic/News event)
                    volatility_multiplier = 2.5  # Lebih longgar dari 2.0
                    if current_range > avg_range * volatility_multiplier:
                        # NEW (Phase 5.22): Allow trend-following entries even in extreme volatility
                        # Only block if we are fighting the momentum (e.g. buying a massive drop)
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        is_with_trend = (
                            direction == SignalDirection.BUY and current_price > ema_20
                        ) or (direction == SignalDirection.SELL and current_price < ema_20)

                        if not is_with_trend:
                            logger.warning(
                                f"{symbol}: REJECTED - Extreme volatility ({current_range:.1f} > {avg_range*volatility_multiplier:.1f}) and counter-trend. Skipping panic move."
                            )
                            return None
                        else:
                            logger.info(
                                f"{symbol}: ALLOWED - Extreme volatility move is trend-aligned. Riding the momentum."
                            )

                # === REJECTION WICK CONFIRMATION (PHASE 5.11) ===
                if asset_class == "commodities" and last_range > 0:
                    lower_wick = min(last_open, last_close) - last_low
                    wick_ratio = lower_wick / last_range

                    # RELAXED: Lower wick threshold to allow more setups for XAUUSD backtest
                    wick_threshold = 0.15  # Default: 0.15 (reduced from 0.2)
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        is_with_trend = (
                            direction == SignalDirection.BUY and current_price > ema_20
                        ) or (direction == SignalDirection.SELL and current_price < ema_20)
                        if is_with_trend:
                            wick_threshold = (
                                0.08  # More lenient for trend-following (reduced from 0.1)
                            )

                    if wick_ratio < wick_threshold:
                        logger.warning(
                            f"{symbol}: REJECTED - No bounce confirmation (Lower Wick: {wick_ratio:.2f} < {wick_threshold})"
                        )
                        return None

                # === SIGNAL CANDLE COLOR MATCH (PHASE 5.12) ===
                # FIX: Melonggarkan untuk trend-following - allow doji dan small bearish jika trend kuat
                if asset_class == "commodities" and last_close <= last_open:
                    # Check if it's a small bearish candle (body < 30% of range) - bisa di-allow
                    if last_range > 0:
                        body_ratio = abs(last_close - last_open) / last_range
                        if body_ratio < 0.3:  # Small body = doji-like, bisa di-allow
                            logger.debug(
                                f"{symbol}: ALLOWED - Small bearish body ({body_ratio:.2f} < 0.30), treating as neutral"
                            )
                        else:
                            logger.warning(
                                f"{symbol}: REJECTED - No bullish confirmation (Candle is Bearish with body {body_ratio:.2f}). Waiting for green candle."
                            )
                            return None
                    else:
                        logger.warning(
                            f"{symbol}: REJECTED - No bullish confirmation (Candle is Bearish). Waiting for green candle."
                        )
                        return None

                # === VOLATILITY-DEPENDENT TREND GATE (PHASE 5.13) ===
                if asset_class == "commodities" and len(data) >= 100:
                    # Calculate volatility
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # FIX: Melonggarkan threshold (dari 1.5x menjadi 2.0x) dan hanya block jika sangat counter-trend
                    # If volatility is very high, trend alignment is MANDATORY
                    if current_range > avg_range * 2.0:  # Lebih longgar dari 1.5x
                        # Use Faster EMA (20) for reactive volatility gating
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        # Hanya block jika price jauh di bawah EMA (bukan hanya sedikit)
                        price_below_ema_pct = (ema_20 - current_price) / ema_20 * 100
                        if (
                            current_price < ema_20 and price_below_ema_pct > 0.3
                        ):  # Hanya block jika > 0.3% di bawah EMA
                            logger.warning(
                                f"{symbol}: REJECTED - Very high volatility ({current_range:.1f} > {avg_range*2.0:.1f}) and strong counter-trend (Price {price_below_ema_pct:.2f}% below EMA). NO counter-trend BUY allowed during crash."
                            )
                            return None

                # SL is always below the zone
                stop_loss = zone.lower_bound - sl_buffer

                # ENTRY is Market Price (current_price)
                entry_price = current_price

                # ═══════════════════════════════════════════════════════
                # ENTRY QUALITY VALIDATION (PHASE 5.1)
                # ═══════════════════════════════════════════════════════
                if asset_class == "commodities":
                    # 1. Anti-Chase: Entry must be near zone upper bound
                    # RELAXED: Increased max deviation to 25 pips for XAUUSD backtest
                    # Allow max 25 pips deviation from zone top (increased from 15.0)
                    max_entry_dev_pips = 25.0  # Increased from 15.0
                    max_entry_dev = max_entry_dev_pips * pip_size
                    entry_dist_from_zone = entry_price - zone.upper_bound

                    if entry_dist_from_zone > max_entry_dev:
                        logger.warning(
                            f"{symbol}: REJECTED - Chasing price too far from zone. "
                            f"Price {entry_price:.5f} is {entry_dist_from_zone/pip_size:.1f} pips "
                            f"above zone top {zone.upper_bound:.5f}. Max allowed: {max_entry_dev_pips}"
                        )
                        return None

                # ENFORCE MINIMUM SL DISTANCE (from config)
                # This ensures SL isn't too tight for the asset class
                if min_sl_distance > 0:
                    actual_sl_dist = entry_price - stop_loss
                    # min_sl_price_dist = min_sl_distance * pip_size  <-- Removed duplicate multiplication
                    if actual_sl_dist < min_sl_distance:  # Changed to use min_sl_distance directly
                        stop_loss = entry_price - min_sl_distance
                        logger.debug(
                            f"{symbol}: SL enforced to min distance {min_sl_distance/pip_size:.1f} pips"
                        )

                # CHASE PROTECTION / MAX STOP LOSS CHECK
                # If price is too high (chasing), risk will be too large
                max_risk_pips = (
                    self.config.get("signal_generation", {})
                    .get("risk_reward", {})
                    .get("max_stop_loss_pips", 100.0)
                )
                if asset_class == "commodities":
                    max_risk_pips = 250.0  # Increased from 200.0 to 250.0 for larger zones

                current_risk = entry_price - stop_loss
                if current_risk > max_risk_pips * pip_size:
                    logger.warning(
                        f"{symbol}: REJECTED - Net Risk too high. "
                        f"Risk: {current_risk/pip_size:.1f} pips > Max {max_risk_pips} pips."
                    )
                    return None

                # Recalculate TP based on ACTUAL entry and FIXED SL to maintain RR
                take_profit = entry_price + (entry_price - stop_loss) * rr_ratio

            else:  # Supply (SELL)
                direction = SignalDirection.SELL

                # === TREND FILTER (PHASE 5.5: Soft Gate) ===
                # We no longer block entries based on trend EMA here to allow reversals.

                # === VOLUME BURST VALIDATION (Commodities) ===
                if asset_class == "commodities" and len(data) >= 20:
                    avg_volume = data["volume"].tail(20).mean()
                    current_volume = data["volume"].iloc[-1]

                    # Adaptive Volume (Phase 5.22): More lenient for trend-following
                    # FIX: Melonggarkan threshold untuk XAUUSD MTF backtest
                    # RELAXED: Further reduced volume threshold to allow more setups
                    vol_threshold = 0.6  # Default: 0.6x (reduced from 0.8x for backtest)
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        is_with_trend = (
                            direction == SignalDirection.BUY and current_price > ema_20
                        ) or (direction == SignalDirection.SELL and current_price < ema_20)
                        if is_with_trend:
                            vol_threshold = (
                                0.5  # Lebih longgar untuk trend-following (reduced from 0.6)
                            )

                    if current_volume < avg_volume * vol_threshold:
                        logger.debug(
                            f"{symbol}: REJECTED - No volume burst (Vol: {current_volume} < {avg_volume:.0f} * {vol_threshold})"
                        )
                        return None

                # === CANDLE SENTIMENT GATE (Commodities) ===
                if asset_class == "commodities" and len(data) >= 1:
                    last_open = data["open"].iloc[-1]
                    last_close = data["close"].iloc[-1]
                    last_high = data["high"].iloc[-1]
                    last_low = data["low"].iloc[-1]
                    last_range = last_high - last_low
                    last_body = abs(last_close - last_open)

                    # Prevent selling into a massive bullish candle (Rocket)
                    # RELAXED: Only reject if body is > 70% of range (was 60%)
                    if last_close > last_open and last_range > 0:
                        body_ratio = last_body / last_range
                        if body_ratio > 0.7:  # Relaxed from 0.6 to 0.7
                            logger.warning(
                                f"{symbol}: REJECTED - Momentum spike detected (Bullish Body Ratio: {body_ratio:.2f})"
                            )
                            return None

                # === REJECTION WICK CONFIRMATION (PHASE 5.11) ===
                if asset_class == "commodities" and last_range > 0:
                    upper_wick = last_high - max(last_open, last_close)
                    wick_ratio = upper_wick / last_range

                    # Adaptive Wick (Phase 5.22): Relax for trend-following in high volatility
                    wick_threshold = 0.3  # Default
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        if current_price < ema_20:  # Trend is DOWN
                            wick_threshold = 0.15  # Easier entry for SELL in downtrend

                    if wick_ratio < wick_threshold:
                        logger.warning(
                            f"{symbol}: REJECTED - No bounce confirmation (Upper Wick: {wick_ratio:.2f} < {wick_threshold})"
                        )
                        return None

                # === SIGNAL CANDLE COLOR MATCH (PHASE 5.12) ===
                if asset_class == "commodities" and last_close >= last_open:
                    logger.warning(
                        f"{symbol}: REJECTED - No bearish confirmation (Candle is Bullish). Waiting for red candle."
                    )
                    return None

                # === VOLATILITY-DEPENDENT TREND GATE (PHASE 5.13) ===
                if asset_class == "commodities" and len(data) >= 100:
                    # Calculate volatility
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # If volatility is high, trend alignment is MANDATORY
                    if current_range > avg_range * 1.5:
                        # Use Faster EMA (20) for reactive volatility gating
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        if current_price > ema_20:
                            logger.warning(
                                f"{symbol}: REJECTED - High volatility trend mismatch. NO counter-trend SELL allowed during spike."
                            )
                            return None

                # SL is always above the zone
                stop_loss = zone.upper_bound + sl_buffer

                # ENTRY is Market Price
                entry_price = current_price

                # ═══════════════════════════════════════════════════════
                # ENTRY QUALITY VALIDATION (PHASE 5.1)
                # ═══════════════════════════════════════════════════════
                if asset_class == "commodities":
                    # 1. Anti-Chase: Entry must be near zone lower bound
                    # RELAXED: Increased max deviation to 25 pips for XAUUSD backtest
                    # Allow max 25 pips deviation from zone bottom (increased from 15.0)
                    max_entry_dev_pips = 25.0  # Increased from 15.0
                    max_entry_dev = max_entry_dev_pips * pip_size
                    entry_dist_from_zone = zone.lower_bound - entry_price

                    if entry_dist_from_zone > max_entry_dev:
                        logger.warning(
                            f"{symbol}: REJECTED - Chasing price too far from zone. "
                            f"Price {entry_price:.5f} is {entry_dist_from_zone/pip_size:.1f} pips "
                            f"below zone bottom {zone.lower_bound:.5f}. Max allowed: {max_entry_dev_pips}"
                        )
                        return None

                # ENFORCE MINIMUM SL DISTANCE (from config)
                if min_sl_distance > 0:
                    actual_sl_dist = stop_loss - entry_price
                    # min_sl_price_dist = min_sl_distance * pip_size  <-- Removed duplicate
                    if actual_sl_dist < min_sl_distance:
                        stop_loss = entry_price + min_sl_distance
                        logger.debug(
                            f"{symbol}: SL enforced to min distance {min_sl_distance/pip_size:.1f} pips"
                        )

                # CHASE PROTECTION
                max_risk_pips = (
                    self.config.get("signal_generation", {})
                    .get("risk_reward", {})
                    .get("max_stop_loss_pips", 100.0)
                )
                if asset_class == "commodities":
                    max_risk_pips = 250.0  # Increased from 200.0 to 250.0 for larger zones

                current_risk = stop_loss - entry_price
                if current_risk > max_risk_pips * pip_size:
                    logger.warning(
                        f"{symbol}: REJECTED - Net Risk too high. "
                        f"Risk: {current_risk/pip_size:.1f} pips > Max {max_risk_pips} pips."
                    )
                    return None

                # Recalculate TP based on ACTUAL entry and FIXED SL
                take_profit = entry_price - (stop_loss - entry_price) * rr_ratio

            # Verify R:R calculation
            if direction == SignalDirection.BUY:
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SELL
                risk = stop_loss - entry_price
                reward = entry_price - take_profit

            calculated_rr = reward / risk if risk > 0 else 0.0

            # Calculate in pips for better understanding
            pip_size = pip_calc.get_pip_size(symbol)
            risk_pips = risk / pip_size
            reward_pips = reward / pip_size

            # TP Calculation Logic:
            # - For BUY: TP = entry_price + (entry_price - stop_loss) * rr_ratio
            #   This means: TP = entry + risk * rr_ratio
            #   Example: Entry=1.1000, SL=1.0985 (15 pips risk), RR=2.0
            #            TP = 1.1000 + (1.1000 - 1.0985) * 2.0 = 1.1000 + 0.0030 = 1.1030 (30 pips reward)
            #
            # - For SELL: TP = entry_price - (stop_loss - entry_price) * rr_ratio
            #   This means: TP = entry - risk * rr_ratio
            #   Example: Entry=1.1000, SL=1.1015 (15 pips risk), RR=2.0
            #            TP = 1.1000 - (1.1015 - 1.1000) * 2.0 = 1.1000 - 0.0030 = 1.0970 (30 pips reward)
            #
            # TP distance is determined by:
            # 1. Risk distance (entry to SL) - controlled by zone height and min SL distance
            # 2. Risk-Reward ratio (default 2.0 = 1:2)
            # 3. No maximum limit - TP follows the RR ratio naturally

            # Validate R:R ratio is close to target (allow 20% tolerance for flexibility)
            rr_tolerance = 0.2  # 20% tolerance (more flexible)
            min_rr = rr_ratio * (1 - rr_tolerance)
            max_rr = rr_ratio * (1 + rr_tolerance)

            logger.info(
                f"{symbol} {direction.value}: Entry={entry_price:.5f}, SL={stop_loss:.5f}, TP={take_profit:.5f} | "
                f"Risk={risk:.5f} ({risk_pips:.1f} pips), Reward={reward:.5f} ({reward_pips:.1f} pips), "
                f"R:R={calculated_rr:.2f} (Target: {rr_ratio:.2f}, Acceptable: {min_rr:.2f}-{max_rr:.2f})"
            )

            # Only reject if R:R is extremely outside acceptable range
            # Allow wider range to account for zone variations
            if calculated_rr < min_rr * 0.7:  # More than 30% below minimum = reject
                logger.warning(
                    f"{symbol}: R:R {calculated_rr:.2f} is too low (min acceptable: {min_rr * 0.7:.2f}). "
                    f"This may indicate zone is too large or SL buffer too wide. Rejecting signal."
                )
                return None
            elif calculated_rr > max_rr * 3.0:  # More than 3x maximum = reject (extreme case)
                logger.warning(
                    f"{symbol}: R:R {calculated_rr:.2f} is extremely high (max acceptable: {max_rr * 3.0:.2f}). "
                    f"Zone may be too large ({zone_height_pips:.1f} pips). Rejecting signal."
                )
                return None
            elif calculated_rr < min_rr:
                # Below target but still acceptable - just warn
                logger.warning(
                    f"{symbol}: R:R {calculated_rr:.2f} is below target {rr_ratio:.2f} "
                    f"(min: {min_rr:.2f}). Accepting signal but zone quality may be suboptimal."
                )
            elif (
                calculated_rr > max_rr * 2.0
            ):  # More than 2x target but less than 3x - warn strongly
                logger.warning(
                    f"{symbol}: R:R {calculated_rr:.2f} is significantly above target {rr_ratio:.2f} "
                    f"(max: {max_rr:.2f}). TP may be far from entry. Zone height: {zone_height_pips:.1f} pips. "
                    f"Accepting signal but consider reviewing zone detection."
                )
            elif calculated_rr > max_rr:
                # Slightly above target - just info
                logger.info(
                    f"{symbol}: R:R {calculated_rr:.2f} is slightly above target {rr_ratio:.2f} "
                    f"(max: {max_rr:.2f}). Acceptable."
                )

            # Validate prices
            if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
                logger.warning(
                    f"{symbol}: Invalid prices for zone signal (Entry: {entry_price}, SL: {stop_loss}, TP: {take_profit})"
                )
                return None

            # Double check SL direction
            if direction == SignalDirection.BUY and stop_loss >= entry_price:
                logger.warning(f"{symbol}: Invalid BUY SL (SL {stop_loss} >= Entry {entry_price})")
                return None
            if direction == SignalDirection.SELL and stop_loss <= entry_price:
                logger.warning(f"{symbol}: Invalid SELL SL (SL {stop_loss} <= Entry {entry_price})")
                return None

            # Prepare data for analyzers
            closes = data["close"].tolist()
            opens = data["open"].tolist()
            highs = data["high"].tolist()
            lows = data["low"].tolist()

            # Calculate Enhancement Scores
            enhancement_score = 0.0
            layer_scores = {}
            layer_details = {}

            # 1. RSI Analysis (Weight: 0.10)
            rsi_res = await self.rsi_analyzer.analyze_rsi_signal(
                symbol, closes, timeframe, zone_type_str
            )
            if rsi_res.signal_type == direction.name:  # Only add if aligns
                score = rsi_res.confidence * 0.10
                enhancement_score += score
                layer_scores["rsi"] = score
                layer_details["rsi"] = rsi_res.details

            # 2. Moving Average (Weight: 0.08)
            ma_res = await self.ma_analyzer.analyze_ma_signal(
                symbol, closes, timeframe, zone_type_str
            )
            if ma_res.signal_type == direction.name:
                score = ma_res.confidence * 0.08
                enhancement_score += score
                layer_scores["ma"] = score
                layer_details["ma"] = ma_res.details

            # 3. Trendline (Weight: 0.20)
            tl_res = await self.trendline_analyzer.analyze_trendline_signal(
                symbol, closes, timeframe
            )
            if (is_demand and "SUPPORT" in tl_res.signal_type) or (
                not is_demand and "RESISTANCE" in tl_res.signal_type
            ):
                score = tl_res.confidence * 0.20
                enhancement_score += score
                layer_scores["trendline"] = score
                layer_details["trendline"] = tl_res.details

            # 4. Price Action (Weight: 0.15)
            pa_res = await self.price_action_analyzer.analyze_pattern(
                symbol, opens, highs, lows, closes, zone_type_str
            )
            if pa_res and pa_res.direction == direction.name:
                score = pa_res.confidence * 0.15
                enhancement_score += score
                layer_scores["price_action"] = score
                layer_details["price_action"] = pa_res.details

            # 5. Fibonacci (Weight: 0.12)
            fib_res = await self.fibonacci_analyzer.analyze_fibonacci(
                symbol, highs, lows, current_price, zone_type_str
            )
            if fib_res:
                score = (
                    fib_res.score * 0.12
                )  # Base score (10-20) * weight? No, fib_res.score is small (10-20).
                # Need to normalize. Fib score 20 is max. 20/20 * 100 * 0.12 = 12 points.
                # fib_res.score is raw points (10, 15, 20).
                # Let's say max raw score is 20. Confidence = (score/20)*100.
                norm_conf = (fib_res.score / 20.0) * 100.0
                score = norm_conf * 0.12
                enhancement_score += score
                layer_scores["fibonacci"] = score
                layer_details["fibonacci"] = fib_res.details

            # 6. Structure (Weight: 0.08)
            struct_res = await self.structure_analyzer.analyze_structure(
                symbol, highs, lows, closes
            )
            # PHASE 5.22 Mastery: Adjusted alignment for Commodities
            if asset_class == "commodities" and struct_res:
                # Only reject if structure is OVERWHELMINGLY opposite (confidence > 90%)
                if struct_res.direction != direction.name and struct_res.confidence > 90.0:
                    logger.warning(
                        f"{symbol}: REJECTED - Extremely strong market structure misalignment ({struct_res.direction} {struct_res.confidence:.1f}% vs {direction.name})"
                    )
                    return None
                elif struct_res.direction != direction.name:
                    logger.debug(
                        f"{symbol}: Weak/Moderate market structure misalignment ({struct_res.direction} {struct_res.confidence:.1f}%). Proceeding due to High-Vol Trend alignment."
                    )

            if struct_res and struct_res.direction == direction.name:
                score = struct_res.confidence * 0.08
                enhancement_score += score
                layer_scores["structure"] = score
                layer_scores["structure_type"] = struct_res.structure_type
                layer_details["structure"] = struct_res.details

            # 7. Breakout (Weight: 0.12) - Only relevant if price is breaking OUT of zone?
            # Actually BreakoutRetest is for re-entry. Here we are AT zone.
            # Maybe check if we are bouncing (Price Action) or breaking through (Invalidation).
            # Breakout Analyzer logic checks if price breaks a level.
            # If Demand Zone, we want price to bounce UP (not break down).
            # So we check if price breaks ABOVE the zone's upper bound? (Confirmation)
            # Let's skip Breakout for initial Zone Entry signal, it's more for confirmation later.
            # Or use it to confirm the bounce started?

            # -------------------------------------------------------------------------
            # SCORE CALCULATION (Weighted Sum based on YAML Config)
            # -------------------------------------------------------------------------
            # We use the weights defined in config/strategy_parameters.yaml

            # Get weights from config (defaulting to the values seen in yaml if missing)
            weights = self.config.get("confluence_weights", {})

            # Base Zone Score (Weight: foundation - typically 0.30)
            foundation_weight = weights.get("foundation", 0.30)
            weighted_foundation_score = zone.strength * foundation_weight

            # Enhancement Scores
            # We calculate the weighted contribution of each active layer
            weighted_enhancement_score = 0.0

            # Helper to add weighted score
            def add_weighted_layer(name, raw_confidence):
                nonlocal weighted_enhancement_score
                w = weights.get(name, 0.0)  # Get weight from config
                # raw_confidence is 0-100 (or close to it)
                # Contribution = raw_confidence * weight
                contribution = raw_confidence * w
                weighted_enhancement_score += contribution
                return contribution

            # Reset layer scores for metadata to show weighted contribution or raw?
            # Let's keep layer_scores as raw confidence in metadata for debugging,
            # but calculation uses weights.

            if "rsi" in layer_scores:
                # layer_scores['rsi'] was stored as weighted in previous steps?
                # Wait, in the code above we calculated: score = rsi_res.confidence * 0.10
                # We need to use the RAW confidence from the analyzer result, NOT the pre-weighted one.
                # rsi_res.confidence is the raw value (0-100).
                add_weighted_layer("rsi", rsi_res.confidence)

            if "ma" in layer_scores:
                add_weighted_layer("ma", ma_res.confidence)
            if "trendline" in layer_scores:
                add_weighted_layer("trendline", tl_res.confidence)
            if "price_action" in layer_scores:
                add_weighted_layer("price_action", pa_res.confidence)

            # Fibonacci score was normalized to 0-100 in previous step
            if "fibonacci" in layer_scores:
                # recalculate raw confidence from the normalized calc we did
                raw_fib = (fib_res.score / 20.0) * 100.0
                add_weighted_layer("fibonacci", raw_fib)

            if "structure" in layer_scores:
                add_weighted_layer("structure", struct_res.confidence)

            # Final Score Calculation
            # Sum of (Score * Weight). Max possible score is 100 if all weights sum to 1.0
            # and all components have 100 confidence.
            final_score = weighted_foundation_score + weighted_enhancement_score

            # Ensure we don't exceed 100
            final_score = min(final_score, 100.0)

            # ═══════════════════════════════════════════════════════
            # QUALITY FILTER: Minimum Score (Confluence Filter)
            # Require multiple confirmation layers for commodities
            # ═══════════════════════════════════════════════════════
            if asset_class == "commodities":
                # === DYNAMIC SCORE THRESHOLD (PHASE 5.8) ===
                # Require higher confluence for counter-trend reversals
                is_counter_trend = False
                if len(data) >= 100:
                    # Reactive Threshold (Phase 5.23): Use faster EMA during volatility
                    ema_ref = data["close"].ewm(span=100, adjust=False).mean().iloc[-1]
                    if current_range > avg_range * 1.5:
                        ema_ref = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]

                    if direction == SignalDirection.BUY and current_price < ema_ref:
                        is_counter_trend = True
                    elif direction == SignalDirection.SELL and current_price > ema_ref:
                        is_counter_trend = True

                # RELAXED: Lower thresholds to allow more setups for XAUUSD backtest
                # Dynamic Threshold: 20.0 for counter-trend, 15.0 for trend-following (further reduced)
                min_score_threshold = 15.0  # Reduced from 18.0 to allow more trades
                if is_counter_trend:
                    min_score_threshold = (
                        18.0 if current_range > avg_range * 1.5 else 20.0
                    )  # Reduced from 22.0/25.0

                if final_score < min_score_threshold:
                    logger.warning(
                        f"{symbol}: REJECTED - {'Counter-trend ' if is_counter_trend else ''}Score too low ({final_score:.1f} < {min_score_threshold}). "
                        f"Need more confluence for {'reversals' if is_counter_trend else 'trend-following'}. "
                        f"Active layers: {list(layer_scores.keys())}"
                    )
                    return None

                # === DIRECTIONAL BIAS FILTER (RELAXED) ===
                # RELAXED: Further relaxed for XAUUSD backtest
                # Only block if trend is VERY strong AND we have very low confluence
                # Allow counter-trend if we have moderate confluence (score > 18)
                if h1_trend_bias == "BEARISH" and direction == SignalDirection.BUY:
                    # Only block if score is very low (weak confluence)
                    if final_score < 18.0:  # Reduced from 25.0
                        logger.warning(
                            f"{symbol}: REJECTED - H1 Trend is BEARISH and confluence too low ({final_score:.1f} < 18.0)."
                        )
                        return None
                    else:
                        logger.debug(
                            f"{symbol}: ALLOWED - Counter-trend BUY with strong confluence ({final_score:.1f})"
                        )
                if h1_trend_bias == "BULLISH" and direction == SignalDirection.SELL:
                    # Only block if score is very low (weak confluence)
                    if final_score < 18.0:  # Reduced from 25.0
                        logger.warning(
                            f"{symbol}: REJECTED - H1 Trend is BULLISH and confluence too low ({final_score:.1f} < 18.0)."
                        )
                        return None
                    else:
                        logger.debug(
                            f"{symbol}: ALLOWED - Counter-trend SELL with strong confluence ({final_score:.1f})"
                        )

                # Technical Confirmation Gate (Phase 5.1)
                # Require at least ONE technical indicator confirmation
                if not layer_scores:
                    logger.warning(
                        f"{symbol}: REJECTED - No technical confirmation. "
                        f"Gold trades require at least one enhancement layer (MA, PA, RSI, Fibo, etc.)."
                    )
                    return None

            # Generate zone_id
            zone_id = (
                f"{symbol}_{zone.zone_type.value}_{zone.lower_bound:.5f}_{zone.upper_bound:.5f}"
            )

            # Create result
            result = StrategyResult(
                strategy_name="foundation",
                symbol=symbol,
                score=final_score,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=timeframe,
                metadata={
                    "zone_id": zone_id,
                    "zone_type": zone.zone_type.value,
                    "foundation_score": weighted_foundation_score,
                    "enhancement_score": weighted_enhancement_score,
                    "layer_scores": layer_scores,
                    "layer_details": layer_details,
                },
            )

            logger.debug(
                f"Created signal: {direction.value} {symbol} "
                f"(Total Score: {final_score:.1f}, Layers: {list(layer_scores.keys())})"
            )

            return result

        except Exception as e:
            logger.error(f"Error creating signal from zone: {e}")
            return None
