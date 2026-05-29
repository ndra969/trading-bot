"""
Moving Average Analysis Layer

This module provides Moving Average analysis including:
- Trend identification (EMA 200, EMA 50, EMA 21)
- Crossover signals (Golden Cross, Death Cross)
- Trend alignment scoring
"""

import logging
from dataclasses import dataclass

from .technical_analyzer import RobustIndicatorCalculator

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class MASignal:
    symbol: str
    timeframe: str
    trend_direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    signal_type: str  # 'BUY', 'SELL', 'NEUTRAL'
    confidence: float
    details: dict


class MovingAverageAnalyzer:
    """
    Analyzes Moving Averages for trend and trade signals.
    """

    def __init__(self, config: dict):
        self.config = config
        self.calculator = RobustIndicatorCalculator()

    async def analyze_ma_signal(
        self, symbol: str, prices: list[float], timeframe: str, zone_type: str = None
    ) -> MASignal:
        """
        Analyze MA signals for a specific symbol/timeframe.

        Args:
            symbol: Symbol name
            prices: List of closing prices
            timeframe: Timeframe string
            zone_type: Optional 'DEMAND' or 'SUPPLY'

        Returns:
            MASignal object with analysis results
        """
        indicators = self.calculator.calculate_all(prices)

        # Extract MA values
        ema_9 = indicators.get("ema_9", [])
        ema_21 = indicators.get("ema_21", [])
        ema_50 = indicators.get("ema_50", [])
        sma_200 = indicators.get("sma_200", [])

        if not ema_50 or not ema_21:
            return MASignal(
                symbol, timeframe, "UNKNOWN", "NEUTRAL", 0, {"error": "Insufficient MA data"}
            )

        current_price = prices[-1]
        curr_ema21 = ema_21[-1]
        curr_ema50 = ema_50[-1]
        curr_sma200 = sma_200[-1] if sma_200 else None

        confidence = 0.0
        details = {}
        trend_direction = "NEUTRAL"
        signal_type = "NEUTRAL"

        # 1. Trend Identification
        if curr_sma200:
            if current_price > curr_sma200:
                trend_direction = "BULLISH"
                details["major_trend"] = "Bullish (> SMA200)"
            elif current_price < curr_sma200:
                trend_direction = "BEARISH"
                details["major_trend"] = "Bearish (< SMA200)"
        else:
            # Fallback if no SMA200 data yet
            if current_price > curr_ema50:
                trend_direction = "BULLISH"
            else:
                trend_direction = "BEARISH"

        # 2. Trend Alignment Scoring
        if zone_type == "DEMAND" or zone_type is None:
            # Strong Uptrend: Price > EMA21 > EMA50 > SMA200
            if curr_sma200 and current_price > curr_ema21 > curr_ema50 > curr_sma200:
                confidence += 25
                signal_type = "BUY"
                details["alignment"] = "Strong Uptrend"
            elif current_price > curr_ema21 > curr_ema50:
                confidence += 15
                if signal_type == "NEUTRAL":
                    signal_type = "BUY"
                details["alignment"] = "Medium Uptrend"
            elif current_price > curr_ema21:
                confidence += 8
                details["alignment"] = "Weak Uptrend"

        if zone_type == "SUPPLY" or zone_type is None:
            # Strong Downtrend: Price < EMA21 < EMA50 < SMA200
            if curr_sma200 and current_price < curr_ema21 < curr_ema50 < curr_sma200:
                confidence += 25
                signal_type = "SELL"
                details["alignment"] = "Strong Downtrend"
            elif current_price < curr_ema21 < curr_ema50:
                confidence += 15
                if signal_type == "NEUTRAL":
                    signal_type = "SELL"
                details["alignment"] = "Medium Downtrend"
            elif current_price < curr_ema21:
                confidence += 8
                details["alignment"] = "Weak Downtrend"

        # 3. Crossover Signals
        if len(ema_21) >= 2 and len(ema_50) >= 2:
            prev_ema21 = ema_21[-2]
            prev_ema50 = ema_50[-2]

            # Golden Cross (EMA21 crosses above EMA50)
            if prev_ema21 <= prev_ema50 and curr_ema21 > curr_ema50:
                if zone_type == "DEMAND" or zone_type is None:
                    confidence += 20
                    signal_type = "BUY"
                    details["crossover"] = "Golden Cross"

            # Death Cross (EMA21 crosses below EMA50)
            if prev_ema21 >= prev_ema50 and curr_ema21 < curr_ema50:
                if zone_type == "SUPPLY" or zone_type is None:
                    confidence += 20
                    signal_type = "SELL"
                    details["crossover"] = "Death Cross"

        # 4. Fast Cross (EMA9 vs EMA21)
        if len(ema_9) >= 2 and len(ema_21) >= 2:
            prev_ema9 = ema_9[-2]
            prev_ema21 = ema_21[-2]
            curr_ema9 = ema_9[-1]

            # Bullish Fast Cross
            if prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21:
                if zone_type == "DEMAND" or zone_type is None:
                    confidence += 12
                    details["fast_cross"] = "Bullish"
                    if signal_type == "NEUTRAL":
                        signal_type = "BUY"

            # Bearish Fast Cross
            if prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21:
                if zone_type == "SUPPLY" or zone_type is None:
                    confidence += 12
                    details["fast_cross"] = "Bearish"
                    if signal_type == "NEUTRAL":
                        signal_type = "SELL"

        return MASignal(
            symbol=symbol,
            timeframe=timeframe,
            trend_direction=trend_direction,
            signal_type=signal_type,
            confidence=min(confidence, 100),
            details=details,
        )
