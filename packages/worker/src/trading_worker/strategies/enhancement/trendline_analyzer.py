"""
Trendline Analysis Layer

This module implements automated trendline detection and analysis.
It identifies support and resistance trendlines based on swing points
and calculates confluence with current price action.
"""

import logging
from dataclasses import dataclass

import numpy as np

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class Trendline:
    start_index: int
    end_index: int
    start_price: float
    end_price: float
    slope: float
    intercept: float
    line_type: str  # 'SUPPORT' or 'RESISTANCE'
    touches: int
    score: float
    angle: float


@dataclass
class TrendlineSignal:
    symbol: str
    timeframe: str
    trendlines: list[Trendline]
    nearest_trendline: Trendline | None
    distance_to_trendline: float  # In pips
    signal_type: (
        str  # 'BOUNCE_SUPPORT', 'BREAK_RESISTANCE', 'BOUNCE_RESISTANCE', 'BREAK_SUPPORT', 'NEUTRAL'
    )
    confidence: float
    details: dict


class TrendlineAnalyzer:
    """
    Analyzes trendlines for confluence.
    """

    def __init__(self, config: dict):
        self.config = config
        self.min_touches = config.get("trendline", {}).get("min_touches", 3)
        self.tolerance = config.get("trendline", {}).get("tolerance", 0.0005)  # Price tolerance
        # Zone-confluence tolerance as a fraction of zone height: how far
        # beyond the zone band a projected line may sit and still count as
        # reinforcing the zone (asset-scale independent by construction).
        self.zone_tolerance = config.get("trendline", {}).get("zone_tolerance", 0.5)

    async def analyze_zone_confluence(
        self,
        symbol: str,
        prices: list[float],
        timeframe: str,
        zone_lower: float,
        zone_upper: float,
        is_demand: bool,
    ) -> TrendlineSignal:
        """
        Evaluate whether a trendline reinforces an S&D zone.

        Unlike analyze_trendline_signal (price within N pips of a line on the
        entry candle — which almost never coincides with a zone entry), this
        projects each top trendline to the current bar and asks whether the
        line passes through or adjacent to the zone band. Tolerance scales
        with zone height, so no pip conversion is needed. Direction filter:
        only SUPPORT lines reinforce a DEMAND zone (BUY) and only RESISTANCE
        lines reinforce a SUPPLY zone (SELL); break types never count.
        """
        if len(prices) < 50 or zone_upper <= zone_lower:
            return TrendlineSignal(
                symbol, timeframe, [], None, 0, "NEUTRAL", 0, {"error": "Insufficient data"}
            )

        swing_highs = self._find_swing_highs(prices)
        swing_lows = self._find_swing_lows(prices)
        resistance_lines = self._generate_trendlines(swing_highs, prices, "RESISTANCE")
        support_lines = self._generate_trendlines(swing_lows, prices, "SUPPORT")

        all_lines = resistance_lines + support_lines
        all_lines.sort(key=lambda x: x.score, reverse=True)
        top_lines = all_lines[:5]

        current_idx = len(prices) - 1
        zone_height = zone_upper - zone_lower
        tolerance = zone_height * self.zone_tolerance
        band_lower = zone_lower - tolerance
        band_upper = zone_upper + tolerance
        zone_mid = (zone_upper + zone_lower) / 2
        half_span = zone_height / 2 + tolerance

        wanted_type = "SUPPORT" if is_demand else "RESISTANCE"

        best_line: Trendline | None = None
        best_confidence = 0.0
        best_line_price = 0.0
        for line in top_lines:
            if line.line_type != wanted_type:
                continue
            line_price = line.slope * current_idx + line.intercept
            if not (band_lower <= line_price <= band_upper):
                continue
            # Confidence: touches (line strength) + how centred the line is
            # within the zone band (a line through the zone middle reinforces
            # the level more than one grazing the tolerance edge).
            centring = 1.0 - abs(line_price - zone_mid) / half_span
            confidence = 20.0 + line.touches * 5.0 + centring * 20.0
            if confidence > best_confidence:
                best_confidence = confidence
                best_line = line
                best_line_price = line_price

        if best_line is None:
            return TrendlineSignal(
                symbol=symbol,
                timeframe=timeframe,
                trendlines=top_lines,
                nearest_trendline=None,
                distance_to_trendline=0,
                signal_type="NEUTRAL",
                confidence=0.0,
                details={"zone": [zone_lower, zone_upper]},
            )

        signal_type = "BOUNCE_SUPPORT" if is_demand else "BOUNCE_RESISTANCE"
        return TrendlineSignal(
            symbol=symbol,
            timeframe=timeframe,
            trendlines=top_lines,
            nearest_trendline=best_line,
            distance_to_trendline=abs(best_line_price - zone_mid),
            signal_type=signal_type,
            confidence=min(best_confidence, 100),
            details={
                "action": f"{wanted_type} trendline reinforces zone",
                "line_price": best_line_price,
                "zone": [zone_lower, zone_upper],
                "touches": best_line.touches,
            },
        )

    async def analyze_trendline_signal(
        self, symbol: str, prices: list[float], timeframe: str, pip_value: float = 0.0001
    ) -> TrendlineSignal:
        """
        Analyze trendline signals for a specific symbol/timeframe.
        """
        if len(prices) < 50:
            return TrendlineSignal(
                symbol, timeframe, [], None, 0, "NEUTRAL", 0, {"error": "Insufficient data"}
            )

        # 1. Detect Swing Points
        swing_highs = self._find_swing_highs(prices)
        swing_lows = self._find_swing_lows(prices)

        # 2. Generate Trendlines
        resistance_lines = self._generate_trendlines(swing_highs, prices, "RESISTANCE")
        support_lines = self._generate_trendlines(swing_lows, prices, "SUPPORT")

        all_lines = resistance_lines + support_lines

        # Filter strongest lines
        all_lines.sort(key=lambda x: x.score, reverse=True)
        top_lines = all_lines[:5]  # Keep top 5 strongest lines

        # 3. Analyze Confluence with Current Price
        current_price = prices[-1]
        current_idx = len(prices) - 1

        nearest_line = None
        min_dist = float("inf")
        signal_type = "NEUTRAL"
        confidence = 0.0
        details = {}

        for line in top_lines:
            # Calculate price at current index on the line
            line_price = line.slope * current_idx + line.intercept

            # Distance in pips
            dist_pips = abs(current_price - line_price) / pip_value

            if dist_pips < min_dist:
                min_dist = dist_pips
                nearest_line = line

                # Check for bounce logic (Price near line)
                if dist_pips <= 20:  # Within 20 pips
                    if line.line_type == "SUPPORT":
                        signal_type = "BOUNCE_SUPPORT"  # Buy Signal
                        confidence = 20 + (line.touches * 5)  # Base 20 + bonus per touch
                        details["action"] = f"Near Support Trendline ({dist_pips:.1f} pips)"
                    elif line.line_type == "RESISTANCE":
                        signal_type = "BOUNCE_RESISTANCE"  # Sell Signal
                        confidence = 20 + (line.touches * 5)
                        details["action"] = f"Near Resistance Trendline ({dist_pips:.1f} pips)"

        return TrendlineSignal(
            symbol=symbol,
            timeframe=timeframe,
            trendlines=top_lines,
            nearest_trendline=nearest_line,
            distance_to_trendline=min_dist if nearest_line else 0,
            signal_type=signal_type,
            confidence=min(confidence, 100),
            details=details,
        )

    def _find_swing_highs(self, data: list[float], window: int = 5) -> list[tuple[int, float]]:
        """Find local maxima indices and values."""
        swings = []
        for i in range(window, len(data) - window):
            is_high = True
            for j in range(1, window + 1):
                if data[i] <= data[i - j] or data[i] <= data[i + j]:
                    is_high = False
                    break
            if is_high:
                swings.append((i, data[i]))
        return swings

    def _find_swing_lows(self, data: list[float], window: int = 5) -> list[tuple[int, float]]:
        """Find local minima indices and values."""
        swings = []
        for i in range(window, len(data) - window):
            is_low = True
            for j in range(1, window + 1):
                if data[i] >= data[i - j] or data[i] >= data[i + j]:
                    is_low = False
                    break
            if is_low:
                swings.append((i, data[i]))
        return swings

    def _generate_trendlines(
        self, points: list[tuple[int, float]], prices: list[float], line_type: str
    ) -> list[Trendline]:
        """
        Generate valid trendlines from swing points.
        Connecting point A to point B, checking if point C, D... are near the line.
        """
        lines = []
        n_points = len(points)

        if n_points < 2:
            return []

        # Try connecting every pair of points
        for i in range(n_points):
            for j in range(i + 1, n_points):
                p1 = points[i]
                p2 = points[j]

                # Calculate line equation: y = mx + c
                if p2[0] == p1[0]:
                    continue  # Vertical line, skip

                slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
                intercept = p1[1] - slope * p1[0]

                # Validate line touches
                touches = 2  # Start with 2 touches (p1 and p2)
                score = 0.0

                # Check other points
                # Only check points AFTER p1 to avoid overfitting past data too much?
                # Or check all swing points?
                # Let's check intermediate points

                valid_line = True

                # Check if line cuts through price body too much (Invalidation)
                # For Resistance: Price shouldn't be consistently above line
                # For Support: Price shouldn't be consistently below line
                # We check all price bars between p1 and p2
                for k in range(p1[0] + 1, p2[0]):
                    price_at_k = prices[k]
                    line_price_k = slope * k + intercept

                    if line_type == "RESISTANCE" and price_at_k > line_price_k * (
                        1 + self.tolerance
                    ):
                        # Significant break above resistance
                        valid_line = False
                        break
                    elif line_type == "SUPPORT" and price_at_k < line_price_k * (
                        1 - self.tolerance
                    ):
                        # Significant break below support
                        valid_line = False
                        break

                if not valid_line:
                    continue

                # Count additional touches (3rd, 4th point...)
                # Check points after p2 or between?
                # Let's look for other swing points that align
                for k in range(j + 1, n_points):
                    p3 = points[k]
                    expected_price = slope * p3[0] + intercept

                    # Check proximity
                    if abs(p3[1] - expected_price) < (p3[1] * self.tolerance):
                        touches += 1

                if touches >= self.min_touches:
                    # Calculate angle (in degrees, roughly)
                    # Note: This is purely mathematical angle, not chart visual angle
                    angle = np.degrees(np.arctan(slope))

                    # Score based on touches and recency (higher index = more recent)
                    recency_score = p2[0] / len(prices)
                    score = (touches * 10) + (recency_score * 5)

                    lines.append(
                        Trendline(
                            start_index=p1[0],
                            end_index=len(prices) - 1,  # Project to current
                            start_price=p1[1],
                            end_price=slope * (len(prices) - 1) + intercept,
                            slope=slope,
                            intercept=intercept,
                            line_type=line_type,
                            touches=touches,
                            score=score,
                            angle=angle,
                        )
                    )

        return lines
