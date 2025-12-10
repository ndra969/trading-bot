"""
Market Structure Analysis Layer

This module detects market structure shifts:
- Break of Structure (BOS): Continuation of trend
- Change of Character (CHoCH): Potential reversal
"""

import logging
from dataclasses import dataclass

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class StructureSignal:
    symbol: str
    structure_type: str  # 'BOS', 'CHOCH', 'NEUTRAL'
    direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    confidence: float
    details: dict


class MarketStructureAnalyzer:
    """
    Analyzes market structure (BOS/CHoCH).
    """

    def __init__(self, config: dict):
        self.config = config
        self.lookback = config.get("structure", {}).get("lookback", 50)

    async def analyze_structure(
        self, symbol: str, highs: list[float], lows: list[float], closes: list[float]
    ) -> StructureSignal | None:
        """
        Analyze recent market structure.
        """
        if len(closes) < self.lookback:
            return None

        # Identify Swings
        swing_highs = self._find_swings(highs, "HIGH")
        swing_lows = self._find_swings(lows, "LOW")

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None

        # Get last significant swings
        last_high = swing_highs[-1]
        prev_high = swing_highs[-2]

        last_low = swing_lows[-1]
        prev_low = swing_lows[-2]

        current_close = closes[-1]

        signal_type = "NEUTRAL"
        direction = "NEUTRAL"
        confidence = 0.0
        desc = ""

        # Determine Current Trend State
        # Uptrend if Higher Highs and Higher Lows
        is_uptrend = False
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            is_uptrend = (
                prev_high["value"] > swing_highs[-3]["value"]
                and prev_low["value"] > swing_lows[-3]["value"]
            )

        # Downtrend if Lower Highs and Lower Lows
        is_downtrend = False
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            is_downtrend = (
                prev_high["value"] < swing_highs[-3]["value"]
                and prev_low["value"] < swing_lows[-3]["value"]
            )

        # Priority: CHoCH (Reversal) > BOS (Continuation)

        # 1. Check for CHoCH (Reversal)
        if is_uptrend and current_close < last_low["value"]:
            signal_type = "CHOCH"
            direction = "BEARISH"
            confidence = 85.0
            desc = "Bearish CHoCH: Uptrend Low Broken"

        elif is_downtrend and current_close > last_high["value"]:
            signal_type = "CHOCH"
            direction = "BULLISH"
            confidence = 85.0
            desc = "Bullish CHoCH: Downtrend High Broken"

        # 2. Check for BOS (Continuation)
        # Only check BOS if not CHoCH
        elif current_close > last_high["value"]:
            signal_type = "BOS"
            direction = "BULLISH"
            confidence = 80.0
            desc = f"Bullish BOS: Break above {last_high['value']:.5f}"

        elif current_close < last_low["value"]:
            signal_type = "BOS"
            direction = "BEARISH"
            confidence = 80.0
            desc = f"Bearish BOS: Break below {last_low['value']:.5f}"

        if signal_type == "NEUTRAL":
            return None

        return StructureSignal(
            symbol=symbol,
            structure_type=signal_type,
            direction=direction,
            confidence=confidence,
            details={
                "description": desc,
                "last_high": last_high["value"],
                "last_low": last_low["value"],
            },
        )

    def _find_swings(self, data: list[float], swing_type: str, window: int = 3) -> list[dict]:
        """Find local swing points."""
        swings = []
        for i in range(window, len(data) - window):
            is_swing = True
            for j in range(1, window + 1):
                if swing_type == "HIGH":
                    if data[i] <= data[i - j] or data[i] <= data[i + j]:
                        is_swing = False
                        break
                else:  # LOW
                    if data[i] >= data[i - j] or data[i] >= data[i + j]:
                        is_swing = False
                        break

            if is_swing:
                swings.append({"index": i, "value": data[i]})
        return swings
