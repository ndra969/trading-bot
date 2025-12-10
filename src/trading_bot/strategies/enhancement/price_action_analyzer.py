"""
Price Action Analysis Layer

This module detects candlestick patterns such as Pinbars, Engulfing,
Inside Bars, and Dojis to confirm entries within Supply/Demand zones.
"""

import logging
from dataclasses import dataclass

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class PriceActionSignal:
    symbol: str
    pattern_type: str  # 'PINBAR', 'ENGULFING', 'DOJI', 'INSIDE_BAR'
    direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    confidence: float
    details: dict


class PriceActionAnalyzer:
    """
    Analyzes price action patterns.
    """

    def __init__(self, config: dict):
        self.config = config

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
        prev_range = prev_high - prev_low
        prev_body = abs(prev_close - prev_open)

        if curr_range == 0:
            return None  # Invalid candle

        signal = None

        # 1. Pinbar Detection
        # Long wick, small body
        # Bullish Pinbar: Long lower wick, body in upper third
        # Bearish Pinbar: Long upper wick, body in lower third

        body_ratio = curr_body / curr_range
        upper_wick = curr_high - max(curr_open, curr_close)
        lower_wick = min(curr_open, curr_close) - curr_low

        is_pinbar = body_ratio < 0.3  # Small body

        if is_pinbar:
            # Bullish Pinbar (Hammer)
            if lower_wick > 2 * upper_wick and lower_wick > 2 * curr_body:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "PINBAR", "BULLISH", 75.0, {"desc": "Bullish Pinbar/Hammer"}
                    )

            # Bearish Pinbar (Shooting Star)
            elif upper_wick > 2 * lower_wick and upper_wick > 2 * curr_body:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "PINBAR", "BEARISH", 75.0, {"desc": "Bearish Pinbar/Shooting Star"}
                    )

        # 2. Engulfing Detection
        # Current body engulfs previous body
        # Bullish: Prev Red, Curr Green, Curr Open < Prev Close, Curr Close > Prev Open
        # Bearish: Prev Green, Curr Red, Curr Open > Prev Close, Curr Close < Prev Open

        is_bullish_candle = curr_close > curr_open
        is_prev_bullish = prev_close > prev_open

        if is_bullish_candle and not is_prev_bullish:
            # Bullish Engulfing
            if curr_close > prev_open and curr_open < prev_close:
                if zone_type == "DEMAND" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "ENGULFING", "BULLISH", 85.0, {"desc": "Bullish Engulfing"}
                    )

        elif not is_bullish_candle and is_prev_bullish:
            # Bearish Engulfing
            if curr_close < prev_open and curr_open > prev_close:
                if zone_type == "SUPPLY" or zone_type is None:
                    return PriceActionSignal(
                        symbol, "ENGULFING", "BEARISH", 85.0, {"desc": "Bearish Engulfing"}
                    )

        # 3. Inside Bar Detection (Consolidation/Indecision)
        if curr_high < prev_high and curr_low > prev_low:
            return PriceActionSignal(symbol, "INSIDE_BAR", "NEUTRAL", 50.0, {"desc": "Inside Bar"})

        # 4. Doji Detection (Indecision)
        if body_ratio < 0.1:
            return PriceActionSignal(symbol, "DOJI", "NEUTRAL", 60.0, {"desc": "Doji"})

        return None
