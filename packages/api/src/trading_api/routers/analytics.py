"""Analytics endpoints: grouped performance + confluence/tuning views.

All read CLOSED positions over an optional time window / symbol filter and
aggregate in Python (portable across SQLite/Postgres, incl. JSON meta_data
fields like market_session and the confluence breakdown).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import Position

from trading_api import aggregations as agg
from trading_api.deps import TimeRange, currency_unit, get_session
from trading_api.schemas import (
    ConfluenceBucket,
    ConfluenceDistribution,
    ConfluenceVsOutcome,
    EquityPoint,
    LayerContribRow,
    LayerContribution,
    StatRow,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_CLOSED = "CLOSED"


async def _load_closed(
    session: AsyncSession,
    window: TimeRange,
    symbol: str | None = None,
    asset_class: str | None = None,
) -> list[dict]:
    """Load CLOSED positions in the window as lightweight trade dicts."""
    filters = [Position.status == _CLOSED]
    if symbol:
        filters.append(Position.symbol == symbol)
    if asset_class:
        filters.append(Position.asset_class == asset_class)
    if window.since:
        filters.append(Position.close_time >= window.since)
    if window.until:
        filters.append(Position.close_time < window.until)

    rows = (await session.execute(select(Position).where(*filters))).scalars().all()
    trades = []
    for p in rows:
        meta = p.meta_data or {}
        trades.append(
            {
                "symbol": p.symbol,
                "asset_class": p.asset_class,
                "exit_type": p.exit_type,
                "close_reason": p.close_reason,
                "pnl": p.realized_pnl_usd,
                "confluence": p.confluence_score,
                "close_time": p.close_time,
                "market_session": meta.get("market_session"),
                "breakdown": meta.get("confluence_breakdown"),
            }
        )
    return trades


def _stat_rows(trades: list[dict], key: str) -> list[StatRow]:
    unit = currency_unit()
    return [
        StatRow(**row, currency_unit=unit) for row in agg.group_stats(trades, lambda t: t.get(key))
    ]


@router.get("/by-asset", response_model=list[StatRow])
async def by_asset(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
) -> list[StatRow]:
    return _stat_rows(await _load_closed(session, window, symbol), "asset_class")


@router.get("/by-symbol", response_model=list[StatRow])
async def by_symbol(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
) -> list[StatRow]:
    return _stat_rows(await _load_closed(session, window), "symbol")


@router.get("/by-session", response_model=list[StatRow])
async def by_session(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
) -> list[StatRow]:
    return _stat_rows(await _load_closed(session, window, symbol), "market_session")


@router.get("/by-close-reason", response_model=list[StatRow])
async def by_close_reason(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
) -> list[StatRow]:
    return _stat_rows(await _load_closed(session, window, symbol), "close_reason")


@router.get("/by-exit-type", response_model=list[StatRow])
async def by_exit_type(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
) -> list[StatRow]:
    return _stat_rows(await _load_closed(session, window, symbol), "exit_type")


@router.get("/equity-curve", response_model=list[EquityPoint])
async def equity_curve(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
) -> list[EquityPoint]:
    trades = await _load_closed(session, window, symbol)
    return [EquityPoint(**p) for p in agg.equity_curve(trades)]


@router.get("/confluence-distribution", response_model=ConfluenceDistribution)
async def confluence_distribution(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    asset_class: str | None = Query(None),
    symbol: str | None = Query(None),
) -> ConfluenceDistribution:
    trades = await _load_closed(session, window, symbol, asset_class)
    confs = [t["confluence"] for t in trades if t.get("confluence") is not None]
    lo, p50, hi = agg.percentiles(confs)
    return ConfluenceDistribution(
        asset_class=asset_class,
        buckets=[ConfluenceBucket(**b) for b in agg.confluence_buckets(trades)],
        min=lo,
        p50=p50,
        max=hi,
    )


@router.get("/confluence-vs-outcome", response_model=ConfluenceVsOutcome)
async def confluence_vs_outcome(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    asset_class: str | None = Query(None),
    symbol: str | None = Query(None),
) -> ConfluenceVsOutcome:
    trades = await _load_closed(session, window, symbol, asset_class)
    win_confs = [t["confluence"] for t in trades if (t.get("pnl") or 0) > 0 and t.get("confluence")]
    loss_confs = [
        t["confluence"] for t in trades if (t.get("pnl") or 0) <= 0 and t.get("confluence")
    ]
    return ConfluenceVsOutcome(
        buckets=[ConfluenceBucket(**b) for b in agg.confluence_buckets(trades)],
        win_avg_confluence=round(sum(win_confs) / len(win_confs), 1) if win_confs else None,
        loss_avg_confluence=round(sum(loss_confs) / len(loss_confs), 1) if loss_confs else None,
    )


@router.get("/layer-contribution", response_model=LayerContribution)
async def layer_contribution(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    asset_class: str | None = Query(None),
    symbol: str | None = Query(None),
) -> LayerContribution:
    trades = await _load_closed(session, window, symbol, asset_class)
    rows, coverage, sample = agg.layer_contribution(trades)
    return LayerContribution(
        rows=[LayerContribRow(**r) for r in rows],
        coverage=coverage,
        sample=sample,
    )
