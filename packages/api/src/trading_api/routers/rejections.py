"""Rejection telemetry endpoints (the 'why setups were blocked' view)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import SignalRejection

from trading_api.deps import Pagination, TimeRange, get_session
from trading_api.schemas import (
    Page,
    RejectionReasonRow,
    RejectionRecent,
    RejectionSymbolRow,
)

router = APIRouter(prefix="/api/v1/rejections", tags=["rejections"])


def _filters(window: TimeRange, symbol: str | None, asset_class: str | None) -> list:
    f = []
    if symbol:
        f.append(SignalRejection.symbol == symbol)
    if asset_class:
        f.append(SignalRejection.asset_class == asset_class)
    if window.since:
        f.append(SignalRejection.created_at >= window.since)
    if window.until:
        f.append(SignalRejection.created_at < window.until)
    return f


@router.get("/by-reason", response_model=list[RejectionReasonRow])
async def by_reason(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
    asset_class: str | None = Query(None),
) -> list[RejectionReasonRow]:
    stmt = (
        select(
            SignalRejection.stage,
            func.count().label("n"),
            func.avg(SignalRejection.confluence_score).label("avg_conf"),
        )
        .where(*_filters(window, symbol, asset_class))
        .group_by(SignalRejection.stage)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        RejectionReasonRow(
            stage=r.stage,
            count=r.n,
            avg_confluence=round(r.avg_conf, 1) if r.avg_conf is not None else None,
        )
        for r in rows
    ]


@router.get("/by-symbol", response_model=list[RejectionSymbolRow])
async def by_symbol(
    session: AsyncSession = Depends(get_session),
    window: TimeRange = Depends(),
    asset_class: str | None = Query(None),
) -> list[RejectionSymbolRow]:
    stmt = (
        select(
            SignalRejection.symbol,
            SignalRejection.stage,
            func.count().label("n"),
        )
        .where(*_filters(window, None, asset_class))
        .group_by(SignalRejection.symbol, SignalRejection.stage)
        .order_by(func.count().desc())
    )
    rows = (await session.execute(stmt)).all()
    return [RejectionSymbolRow(symbol=r.symbol, stage=r.stage, count=r.n) for r in rows]


@router.get("/recent", response_model=Page[RejectionRecent])
async def recent(
    session: AsyncSession = Depends(get_session),
    page: Pagination = Depends(),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
    asset_class: str | None = Query(None),
) -> Page[RejectionRecent]:
    filters = _filters(window, symbol, asset_class)
    total = await session.scalar(select(func.count()).select_from(SignalRejection).where(*filters))
    rows = (
        (
            await session.execute(
                select(SignalRejection)
                .where(*filters)
                .order_by(SignalRejection.created_at.desc())
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    items = [
        RejectionRecent(
            created_at=r.created_at,
            symbol=r.symbol,
            asset_class=r.asset_class,
            direction=r.direction,
            stage=r.stage,
            confluence_score=r.confluence_score,
            details=r.details or {},
        )
        for r in rows
    ]
    return Page(items=items, total=total or 0, limit=page.limit, offset=page.offset)
