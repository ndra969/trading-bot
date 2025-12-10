"""
RSI Analysis Layer

This module provides RSI-specific analysis including:
- Overbought/Oversold detection
- Bullish/Bearish Divergence
- Trend alignment
- Confluence scoring
"""

import logging
from dataclasses import dataclass

from .technical_analyzer import RobustIndicatorCalculator

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class RSISignal:
    symbol: str
    timeframe: str
    rsi_value: float
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    confidence: float
    details: dict


class RSIAnalyzer:
    """
    Analyzes RSI for trade signals and confluence.
    """

    def __init__(self, config: dict):
        self.config = config
        self.calculator = RobustIndicatorCalculator()

        # Default parameters if not in config
        self.period = config.get("rsi", {}).get("period", 14)
        self.overbought = config.get("rsi", {}).get("overbought", 70)
        self.oversold = config.get("rsi", {}).get("oversold", 30)

    async def analyze_rsi_signal(
        self, symbol: str, prices: list[float], timeframe: str, zone_type: str = None
    ) -> RSISignal:
        """
        Analyze RSI signals for a specific symbol/timeframe.

        Args:
            symbol: Symbol name
            prices: List of closing prices
            timeframe: Timeframe string (e.g., 'H1')
            zone_type: Optional 'DEMAND' or 'SUPPLY' to filter signals

        Returns:
            RSISignal object with analysis results
        """
        # Calculate RSI
        indicators = self.calculator.calculate_all(prices)
        rsi_values = indicators.get("rsi", [])

        if not rsi_values:
            return RSISignal(symbol, timeframe, 0, "NEUTRAL", 0, {"error": "No RSI data"})

        current_rsi = rsi_values[-1]

        # Initialize signal
        signal_type = "NEUTRAL"
        confidence = 0.0
        details = {"value": current_rsi, "condition": "NEUTRAL", "divergence": None}

        # 1. Analyze Overbought/Oversold
        if current_rsi <= self.oversold:
            details["condition"] = "OVERSOLD"
            if zone_type == "DEMAND" or zone_type is None:
                signal_type = "BUY"
                confidence += 20  # Strong buy signal

        elif current_rsi >= self.overbought:
            details["condition"] = "OVERBOUGHT"
            if zone_type == "SUPPLY" or zone_type is None:
                signal_type = "SELL"
                confidence += 20  # Strong sell signal

        # 2. Check for rising from oversold / falling from overbought (Reversal)
        if len(rsi_values) >= 3:
            prev_rsi = rsi_values[-2]
            prev2_rsi = rsi_values[-3]

            # Rising from oversold
            if prev_rsi < self.oversold and current_rsi > prev_rsi:
                if zone_type == "DEMAND" or zone_type is None:
                    signal_type = "BUY"
                    confidence += 15
                    details["reversal"] = "Bullish Reversal"

            # Falling from overbought
            elif prev_rsi > self.overbought and current_rsi < prev_rsi:
                if zone_type == "SUPPLY" or zone_type is None:
                    signal_type = "SELL"
                    confidence += 15
                    details["reversal"] = "Bearish Reversal"

        # 3. Analyze Divergence
        divergence_score, divergence_type = self._check_divergences(prices, rsi_values, zone_type)
        if divergence_score > 0:
            confidence += divergence_score
            details["divergence"] = divergence_type
            # Update signal type if divergence is strong and we were neutral
            if signal_type == "NEUTRAL":
                signal_type = "BUY" if "Bullish" in divergence_type else "SELL"

        # 4. Trend Context (RSI > 50 in Uptrend)
        # Simple trend check using RSI level
        if zone_type == "DEMAND" and current_rsi > 50 and current_rsi < 70:
            confidence += 8
            details["trend"] = "Bullish Momentum"
        elif zone_type == "SUPPLY" and current_rsi < 50 and current_rsi > 30:
            confidence += 8
            details["trend"] = "Bearish Momentum"

        return RSISignal(
            symbol=symbol,
            timeframe=timeframe,
            rsi_value=current_rsi,
            signal_type=signal_type,
            confidence=min(confidence, 100),  # Cap at 100
            details=details,
        )

    def _check_divergences(
        self, prices: list[float], rsi_values: list[float], zone_type: str = None
    ) -> (float, str | None):
        """
        Check for RSI divergences.
        Returns: (score, description)
        """
        lookback = 20  # Look for swings in last 20 candles
        if len(prices) < lookback or len(rsi_values) < lookback:
            return 0, None

        # Find swing points
        price_lows = self._find_swing_lows(prices[-lookback:])
        rsi_lows = self._find_swing_lows(rsi_values[-lookback:])

        price_highs = self._find_swing_highs(prices[-lookback:])
        rsi_highs = self._find_swing_highs(rsi_values[-lookback:])

        score = 0
        divergence_type = None

        # Bullish Divergence (Price Lower Low, RSI Higher Low)
        if (
            (zone_type == "DEMAND" or zone_type is None)
            and len(price_lows) >= 2
            and len(rsi_lows) >= 2
        ):
            # Check last 2 swings
            curr_price_low = price_lows[-1]
            prev_price_low = price_lows[-2]

            curr_rsi_low = rsi_lows[-1]
            prev_rsi_low = rsi_lows[-2]

            # Use index to ensure we are comparing roughly same timeframes (allow small drift)
            if abs(curr_price_low["index"] - curr_rsi_low["index"]) <= 3:
                if (
                    curr_price_low["value"] < prev_price_low["value"]
                    and curr_rsi_low["value"] > prev_rsi_low["value"]
                ):
                    score = 25
                    divergence_type = "Bullish Divergence"

        # Bearish Divergence (Price Higher High, RSI Lower High)
        if (
            (zone_type == "SUPPLY" or zone_type is None)
            and len(price_highs) >= 2
            and len(rsi_highs) >= 2
        ):
            curr_price_high = price_highs[-1]
            prev_price_high = price_highs[-2]

            curr_rsi_high = rsi_highs[-1]
            prev_rsi_high = rsi_highs[-2]

            if abs(curr_price_high["index"] - curr_rsi_high["index"]) <= 3:
                if (
                    curr_price_high["value"] > prev_price_high["value"]
                    and curr_rsi_high["value"] < prev_rsi_high["value"]
                ):
                    score = 25
                    divergence_type = "Bearish Divergence"

        return score, divergence_type

    def _find_swing_lows(self, data: list[float], window: int = 3) -> list[dict]:
        """Find local minima (swing lows)."""
        swings = []
        for i in range(window, len(data) - window):
            is_low = True
            for j in range(1, window + 1):
                if data[i] >= data[i - j] or data[i] >= data[i + j]:
                    is_low = False
                    break
            if is_low:
                swings.append({"index": i, "value": data[i]})
        return swings

    def _find_swing_highs(self, data: list[float], window: int = 3) -> list[dict]:
        """Find local maxima (swing highs)."""
        swings = []
        for i in range(window, len(data) - window):
            is_high = True
            for j in range(1, window + 1):
                if data[i] <= data[i - j] or data[i] <= data[i + j]:
                    is_high = False
                    break
            if is_high:
                swings.append({"index": i, "value": data[i]})
        return swings
