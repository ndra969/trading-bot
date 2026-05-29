"""
Price Action Analysis Layer

This module detects comprehensive candlestick patterns including:
- Basic Patterns: Pinbars, Engulfing, Inside Bars, Dojis
- Reversal Patterns: Harami, Morning/Evening Star, Double Top/Bottom
- Structure Patterns: Pullback/Retest, Order Block, Liquidity Sweep
- Continuation Patterns: Outside Bar
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PriceActionSignal:
    symbol: str
    pattern_type: str  # PINBAR, ENGULFING, DOJI, INSIDE_BAR, HARAMI, OUTSIDE_BAR, MORNING_STAR, EVENING_STAR, PULLBACK, ORDER_BLOCK, LIQUIDITY_SWEEP, DOUBLE_TOP, DOUBLE_BOTTOM
    direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    confidence: float
    details: dict


@dataclass
class CandleData:
    """Container for current and previous candle data + history."""

    symbol: str
    # Current candle
    curr_open: float
    curr_high: float
    curr_low: float
    curr_close: float
    # Previous candle
    prev_open: float
    prev_high: float
    prev_low: float
    prev_close: float
    # Derived values
    curr_range: float
    curr_body: float
    body_ratio: float
    upper_wick: float
    lower_wick: float
    is_bullish_candle: bool
    is_prev_bullish: bool
    # Full history (for multi-candle patterns)
    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]


class PriceActionAnalyzer:
    """Analyzes comprehensive price action patterns."""

    DEFAULT_PATTERNS = [
        "PINBAR",
        "ENGULFING",
        "INSIDE_BAR",
        "DOJI",
        "HARAMI",
        "OUTSIDE_BAR",
        "MORNING_STAR",
        "EVENING_STAR",
        "PULLBACK",
        "ORDER_BLOCK",
        "LIQUIDITY_SWEEP",
    ]

    def __init__(self, config: dict):
        self.config = config
        self.enabled_patterns = config.get("price_action", {}).get(
            "enabled_patterns", self.DEFAULT_PATTERNS
        )

    async def analyze_pattern(
        self,
        symbol: str,
        opens: list[float],
        highs: list[float],
        lows: list[float],
        closes: list[float],
        zone_type: str = None,
    ) -> PriceActionSignal | None:
        """
        Analyze candlestick patterns on the latest candle(s).
        Returns the first matching pattern by priority order.
        """
        if len(closes) < 3:
            return None

        candle = self._build_candle_data(symbol, opens, highs, lows, closes)
        if candle is None:
            return None  # Invalid candle (zero range)

        # Pattern detection in priority order
        detectors = [
            self._detect_pinbar,
            self._detect_engulfing,
            self._detect_harami,
            self._detect_inside_bar,
            self._detect_doji,
            self._detect_outside_bar,
            self._detect_morning_evening_star,
            self._detect_pullback,
            self._detect_order_block,
            self._detect_liquidity_sweep,
            self._detect_double_top_bottom,
        ]

        for detector in detectors:
            signal = detector(candle, zone_type)
            if signal is not None:
                return signal

        return None

    def _build_candle_data(
        self,
        symbol: str,
        opens: list[float],
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> CandleData | None:
        """Build CandleData from price history. Returns None for invalid candles."""
        curr_open, curr_high, curr_low, curr_close = opens[-1], highs[-1], lows[-1], closes[-1]
        prev_open, prev_high, prev_low, prev_close = opens[-2], highs[-2], lows[-2], closes[-2]

        curr_range = curr_high - curr_low
        if curr_range == 0:
            return None

        curr_body = abs(curr_close - curr_open)
        return CandleData(
            symbol=symbol,
            curr_open=curr_open,
            curr_high=curr_high,
            curr_low=curr_low,
            curr_close=curr_close,
            prev_open=prev_open,
            prev_high=prev_high,
            prev_low=prev_low,
            prev_close=prev_close,
            curr_range=curr_range,
            curr_body=curr_body,
            body_ratio=curr_body / curr_range,
            upper_wick=curr_high - max(curr_open, curr_close),
            lower_wick=min(curr_open, curr_close) - curr_low,
            is_bullish_candle=curr_close > curr_open,
            is_prev_bullish=prev_close > prev_open,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
        )

    # ========== Pattern Detectors ==========

    def _detect_pinbar(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """1. Pinbar Detection - Long wick, small body."""
        if not (0.1 <= c.body_ratio < 0.35):
            return None

        # Bullish Pinbar (Hammer): long lower wick
        if c.lower_wick > 1.5 * c.upper_wick and c.lower_wick > 1.5 * c.curr_body:
            if zone_type == "DEMAND" or zone_type is None:
                return PriceActionSignal(
                    c.symbol, "PINBAR", "BULLISH", 75.0, {"desc": "Bullish Pinbar/Hammer"}
                )
        # Bearish Pinbar (Shooting Star): long upper wick
        elif c.upper_wick > 1.5 * c.lower_wick and c.upper_wick > 1.5 * c.curr_body:
            if zone_type == "SUPPLY" or zone_type is None:
                return PriceActionSignal(
                    c.symbol, "PINBAR", "BEARISH", 75.0, {"desc": "Bearish Pinbar/Shooting Star"}
                )
        return None

    def _detect_engulfing(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """2. Engulfing Detection - Current candle fully engulfs previous."""
        range_engulfs = c.curr_high > c.prev_high and c.curr_low < c.prev_low

        if c.is_bullish_candle and not c.is_prev_bullish:
            body_engulfs = c.curr_close > c.prev_open and c.curr_open < c.prev_close
            if body_engulfs and range_engulfs:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "ENGULFING", "BULLISH", 85.0, {"desc": "Bullish Engulfing"}
                    )
        elif not c.is_bullish_candle and c.is_prev_bullish:
            body_engulfs = c.curr_close < c.prev_open and c.curr_open > c.prev_close
            if body_engulfs and range_engulfs:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "ENGULFING", "BEARISH", 85.0, {"desc": "Bearish Engulfing"}
                    )
        return None

    def _detect_harami(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """3. Harami Detection - Small candle inside large candle (reversal)."""
        if "HARAMI" not in self.enabled_patterns:
            return None

        prev_range = c.prev_high - c.prev_low
        if prev_range <= 0:
            return None
        if not (c.curr_high < c.prev_high and c.curr_low > c.prev_low):
            return None
        if c.curr_range >= 0.5 * prev_range:  # Current must be significantly smaller
            return None

        # Bullish Harami: Large red candle followed by small green candle
        if not c.is_prev_bullish and c.is_bullish_candle:
            if zone_type == "DEMAND" or zone_type is None:
                return PriceActionSignal(
                    c.symbol, "HARAMI", "BULLISH", 70.0, {"desc": "Bullish Harami"}
                )
        # Bearish Harami: Large green candle followed by small red candle
        elif c.is_prev_bullish and not c.is_bullish_candle:
            if zone_type == "SUPPLY" or zone_type is None:
                return PriceActionSignal(
                    c.symbol, "HARAMI", "BEARISH", 70.0, {"desc": "Bearish Harami"}
                )
        return None

    def _detect_inside_bar(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """4. Inside Bar Detection - Consolidation/indecision."""
        if "INSIDE_BAR" not in self.enabled_patterns:
            return None
        if c.curr_high < c.prev_high and c.curr_low > c.prev_low:
            return PriceActionSignal(
                c.symbol, "INSIDE_BAR", "NEUTRAL", 50.0, {"desc": "Inside Bar"}
            )
        return None

    def _detect_doji(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """5. Doji Detection - Indecision (very small body)."""
        if "DOJI" not in self.enabled_patterns:
            return None
        if c.body_ratio < 0.1:
            return PriceActionSignal(c.symbol, "DOJI", "NEUTRAL", 60.0, {"desc": "Doji"})
        return None

    def _detect_outside_bar(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """6. Outside Bar Detection - Expansion/volatility."""
        if "OUTSIDE_BAR" not in self.enabled_patterns:
            return None
        if not (c.curr_high > c.prev_high and c.curr_low < c.prev_low):
            return None

        direction = "BULLISH" if c.is_bullish_candle else "BEARISH"
        confidence = (
            70.0
            if (c.curr_close > c.prev_close and direction == "BULLISH")
            or (c.curr_close < c.prev_close and direction == "BEARISH")
            else 50.0
        )

        if zone_type == "DEMAND" and direction == "BULLISH":
            return PriceActionSignal(
                c.symbol, "OUTSIDE_BAR", "BULLISH", confidence, {"desc": "Bullish Outside Bar"}
            )
        elif zone_type == "SUPPLY" and direction == "BEARISH":
            return PriceActionSignal(
                c.symbol, "OUTSIDE_BAR", "BEARISH", confidence, {"desc": "Bearish Outside Bar"}
            )
        elif zone_type is None:
            return PriceActionSignal(
                c.symbol, "OUTSIDE_BAR", direction, confidence, {"desc": f"{direction} Outside Bar"}
            )
        return None

    def _detect_morning_evening_star(
        self, c: CandleData, zone_type: str | None
    ) -> PriceActionSignal | None:
        """7. Morning/Evening Star Detection - 3-candle reversal."""
        if len(c.closes) < 3:
            return None
        morning_enabled = "MORNING_STAR" in self.enabled_patterns
        evening_enabled = "EVENING_STAR" in self.enabled_patterns
        if not (morning_enabled or evening_enabled):
            return None

        prev2_open = c.opens[-3]
        prev2_high = c.highs[-3]
        prev2_low = c.lows[-3]
        prev2_close = c.closes[-3]
        prev2_range = prev2_high - prev2_low
        if prev2_range <= 0:
            return None

        prev2_body = abs(prev2_close - prev2_open)
        prev_body = abs(c.prev_close - c.prev_open)

        # Morning Star: Large red → Small body → Large green
        if morning_enabled:
            if (
                prev2_close < prev2_open
                and prev_body < 0.3 * prev2_body
                and c.curr_close > c.curr_open
                and c.curr_close > (prev2_open + prev2_close) / 2
            ):
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "MORNING_STAR", "BULLISH", 80.0, {"desc": "Morning Star"}
                    )

        # Evening Star: Large green → Small body → Large red
        if evening_enabled:
            if (
                prev2_close > prev2_open
                and prev_body < 0.3 * prev2_body
                and c.curr_close < c.curr_open
                and c.curr_close < (prev2_open + prev2_close) / 2
            ):
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "EVENING_STAR", "BEARISH", 80.0, {"desc": "Evening Star"}
                    )
        return None

    def _detect_pullback(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """8. Pullback/Retest Detection - Price returns to level."""
        if "PULLBACK" not in self.enabled_patterns or len(c.closes) < 5:
            return None

        # Skip if inside bar or harami pattern (to avoid false detection)
        is_inside_bar = c.curr_high < c.prev_high and c.curr_low > c.prev_low
        prev_range = c.prev_high - c.prev_low
        is_harami = False
        if prev_range > 0 and is_inside_bar:
            is_harami = c.curr_range < 0.5 * prev_range
        if is_inside_bar or is_harami:
            return None

        recent_high = max(c.highs[-5:])
        recent_low = min(c.lows[-5:])
        recent_range = recent_high - recent_low
        if recent_range <= 0:
            return None

        if zone_type == "DEMAND":
            return self._detect_demand_pullback(c, recent_low, recent_range)
        elif zone_type == "SUPPLY":
            return self._detect_supply_pullback(c, recent_high, recent_range)
        return None

    def _detect_demand_pullback(
        self, c: CandleData, recent_low: float, recent_range: float
    ) -> PriceActionSignal | None:
        """Pullback to DEMAND zone (support) = BULLISH signal."""
        prev_max_close = max(c.closes[-5:-1])
        is_near_support = c.curr_low <= recent_low + 0.3 * recent_range

        if c.curr_close >= prev_max_close or not is_near_support:
            return None

        # Current bullish or showing bounce (close in upper 70% of range)
        if c.is_bullish_candle or c.curr_close > c.curr_low + 0.3 * c.curr_range:
            return PriceActionSignal(
                c.symbol, "PULLBACK", "BULLISH", 65.0, {"desc": "Pullback to Demand Zone"}
            )
        return None

    def _detect_supply_pullback(
        self, c: CandleData, recent_high: float, recent_range: float
    ) -> PriceActionSignal | None:
        """Pullback to SUPPLY zone (resistance) = BEARISH signal."""
        prev_min_close = min(c.closes[-5:-1])
        is_near_resistance = c.curr_high >= recent_high - 0.3 * recent_range

        if c.curr_close <= prev_min_close or not is_near_resistance:
            return None

        # Bearish candle = clear rejection
        if not c.is_bullish_candle:
            return PriceActionSignal(
                c.symbol, "PULLBACK", "BEARISH", 65.0, {"desc": "Pullback to Supply Zone"}
            )

        # Bullish candle - only accept with STRONG rejection signs
        upper_wick_ratio = c.upper_wick / c.curr_range
        close_position = (c.curr_close - c.curr_low) / c.curr_range
        body_ratio = c.curr_body / c.curr_range

        strong_rejection = upper_wick_ratio > 0.5 and close_position < 0.4 and body_ratio < 0.5
        if strong_rejection:
            return PriceActionSignal(
                c.symbol,
                "PULLBACK",
                "BEARISH",
                60.0,
                {"desc": "Pullback to Supply Zone (with rejection wick)"},
            )
        return None

    def _detect_order_block(self, c: CandleData, zone_type: str | None) -> PriceActionSignal | None:
        """9. Order Block Detection - Strong candle before significant move."""
        if "ORDER_BLOCK" not in self.enabled_patterns or len(c.closes) < 4:
            return None

        prev_body = abs(c.prev_close - c.prev_open)
        prev_range = c.prev_high - c.prev_low
        if prev_range <= 0:
            return None

        prev_body_ratio = prev_body / prev_range

        # Strong bullish candle followed by continuation
        if c.is_prev_bullish and prev_body_ratio > 0.7:
            if c.curr_close > c.prev_close:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "ORDER_BLOCK", "BULLISH", 75.0, {"desc": "Bullish Order Block"}
                    )

        # Strong bearish candle followed by continuation
        elif not c.is_prev_bullish and prev_body_ratio > 0.7:
            if c.curr_close < c.prev_close:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        c.symbol, "ORDER_BLOCK", "BEARISH", 75.0, {"desc": "Bearish Order Block"}
                    )
        return None

    def _detect_liquidity_sweep(
        self, c: CandleData, zone_type: str | None
    ) -> PriceActionSignal | None:
        """10. Liquidity Sweep Detection - Price breaks level then reverses."""
        if "LIQUIDITY_SWEEP" not in self.enabled_patterns or len(c.closes) < 4:
            return None

        prev_swing_high = max(c.highs[-4:-1])
        prev_swing_low = min(c.lows[-4:-1])

        # Bullish sweep: broke below low then reversed up
        if c.curr_low < prev_swing_low and c.curr_close > prev_swing_low:
            if zone_type == "DEMAND" or zone_type is None:
                return PriceActionSignal(
                    c.symbol,
                    "LIQUIDITY_SWEEP",
                    "BULLISH",
                    80.0,
                    {"desc": "Bullish Liquidity Sweep"},
                )
        # Bearish sweep: broke above high then reversed down
        elif c.curr_high > prev_swing_high and c.curr_close < prev_swing_high:
            if zone_type == "SUPPLY" or zone_type is None:
                return PriceActionSignal(
                    c.symbol,
                    "LIQUIDITY_SWEEP",
                    "BEARISH",
                    80.0,
                    {"desc": "Bearish Liquidity Sweep"},
                )
        return None

    def _detect_double_top_bottom(
        self, c: CandleData, zone_type: str | None
    ) -> PriceActionSignal | None:
        """11. Double Top/Bottom Detection - Reversal pattern."""
        if len(c.closes) < 10:
            return None
        top_enabled = "DOUBLE_TOP" in self.enabled_patterns
        bottom_enabled = "DOUBLE_BOTTOM" in self.enabled_patterns
        if not (top_enabled or bottom_enabled):
            return None

        lookback = min(20, len(c.closes))
        recent_highs = [c.highs[i] for i in range(len(c.highs) - lookback, len(c.highs) - 1)]
        recent_lows = [c.lows[i] for i in range(len(c.lows) - lookback, len(c.lows) - 1)]
        price_tolerance = 0.002  # 0.2%

        # Double Top
        if top_enabled and len(recent_highs) >= 2:
            sorted_highs = sorted(recent_highs, reverse=True)
            top1, top2 = sorted_highs[0], sorted_highs[1]
            if abs(top1 - top2) / top1 < price_tolerance:
                if c.curr_close < top1 * 0.995:
                    if zone_type == "SUPPLY" or zone_type is None:
                        return PriceActionSignal(
                            c.symbol, "DOUBLE_TOP", "BEARISH", 75.0, {"desc": "Double Top Reversal"}
                        )

        # Double Bottom
        if bottom_enabled and len(recent_lows) >= 2:
            sorted_lows = sorted(recent_lows)
            bottom1, bottom2 = sorted_lows[0], sorted_lows[1]
            if abs(bottom1 - bottom2) / bottom1 < price_tolerance:
                if c.curr_close > bottom1 * 1.005:
                    if zone_type == "DEMAND" or zone_type is None:
                        return PriceActionSignal(
                            c.symbol,
                            "DOUBLE_BOTTOM",
                            "BULLISH",
                            75.0,
                            {"desc": "Double Bottom Reversal"},
                        )
        return None
