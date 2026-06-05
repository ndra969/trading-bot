"""Account summary endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import Position, TradingAccount

from trading_api.deps import currency_unit, get_session
from trading_api.schemas import AccountSummary

router = APIRouter(prefix="/api/v1/account", tags=["account"])

_CLOSED = "CLOSED"


@router.get("/summary", response_model=AccountSummary)
async def summary(session: AsyncSession = Depends(get_session)) -> AccountSummary:
    account = await session.scalar(
        select(TradingAccount)
        .where(TradingAccount.is_active.is_(True))
        .order_by(TradingAccount.updated_at.desc())
    )

    open_count = await session.scalar(
        select(func.count()).select_from(Position).where(Position.status != _CLOSED)
    )
    exposure = await session.scalar(
        select(func.coalesce(func.sum(Position.risk_amount_usd), 0.0)).where(
            Position.status != _CLOSED
        )
    )

    return AccountSummary(
        broker_name=account.broker_name if account else None,
        balance=account.balance if account else 0.0,
        equity=account.equity if account else 0.0,
        leverage=account.leverage if account else None,
        open_count=open_count or 0,
        total_exposure=round(exposure or 0.0, 2),
        currency_unit=currency_unit(),
    )
