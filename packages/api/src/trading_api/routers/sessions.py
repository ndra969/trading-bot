"""Trading sessions endpoint (paginated)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import TradingSession

from trading_api.deps import Pagination, TimeRange, currency_unit, get_session
from trading_api.schemas import Page, SessionOut

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=Page[SessionOut])
async def sessions(
    session: AsyncSession = Depends(get_session),
    page: Pagination = Depends(),
    window: TimeRange = Depends(),
) -> Page[SessionOut]:
    filters = []
    if window.since:
        filters.append(TradingSession.start_time >= window.since)
    if window.until:
        filters.append(TradingSession.start_time < window.until)

    total = await session.scalar(select(func.count()).select_from(TradingSession).where(*filters))
    rows = (
        (
            await session.execute(
                select(TradingSession)
                .where(*filters)
                .order_by(TradingSession.start_time.desc())
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        .scalars()
        .all()
    )
    unit = currency_unit()
    items = [
        SessionOut(
            session_id=s.session_id,
            status=s.status,
            trading_type=s.trading_type,
            start_time=s.start_time,
            end_time=s.end_time,
            total_trades=s.total_trades,
            winning_trades=s.winning_trades,
            losing_trades=s.losing_trades,
            win_rate=s.win_rate,
            total_pnl_usd=s.total_pnl_usd,
            profit_factor=s.profit_factor,
            max_drawdown=s.max_drawdown,
            currency_unit=unit,
        )
        for s in rows
    ]
    return Page(items=items, total=total or 0, limit=page.limit, offset=page.offset)
