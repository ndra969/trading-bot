"""Foundation Engine - Coordinates foundation strategy."""

from datetime import datetime
from typing import Any

import pandas as pd
from trading_core.enums.rejection_stage import RejectionStage
from trading_core.utils.logger import get_logger

from trading_worker.strategies.enhancement.breakout_analyzer import BreakoutAnalyzer
from trading_worker.strategies.enhancement.fibonacci_analyzer import FibonacciAnalyzer
from trading_worker.strategies.enhancement.ma_analyzer import MovingAverageAnalyzer
from trading_worker.strategies.enhancement.price_action_analyzer import PriceActionAnalyzer
from trading_worker.strategies.enhancement.rsi_analyzer import RSIAnalyzer
from trading_worker.strategies.enhancement.structure_analyzer import MarketStructureAnalyzer
from trading_worker.strategies.enhancement.trendline_analyzer import TrendlineAnalyzer
from trading_worker.strategies.foundation.supply_demand import SupplyDemandStrategy
from trading_worker.strategies.foundation.zone_detector import DetectedZone
from trading_worker.strategies.models import SignalDirection, StrategyResult

logger = get_logger(__name__)


class FoundationEngine:
    """
    Foundation strategy engine.

    Coordinates all foundation strategy components.
    """

    def __init__(
        self,
        config: dict[str, Any] = None,
        use_database: bool = True,
        symbol_mapper=None,
        rejection_recorder=None,
    ):
        """
        Initialize foundation engine.

        Args:
            config: Engine configuration
            use_database: Whether to persist zones to database
            symbol_mapper: Optional SymbolMapper for symbol normalization (EURUSDc -> EURUSD)
            rejection_recorder: Optional RejectionRecorder for tuning telemetry.
                When None (tests/backtests), rejection recording is a no-op.
        """
        self.config = config or {}
        self.symbol_mapper = symbol_mapper  # Store for symbol normalization
        self.rejection_recorder = rejection_recorder

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

    def _record_rejection(
        self,
        stage: RejectionStage,
        symbol: str,
        *,
        direction: SignalDirection | None = None,
        asset_class: str | None = None,
        confluence_score: float | None = None,
        **details: Any,
    ) -> None:
        """Record a rejected setup for tuning telemetry (no-op without recorder).

        Fire-and-forget: never raises into the signal path. Call this right
        before the matching ``return None`` / ``return False`` — it does not
        change control flow.
        """
        recorder = self.rejection_recorder
        if recorder is None:
            return
        try:
            recorder.record(
                stage=stage,
                symbol=symbol,
                asset_class=asset_class,
                direction=direction.name if direction is not None else None,
                confluence_score=confluence_score,
                details=details or None,
            )
        except Exception:  # pragma: no cover - telemetry must never break trading
            pass

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
        from trading_worker.position.pip_calculator import PipCalculator

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
        from trading_worker.position.pip_calculator import PipCalculator

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

    def _passes_zone_quality_filters(
        self,
        symbol: str,
        zone: DetectedZone,
        asset_class: str,
        zone_height_pips: float,
    ) -> bool:
        """Apply asset-specific zone quality filters (width + strength).

        Returns:
            True if zone passes all filters, False if rejected.
        """
        if asset_class == "commodities":
            # Filter 1: Zone Width (Precision Filter)
            # Gold can have larger zones due to volatility, allow more flexibility
            max_zone_width = 1000.0  # pips
            if zone_height_pips > max_zone_width:
                logger.warning(
                    f"{symbol}: REJECTED - Zone too wide ({zone_height_pips:.1f} pips > {max_zone_width} pips). "
                    f"Wide zones lack precision and increase risk."
                )
                return False

            # Filter 2: Zone Strength (Quality Filter)
            min_zone_strength = 0.4
            if zone.strength < min_zone_strength:
                logger.warning(
                    f"{symbol}: REJECTED - Zone strength too low ({zone.strength:.2f} < {min_zone_strength}). "
                    f"Only trade reasonably tested zones."
                )
                return False

        elif asset_class == "crypto":
            # Filter 1: Zone Width (Precision Filter)
            # Max 600 pips for BTCUSD to prevent huge risk
            max_zone_width = 600.0  # pips
            if zone_height_pips > max_zone_width:
                logger.warning(
                    f"{symbol}: REJECTED - Zone too wide ({zone_height_pips:.1f} pips > {max_zone_width} pips). "
                    f"Wide zones increase risk beyond acceptable limits for crypto."
                )
                return False

            # Filter 2: Zone Strength - Crypto requires strong zones
            min_zone_strength = 0.5
            if zone.strength < min_zone_strength:
                logger.warning(
                    f"{symbol}: REJECTED - Zone strength too low ({zone.strength:.2f} < {min_zone_strength}). "
                    f"Crypto requires strong zones due to high volatility."
                )
                return False

        return True

    def _build_strategy_result(
        self,
        symbol: str,
        zone: DetectedZone,
        direction: SignalDirection,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        timeframe: str,
        final_score: float,
        weighted_foundation_score: float,
        weighted_enhancement_score: float,
        layer_scores: dict,
        layer_details: dict,
        raw_confidences: dict,
        current_price: float,
    ) -> StrategyResult:
        """Build the final StrategyResult after all filters have passed.

        Generates zone_id, logs the successful signal, and packages all
        confluence data into metadata for downstream consumers.
        """
        zone_id = f"{symbol}_{zone.zone_type.value}_{zone.lower_bound:.5f}_{zone.upper_bound:.5f}"

        # Observability (ui-dashboard Goal 7): the foundation-vs-enhancement
        # split + per-layer raw confidences only existed in transient logs.
        # Persist them so the API / Tuning view can show WHY a trade scored
        # what it did. Pure metadata — does not affect scoring or execution.
        confluence_breakdown = {
            "foundation_share": round(weighted_foundation_score, 2),
            "enhancement_share": round(weighted_enhancement_score, 2),
            "raw_confidences": {k: round(float(v), 2) for k, v in raw_confidences.items()},
            "active_layers": sorted(raw_confidences.keys()),
        }

        logger.info(
            f"{symbol}: ✅ SIGNAL CREATED - {direction.value} | "
            f"Confluence: {final_score:.1f}% (Foundation: {weighted_foundation_score:.1f}%, "
            f"Enhancement: {weighted_enhancement_score:.1f}%) | "
            f"Layers: {list(layer_scores.keys())} | "
            f"Price: {current_price:.5f}"
        )

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
                "confluence_breakdown": confluence_breakdown,
            },
        )

        logger.debug(
            f"Created signal: {direction.value} {symbol} "
            f"(Total Score: {final_score:.1f}, Layers: {list(layer_scores.keys())})"
        )
        return result

    def _passes_final_quality_filters(
        self,
        symbol: str,
        direction: SignalDirection,
        asset_class: str,
        final_score: float,
        weighted_foundation_score: float,
        weighted_enhancement_score: float,
        layer_scores: dict,
        h1_trend_bias: str | None,
        data: pd.DataFrame,
        current_price: float,
        current_range: float,
        avg_range: float,
    ) -> bool:
        """Apply final quality filters after confluence scoring.

        All thresholds resolved per asset class from
        ``signal_generation.quality_thresholds.<asset_class>`` with a
        fallback to ``quality_thresholds.default``. Same for
        ``validation_rules``.

        Filter chain (order matters):
            1. Asset-class minimum confluence
               (commodities uses a separate counter-trend threshold)
            2. Price action confirmation requirement (per asset)
            3. Universal H1 Sniper Gate (counter-trend block, all assets)
            4. Commodities-specific: require at least one enhancement layer

        Returns:
            True if signal passes all filters, False if rejected.
        """
        thresholds = self._resolve_quality_thresholds(asset_class)
        rules = self._resolve_validation_rules(asset_class)

        # 1. Asset-class minimum confluence
        is_counter_trend_commodity = False
        if asset_class == "commodities":
            is_counter_trend_commodity = self._is_counter_trend(
                direction, data, current_price, current_range, avg_range
            )
            min_confluence = (
                thresholds.get("min_confluence_score_counter", 50.0)
                if is_counter_trend_commodity
                else thresholds.get("min_confluence_score", 40.0)
            )
        else:
            min_confluence = thresholds.get("min_confluence_score", 65.0)

        if final_score < min_confluence:
            counter_label = "Counter-trend " if is_counter_trend_commodity else ""
            logger.info(
                f"{symbol}: REJECTED - {counter_label}Confluence too low "
                f"({final_score:.1f}% < {min_confluence}%, asset_class={asset_class}). "
                f"Active layers: {list(layer_scores.keys())}, "
                f"Foundation: {weighted_foundation_score:.1f}%, "
                f"Enhancement: {weighted_enhancement_score:.1f}%"
            )
            self._record_rejection(
                RejectionStage.CONFLUENCE_TOO_LOW,
                symbol,
                direction=direction,
                asset_class=asset_class,
                confluence_score=final_score,
                min_confluence=min_confluence,
            )
            return False

        # 2. Price Action Confirmation Requirement
        if rules.get("require_price_action", False):
            min_pa_score = thresholds.get("min_price_action_score", 10.0)
            # price_action layer_score = raw_confidence * 0.15, so raw = score / 0.15
            pa_weighted = layer_scores.get("price_action", 0.0)
            pa_raw = (pa_weighted / 0.15) if pa_weighted > 0 else 0.0

            if pa_raw < min_pa_score:
                logger.warning(
                    f"{symbol}: REJECTED - Price action confirmation required but insufficient "
                    f"(score: {pa_raw:.1f}% < min: {min_pa_score}%). "
                    f"No clear rejection pattern detected."
                )
                self._record_rejection(
                    RejectionStage.PRICE_ACTION_REQUIRED,
                    symbol,
                    direction=direction,
                    asset_class=asset_class,
                    confluence_score=final_score,
                    pa_raw=round(pa_raw, 1),
                )
                return False
            logger.debug(
                f"{symbol}: ✅ Price action confirmed (score: {pa_raw:.1f}% ≥ {min_pa_score}%)"
            )

        # 3. UNIVERSAL H1 Sniper Gate - blocks counter-trend trades on ALL asset classes
        if h1_trend_bias == "BEARISH" and direction == SignalDirection.BUY:
            logger.warning(
                f"{symbol}: REJECTED - H1 Trend is BEARISH. "
                f"Counter-trend BUY blocked by SNIPER Gate (Universal)."
            )
            self._record_rejection(
                RejectionStage.COUNTER_TREND_GATE,
                symbol,
                direction=direction,
                asset_class=asset_class,
                confluence_score=final_score,
                h1_trend_bias=h1_trend_bias,
            )
            return False
        if h1_trend_bias == "BULLISH" and direction == SignalDirection.SELL:
            logger.warning(
                f"{symbol}: REJECTED - H1 Trend is BULLISH. "
                f"Counter-trend SELL blocked by SNIPER Gate (Universal)."
            )
            self._record_rejection(
                RejectionStage.COUNTER_TREND_GATE,
                symbol,
                direction=direction,
                asset_class=asset_class,
                confluence_score=final_score,
                h1_trend_bias=h1_trend_bias,
            )
            return False

        # 4. Commodities-specific: at least one enhancement layer required
        if asset_class == "commodities" and not layer_scores:
            logger.warning(
                f"{symbol}: REJECTED - No technical confirmation. "
                f"Gold trades require at least one enhancement layer."
            )
            self._record_rejection(
                RejectionStage.NO_ENHANCEMENT_LAYER,
                symbol,
                direction=direction,
                asset_class=asset_class,
                confluence_score=final_score,
            )
            return False

        return True

    def _resolve_quality_thresholds(self, asset_class: str) -> dict:
        """Resolve per-asset quality thresholds with fallback to default.

        Reads ``signal_generation.quality_thresholds.<asset_class>`` and
        falls back to ``quality_thresholds.default``. Supports the legacy
        flat structure (where ``min_confluence_score`` etc. live directly
        under ``quality_thresholds``) for backward compatibility.
        """
        qt = self.config.get("signal_generation", {}).get("quality_thresholds", {})
        per_asset = qt.get(asset_class)
        if isinstance(per_asset, dict):
            # Merge default + per-asset (per-asset wins). Fall back to legacy
            # flat values for keys missing from both.
            default = qt.get("default", {}) if isinstance(qt.get("default"), dict) else {}
            merged = {**self._legacy_flat_thresholds(qt), **default, **per_asset}
            return merged

        # No per-asset entry → use default, falling back to legacy flat layout
        default = qt.get("default")
        if isinstance(default, dict):
            return {**self._legacy_flat_thresholds(qt), **default}
        return self._legacy_flat_thresholds(qt)

    @staticmethod
    def _legacy_flat_thresholds(qt: dict) -> dict:
        """Extract recognised top-level keys from the old flat schema."""
        legacy_keys = (
            "min_confluence_score",
            "min_confluence_score_counter",
            "min_foundation_score",
            "min_price_action_score",
        )
        return {k: qt[k] for k in legacy_keys if k in qt and not isinstance(qt[k], dict)}

    def _resolve_validation_rules(self, asset_class: str) -> dict:
        """Resolve per-asset validation rules with fallback to default."""
        vr = self.config.get("signal_generation", {}).get("validation_rules", {})
        per_asset = vr.get(asset_class)
        if isinstance(per_asset, dict):
            default = vr.get("default", {}) if isinstance(vr.get("default"), dict) else {}
            return {**self._legacy_flat_rules(vr), **default, **per_asset}

        default = vr.get("default")
        if isinstance(default, dict):
            return {**self._legacy_flat_rules(vr), **default}
        return self._legacy_flat_rules(vr)

    @staticmethod
    def _legacy_flat_rules(vr: dict) -> dict:
        """Extract recognised top-level keys from the old flat schema."""
        legacy_keys = ("require_foundation", "require_price_action")
        return {k: vr[k] for k in legacy_keys if k in vr and not isinstance(vr[k], dict)}

    def _climax_multiplier(self, asset_class: str) -> float:
        """Resolve the climax-candle range multiplier for an asset class.

        Reads ``signal_generation.volatility_filter.<asset_class>.climax_multiplier``
        with a fallback to ``volatility_filter.default`` and finally a hard 2.5.
        """
        vf = self.config.get("signal_generation", {}).get("volatility_filter", {})
        per_asset = vf.get(asset_class) if isinstance(vf.get(asset_class), dict) else {}
        default = vf.get("default") if isinstance(vf.get("default"), dict) else {}
        return float(
            per_asset.get(
                "climax_multiplier",
                default.get("climax_multiplier", 2.5),
            )
        )

    def _commodity_gates(self) -> dict:
        """Per-direction commodities entry-gate thresholds (config-driven).

        Reads ``signal_generation.commodity_gates``; every default reproduces
        the prior hardcoded value exactly, so a missing/partial config leaves
        behaviour unchanged. BUY/SELL are separate so their asymmetry is
        explicit and tunable.
        """
        cfg = self.config.get("signal_generation", {}).get("commodity_gates", {})

        def g(path: tuple, default: float) -> float:
            cur: object = cfg
            for key in path:
                if not isinstance(cur, dict) or key not in cur:
                    return default
                cur = cur[key]
            return cur if isinstance(cur, int | float) else default

        return {
            "rejection_wick": {
                "buy": {
                    "min_ratio": g(("rejection_wick", "buy", "min_ratio"), 0.15),
                    "trend_following_ratio": g(
                        ("rejection_wick", "buy", "trend_following_ratio"), 0.08
                    ),
                },
                "sell": {
                    "min_ratio": g(("rejection_wick", "sell", "min_ratio"), 0.30),
                    "trend_following_ratio": g(
                        ("rejection_wick", "sell", "trend_following_ratio"), 0.15
                    ),
                },
            },
            "color_match": {
                "buy_small_body_exception": g(("color_match", "buy_small_body_exception"), 0.30),
                "sell_small_body_exception": g(("color_match", "sell_small_body_exception"), 0.0),
            },
            "volatility_trend_gate": {
                "buy": {
                    "vol_mult": g(("volatility_trend_gate", "buy", "vol_mult"), 2.0),
                    "ema_buffer_pct": g(("volatility_trend_gate", "buy", "ema_buffer_pct"), 0.3),
                },
                "sell": {
                    "vol_mult": g(("volatility_trend_gate", "sell", "vol_mult"), 1.5),
                    "ema_buffer_pct": g(("volatility_trend_gate", "sell", "ema_buffer_pct"), 0.0),
                },
            },
        }

    def _is_climax_candle(self, asset_class: str, data: pd.DataFrame) -> bool:
        """Detect an overextended / exhaustion candle (chasing a spent move).

        True when the latest candle's high-low range exceeds
        ``climax_multiplier × ATR(14)-equivalent average range``. Applies to
        ALL asset classes. Needs at least 14 bars; returns False otherwise.
        """
        if len(data) < 14:
            return False
        ranges = data["high"] - data["low"]
        avg_range = float(ranges.tail(14).mean())
        if avg_range <= 0:
            return False
        current_range = float(data["high"].iloc[-1] - data["low"].iloc[-1])
        return current_range > avg_range * self._climax_multiplier(asset_class)

    def _is_counter_trend(
        self,
        direction: SignalDirection,
        data: pd.DataFrame,
        current_price: float,
        current_range: float,
        avg_range: float,
    ) -> bool:
        """Detect if signal direction is counter to the prevailing trend.

        Uses EMA 100 reference, but switches to EMA 20 during high volatility
        (current_range > 1.5x avg_range) - Reactive Threshold (Phase 5.23).
        """
        if len(data) < 100:
            return False

        ema_ref = data["close"].ewm(span=100, adjust=False).mean().iloc[-1]
        if current_range > avg_range * 1.5:
            ema_ref = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]

        if direction == SignalDirection.BUY and current_price < ema_ref:
            return True
        if direction == SignalDirection.SELL and current_price > ema_ref:
            return True
        return False

    def _calculate_confluence_score(
        self, zone: DetectedZone, raw_confidences: dict
    ) -> tuple[float, float, float]:
        """Confluence as a weighted AVERAGE over the layers that participated.

        Uses weights from `confluence_weights` config section:
            foundation: 0.30 (S&D zone strength)
            trendline: 0.20, price_action: 0.15, fibonacci: 0.12,
            breakout: 0.12, structure: 0.08, rsi: 0.10, ma: 0.08

        Foundation (zone strength) always participates. An enhancement layer
        participates only when it agreed with the trade direction (i.e. it is
        present in ``raw_confidences``). The score is normalised by the summed
        weight of the *participating* layers, so it expresses the weighted % of
        confidence among the signals that actually spoke — rather than an
        absolute sum that can never approach 100 because trend/momentum layers
        (rsi, structure, breakout) structurally stay silent at reversal zones.

        Returns:
            (final_score, foundation_share, enhancement_share). The two shares
            sum to final_score; all three are 0-100.
        """
        weights = self.config.get("confluence_weights", {})
        foundation_weight = weights.get("foundation", 0.30)

        # Foundation always participates; its raw confidence is the zone strength.
        foundation_contrib = zone.strength * foundation_weight

        enhancement_layers = (
            "rsi",
            "ma",
            "trendline",
            "price_action",
            "fibonacci",
            "structure",
            "breakout",
        )
        enhancement_contrib = sum(
            raw_confidences.get(layer, 0.0) * weights.get(layer, 0.0)
            for layer in enhancement_layers
        )

        # Denominator: weight of every layer that actually contributed.
        participating_weight = foundation_weight + sum(
            weights.get(layer, 0.0) for layer in enhancement_layers if layer in raw_confidences
        )

        if participating_weight <= 0:
            return 0.0, 0.0, 0.0

        foundation_share = min(foundation_contrib / participating_weight, 100.0)
        enhancement_share = enhancement_contrib / participating_weight
        final_score = min(foundation_share + enhancement_share, 100.0)
        return final_score, foundation_share, enhancement_share

    async def _run_enhancement_analyzers(
        self,
        symbol: str,
        direction: SignalDirection,
        is_demand: bool,
        zone_type_str: str,
        timeframe: str,
        asset_class: str,
        opens: list,
        highs: list,
        lows: list,
        closes: list,
        current_price: float,
    ) -> tuple[dict, dict, dict] | None:
        """Run all enhancement layer analyzers with hard-rejection gates.

        Enhancement layers (in order):
            1. RSI Analysis (10%) - blocks if RSI strongly against direction
            2. Moving Average (8%)
            3. Trendline (20%)
            4. Price Action (15%) - REQUIRED, supports NEUTRAL patterns
            5. Fibonacci (12%)
            6. Structure (8%) - blocks if commodities + >90% opposite
            7. Breakout (12%) - skipped at zone entry (used for confirmation later)

        Returns:
            (layer_scores, layer_details, raw_confidences) or None if hard-rejected.
            - layer_scores: pre-weighted contribution per layer (debug/metadata)
            - layer_details: full analyzer result details per layer
            - raw_confidences: raw analyzer confidence (0-100) per layer, used for
              final weighted score calculation via config-driven weights
        """
        layer_scores: dict = {}
        layer_details: dict = {}
        raw_confidences: dict = {}

        # 1. RSI Analysis (Weight: 0.10) - with hard rejection gate
        rsi_res = await self.rsi_analyzer.analyze_rsi_signal(
            symbol, closes, timeframe, zone_type_str
        )

        # CRITICAL: Block signal if RSI is strongly against direction
        # RSI oversold (< 35) blocks SELL, overbought (> 65) blocks BUY
        if direction == SignalDirection.SELL and rsi_res.details.get("condition") == "OVERSOLD":
            logger.warning(
                f"{symbol}: REJECTING SELL signal - RSI is oversold ({rsi_res.rsi_value:.1f}). "
                f"Cannot short when market is already oversold."
            )
            self._record_rejection(
                RejectionStage.RSI_GATE,
                symbol,
                direction=direction,
                asset_class=asset_class,
                condition="OVERSOLD",
                rsi=round(float(rsi_res.rsi_value), 1),
            )
            return None
        elif direction == SignalDirection.BUY and rsi_res.details.get("condition") == "OVERBOUGHT":
            logger.warning(
                f"{symbol}: REJECTING BUY signal - RSI is overbought ({rsi_res.rsi_value:.1f}). "
                f"Cannot buy when market is already overbought."
            )
            self._record_rejection(
                RejectionStage.RSI_GATE,
                symbol,
                direction=direction,
                asset_class=asset_class,
                condition="OVERBOUGHT",
                rsi=round(float(rsi_res.rsi_value), 1),
            )
            return None

        if rsi_res.signal_type == direction.name:
            layer_scores["rsi"] = rsi_res.confidence * 0.10
            layer_details["rsi"] = rsi_res.details
            raw_confidences["rsi"] = rsi_res.confidence

        # 2. Moving Average (Weight: 0.08)
        ma_res = await self.ma_analyzer.analyze_ma_signal(symbol, closes, timeframe, zone_type_str)
        if ma_res.signal_type == direction.name:
            layer_scores["ma"] = ma_res.confidence * 0.08
            layer_details["ma"] = ma_res.details
            raw_confidences["ma"] = ma_res.confidence

        # 3. Trendline (Weight: 0.20)
        tl_res = await self.trendline_analyzer.analyze_trendline_signal(symbol, closes, timeframe)
        if (is_demand and "SUPPORT" in tl_res.signal_type) or (
            not is_demand and "RESISTANCE" in tl_res.signal_type
        ):
            layer_scores["trendline"] = tl_res.confidence * 0.20
            layer_details["trendline"] = tl_res.details
            raw_confidences["trendline"] = tl_res.confidence

        # 4. Price Action (Weight: 0.15) - REQUIRED for entry quality
        pa_res = await self.price_action_analyzer.analyze_pattern(
            symbol, opens, highs, lows, closes, zone_type_str
        )
        self._score_price_action(
            symbol, pa_res, direction, layer_scores, layer_details, raw_confidences
        )

        # 5. Fibonacci (Weight: 0.12)
        fib_res = await self.fibonacci_analyzer.analyze_fibonacci(
            symbol, highs, lows, current_price, zone_type_str
        )
        if fib_res:
            # fib_res.score is raw points (10-20), normalize to 0-100 then apply weight
            norm_conf = (fib_res.score / 20.0) * 100.0
            layer_scores["fibonacci"] = norm_conf * 0.12
            layer_details["fibonacci"] = fib_res.details
            raw_confidences["fibonacci"] = norm_conf

        # 6. Structure (Weight: 0.08) - with hard rejection gate for commodities
        struct_res = await self.structure_analyzer.analyze_structure(symbol, highs, lows, closes)
        # PHASE 5.22: Adjusted alignment for Commodities
        if asset_class == "commodities" and struct_res:
            # Only reject if structure is OVERWHELMINGLY opposite (confidence > 90%)
            if struct_res.direction != direction.name and struct_res.confidence > 90.0:
                logger.warning(
                    f"{symbol}: REJECTED - Extremely strong market structure misalignment "
                    f"({struct_res.direction} {struct_res.confidence:.1f}% vs {direction.name})"
                )
                self._record_rejection(
                    RejectionStage.STRUCTURE_GATE,
                    symbol,
                    direction=direction,
                    asset_class=asset_class,
                    structure_direction=struct_res.direction,
                    structure_confidence=round(float(struct_res.confidence), 1),
                )
                return None
            elif struct_res.direction != direction.name:
                logger.debug(
                    f"{symbol}: Weak/Moderate market structure misalignment "
                    f"({struct_res.direction} {struct_res.confidence:.1f}%). "
                    f"Proceeding due to High-Vol Trend alignment."
                )

        if struct_res and struct_res.direction == direction.name:
            layer_scores["structure"] = struct_res.confidence * 0.08
            # structure_type is metadata (a string) — keep it out of layer_scores,
            # which must stay a {layer: float} map (it drives logging/keys()).
            layer_details["structure"] = {
                **(struct_res.details or {}),
                "structure_type": struct_res.structure_type,
            }
            raw_confidences["structure"] = struct_res.confidence

        # 7. Breakout (Weight: 0.12) - skipped at zone entry, used for confirmation later
        # BreakoutRetest is for re-entry; here we are AT zone, expecting bounce or break.

        return layer_scores, layer_details, raw_confidences

    def _score_price_action(
        self,
        symbol: str,
        pa_res,
        direction: SignalDirection,
        layer_scores: dict,
        layer_details: dict,
        raw_confidences: dict,
    ) -> None:
        """Score price action layer; mutates layer_scores/details/raw_confidences.

        ``raw_confidences`` drives the normalised confluence score, so it MUST
        carry the *directional* contribution — never a contradicting pattern's
        raw confidence:

        - Direction match  → full score (conf * 0.15);  raw = conf
        - NEUTRAL pattern  → half score (0.5*conf*0.15); raw = 0.5*conf
        - Wrong direction / no pattern → score 0.0 and price_action does NOT
          participate (key omitted from raw_confidences). A bullish pinbar must
          not inflate a SELL's confluence.
        """
        if not pa_res:
            layer_scores["price_action"] = 0.0
            layer_details["price_action"] = {"status": "no_pattern"}
            logger.debug(f"{symbol}: No price action pattern detected")
            return

        # Direction matches - full score
        if pa_res.direction == direction.name:
            layer_scores["price_action"] = pa_res.confidence * 0.15
            raw_confidences["price_action"] = pa_res.confidence
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
            return

        # NEUTRAL patterns (Inside Bar, Doji) - reduced score (50%)
        if pa_res.direction == "NEUTRAL":
            layer_scores["price_action"] = (pa_res.confidence * 0.5) * 0.15
            raw_confidences["price_action"] = pa_res.confidence * 0.5
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
                f"(confidence: {pa_res.confidence:.1f}%, reduced to {pa_res.confidence * 0.5:.1f}%)"
            )
            return

        # Wrong direction - no score, and DO NOT let it participate in confluence
        layer_scores["price_action"] = 0.0
        layer_details["price_action"] = {
            "status": "wrong_direction",
            "detected_pattern": pa_res.pattern_type,
            "detected_direction": pa_res.direction,
            "required_direction": direction.name,
        }
        logger.debug(
            f"{symbol}: Price action pattern detected but wrong direction: "
            f"{pa_res.pattern_type} ({pa_res.direction}) != required {direction.name} "
            f"— excluded from confluence"
        )

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
            gates = self._commodity_gates()  # per-direction commodities gate thresholds

            # Get R:R ratio from config (default 2.0 for 1:2)
            rr_ratio = (
                self.config.get("signal_generation", {})
                .get("risk_reward", {})
                .get("default_take_profit_ratio", 2.0)
            )

            # Determine asset class for SL buffer adjustment
            from trading_worker.position.pip_calculator import PipCalculator

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

            # Apply asset-specific zone quality filters
            if not self._passes_zone_quality_filters(symbol, zone, asset_class, zone_height_pips):
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
                        self._record_rejection(
                            RejectionStage.VOLUME_BURST,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
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
                            self._record_rejection(
                                RejectionStage.FALLING_KNIFE,
                                symbol,
                                direction=direction,
                                asset_class=asset_class,
                                body_ratio=round(body_ratio, 2),
                            )
                            return None

                # === FLASH CRASH / CLIMAX PROTECTION (Volatility Filter) ===
                # APPLIES TO ALL ASSET CLASSES. Per-asset multipliers live in
                # signal_generation.volatility_filter (see _is_climax_candle).
                # Prevent entry on extreme exhaustion candles (chasing tops/bottoms).
                # current_range/avg_range are also reused downstream (counter-trend
                # gate + final quality filters), so compute them unconditionally.
                if len(data) >= 14:
                    ranges = data["high"] - data["low"]
                    avg_range = float(ranges.tail(14).mean())
                    current_range = float(data["high"].iloc[-1] - data["low"].iloc[-1])
                else:
                    avg_range = 0.0
                    current_range = 0.0

                if self._is_climax_candle(asset_class, data):
                    logger.warning(
                        f"{symbol}: REJECTED - Climax Candle / Extreme Volatility "
                        f"({current_range:.5f} > "
                        f"{avg_range * self._climax_multiplier(asset_class):.5f}, "
                        f"asset_class={asset_class}). "
                        "Risk of reversal is high. Waiting for consolidation."
                    )
                    self._record_rejection(
                        RejectionStage.CLIMAX,
                        symbol,
                        direction=direction,
                        asset_class=asset_class,
                        current_range=round(current_range, 5),
                        avg_range=round(avg_range, 5),
                    )
                    return None

                # === REJECTION WICK CONFIRMATION (PHASE 5.11) ===
                if asset_class == "commodities" and last_range > 0:
                    lower_wick = min(last_open, last_close) - last_low
                    wick_ratio = lower_wick / last_range

                    wick_cfg = gates["rejection_wick"]["buy"]
                    wick_threshold = wick_cfg["min_ratio"]
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        is_with_trend = (
                            direction == SignalDirection.BUY and current_price > ema_20
                        ) or (direction == SignalDirection.SELL and current_price < ema_20)
                        if is_with_trend:
                            wick_threshold = wick_cfg["trend_following_ratio"]

                    if wick_ratio < wick_threshold:
                        logger.warning(
                            f"{symbol}: REJECTED - No bounce confirmation (Lower Wick: {wick_ratio:.2f} < {wick_threshold})"
                        )
                        self._record_rejection(
                            RejectionStage.REJECTION_WICK,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            wick_ratio=round(wick_ratio, 2),
                            threshold=wick_threshold,
                        )
                        return None

                # === SIGNAL CANDLE COLOR MATCH (PHASE 5.12) ===
                # Allow doji / small bearish body (< exception) as neutral; else require green.
                if asset_class == "commodities" and last_close <= last_open:
                    body_exception = gates["color_match"]["buy_small_body_exception"]
                    if last_range > 0:
                        body_ratio = abs(last_close - last_open) / last_range
                        if body_ratio < body_exception:  # Small body = doji-like, allow
                            logger.debug(
                                f"{symbol}: ALLOWED - Small bearish body "
                                f"({body_ratio:.2f} < {body_exception}), treating as neutral"
                            )
                        else:
                            logger.warning(
                                f"{symbol}: REJECTED - No bullish confirmation (Candle is Bearish with body {body_ratio:.2f}). Waiting for green candle."
                            )
                            self._record_rejection(
                                RejectionStage.COLOR_MATCH,
                                symbol,
                                direction=direction,
                                asset_class=asset_class,
                                body_ratio=round(body_ratio, 2),
                            )
                            return None
                    else:
                        logger.warning(
                            f"{symbol}: REJECTED - No bullish confirmation (Candle is Bearish). Waiting for green candle."
                        )
                        self._record_rejection(
                            RejectionStage.COLOR_MATCH,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                        )
                        return None

                # === VOLATILITY-DEPENDENT TREND GATE (PHASE 5.13) ===
                if asset_class == "commodities" and len(data) >= 100:
                    # Calculate volatility
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # In very high volatility, block counter-trend BUY (price below
                    # EMA20 by more than ema_buffer_pct). Thresholds are config-driven.
                    vt_cfg = gates["volatility_trend_gate"]["buy"]
                    if current_range > avg_range * vt_cfg["vol_mult"]:
                        # Use Faster EMA (20) for reactive volatility gating
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        price_below_ema_pct = (ema_20 - current_price) / ema_20 * 100
                        if (
                            current_price < ema_20
                            and price_below_ema_pct > vt_cfg["ema_buffer_pct"]
                        ):
                            logger.warning(
                                f"{symbol}: REJECTED - Very high volatility ({current_range:.1f} > {avg_range*vt_cfg['vol_mult']:.1f}) and strong counter-trend (Price {price_below_ema_pct:.2f}% below EMA). NO counter-trend BUY allowed during crash."
                            )
                            self._record_rejection(
                                RejectionStage.VOLATILITY_TREND_GATE,
                                symbol,
                                direction=direction,
                                asset_class=asset_class,
                                price_below_ema_pct=round(price_below_ema_pct, 2),
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
                        self._record_rejection(
                            RejectionStage.ANTI_CHASE,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            dev_pips=round(entry_dist_from_zone_bottom / pip_size, 1),
                            max_pips=max_entry_dev_pips,
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
                        self._record_rejection(
                            RejectionStage.ANTI_CHASE,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            dev_pips=round(entry_dist_from_zone_top / pip_size, 1),
                            max_pips=max_entry_dev_pips,
                            above_upper_bound=True,
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
                symbol_cfg = (
                    symbols_cfg.get(symbol_for_config, {}) if isinstance(symbols_cfg, dict) else {}
                )
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
                    self._record_rejection(
                        RejectionStage.MAX_STOP_LOSS,
                        symbol,
                        direction=direction,
                        asset_class=asset_class,
                        risk_pips=round(current_risk / pip_size, 1),
                        max_pips=max_risk_pips,
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
                        self._record_rejection(
                            RejectionStage.VOLUME_BURST,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
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
                            self._record_rejection(
                                RejectionStage.MOMENTUM_SPIKE,
                                symbol,
                                direction=direction,
                                asset_class=asset_class,
                                body_ratio=round(body_ratio, 2),
                            )
                            return None

                # === FLASH CRASH / CLIMAX PROTECTION (Volatility Filter) ===
                # APPLIES TO ALL ASSET CLASSES. Per-asset multipliers live in
                # signal_generation.volatility_filter (see _is_climax_candle).
                # Prevent entry on extreme exhaustion candles (chasing tops/bottoms).
                # current_range/avg_range are also reused downstream (counter-trend
                # gate + final quality filters), so compute them unconditionally.
                if len(data) >= 14:
                    ranges = data["high"] - data["low"]
                    avg_range = float(ranges.tail(14).mean())
                    current_range = float(data["high"].iloc[-1] - data["low"].iloc[-1])
                else:
                    avg_range = 0.0
                    current_range = 0.0

                if self._is_climax_candle(asset_class, data):
                    logger.warning(
                        f"{symbol}: REJECTED - Climax Candle / Extreme Volatility "
                        f"({current_range:.5f} > "
                        f"{avg_range * self._climax_multiplier(asset_class):.5f}, "
                        f"asset_class={asset_class}). "
                        "Risk of reversal is high. Waiting for consolidation."
                    )
                    self._record_rejection(
                        RejectionStage.CLIMAX,
                        symbol,
                        direction=direction,
                        asset_class=asset_class,
                        current_range=round(current_range, 5),
                        avg_range=round(avg_range, 5),
                    )
                    return None

                # === REJECTION WICK CONFIRMATION (PHASE 5.11) ===
                if asset_class == "commodities" and last_range > 0:
                    upper_wick = last_high - max(last_open, last_close)
                    wick_ratio = upper_wick / last_range

                    wick_cfg = gates["rejection_wick"]["sell"]
                    wick_threshold = wick_cfg["min_ratio"]
                    if len(data) > 100:
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        if current_price < ema_20:  # Trend is DOWN (with-trend for SELL)
                            wick_threshold = wick_cfg["trend_following_ratio"]

                    if wick_ratio < wick_threshold:
                        logger.warning(
                            f"{symbol}: REJECTED - No bounce confirmation (Upper Wick: {wick_ratio:.2f} < {wick_threshold})"
                        )
                        self._record_rejection(
                            RejectionStage.REJECTION_WICK,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            wick_ratio=round(wick_ratio, 2),
                            threshold=wick_threshold,
                        )
                        return None

                # === SIGNAL CANDLE COLOR MATCH (PHASE 5.12) ===
                # Allow doji / small bullish body (< exception) as neutral; else require red.
                # Default exception 0.0 => reject any bullish candle (strict).
                if asset_class == "commodities" and last_close >= last_open:
                    body_exception = gates["color_match"]["sell_small_body_exception"]
                    body_ratio = abs(last_close - last_open) / last_range if last_range > 0 else 1.0
                    if body_ratio < body_exception:
                        logger.debug(
                            f"{symbol}: ALLOWED - Small bullish body "
                            f"({body_ratio:.2f} < {body_exception}), treating as neutral"
                        )
                    else:
                        logger.warning(
                            f"{symbol}: REJECTED - No bearish confirmation (Candle is Bullish). "
                            "Waiting for red candle."
                        )
                        self._record_rejection(
                            RejectionStage.COLOR_MATCH,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            body_ratio=round(body_ratio, 2),
                        )
                        return None

                # === VOLATILITY-DEPENDENT TREND GATE (PHASE 5.13) ===
                if asset_class == "commodities" and len(data) >= 100:
                    # Calculate volatility
                    ranges = data["high"] - data["low"]
                    avg_range = ranges.tail(14).mean()
                    current_range = data["high"].iloc[-1] - data["low"].iloc[-1]

                    # In very high volatility, block counter-trend SELL (price above
                    # EMA20 by more than ema_buffer_pct). Thresholds are config-driven.
                    vt_cfg = gates["volatility_trend_gate"]["sell"]
                    if current_range > avg_range * vt_cfg["vol_mult"]:
                        # Use Faster EMA (20) for reactive volatility gating
                        ema_20 = data["close"].ewm(span=20, adjust=False).mean().iloc[-1]
                        price_above_ema_pct = (current_price - ema_20) / ema_20 * 100
                        if (
                            current_price > ema_20
                            and price_above_ema_pct > vt_cfg["ema_buffer_pct"]
                        ):
                            logger.warning(
                                f"{symbol}: REJECTED - High volatility trend mismatch "
                                f"({current_range:.1f} > {avg_range*vt_cfg['vol_mult']:.1f}). "
                                "NO counter-trend SELL allowed during spike."
                            )
                            self._record_rejection(
                                RejectionStage.VOLATILITY_TREND_GATE,
                                symbol,
                                direction=direction,
                                asset_class=asset_class,
                                price_above_ema_pct=round(price_above_ema_pct, 2),
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
                        self._record_rejection(
                            RejectionStage.ANTI_CHASE,
                            symbol,
                            direction=direction,
                            asset_class=asset_class,
                            dev_pips=round(entry_dist_from_zone / pip_size, 1),
                            max_pips=max_entry_dev_pips,
                        )
                        return None

                # CHASE PROTECTION / MAX STOP LOSS CHECK
                # Priority: Symbol-specific > Asset-class > Global default
                symbols_cfg = self.config.get("symbols", {})
                symbol_cfg = (
                    symbols_cfg.get(symbol_for_config, {}) if isinstance(symbols_cfg, dict) else {}
                )
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
                    self._record_rejection(
                        RejectionStage.MAX_STOP_LOSS,
                        symbol,
                        direction=direction,
                        asset_class=asset_class,
                        risk_pips=round(current_risk / pip_size, 1),
                        max_pips=max_risk_pips,
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

            # Run enhancement layer analysis with hard-rejection gates
            enhancement_result = await self._run_enhancement_analyzers(
                symbol=symbol,
                direction=direction,
                is_demand=is_demand,
                zone_type_str=zone_type_str,
                timeframe=timeframe,
                asset_class=asset_class,
                opens=opens,
                highs=highs,
                lows=lows,
                closes=closes,
                current_price=current_price,
            )
            if enhancement_result is None:
                return None  # Hard rejection by RSI block or structure block
            layer_scores, layer_details, raw_confidences = enhancement_result

            # Calculate final confluence score using config-driven weights
            (
                final_score,
                weighted_foundation_score,
                weighted_enhancement_score,
            ) = self._calculate_confluence_score(zone, raw_confidences)

            # Apply final quality filters (min confluence, price action req, H1 gate, etc)
            if not self._passes_final_quality_filters(
                symbol=symbol,
                direction=direction,
                asset_class=asset_class,
                final_score=final_score,
                weighted_foundation_score=weighted_foundation_score,
                weighted_enhancement_score=weighted_enhancement_score,
                layer_scores=layer_scores,
                h1_trend_bias=h1_trend_bias,
                data=data,
                current_price=current_price,
                current_range=current_range,
                avg_range=avg_range,
            ):
                return None

            return self._build_strategy_result(
                symbol=symbol,
                zone=zone,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=timeframe,
                final_score=final_score,
                weighted_foundation_score=weighted_foundation_score,
                weighted_enhancement_score=weighted_enhancement_score,
                layer_scores=layer_scores,
                layer_details=layer_details,
                raw_confidences=raw_confidences,
                current_price=current_price,
            )

        except Exception as e:
            logger.error(f"Error creating signal from zone: {e}")
            return None
