"""
Breakout Analysis Layer

This module validates breakouts from key levels (Supply/Demand zones).
It checks for:
- Strong candle close (body size)
- Volume confirmation
- Retest patterns (optional)
"""

import logging
from dataclasses import dataclass

import numpy as np

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class BreakoutSignal:
    symbol: str
    breakout_type: str  # 'BULLISH', 'BEARISH'
    confidence: float
    details: dict


class BreakoutAnalyzer:
    """
    Validates breakouts.
    """

    def __init__(self, config: dict):
        self.config = config
        self.volume_threshold = config.get("breakout", {}).get(
            "volume_threshold", 1.5
        )  # 1.5x avg volume
        self.min_body_ratio = config.get("breakout", {}).get(
            "min_body_ratio", 0.6
        )  # Body > 60% of range

    async def analyze_breakout(
        self,
        symbol: str,
        opens: list[float],
        highs: list[float],
        lows: list[float],
        closes: list[float],
        volumes: list[float],
        level_price: float,
        expected_direction: str,
    ) -> BreakoutSignal | None:
        """
        Analyze if a valid breakout occurred at level_price.

        Args:
            level_price: The price level being broken (e.g. Resistance/Support)
            expected_direction: 'BULLISH' (break above) or 'BEARISH' (break below)
        """
        if len(closes) < 20:
            return None

        # Get latest candle
        curr_open = opens[-1]
        curr_close = closes[-1]
        curr_high = highs[-1]
        curr_low = lows[-1]
        curr_volume = volumes[-1]

        # Previous candle (to check if we were below/above before)
        prev_close = closes[-2]

        confidence = 0.0
        details = {}

        # 1. Check Breakout Condition
        is_breakout = False

        if expected_direction == "BULLISH":
            # Price breaks ABOVE level
            # Condition: Close > Level AND Prev Close < Level (or near)
            if curr_close > level_price and prev_close <= level_price * 1.001:
                is_breakout = True

        elif expected_direction == "BEARISH":
            # Price breaks BELOW level
            if curr_close < level_price and prev_close >= level_price * 0.999:
                is_breakout = True

        if not is_breakout:
            return None

        # 2. Validate Candle Strength (Body Size)
        candle_range = curr_high - curr_low
        body_size = abs(curr_close - curr_open)

        if candle_range == 0:
            return None

        body_ratio = body_size / candle_range

        if body_ratio >= self.min_body_ratio:
            confidence += 40
            details["candle"] = "Strong Body"
        else:
            details["candle"] = "Weak Body"
            # Weak breakout, maybe fakeout
            return None

        # 3. Validate Volume
        # Compare current volume to average of last 20
        avg_volume = np.mean(
            volumes[-21:-1]
        )  # Exclude current? No, compare current to moving average

        if avg_volume > 0:
            vol_ratio = curr_volume / avg_volume
            if vol_ratio >= self.volume_threshold:
                confidence += 40
                details["volume"] = f"High ({vol_ratio:.1f}x avg)"
            else:
                confidence += 10  # Low confidence if volume weak
                details["volume"] = f"Low ({vol_ratio:.1f}x avg)"

        # 4. Momentum Check (Close near High/Low)
        if expected_direction == "BULLISH":
            # Close should be near High (little upper wick)
            upper_wick = curr_high - curr_close
            if upper_wick < (candle_range * 0.2):
                confidence += 20
        else:
            # Close should be near Low (little lower wick)
            lower_wick = curr_close - curr_low
            if lower_wick < (candle_range * 0.2):
                confidence += 20

        return BreakoutSignal(
            symbol=symbol,
            breakout_type=expected_direction,
            confidence=min(confidence, 100),
            details=details,
        )
