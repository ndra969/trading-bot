"""Config endpoint: the active signal_generation tuning knobs (read-only).

Lets the Tuning view draw the active gates over the distributions without the
operator opening the YAML.
"""

from __future__ import annotations

from fastapi import APIRouter

from trading_api.deps import get_config
from trading_api.schemas import ThresholdsOut

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/thresholds", response_model=ThresholdsOut)
async def thresholds() -> ThresholdsOut:
    cfg = get_config()
    sig = cfg.get("signal_generation") or {}
    return ThresholdsOut(
        quality_thresholds=sig.get("quality_thresholds", {}),
        confluence_weights=cfg.get("confluence_weights") or {},
        volatility_filter=sig.get("volatility_filter", {}),
        commodity_gates=sig.get("commodity_gates", {}),
    )
