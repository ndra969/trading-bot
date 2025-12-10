"""Foundation Engine - Coordinates foundation strategy."""

from typing import Any

import pandas as pd

from trading_bot.strategies.foundation.supply_demand import SupplyDemandStrategy
from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.strategies.enhancement.rsi_analyzer import RSIAnalyzer
from trading_bot.strategies.enhancement.ma_analyzer import MovingAverageAnalyzer
from trading_bot.strategies.enhancement.trendline_analyzer import TrendlineAnalyzer
from trading_bot.strategies.enhancement.price_action_analyzer import PriceActionAnalyzer
from trading_bot.strategies.enhancement.fibonacci_analyzer import FibonacciAnalyzer
from trading_bot.strategies.enhancement.structure_analyzer import MarketStructureAnalyzer
from trading_bot.strategies.enhancement.breakout_analyzer import BreakoutAnalyzer
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
        
        # Log analysis context
        if zones:
            nearest_zone = min(zones, key=lambda z: min(abs(current_price - z.upper_bound), abs(current_price - z.lower_bound)))
            dist_to_nearest = min(abs(current_price - nearest_zone.upper_bound), abs(current_price - nearest_zone.lower_bound))
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
                result = await self._create_signal_from_zone(symbol, zone, current_price, timeframe, data)
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

    async def _create_signal_from_zone(
        self,
        symbol: str,
        zone: DetectedZone,
        current_price: float,
        timeframe: str,
        data: pd.DataFrame,
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
            # Determine if zone is demand or supply
            is_demand = self._is_demand_zone(zone, data)
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
            
            zone_height = zone.upper_bound - zone.lower_bound
            zone_height_pips = zone_height / pip_size
            
            # Crypto needs much wider SL buffer due to high volatility
            if asset_class == "crypto":
                # For crypto: Use 150% of zone height OR minimum 1000 points, whichever is larger
                buffer_percentage = 1.5  # 150% of zone height
                min_buffer_points = 1000.0  # Minimum 1000 points for BTC
                calculated_buffer = zone_height * buffer_percentage
                sl_buffer = max(calculated_buffer, min_buffer_points)
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
                min_sl_distance_pips = self.config.get(
                    "signal_generation", {}
                ).get("risk_reward", {}).get("min_stop_loss_distance", {}).get("forex_major", 15.0)
                min_sl_distance = min_sl_distance_pips * pip_size
                
                # Ensure SL buffer is at least minimum distance
                if sl_buffer < min_sl_distance:
                    sl_buffer = min_sl_distance
                    logger.debug(f"{symbol}: Using minimum SL buffer {min_sl_distance_pips} pips (150 points for 5-digit broker)")
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
                min_sl_distance_pips = self.config.get(
                    "signal_generation", {}
                ).get("risk_reward", {}).get("min_stop_loss_distance", {}).get("forex_jpy", 15.0)
                min_sl_distance = min_sl_distance_pips * pip_size
                if sl_buffer < min_sl_distance:
                    sl_buffer = min_sl_distance
                    logger.debug(f"{symbol}: Using minimum SL buffer {min_sl_distance_pips} pips (150 points for 5-digit broker)")
            else:
                # For commodities: 50% of zone height (no cap for now)
                sl_buffer = zone_height * 0.5
            
            if is_demand:
                direction = SignalDirection.BUY
                # For demand zone (BUY): Entry at lower_bound (bottom of zone) when price returns to zone
                # This is the optimal entry point for buying from demand zone
                # If current price is already in zone, use current price; otherwise use lower_bound
                if zone.lower_bound <= current_price <= zone.upper_bound:
                    entry_price = current_price  # Price already in zone, enter at current price
                else:
                    entry_price = zone.lower_bound  # Price approaching zone, enter at lower bound
                stop_loss = zone.lower_bound - sl_buffer
                take_profit = entry_price + (entry_price - stop_loss) * rr_ratio
            else:
                direction = SignalDirection.SELL
                # For supply zone (SELL): Entry at upper_bound (top of zone) when price returns to zone
                # This is the optimal entry point for selling from supply zone
                # If current price is already in zone, use current price; otherwise use upper_bound
                if zone.lower_bound <= current_price <= zone.upper_bound:
                    entry_price = current_price  # Price already in zone, enter at current price
                else:
                    entry_price = zone.upper_bound  # Price approaching zone, enter at upper bound
                stop_loss = zone.upper_bound + sl_buffer
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
            elif calculated_rr > max_rr * 2.0:  # More than 2x target but less than 3x - warn strongly
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
            volumes = data["volume"].tolist()

            # Calculate Enhancement Scores
            enhancement_score = 0.0
            layer_scores = {}
            layer_details = {}

            # 1. RSI Analysis (Weight: 0.10)
            rsi_res = await self.rsi_analyzer.analyze_rsi_signal(symbol, closes, timeframe, zone_type_str)
            if rsi_res.signal_type == direction.name: # Only add if aligns
                score = rsi_res.confidence * 0.10
                enhancement_score += score
                layer_scores['rsi'] = score
                layer_details['rsi'] = rsi_res.details

            # 2. Moving Average (Weight: 0.08)
            ma_res = await self.ma_analyzer.analyze_ma_signal(symbol, closes, timeframe, zone_type_str)
            if ma_res.signal_type == direction.name:
                score = ma_res.confidence * 0.08
                enhancement_score += score
                layer_scores['ma'] = score
                layer_details['ma'] = ma_res.details

            # 3. Trendline (Weight: 0.20)
            tl_res = await self.trendline_analyzer.analyze_trendline_signal(symbol, closes, timeframe)
            if (is_demand and 'SUPPORT' in tl_res.signal_type) or (not is_demand and 'RESISTANCE' in tl_res.signal_type):
                score = tl_res.confidence * 0.20
                enhancement_score += score
                layer_scores['trendline'] = score
                layer_details['trendline'] = tl_res.details

            # 4. Price Action (Weight: 0.15)
            pa_res = await self.price_action_analyzer.analyze_pattern(symbol, opens, highs, lows, closes, zone_type_str)
            if pa_res and pa_res.direction == direction.name:
                score = pa_res.confidence * 0.15
                enhancement_score += score
                layer_scores['price_action'] = score
                layer_details['price_action'] = pa_res.details

            # 5. Fibonacci (Weight: 0.12)
            fib_res = await self.fibonacci_analyzer.analyze_fibonacci(symbol, highs, lows, current_price, zone_type_str)
            if fib_res:
                score = fib_res.score * 0.12 # Base score (10-20) * weight? No, fib_res.score is small (10-20). 
                # Need to normalize. Fib score 20 is max. 20/20 * 100 * 0.12 = 12 points.
                # fib_res.score is raw points (10, 15, 20).
                # Let's say max raw score is 20. Confidence = (score/20)*100.
                norm_conf = (fib_res.score / 20.0) * 100.0
                score = norm_conf * 0.12
                enhancement_score += score
                layer_scores['fibonacci'] = score
                layer_details['fibonacci'] = fib_res.details

            # 6. Structure (Weight: 0.08)
            struct_res = await self.structure_analyzer.analyze_structure(symbol, highs, lows, closes)
            if struct_res and struct_res.direction == direction.name:
                score = struct_res.confidence * 0.08
                enhancement_score += score
                layer_scores['structure'] = score
                layer_details['structure'] = struct_res.details

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
            
            if 'rsi' in layer_scores: 
                # layer_scores['rsi'] was stored as weighted in previous steps?
                # Wait, in the code above we calculated: score = rsi_res.confidence * 0.10
                # We need to use the RAW confidence from the analyzer result, NOT the pre-weighted one.
                # rsi_res.confidence is the raw value (0-100).
                add_weighted_layer('rsi', rsi_res.confidence)
                
            if 'ma' in layer_scores: add_weighted_layer('ma', ma_res.confidence)
            if 'trendline' in layer_scores: add_weighted_layer('trendline', tl_res.confidence)
            if 'price_action' in layer_scores: add_weighted_layer('price_action', pa_res.confidence)
            
            # Fibonacci score was normalized to 0-100 in previous step
            if 'fibonacci' in layer_scores: 
                # recalculate raw confidence from the normalized calc we did
                raw_fib = (fib_res.score / 20.0) * 100.0
                add_weighted_layer('fibonacci', raw_fib)
                
            if 'structure' in layer_scores: add_weighted_layer('structure', struct_res.confidence)

            # Final Score Calculation
            # Sum of (Score * Weight). Max possible score is 100 if all weights sum to 1.0
            # and all components have 100 confidence.
            final_score = weighted_foundation_score + weighted_enhancement_score
            
            # Ensure we don't exceed 100
            final_score = min(final_score, 100.0)
            
            # Generate zone_id
            zone_id = f"{symbol}_{zone.zone_type.value}_{zone.lower_bound:.5f}_{zone.upper_bound:.5f}"

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
                    "layer_details": layer_details
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
