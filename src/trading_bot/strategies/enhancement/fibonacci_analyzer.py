"""
Fibonacci Confluence Layer

This module implements automated Fibonacci retracement analysis.
It detects major market swings and calculates key Fibonacci levels
to find confluence with Supply/Demand zones.
"""

import logging
from dataclasses import dataclass

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class FibonacciLevel:
    level: float  # e.g., 0.618
    price: float
    name: str  # e.g., '61.8%'


@dataclass
class FibonacciSignal:
    symbol: str
    swing_high: float
    swing_low: float
    direction: str  # 'UP' (drawing from Low to High) or 'DOWN' (High to Low)
    confluence_level: FibonacciLevel | None
    score: float
    details: dict


class FibonacciAnalyzer:
    """
    Analyzes Fibonacci confluences.
    """

    def __init__(self, config: dict):
        self.config = config
        self.lookback = config.get("fibonacci", {}).get("lookback", 100)
        self.tolerance = config.get("fibonacci", {}).get("tolerance", 0.0005)  # Price tolerance

        # Key levels and their scores
        self.levels = {0.382: 10, 0.500: 15, 0.618: 20, 0.786: 10}  # Golden Ratio

    async def analyze_fibonacci(
        self, symbol: str, highs: list[float], lows: list[float], zone_price: float, zone_type: str
    ) -> FibonacciSignal | None:
        """
        Analyze Fibonacci confluence for a specific zone.
        """
        if len(highs) < self.lookback:
            return None

        # Get recent data
        recent_highs = highs[-self.lookback :]
        recent_lows = lows[-self.lookback :]

        # Identify Major Swing High and Low
        # Strategy:
        # For Demand Zone (Buying), we expect price to retrace DOWN.
        # So we draw Fibo from Swing Low to Swing High.
        # For Supply Zone (Selling), we expect price to retrace UP.
        # So we draw Fibo from Swing High to Swing Low.

        max_high = max(recent_highs)
        min_low = min(recent_lows)

        # Find indices (relative to the slice)
        high_idx = recent_highs.index(max_high)
        low_idx = recent_lows.index(min_low)

        # Determine Fibo Direction based on Zone Type
        swing_start = 0.0
        swing_end = 0.0
        direction = "UNKNOWN"

        if zone_type == "DEMAND":
            # Looking for retracement of an UP move (Low -> High)
            # Valid if Low happened BEFORE High
            if low_idx < high_idx:
                swing_start = min_low
                swing_end = max_high
                direction = "UP"
            else:
                # If High happened before Low, we are in a downtrend.
                # Maybe use the previous High-Low?
                # For simplicity, if structure isn't clear, skip.
                return None

        elif zone_type == "SUPPLY":
            # Looking for retracement of a DOWN move (High -> Low)
            # Valid if High happened BEFORE Low
            if high_idx < low_idx:
                swing_start = max_high
                swing_end = min_low
                direction = "DOWN"
            else:
                return None

        else:
            return None

        # Calculate Levels
        diff = swing_end - swing_start
        levels = []

        # Retracement formula:
        # If UP (Start=Low, End=High): Level Price = End - (Diff * Ratio)
        # If DOWN (Start=High, End=Low): Level Price = End - (Diff * Ratio) ... Wait
        # Correction:
        # UP Move (100 -> 200): 50% retrace is 150. (200 - 100*0.5)
        # DOWN Move (200 -> 100): 50% retrace is 150. (100 - (-100)*0.5) -> (100 + 50) = 150.
        # Formula: Start + (Diff * (1 - Ratio)) ? No.
        # Standard: Level = SwingHigh - (Range * Ratio) for Uptrend Retracement (finding support)
        # Standard: Level = SwingLow + (Range * Ratio) for Downtrend Retracement (finding resistance)

        range_val = abs(max_high - min_low)

        best_level = None
        best_score = 0
        min_dist = float("inf")

        for ratio, score_val in self.levels.items():
            level_price = 0.0
            if direction == "UP":  # Retracing down to Demand
                level_price = max_high - (range_val * ratio)
            else:  # Retracing up to Supply
                level_price = min_low + (range_val * ratio)

            # Check Confluence with Zone Price
            # Use percentage difference or fixed tolerance
            dist = abs(level_price - zone_price)

            # Normalize distance by price? or use tolerance
            if dist < (zone_price * self.tolerance):  # Within tolerance (e.g. 0.05%)
                if score_val > best_score:
                    best_score = score_val
                    best_level = FibonacciLevel(ratio, level_price, f"{ratio*100:.1f}%")

        if best_level:
            return FibonacciSignal(
                symbol=symbol,
                swing_high=max_high,
                swing_low=min_low,
                direction=direction,
                confluence_level=best_level,
                score=best_score,
                details={
                    "level": best_level.name,
                    "price": best_level.price,
                    "swing_range": range_val,
                },
            )

        return None
