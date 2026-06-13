"""Trading sessions endpoint (paginated).

Per-run sessions (one row per bot start). Aggregate stats (trades / win-rate /
P&L / profit factor) are DERIVED from the linked closed positions rather than
read from the denormalized counters on the session row: seeded/historical
positions were inserted without going through the bot's close path, so those
counters are stale. Deriving from positions is always correct.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from trading_core.data.models import Position, TradingSession

from trading_api.deps import Pagination, TimeRange, currency_unit, get_session
from trading_api.schemas import Page, SessionOut

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


async def _stats_by_session(db: AsyncSession, session_ids: list[str]) -> dict[str, dict]:
    """Aggregate closed positions (with a recorded outcome) per session_id."""
    if not session_ids:
        return {}
    wins = func.sum(case((Position.is_winner.is_(True), 1), else_=0))
    losses = func.sum(case((Position.is_winner.is_(False), 1), else_=0))
    gross_profit = func.sum(
        case((Position.realized_pnl_usd > 0, Position.realized_pnl_usd), else_=0)
    )
    gross_loss = func.sum(
        case((Position.realized_pnl_usd < 0, -Position.realized_pnl_usd), else_=0)
    )
    stmt = (
        select(
            Position.session_id,
            func.count().label("total"),
            wins.label("wins"),
            losses.label("losses"),
            func.coalesce(func.sum(Position.realized_pnl_usd), 0.0).label("pnl"),
            func.coalesce(gross_profit, 0.0).label("gross_profit"),
            func.coalesce(gross_loss, 0.0).label("gross_loss"),
        )
        .where(
            Position.status == "CLOSED",
            Position.is_winner.isnot(None),
            Position.session_id.in_(session_ids),
        )
        .group_by(Position.session_id)
    )
    out: dict[str, dict] = {}
    for r in (await db.execute(stmt)).all():
        total = r.total or 0
        out[r.session_id] = {
            "total_trades": total,
            "winning_trades": r.wins or 0,
            "losing_trades": r.losses or 0,
            "win_rate": round((r.wins or 0) / total * 100, 1) if total else 0.0,
            "total_pnl_usd": round(r.pnl or 0.0, 2),
            "profit_factor": (
                round((r.gross_profit or 0.0) / r.gross_loss, 2) if r.gross_loss else 0.0
            ),
        }
    return out


def _to_out(s: TradingSession, stats: dict | None, unit: str) -> SessionOut:
    st = stats or {}
    return SessionOut(
        session_id=s.session_id,
        status=s.status,
        trading_type=s.trading_type,
        start_time=s.start_time,
        end_time=s.end_time,
        total_trades=st.get("total_trades", 0),
        winning_trades=st.get("winning_trades", 0),
        losing_trades=st.get("losing_trades", 0),
        win_rate=st.get("win_rate", 0.0),
        total_pnl_usd=st.get("total_pnl_usd", 0.0),
        profit_factor=st.get("profit_factor", 0.0),
        max_drawdown=s.max_drawdown,
        currency_unit=unit,
    )


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
    stats = await _stats_by_session(session, [s.session_id for s in rows])
    items = [_to_out(s, stats.get(s.session_id), unit) for s in rows]
    return Page(items=items, total=total or 0, limit=page.limit, offset=page.offset)


@router.get("/current", response_model=SessionOut | None)
async def current_session(
    session: AsyncSession = Depends(get_session),
) -> SessionOut | None:
    """The currently ACTIVE session (live bot), or null when none is running."""
    s = (
        await session.execute(
            select(TradingSession)
            .where(TradingSession.status == "ACTIVE")
            .order_by(TradingSession.start_time.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not s:
        return None
    stats = await _stats_by_session(session, [s.session_id])
    return _to_out(s, stats.get(s.session_id), currency_unit())
