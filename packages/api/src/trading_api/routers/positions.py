"""Positions endpoints: live open, paginated closed history, single drill-down."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import Position

from trading_api.deps import Pagination, TimeRange, currency_unit, get_session
from trading_api.schemas import (
    ClosedPosition,
    ConfluenceBreakdown,
    OpenPosition,
    Page,
    PositionDetail,
)

router = APIRouter(prefix="/api/v1/positions", tags=["positions"])

_CLOSED = "CLOSED"


@router.get("/open", response_model=list[OpenPosition])
async def open_positions(session: AsyncSession = Depends(get_session)) -> list[OpenPosition]:
    rows = (
        (await session.execute(select(Position).where(Position.status != _CLOSED))).scalars().all()
    )
    unit = currency_unit()
    return [
        OpenPosition(
            position_id=p.position_id,
            symbol=p.symbol,
            position_type=p.position_type,
            status=p.status,
            entry_price=p.entry_price,
            stop_loss=p.stop_loss,
            take_profit=p.take_profit,
            current_price=p.current_price,
            current_pnl_usd=p.current_pnl_usd,
            current_profit_pips=p.current_profit_pips,
            confluence_score=p.confluence_score,
            asset_class=p.asset_class,
            open_time=p.open_time,
            currency_unit=unit,
        )
        for p in rows
    ]


@router.get("/closed", response_model=Page[ClosedPosition])
async def closed_positions(
    session: AsyncSession = Depends(get_session),
    page: Pagination = Depends(),
    window: TimeRange = Depends(),
    symbol: str | None = Query(None),
    exit_type: str | None = Query(None),
    close_reason: str | None = Query(None),
) -> Page[ClosedPosition]:
    filters = [Position.status == _CLOSED]
    if symbol:
        filters.append(Position.symbol == symbol)
    if exit_type:
        filters.append(Position.exit_type == exit_type)
    if close_reason:
        filters.append(Position.close_reason == close_reason)
    if window.since:
        filters.append(Position.close_time >= window.since)
    if window.until:
        filters.append(Position.close_time < window.until)

    total = await session.scalar(select(func.count()).select_from(Position).where(*filters))
    rows = (
        (
            await session.execute(
                select(Position)
                .where(*filters)
                .order_by(Position.close_time.desc())
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    unit = currency_unit()
    items = [
        ClosedPosition(
            position_id=p.position_id,
            symbol=p.symbol,
            position_type=p.position_type,
            asset_class=p.asset_class,
            exit_type=p.exit_type,
            close_reason=p.close_reason,
            is_winner=p.is_winner,
            realized_pnl_usd=p.realized_pnl_usd,
            realized_profit_pips=p.realized_profit_pips,
            confluence_score=p.confluence_score,
            holding_time_seconds=p.holding_time_seconds,
            open_time=p.open_time,
            close_time=p.close_time,
            currency_unit=unit,
        )
        for p in rows
    ]
    return Page(items=items, total=total or 0, limit=page.limit, offset=page.offset)


@router.get("/{position_id}", response_model=PositionDetail)
async def position_detail(
    position_id: str, session: AsyncSession = Depends(get_session)
) -> PositionDetail:
    p = await session.scalar(select(Position).where(Position.position_id == position_id))
    if p is None:
        raise HTTPException(status_code=404, detail=f"position {position_id} not found")

    meta = p.meta_data or {}
    breakdown_raw = meta.get("confluence_breakdown")
    breakdown = ConfluenceBreakdown(**breakdown_raw) if isinstance(breakdown_raw, dict) else None

    return PositionDetail(
        position_id=p.position_id,
        symbol=p.symbol,
        position_type=p.position_type,
        asset_class=p.asset_class,
        exit_type=p.exit_type,
        close_reason=p.close_reason,
        is_winner=p.is_winner,
        realized_pnl_usd=p.realized_pnl_usd,
        realized_profit_pips=p.realized_profit_pips,
        confluence_score=p.confluence_score,
        holding_time_seconds=p.holding_time_seconds,
        open_time=p.open_time,
        close_time=p.close_time,
        entry_price=p.entry_price,
        stop_loss=p.stop_loss,
        take_profit=p.take_profit,
        close_price=p.close_price,
        mae_pips=p.mae_pips,
        mfe_pips=p.mfe_pips,
        max_profit_pips=p.max_profit_pips,
        max_drawdown_pips=p.max_drawdown_pips,
        slippage_pips=p.slippage_pips,
        entry_to_sl_pips=p.entry_to_sl_pips,
        entry_to_tp_pips=p.entry_to_tp_pips,
        breakeven_activated=p.breakeven_activated,
        trailing_activated=p.trailing_activated,
        market_session=meta.get("market_session"),
        confluence_breakdown=breakdown,
        currency_unit=currency_unit(),
    )
