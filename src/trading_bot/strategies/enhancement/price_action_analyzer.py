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

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class PriceActionSignal:
    symbol: str
    pattern_type: str  # Pattern types: PINBAR, ENGULFING, DOJI, INSIDE_BAR, HARAMI, OUTSIDE_BAR, MORNING_STAR, EVENING_STAR, PULLBACK, ORDER_BLOCK, LIQUIDITY_SWEEP, DOUBLE_TOP, DOUBLE_BOTTOM
    direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    confidence: float
    details: dict


class PriceActionAnalyzer:
    """
    Analyzes comprehensive price action patterns.
    """

    def __init__(self, config: dict):
        self.config = config
        self.enabled_patterns = config.get("price_action", {}).get(
            "enabled_patterns",
            [
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
            ],
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
        Supports multiple pattern types including reversal, continuation, and structure patterns.
        """
        if len(closes) < 3:
            return None

        # Get latest candle data
        curr_open = opens[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]
        curr_close = closes[-1]

        # Previous candle data
        prev_open = opens[-2]
        prev_high = highs[-2]
        prev_low = lows[-2]
        prev_close = closes[-2]

        # Basic calculations
        curr_range = curr_high - curr_low
        curr_body = abs(curr_close - curr_open)
        # prev_range = prev_high - prev_low  # Not used
        # prev_body = abs(prev_close - prev_open)  # Not used

        if curr_range == 0:
            return None  # Invalid candle

        # 1. Pinbar Detection
        # Long wick, small body
        # Bullish Pinbar: Long lower wick, body in upper third
        # Bearish Pinbar: Long upper wick, body in lower third

        body_ratio = curr_body / curr_range
        upper_wick = curr_high - max(curr_open, curr_close)
        lower_wick = min(curr_open, curr_close) - curr_low

        # Pinbar requires small body (but not too small - doji is < 0.1)
        # Use range 0.1 to 0.35 to avoid overlap with doji
        is_pinbar = 0.1 <= body_ratio < 0.35

        if is_pinbar:
            # Bullish Pinbar (Hammer)
            # More flexible: lower wick should be significantly larger than upper wick and body
            # Changed from 2x to 1.5x for more lenient detection
            if lower_wick > 1.5 * upper_wick and lower_wick > 1.5 * curr_body:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "PINBAR", "BULLISH", 75.0, {"desc": "Bullish Pinbar/Hammer"}
                    )

            # Bearish Pinbar (Shooting Star)
            # More flexible: upper wick should be significantly larger than lower wick and body
            # Changed from 2x to 1.5x for more lenient detection
            elif upper_wick > 1.5 * lower_wick and upper_wick > 1.5 * curr_body:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "PINBAR", "BEARISH", 75.0, {"desc": "Bearish Pinbar/Shooting Star"}
                    )

        # 2. Engulfing Detection
        # Current candle completely engulfs previous candle (both body AND range)
        # Bullish: Prev Red, Curr Green, Curr High > Prev High, Curr Low < Prev Low, Curr body engulfs prev body
        # Bearish: Prev Green, Curr Red, Curr High > Prev High, Curr Low < Prev Low, Curr body engulfs prev body

        is_bullish_candle = curr_close > curr_open
        is_prev_bullish = prev_close > prev_open

        # Check if current candle engulfs previous candle (range engulfing)
        range_engulfs = curr_high > prev_high and curr_low < prev_low

        if is_bullish_candle and not is_prev_bullish:
            # Bullish Engulfing
            # Current green candle must engulf previous red candle
            # Body engulfing: curr_close > prev_open AND curr_open < prev_close
            # Range engulfing: curr_high > prev_high AND curr_low < prev_low
            body_engulfs = curr_close > prev_open and curr_open < prev_close
            if body_engulfs and range_engulfs:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "ENGULFING", "BULLISH", 85.0, {"desc": "Bullish Engulfing"}
                    )

        elif not is_bullish_candle and is_prev_bullish:
            # Bearish Engulfing
            # Current red candle must engulf previous green candle
            # Body engulfing: curr_close < prev_open AND curr_open > prev_close
            # Range engulfing: curr_high > prev_high AND curr_low < prev_low
            body_engulfs = curr_close < prev_open and curr_open > prev_close
            if body_engulfs and range_engulfs:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "ENGULFING", "BEARISH", 85.0, {"desc": "Bearish Engulfing"}
                    )

        # 3. Harami Detection (Reversal Pattern) - Check BEFORE Inside Bar (more specific)
        if "HARAMI" in self.enabled_patterns and len(closes) >= 2:
            prev_range = prev_high - prev_low
            if prev_range > 0:
                # Current candle is completely inside previous candle
                if curr_high < prev_high and curr_low > prev_low:
                    # Harami: small candle inside large candle (potential reversal)
                    curr_range = curr_high - curr_low
                    if curr_range < 0.5 * prev_range:  # Current candle is significantly smaller
                        is_prev_bullish = prev_close > prev_open
                        is_curr_bullish = curr_close > curr_open

                        # Bullish Harami: Large red candle followed by small green candle
                        if not is_prev_bullish and is_curr_bullish:
                            if zone_type == "DEMAND" or zone_type is None:
                                return PriceActionSignal(
                                    symbol, "HARAMI", "BULLISH", 70.0, {"desc": "Bullish Harami"}
                                )

                        # Bearish Harami: Large green candle followed by small red candle
                        elif is_prev_bullish and not is_curr_bullish:
                            if zone_type == "SUPPLY" or zone_type is None:
                                return PriceActionSignal(
                                    symbol, "HARAMI", "BEARISH", 70.0, {"desc": "Bearish Harami"}
                                )

        # 4. Inside Bar Detection (Consolidation/Indecision) - Generic inside bar
        if "INSIDE_BAR" in self.enabled_patterns:
            if curr_high < prev_high and curr_low > prev_low:
                return PriceActionSignal(
                    symbol, "INSIDE_BAR", "NEUTRAL", 50.0, {"desc": "Inside Bar"}
                )

        # 5. Doji Detection (Indecision)
        if "DOJI" in self.enabled_patterns:
            if body_ratio < 0.1:
                return PriceActionSignal(symbol, "DOJI", "NEUTRAL", 60.0, {"desc": "Doji"})

        # 6. Outside Bar Detection (Expansion/Volatility)
        if "OUTSIDE_BAR" in self.enabled_patterns:
            if curr_high > prev_high and curr_low < prev_low:
                # Outside bar that engulfs previous candle
                direction = "BULLISH" if curr_close > curr_open else "BEARISH"
                confidence = (
                    70.0
                    if (curr_close > prev_close and direction == "BULLISH")
                    or (curr_close < prev_close and direction == "BEARISH")
                    else 50.0
                )
                if zone_type == "DEMAND" and direction == "BULLISH":
                    return PriceActionSignal(
                        symbol,
                        "OUTSIDE_BAR",
                        "BULLISH",
                        confidence,
                        {"desc": "Bullish Outside Bar"},
                    )
                elif zone_type == "SUPPLY" and direction == "BEARISH":
                    return PriceActionSignal(
                        symbol,
                        "OUTSIDE_BAR",
                        "BEARISH",
                        confidence,
                        {"desc": "Bearish Outside Bar"},
                    )
                elif zone_type is None:
                    return PriceActionSignal(
                        symbol,
                        "OUTSIDE_BAR",
                        direction,
                        confidence,
                        {"desc": f"{direction} Outside Bar"},
                    )

        # 7. Morning Star / Evening Star Detection (3-candle reversal pattern)
        if len(closes) >= 3 and (
            "MORNING_STAR" in self.enabled_patterns or "EVENING_STAR" in self.enabled_patterns
        ):
            prev2_open = opens[-3]
            prev2_high = highs[-3]
            prev2_low = lows[-3]
            prev2_close = closes[-3]

            prev2_range = prev2_high - prev2_low
            if prev2_range > 0:
                prev2_body = abs(prev2_close - prev2_open)
                curr_body = abs(curr_close - curr_open)
                prev_body = abs(prev_close - prev_open)

                # Morning Star: Large red → Small body (gap down) → Large green
                if "MORNING_STAR" in self.enabled_patterns:
                    if (
                        prev2_close < prev2_open
                        and prev_body < 0.3 * prev2_body  # First candle is red
                        and curr_close > curr_open  # Middle candle is small
                        and curr_close > (prev2_open + prev2_close) / 2  # Third candle is green
                    ):  # Third candle closes above midpoint of first
                        if zone_type == "DEMAND" or zone_type is None:
                            return PriceActionSignal(
                                symbol, "MORNING_STAR", "BULLISH", 80.0, {"desc": "Morning Star"}
                            )

                # Evening Star: Large green → Small body (gap up) → Large red
                if "EVENING_STAR" in self.enabled_patterns:
                    if (
                        prev2_close > prev2_open
                        and prev_body < 0.3 * prev2_body  # First candle is green
                        and curr_close < curr_open  # Middle candle is small
                        and curr_close < (prev2_open + prev2_close) / 2  # Third candle is red
                    ):  # Third candle closes below midpoint of first
                        if zone_type == "SUPPLY" or zone_type is None:
                            return PriceActionSignal(
                                symbol, "EVENING_STAR", "BEARISH", 80.0, {"desc": "Evening Star"}
                            )

        # 8. Pullback/Retest Detection (Price returns to level after breakout)
        # Check AFTER Harami but BEFORE Inside Bar to avoid false detection
        if "PULLBACK" in self.enabled_patterns and len(closes) >= 5:
            # Look for price that broke a level and is now retesting it
            # Simplified: Check if price made a move then pulled back to previous level
            # Only detect if NOT an inside bar or harami pattern (to avoid confusion)
            is_inside_bar = curr_high < prev_high and curr_low > prev_low
            prev_range = prev_high - prev_low
            is_harami = False
            if prev_range > 0 and is_inside_bar:
                curr_range = curr_high - curr_low
                is_harami = curr_range < 0.5 * prev_range  # Harami is small inside large

            if not is_inside_bar and not is_harami:  # Not inside bar AND not harami
                recent_high = max(highs[-5:])
                recent_low = min(lows[-5:])
                recent_range = recent_high - recent_low

                if recent_range > 0:
                    # Check for pullback to support (demand zone)
                    if zone_type == "DEMAND":
                        # Pullback to DEMAND zone (support) = BULLISH signal
                        # Price was higher, now retesting support (demand zone)
                        # After pullback, price should bounce UP (BULLISH)
                        prev_max_close = max(closes[-5:-1])
                        # Condition: Price was higher (prev_max_close), now near support
                        # AND current candle shows potential bounce (close > open or small body)
                        is_bullish_candle = curr_close > curr_open
                        is_near_support = curr_low <= recent_low + 0.3 * recent_range

                        if curr_close < prev_max_close and is_near_support:
                            # If current candle is bullish or showing bounce, it's BULLISH pullback
                            if is_bullish_candle or curr_close > curr_low + 0.3 * (
                                curr_high - curr_low
                            ):
                                return PriceActionSignal(
                                    symbol,
                                    "PULLBACK",
                                    "BULLISH",
                                    65.0,
                                    {"desc": "Pullback to Demand Zone"},
                                )
                            # If still bearish but near support, might be completing pullback
                            # Don't return BEARISH, just return None (let other patterns catch it)

                    # Check for pullback to resistance (supply zone)
                    elif zone_type == "SUPPLY":
                        # Pullback to SUPPLY zone (resistance) = BEARISH signal
                        # Price was lower, now retesting resistance (supply zone)
                        # After pullback, price should bounce DOWN (BEARISH)
                        prev_min_close = min(closes[-5:-1])
                        # Condition: Price was lower (prev_min_close), now near resistance
                        # AND current candle shows potential rejection (close < open or rejection wick)
                        is_bearish_candle = curr_close < curr_open
                        is_near_resistance = curr_high >= recent_high - 0.3 * recent_range
                        curr_range = curr_high - curr_low

                        if curr_close > prev_min_close and is_near_resistance:
                            # CRITICAL: For BEARISH pullback at SUPPLY zone, we MUST have clear rejection
                            # Cannot detect BEARISH pullback if candle is still bullish (green) without rejection
                            upper_wick = curr_high - max(curr_open, curr_close)
                            upper_wick_ratio = upper_wick / curr_range if curr_range > 0 else 0
                            close_position = (
                                (curr_close - curr_low) / curr_range if curr_range > 0 else 0.5
                            )
                            body_ratio = (
                                abs(curr_close - curr_open) / curr_range if curr_range > 0 else 0
                            )

                            # STRICT REJECTION REQUIREMENTS for BEARISH pullback:
                            # 1. Bearish candle (close < open) - REQUIRED for strong BEARISH pullback
                            # 2. OR if bullish candle, MUST have:
                            #    - Upper wick > 50% of range (strong rejection from high)
                            #    - AND close in lower 40% of range (price rejected down)
                            #    - AND body < 50% of range (not a strong bullish candle)

                            if is_bearish_candle:
                                # Bearish candle = clear rejection, valid BEARISH pullback
                                return PriceActionSignal(
                                    symbol,
                                    "PULLBACK",
                                    "BEARISH",
                                    65.0,
                                    {"desc": "Pullback to Supply Zone"},
                                )
                            elif is_bullish_candle := curr_close > curr_open:
                                # Bullish candle - only accept if STRONG rejection signs
                                # Must have: large upper wick (>50%) AND close rejected down (<40% of range) AND small body
                                strong_rejection = (
                                    upper_wick_ratio > 0.5
                                    and close_position  # Large upper wick (rejected from high)
                                    < 0.4
                                    and body_ratio  # Close in lower 40% (rejected down)
                                    < 0.5  # Not a strong bullish body
                                )
                                if strong_rejection:
                                    return PriceActionSignal(
                                        symbol,
                                        "PULLBACK",
                                        "BEARISH",
                                        60.0,
                                        {"desc": "Pullback to Supply Zone (with rejection wick)"},
                                    )
                                # If bullish candle without strong rejection, don't return BEARISH pullback
                                # This prevents false BEARISH signals when price is still rising

                            # If no clear rejection, return None (don't detect BEARISH pullback)

        # 9. Order Block Detection (Last candle before structure break)
        if "ORDER_BLOCK" in self.enabled_patterns and len(closes) >= 4:
            # Order block: Strong candle before a significant move
            # Check if previous candle was strong and current candle confirms direction
            prev_body = abs(prev_close - prev_open)
            prev_range = prev_high - prev_low

            if prev_range > 0:
                prev_body_ratio = prev_body / prev_range

                # Strong bullish candle followed by continuation
                if prev_close > prev_open and prev_body_ratio > 0.7:  # Strong bullish body
                    if curr_close > prev_close:  # Continuation up
                        if zone_type == "DEMAND" or zone_type is None:
                            return PriceActionSignal(
                                symbol,
                                "ORDER_BLOCK",
                                "BULLISH",
                                75.0,
                                {"desc": "Bullish Order Block"},
                            )

                # Strong bearish candle followed by continuation
                elif prev_close < prev_open and prev_body_ratio > 0.7:  # Strong bearish body
                    if curr_close < prev_close:  # Continuation down
                        if zone_type == "SUPPLY" or zone_type is None:
                            return PriceActionSignal(
                                symbol,
                                "ORDER_BLOCK",
                                "BEARISH",
                                75.0,
                                {"desc": "Bearish Order Block"},
                            )

        # 10. Liquidity Sweep Detection (Price breaks level then reverses)
        if "LIQUIDITY_SWEEP" in self.enabled_patterns and len(closes) >= 4:
            # Liquidity sweep: Price breaks previous high/low then reverses
            prev_swing_high = max(highs[-4:-1])
            prev_swing_low = min(lows[-4:-1])

            # Bullish liquidity sweep: Price broke below previous low then reversed up
            if curr_low < prev_swing_low and curr_close > prev_swing_low:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        symbol,
                        "LIQUIDITY_SWEEP",
                        "BULLISH",
                        80.0,
                        {"desc": "Bullish Liquidity Sweep"},
                    )

            # Bearish liquidity sweep: Price broke above previous high then reversed down
            elif curr_high > prev_swing_high and curr_close < prev_swing_high:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        symbol,
                        "LIQUIDITY_SWEEP",
                        "BEARISH",
                        80.0,
                        {"desc": "Bearish Liquidity Sweep"},
                    )

        # 11. Double Top / Double Bottom Detection (Reversal pattern)
        if len(closes) >= 10 and (
            "DOUBLE_TOP" in self.enabled_patterns or "DOUBLE_BOTTOM" in self.enabled_patterns
        ):
            # Look for two similar highs (double top) or lows (double bottom)
            lookback = min(20, len(closes))
            recent_highs = [highs[i] for i in range(len(highs) - lookback, len(highs) - 1)]
            recent_lows = [lows[i] for i in range(len(lows) - lookback, len(lows) - 1)]

            if len(recent_highs) >= 2 and "DOUBLE_TOP" in self.enabled_patterns:
                # Find two similar highs
                sorted_highs = sorted(recent_highs, reverse=True)
                if len(sorted_highs) >= 2:
                    top1 = sorted_highs[0]
                    top2 = sorted_highs[1]
                    price_tolerance = 0.002  # 0.2% tolerance

                    if abs(top1 - top2) / top1 < price_tolerance:
                        # Double top found, current price should be declining
                        if curr_close < top1 * 0.995:  # Price declined from top
                            if zone_type == "SUPPLY" or zone_type is None:
                                return PriceActionSignal(
                                    symbol,
                                    "DOUBLE_TOP",
                                    "BEARISH",
                                    75.0,
                                    {"desc": "Double Top Reversal"},
                                )

            if len(recent_lows) >= 2 and "DOUBLE_BOTTOM" in self.enabled_patterns:
                # Find two similar lows
                sorted_lows = sorted(recent_lows)
                if len(sorted_lows) >= 2:
                    bottom1 = sorted_lows[0]
                    bottom2 = sorted_lows[1]
                    price_tolerance = 0.002  # 0.2% tolerance

                    if abs(bottom1 - bottom2) / bottom1 < price_tolerance:
                        # Double bottom found, current price should be rising
                        if curr_close > bottom1 * 1.005:  # Price rose from bottom
                            if zone_type == "DEMAND" or zone_type is None:
                                return PriceActionSignal(
                                    symbol,
                                    "DOUBLE_BOTTOM",
                                    "BULLISH",
                                    75.0,
                                    {"desc": "Double Bottom Reversal"},
                                )

        return None
