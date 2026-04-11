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

    def __init__(
        self, config: dict[str, Any] = None, use_database: bool = True, symbol_mapper=None
    ):
        """
        Initialize foundation engine.

        Args:
            config: Engine configuration
            use_database: Whether to persist zones to database
            symbol_mapper: Optional SymbolMapper for symbol normalization (EURUSDc -> EURUSD)
        """
        self.config = config or {}
        self.symbol_mapper = symbol_mapper  # Store for symbol normalization

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
        self,
        symbol: str,
        data: pd.DataFrame,
        timeframe: str = "H1",
        h1_trend_bias: str = None,
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
                    symbol, zone, current_price, timeframe, data, h1_trend_bias
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
        # or within 10% of the zone size above/below the zone (tightened from 20% for better precision)
        zone_size = zone.upper_bound - zone.lower_bound
        tolerance = (
            zone_size * 0.1
        )  # Reduced from 0.2 (20%) to 0.1 (10%) for tighter entry validation

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

        # IMPROVED LOGIC: Consider zone type and price position
        # For REJECTION zones: Zone type indicates rejection direction
        # - Lower wick rejection = DEMAND (support)
        # - Upper wick rejection = SUPPLY (resistance)
        # For other zone types: Use price position relative to midpoint

        if zone.zone_type.value == "rejection":
            # For rejection zones, check if price is near lower bound (demand) or upper bound (supply)
            zone_size = zone.upper_bound - zone.lower_bound
            lower_third = zone.lower_bound + (zone_size * 0.33)
            upper_third = zone.upper_bound - (zone_size * 0.33)

            # If price is in lower third, it's likely a DEMAND zone (support)
            # If price is in upper third, it's likely a SUPPLY zone (resistance)
            if current_price <= lower_third:
                return True  # DEMAND (support)
            elif current_price >= upper_third:
                return False  # SUPPLY (resistance)
            # If in middle third, use midpoint logic as fallback
            return current_price > midpoint
        else:
            # For consolidation/breakout_origin zones, use midpoint logic
            # If price is approaching from above, it's a DEMAND zone (Support)
            # If price is approaching from below, it's a SUPPLY zone (Resistance)
            return current_price > midpoint

    def _get_sl_config(self, symbol: str) -> dict:
        """
        Get SL configuration with fallback hierarchy.

        Priority:
        1. Symbol-specific config (active_symbols.yaml)
        2. Asset class config (strategy_parameters.yaml)
        3. Hardcoded defaults

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with SL configuration
        """
        # Try symbol-specific config first (active_symbols.yaml)
        # CRITICAL: Convert broker symbol to universal format using broker mappings (EURUSDc -> EURUSD)
        # This ensures we use the proper broker mapping from symbol_mapping.yaml (e.g., exness_cent)
        symbol_for_config = symbol
        if self.symbol_mapper:
            try:
                # Use convert_to_universal_symbol() to properly map broker symbols to universal format
                # EURUSDc (exness_cent) -> EURUSD (universal) using the broker's reverse mapping
                symbol_for_config = self.symbol_mapper.convert_to_universal_symbol(symbol)
            except Exception:
                # Fallback to basic normalization if conversion fails
                symbol_for_config = symbol.upper().strip()

        # 1. First, check if symbol has specific SL configuration
        symbols_cfg = self.config.get("symbols", {})
        symbol_cfg = symbols_cfg.get(symbol_for_config, {}) if isinstance(symbols_cfg, dict) else {}
        
        # Priority 1: Symbol-specific config
        if symbol_cfg:
            config = {
                "use_zone_based": symbol_cfg.get("use_zone_based_sl", False),
                "zone_buffer": symbol_cfg.get("zone_sl_buffer_multiplier", 1.2),
                "min_sl": symbol_cfg.get("min_stop_loss_pips", 80),
                "max_sl": symbol_cfg.get("max_stop_loss_pips", 300),
                "default_sl": symbol_cfg.get("default_stop_loss_pips", 150),
                "source": "symbol_config",
            }
            logger.debug(
                f"{symbol}: Using symbol-specific SL config (min={config['min_sl']}p, max={config['max_sl']}p)"
            )
            return config

        # Fallback to asset class config (strategy_parameters.yaml)
        from trading_bot.position.pip_calculator import PipCalculator

        pip_calc = PipCalculator()
        asset_class = pip_calc._determine_asset_class(symbol)

        strategy_cfg = self.config.get("signal_generation", {}).get("risk_reward", {})

        min_sl_config = strategy_cfg.get("min_stop_loss_distance", {})
        max_sl_config = strategy_cfg.get("max_stop_loss_distance", {})

        config = {
            "use_zone_based": strategy_cfg.get("use_zone_based_sl", False),
            "zone_buffer": strategy_cfg.get("zone_sl_buffer_multiplier", 1.2),
            "min_sl": min_sl_config.get(asset_class, 80.0),
            "max_sl": max_sl_config.get(asset_class, 300.0),
            "default_sl": min_sl_config.get(asset_class, 150.0),
            "source": "asset_class_config",
        }
        logger.debug(
            f"{symbol}: Using asset class ({asset_class}) SL config "
            f"(min={config['min_sl']}p, max={config['max_sl']}p)"
        )
        return config

    def _calculate_zone_based_sl(
        self, zone: DetectedZone, entry_price: float, direction: str, symbol: str
    ) -> tuple[float, float]:
        """
        Calculate SL based on zone size with min/max limits.

        This implements zone-based SL that adapts to market structure:
        - Small zones: Use minimum SL (prevents too tight)
        - Medium zones: Use zone size × buffer (adaptive)
        - Large zones: Use maximum SL (prevents too wide)

        Args:
            zone: Detected zone
            entry_price: Entry price
            direction: "BUY" or "SELL"
            symbol: Trading symbol

        Returns:
            Tuple of (sl_price, sl_distance_pips)
        """
        from trading_bot.position.pip_calculator import PipCalculator

        pip_calc = PipCalculator()
        pip_size = pip_calc.get_pip_size(symbol)

        # Get config (with fallback hierarchy)
        config = self._get_sl_config(symbol)

        if config["use_zone_based"]:
            # Calculate zone size in pips
            zone_size_price = zone.upper_bound - zone.lower_bound
            zone_size_pips = zone_size_price / pip_size

            # Add buffer (SL beyond zone boundary, not inside)
            sl_distance_pips = zone_size_pips * config["zone_buffer"]

            # Apply min/max limits
            sl_distance_pips = max(config["min_sl"], min(sl_distance_pips, config["max_sl"]))

            logger.debug(
                f"{symbol}: Zone-based SL | "
                f"Zone={zone_size_pips:.1f}p, "
                f"Buffered={zone_size_pips * config['zone_buffer']:.1f}p, "
                f"Final={sl_distance_pips:.1f}p (${sl_distance_pips/10:.1f})"
            )
        else:
            # Use default fixed SL
            sl_distance_pips = config["default_sl"]
            logger.debug(
                f"{symbol}: Fixed SL | " f"{sl_distance_pips:.1f}p (${sl_distance_pips/10:.1f})"
            )

        # Calculate SL price
        sl_distance_price = sl_distance_pips * pip_size

        if direction == "BUY":
            # SL below entry for BUY
            sl_price = entry_price - sl_distance_price
        else:  # SELL
            # SL above entry for SELL
            sl_price = entry_price + sl_distance_price

        return sl_price, sl_distance_pips

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

            # Convert symbol to universal format for config lookup (e.g., EURUSDc -> EURUSD)
            symbol_for_config = symbol
            if self.symbol_mapper:
                try:
                    symbol_for_config = self.symbol_mapper.convert_to_universal_symbol(symbol)
                except Exception:
                    symbol_for_config = symbol.upper().strip()

            zone_height = zone.upper_bound - zone.lower_bound
            zone_height_pips = zone_height / pip_size

            # ═══════════════════════════════════════════════════════
            # QUALITY FILTERS: Asset-specific zone validation
            # ═══════════════════════════════════════════════════════
            if asset_class == "commodities":
                # Filter 1: Zone Width (Precision Filter)
                # RELAXED: Increased max zone width to 1000 pips for XAUUSD
                # Gold can have larger zones due to volatility, allow more flexibility
                max_acceptable_zone_width = 1000.0  # pips (increased from 500.0)
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

            elif asset_class == "crypto":
                # Filter 1: Zone Width (Precision Filter)
                # Crypto has extreme volatility, but we still need reasonable zones
                # Max 600 pips for BTCUSD to prevent huge risk
                max_acceptable_zone_width = 600.0  # pips
                if zone_height_pips > max_acceptable_zone_width:
                    logger.warning(
                        f"{symbol}: REJECTED - Zone too wide ({zone_height_pips:.1f} pips > {max_acceptable_zone_width} pips). "
                        f"Wide zones increase risk beyond acceptable limits for crypto."
                    )
                    return None

                # Filter 2: Zone Strength (Quality Filter)
                # Require strong zones for crypto due to high volatility
                min_zone_strength = 0.5  # Higher threshold for crypto
                if zone.strength < min_zone_strength:
                    logger.warning(
                        f"{symbol}: REJECTED - Zone strength too low ({zone.strength:.2f} < {min_zone_strength}). "
                        f"Crypto requires strong zones due to high volatility."
                    )
                    return None

            # -------------------------------------------------------------------------
            # SL & DISTANCE CALCULATION (Refactored 2026-01-22)
            # Replaces old 'sl_buffer' logic with unified zone-based calculation
            # -------------------------------------------------------------------------
            direction_str = "BUY" if is_demand else "SELL"
            stop_loss, sl_distance_pips = self._calculate_zone_based_sl(
                zone, current_price, direction_str, symbol
            )

            # Entry is always current market price
            entry_price = current_price

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

                # === FLASH CRASH / CLIMAX PROTECTION (Volatility Filter) ===
                # APPLIES TO ALL ASSET CLASSES (Fixed 2026-02-11)
                # Prevent entry on extreme exhaustion candles (chasing tops/bottoms)
                if len(data) >= 14:
                    # Calculate ATR(14) equivalent (moving range)
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # Thresholds by asset class
                    vol_multiplier = 3.0  # Default (loose)
                    if asset_class == "commodities":
                        vol_multiplier = 2.0  # Strict for Gold/Silver (was 2.5 loose)
                    elif asset_class == "crypto":
                        vol_multiplier = 2.5
                    elif asset_class == "forex_majors":
                        vol_multiplier = 2.5

                    # If current candle is > multiplier * avg range, it's likely exhaustion
                    if current_range > avg_range * vol_multiplier:
                        logger.warning(
                            f"{symbol}: REJECTED - Climax Candle / Extreme Volatility "
                            f"({current_range:.1f} > {avg_range*vol_multiplier:.1f}). "
                            "Risk of reversal is high. Waiting for consolidation."
                        )
                        return None

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

                # ═══════════════════════════════════════════════════════
                # ENTRY QUALITY VALIDATION (PHASE 5.1)
                # ═══════════════════════════════════════════════════════
                # Anti-Chase Validation: For BUY at DEMAND zone, entry should be near zone LOWER bound (support)
                # NOT near upper bound (that would be chasing price above the zone)
                if asset_class == "commodities":
                    # 1. Anti-Chase: Entry must be near zone LOWER bound (support level)
                    # RELAXED: Increased max deviation to 25 pips for XAUUSD backtest
                    # Allow max 25 pips deviation from zone BOTTOM (support level)
                    max_entry_dev_pips = 25.0  # Increased from 15.0
                    max_entry_dev = max_entry_dev_pips * pip_size
                    # Entry distance from zone LOWER bound (support level)
                    entry_dist_from_zone_bottom = entry_price - zone.lower_bound

                    # Check if entry is too far above zone bottom (chasing price)
                    if entry_dist_from_zone_bottom > max_entry_dev:
                        logger.warning(
                            f"{symbol}: REJECTED - Chasing price too far from zone BOTTOM (support). "
                            f"Price {entry_price:.5f} is {entry_dist_from_zone_bottom/pip_size:.1f} pips "
                            f"above zone BOTTOM {zone.lower_bound:.5f}. Max allowed: {max_entry_dev_pips}. "
                            f"Zone range: {zone.lower_bound:.5f} - {zone.upper_bound:.5f}"
                        )
                        return None

                    # Additional validation: Entry should not be above zone upper bound
                    # If entry is above zone upper bound, it means we're chasing price (not at support)
                    entry_dist_from_zone_top = entry_price - zone.upper_bound
                    if entry_dist_from_zone_top > max_entry_dev:
                        logger.warning(
                            f"{symbol}: REJECTED - Entry {entry_price:.5f} is ABOVE zone upper bound "
                            f"{zone.upper_bound:.5f} by {entry_dist_from_zone_top/pip_size:.1f} pips. "
                            f"This is chasing price, not trading at support. "
                            f"Zone range: {zone.lower_bound:.5f} - {zone.upper_bound:.5f}"
                        )
                        return None

                    # Ideal entry: Should be within zone boundaries or slightly above lower bound
                    if entry_price < zone.lower_bound:
                        logger.debug(
                            f"{symbol}: Entry {entry_price:.5f} is below zone lower bound "
                            f"{zone.lower_bound:.5f}. This is acceptable (price at support)."
                        )

                # CHASE PROTECTION / MAX STOP LOSS CHECK
                # If price is too high (chasing), risk will be too large
                # Priority: Symbol-specific > Asset-class > Global default
                symbols_cfg = self.config.get("symbols", {})
                symbol_cfg = symbols_cfg.get(symbol_for_config, {}) if isinstance(symbols_cfg, dict) else {}
                max_risk_pips = symbol_cfg.get("max_stop_loss_pips")

                if max_risk_pips is None:
                    # No symbol-specific config, check asset-class
                    max_risk_pips = (
                        self.config.get("signal_generation", {})
                        .get("risk_reward", {})
                        .get("max_stop_loss_distance", {})
                        .get(asset_class, 100.0)
                    )
                    # Special case: commodities use a higher limit
                    if asset_class == "commodities":
                        max_risk_pips = max(max_risk_pips, 250.0)

                current_risk = entry_price - stop_loss
                if current_risk > max_risk_pips * pip_size:
                    logger.debug(
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

                # === FLASH CRASH / CLIMAX PROTECTION (Volatility Filter) ===
                # APPLIES TO ALL ASSET CLASSES (Fixed 2026-02-11)
                # Prevent entry on extreme exhaustion candles (chasing tops/bottoms)
                if len(data) >= 14:
                    # Calculate ATR(14) equivalent (moving range)
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # Thresholds by asset class
                    vol_multiplier = 3.0  # Default (loose)
                    if asset_class == "commodities":
                        vol_multiplier = 2.0  # Strict for Gold/Silver (was 2.5 loose)
                    elif asset_class == "crypto":
                        vol_multiplier = 2.5
                    elif asset_class == "forex_majors":
                        vol_multiplier = 2.5

                    # If current candle is > multiplier * avg range, it's likely exhaustion
                    if current_range > avg_range * vol_multiplier:
                        logger.warning(
                            f"{symbol}: REJECTED - Climax Candle / Extreme Volatility "
                            f"({current_range:.1f} > {avg_range*vol_multiplier:.1f}). "
                            "Risk of reversal is high. Waiting for consolidation."
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

                # CHASE PROTECTION / MAX STOP LOSS CHECK
                # Priority: Symbol-specific > Asset-class > Global default
                symbols_cfg = self.config.get("symbols", {})
                symbol_cfg = symbols_cfg.get(symbol_for_config, {}) if isinstance(symbols_cfg, dict) else {}
                max_risk_pips = symbol_cfg.get("max_stop_loss_pips")

                if max_risk_pips is None:
                    # No symbol-specific config, check asset-class
                    max_risk_pips = (
                        self.config.get("signal_generation", {})
                        .get("risk_reward", {})
                        .get("max_stop_loss_distance", {})
                        .get(asset_class, 100.0)
                    )
                    # Special case: commodities use a higher limit
                    if asset_class == "commodities":
                        max_risk_pips = max(max_risk_pips, 250.0)

                current_risk = stop_loss - entry_price
                if current_risk > max_risk_pips * pip_size:
                    logger.debug(
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

            # ═══════════════════════════════════════════════════════
            # SAVE ORIGINAL RR (for validation)
            # ═══════════════════════════════════════════════════════
            # Save original RR before any modifications
            # With TP cap removed, this is just for clarity/validation
            original_rr = calculated_rr

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
            # 3. NO TP CAP - Partial close needs original TP distance for proper levels

            # ═══════════════════════════════════════════════════════
            # TP CAPPING DISABLED - To allow partial close at proper levels
            # ═══════════════════════════════════════════════════════
            # TP capping has been removed because:
            # 1. Partial close levels are calculated as proportion of TP distance
            # 2. Capping TP reduces partial close levels, losing profit potential
            # 3. With zone-based SL + RR ratio, TP is already naturally constrained
            # 4. Better to have realistic TP with partial close than capped TP with reduced levels
            #
            # Original capping logic (lines 861-918) has been commented out
            # and can be restored if needed for specific use cases.
            # ═══════════════════════════════════════════════════════

            # ═══════════════════════════════════════════════════════
            # R:R VALIDATION (Check ORIGINAL R:R)
            # ═══════════════════════════════════════════════════════
            # original_rr was saved at line 851
            # No TP cap means calculated_rr = original_rr

            # More lenient for crypto due to high volatility
            rr_tolerance = 0.3 if asset_class == "crypto" else 0.2  # 30% for crypto, 20% for others
            min_rr = rr_ratio * (1 - rr_tolerance)

            logger.info(
                f"{symbol} {direction.value}: Entry={entry_price:.5f}, SL={stop_loss:.5f}, TP={take_profit:.5f} | "
                f"Risk={risk:.5f} ({risk_pips:.1f} pips), Reward={reward:.5f} ({reward_pips:.1f} pips), "
                f"R:R={calculated_rr:.2f} (Original: {original_rr:.2f}, Target: {rr_ratio:.2f}, Min: {min_rr:.2f})"
            )

            # ONLY reject if ORIGINAL R:R is below minimum acceptable
            # Accept any R:R >= min_rr, even if far from target (profit is profit!)
            if original_rr < min_rr:
                logger.warning(
                    f"{symbol}: R:R {original_rr:.2f} is too low (min acceptable: {min_rr:.2f}). "
                    f"This may indicate zone is too large or SL buffer too wide. Rejecting signal."
                )
                return None

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

            # CRITICAL: Block signal if RSI is strongly against direction
            # RSI oversold (< 35) should block SELL signals
            # RSI overbought (> 65) should block BUY signals
            if direction == SignalDirection.SELL and rsi_res.details.get("condition") == "OVERSOLD":
                logger.warning(
                    f"{symbol}: REJECTING SELL signal - RSI is oversold ({rsi_res.rsi_value:.1f}). "
                    f"Cannot short when market is already oversold."
                )
                return None
            elif (
                direction == SignalDirection.BUY
                and rsi_res.details.get("condition") == "OVERBOUGHT"
            ):
                logger.warning(
                    f"{symbol}: REJECTING BUY signal - RSI is overbought ({rsi_res.rsi_value:.1f}). "
                    f"Cannot buy when market is already overbought."
                )
                return None

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

            # 4. Price Action (Weight: 0.15) - REQUIRED for entry quality
            pa_res = await self.price_action_analyzer.analyze_pattern(
                symbol, opens, highs, lows, closes, zone_type_str
            )
            price_action_score = 0.0
            if pa_res:
                # Accept pattern if direction matches OR if pattern is NEUTRAL (Inside Bar, Doji)
                # NEUTRAL patterns can work for both BUY and SELL, but with lower confidence
                if pa_res.direction == direction.name:
                    price_action_score = pa_res.confidence * 0.15
                    enhancement_score += price_action_score
                    layer_scores["price_action"] = price_action_score
                    layer_details["price_action"] = {
                        **pa_res.details,
                        "pattern_type": pa_res.pattern_type,
                        "direction": pa_res.direction,
                        "confidence": pa_res.confidence,
                        "status": "detected",
                    }
                    logger.debug(
                        f"{symbol}: Price action pattern detected: {pa_res.pattern_type} "
                        f"({pa_res.direction}, confidence: {pa_res.confidence:.1f}%)"
                    )
                elif pa_res.direction == "NEUTRAL":
                    # NEUTRAL patterns (Inside Bar, Doji) can be used but with reduced score
                    # Use 50% of original confidence for NEUTRAL patterns
                    price_action_score = (pa_res.confidence * 0.5) * 0.15
                    enhancement_score += price_action_score
                    layer_scores["price_action"] = price_action_score
                    layer_details["price_action"] = {
                        **pa_res.details,
                        "pattern_type": pa_res.pattern_type,
                        "direction": pa_res.direction,
                        "confidence": pa_res.confidence,
                        "status": "neutral_pattern",
                        "original_confidence": pa_res.confidence,
                    }
                    logger.debug(
                        f"{symbol}: Price action NEUTRAL pattern detected: {pa_res.pattern_type} "
                        f"(confidence: {pa_res.confidence:.1f}%, reduced to {pa_res.confidence * 0.5:.1f}% for NEUTRAL)"
                    )
                else:
                    # Wrong direction - log for debugging
                    layer_scores["price_action"] = 0.0
                    layer_details["price_action"] = {
                        "status": "wrong_direction",
                        "detected_pattern": pa_res.pattern_type,
                        "detected_direction": pa_res.direction,
                        "required_direction": direction.name,
                    }
                    logger.debug(
                        f"{symbol}: Price action pattern detected but wrong direction: "
                        f"{pa_res.pattern_type} ({pa_res.direction}) != required {direction.name}"
                    )
            else:
                # No price action pattern detected
                layer_scores["price_action"] = 0.0
                layer_details["price_action"] = {"status": "no_pattern"}
                logger.debug(f"{symbol}: No price action pattern detected")

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
            if "price_action" in layer_scores and pa_res is not None:
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
            # QUALITY FILTER: UNIVERSAL Minimum Score (Week 15.5.3)
            # Apply strict confluence filter to ALL asset classes
            # ═══════════════════════════════════════════════════════

            # Get minimum confluence from config (default: 75%)
            min_confluence_global = (
                self.config.get("signal_generation", {})
                .get("quality_thresholds", {})
                .get("min_confluence_score", 75.0)
            )

            # Apply UNIVERSAL minimum confluence check (Skip for Commodities as they have dynamic thresholds)
            if asset_class != "commodities" and final_score < min_confluence_global:
                logger.info(
                    f"{symbol}: REJECTED - Confluence too low ({final_score:.1f}% < {min_confluence_global}%). "
                    f"Active layers: {list(layer_scores.keys())}, "
                    f"Foundation: {weighted_foundation_score:.1f}%, "
                    f"Enhancement: {weighted_enhancement_score:.1f}%"
                )
                return None

            # ═══════════════════════════════════════════════════════
            # PRICE ACTION CONFIRMATION REQUIREMENT (NEW)
            # Require price action confirmation to prevent premature entries
            # ═══════════════════════════════════════════════════════
            require_price_action = (
                self.config.get("signal_generation", {})
                .get("validation_rules", {})
                .get("require_price_action", False)
            )

            if require_price_action:
                min_price_action_score = (
                    self.config.get("signal_generation", {})
                    .get("quality_thresholds", {})
                    .get("min_price_action_score", 10.0)
                )

                # Check if price action score meets minimum requirement
                price_action_raw_score = layer_scores.get("price_action", 0.0)
                # Convert back to raw confidence (0-100) from weighted score
                # price_action_score = raw_confidence * 0.15, so raw = price_action_score / 0.15
                price_action_raw_confidence = (
                    (price_action_raw_score / 0.15) if price_action_raw_score > 0 else 0.0
                )

                if price_action_raw_confidence < min_price_action_score:
                    logger.warning(
                        f"{symbol}: REJECTED - Price action confirmation required but insufficient "
                        f"(score: {price_action_raw_confidence:.1f}% < min: {min_price_action_score}%). "
                        f"No clear rejection pattern detected. Waiting for price action confirmation."
                    )
                    return None
                else:
                    logger.debug(
                        f"{symbol}: ✅ Price action confirmed (score: {price_action_raw_confidence:.1f}% ≥ {min_price_action_score}%)"
                    )

            # ═══════════════════════════════════════════════════════
            # UNIVERSAL H1 SNIPER GATE (FIX 2026-04-09)
            # Apply H1 Trend Gate to ALL asset classes (forex + commodities + crypto)
            # Previously this only ran inside the 'if asset_class == commodities' block —
            # meaning forex pairs were NEVER filtered by H1 trend bias. This caused
            # counter-trend trades on EURUSD, USDJPY, USDCHF, EURJPY etc.
            # ═══════════════════════════════════════════════════════
            if h1_trend_bias == "BEARISH" and direction == SignalDirection.BUY:
                logger.warning(
                    f"{symbol}: REJECTED - H1 Trend is BEARISH. "
                    f"Counter-trend BUY blocked by SNIPER Gate (Universal)."
                )
                return None
            if h1_trend_bias == "BULLISH" and direction == SignalDirection.SELL:
                logger.warning(
                    f"{symbol}: REJECTED - H1 Trend is BULLISH. "
                    f"Counter-trend SELL blocked by SNIPER Gate (Universal)."
                )
                return None

            # ═══════════════════════════════════════════════════════
            # ADDITIONAL QUALITY FILTERS: Asset-specific refinements
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

                # === DIRECTIONAL BIAS FILTER (PHASE 5.24: Strict Gate) ===
                # NOTE: Universal H1 Sniper Gate is now applied ABOVE (before this block)
                # for ALL asset classes. The check below is kept as documentation only
                # and is no longer needed since it's already handled universally above.

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

            # Log successful signal creation with detailed confluence breakdown
            logger.info(
                f"{symbol}: ✅ SIGNAL CREATED - {direction.value} | "
                f"Confluence: {final_score:.1f}% (Foundation: {weighted_foundation_score:.1f}%, "
                f"Enhancement: {weighted_enhancement_score:.1f}%) | "
                f"Layers: {list(layer_scores.keys())} | "
                f"Price: {current_price:.5f}"
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
