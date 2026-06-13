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
        fib_cfg = config.get("fibonacci", {})
        self.lookback = fib_cfg.get("lookback", 100)
        self.tolerance = fib_cfg.get("tolerance", 0.0005)  # Price tolerance

        # Key levels and their scores — config keys are stringified floats
        # ("0.382") in YAML; coerce back to float here. Falls back to the
        # classical Golden Ratio set if no config provided.
        levels_cfg = fib_cfg.get("levels")
        if isinstance(levels_cfg, dict) and levels_cfg:
            self.levels = {float(k): float(v) for k, v in levels_cfg.items()}
        else:
            self.levels = {0.382: 10, 0.500: 15, 0.618: 20, 0.786: 10}

        # Pivot window for swing-leg detection (bars on each side that must
        # be lower/higher for a bar to count as a pivot high/low).
        self.swing_window = fib_cfg.get("swing_window", 5)

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

        # Swing selection (spec enhancement-layer-rework): measure the
        # retracement off the most recent *structural* leg (pivot high/low),
        # not the global lookback extremes — the global max/min can be stale
        # and ignore intermediate structure, which made deep retracements of
        # old moves score highest (and dominate losers).
        leg = self._find_recent_leg(recent_highs, recent_lows, zone_type)
        if leg is None:
            return None
        min_low, max_high, direction = leg

        # Calculate Levels
        # diff = swing_end - swing_start  # Not used in calculation
        # levels = []  # Not used, we calculate best_level directly

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
        # min_dist = float("inf")  # Not used in current implementation

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
                    best_level = FibonacciLevel(ratio, level_price, f"{ratio * 100:.1f}%")

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
                    "swing_high": max_high,
                    "swing_low": min_low,
                },
            )

        return None

    def _find_recent_leg(
        self, highs: list[float], lows: list[float], zone_type: str
    ) -> tuple[float, float, str] | None:
        """Find the most recent structural swing leg for the zone type.

        DEMAND (expects a retracement DOWN of an UP move): the latest pivot
        high, paired with the latest pivot low that precedes it.
        SUPPLY (retracement UP of a DOWN move): the latest pivot low, paired
        with the latest pivot high that precedes it.

        Returns:
            (leg_low, leg_high, direction) where direction is "UP"/"DOWN",
            or None when the recent structure does not form a valid leg.
        """
        pivot_highs = self._find_pivots(highs, is_high=True)
        pivot_lows = self._find_pivots(lows, is_high=False)
        if not pivot_highs or not pivot_lows:
            return None

        if zone_type == "DEMAND":
            high_idx, high_val = pivot_highs[-1]
            lows_before = [(i, v) for i, v in pivot_lows if i < high_idx]
            if not lows_before:
                return None
            _, low_val = lows_before[-1]
            if low_val >= high_val:
                return None
            return low_val, high_val, "UP"

        if zone_type == "SUPPLY":
            low_idx, low_val = pivot_lows[-1]
            highs_before = [(i, v) for i, v in pivot_highs if i < low_idx]
            if not highs_before:
                return None
            _, high_val = highs_before[-1]
            if high_val <= low_val:
                return None
            return low_val, high_val, "DOWN"

        return None

    def _find_pivots(self, data: list[float], is_high: bool) -> list[tuple[int, float]]:
        """Find pivot points (local extremes) with the configured window."""
        window = self.swing_window
        pivots = []
        for i in range(window, len(data) - window):
            is_pivot = True
            for j in range(1, window + 1):
                if is_high:
                    if data[i] <= data[i - j] or data[i] <= data[i + j]:
                        is_pivot = False
                        break
                else:
                    if data[i] >= data[i - j] or data[i] >= data[i + j]:
                        is_pivot = False
                        break
            if is_pivot:
                pivots.append((i, data[i]))
        return pivots
