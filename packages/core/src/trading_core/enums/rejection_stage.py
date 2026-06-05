"""Signal rejection stages for tuning telemetry.

A stable enum of the reasons the signal pipeline can reject a setup. Shared
by the worker (which records rejections) and the API (which groups them) so
the two never drift. Stored as the string value in
``signal_rejections.stage``.
"""

from __future__ import annotations

from enum import Enum


class RejectionStage(str, Enum):
    """Why a candidate setup was rejected before becoming a signal."""

    # Confluence / scoring
    CONFLUENCE_TOO_LOW = "confluence_too_low"
    PRICE_ACTION_REQUIRED = "price_action_required"  # require_price_action + insufficient PA
    PA_WRONG_DIRECTION = "pa_wrong_direction"

    # Trend / structure gates
    COUNTER_TREND_GATE = "counter_trend_gate"  # universal H1 sniper gate
    RSI_GATE = "rsi_gate"  # RSI overbought/oversold against direction
    STRUCTURE_GATE = "structure_gate"  # commodities strong opposite structure
    VOLATILITY_TREND_GATE = "volatility_trend_gate"

    # Candle / volatility gates
    CLIMAX = "climax"  # exhaustion candle
    FALLING_KNIFE = "falling_knife"  # large bearish body on a BUY
    MOMENTUM_SPIKE = "momentum_spike"  # large bullish body on a SELL
    REJECTION_WICK = "rejection_wick"  # insufficient bounce/rejection wick
    COLOR_MATCH = "color_match"  # signal candle wrong colour
    VOLUME_BURST = "volume_burst"  # no volume confirmation

    # Entry quality / risk
    ANTI_CHASE = "anti_chase"  # entry too far from zone
    MAX_STOP_LOSS = "max_stop_loss"  # risk too large
    NO_ENHANCEMENT_LAYER = "no_enhancement_layer"  # commodities require >=1 layer

    OTHER = "other"
