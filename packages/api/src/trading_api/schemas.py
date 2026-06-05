"""Pydantic v2 response models for the read-only dashboard API.

Monetary payloads carry a top-level ``currency_unit`` so the frontend labels
USC vs USD correctly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Page[T](BaseModel):
    """Pagination envelope for list endpoints."""

    items: list[T]
    total: int
    limit: int
    offset: int


class Health(BaseModel):
    status: str
    database: bool


class OpenPosition(BaseModel):
    position_id: str
    symbol: str
    position_type: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit: float
    current_price: float | None
    current_pnl_usd: float
    current_profit_pips: float
    confluence_score: float
    asset_class: str | None
    open_time: datetime | None
    currency_unit: str


class ClosedPosition(BaseModel):
    position_id: str
    symbol: str
    position_type: str
    asset_class: str | None
    exit_type: str | None
    close_reason: str | None
    is_winner: bool | None
    realized_pnl_usd: float
    realized_profit_pips: float
    confluence_score: float
    holding_time_seconds: int
    open_time: datetime | None
    close_time: datetime | None
    currency_unit: str


class ConfluenceBreakdown(BaseModel):
    foundation_share: float | None = None
    enhancement_share: float | None = None
    raw_confidences: dict[str, float] = {}
    active_layers: list[str] = []


class PositionDetail(ClosedPosition):
    """Full single-trade drill-down: quality metrics + confluence breakdown."""

    entry_price: float
    stop_loss: float
    take_profit: float
    close_price: float | None
    mae_pips: float
    mfe_pips: float
    max_profit_pips: float
    max_drawdown_pips: float
    slippage_pips: float
    entry_to_sl_pips: float
    entry_to_tp_pips: float
    breakeven_activated: bool
    trailing_activated: bool
    market_session: str | None
    # None when the row predates breakdown persistence (Goal 7).
    confluence_breakdown: ConfluenceBreakdown | None


class ThresholdsOut(BaseModel):
    """The active tuning knobs from the loaded YAML (read-only)."""

    quality_thresholds: dict
    confluence_weights: dict
    volatility_filter: dict
    commodity_gates: dict


# --- Analytics -------------------------------------------------------------


class StatRow(BaseModel):
    """A grouped performance row (by asset / symbol / session / reason / exit)."""

    key: str
    count: int
    wins: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    avg_confluence: float
    currency_unit: str


class EquityPoint(BaseModel):
    close_time: datetime
    cumulative_pnl: float


class ConfluenceBucket(BaseModel):
    bucket: str
    lower: float
    upper: float
    count: int
    wins: int
    win_rate: float
    avg_pnl: float


class ConfluenceDistribution(BaseModel):
    asset_class: str | None
    buckets: list[ConfluenceBucket]
    min: float | None
    p50: float | None
    max: float | None


class ConfluenceVsOutcome(BaseModel):
    buckets: list[ConfluenceBucket]
    win_avg_confluence: float | None
    loss_avg_confluence: float | None


class LayerContribRow(BaseModel):
    layer: str
    participation_rate: float  # fraction of sampled trades the layer fired in
    avg_contribution: float  # avg raw confidence when it fired


class LayerContribution(BaseModel):
    rows: list[LayerContribRow]
    coverage: float  # fraction of closed trades carrying a breakdown
    sample: int  # trades with a breakdown


# --- Rejections ------------------------------------------------------------


class RejectionReasonRow(BaseModel):
    stage: str
    count: int
    avg_confluence: float | None


class RejectionSymbolRow(BaseModel):
    symbol: str
    stage: str
    count: int


class RejectionRecent(BaseModel):
    created_at: datetime
    symbol: str
    asset_class: str | None
    direction: str | None
    stage: str
    confluence_score: float | None
    details: dict
