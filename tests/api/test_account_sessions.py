"""Endpoint tests for account + sessions routers (in-memory SQLite)."""

from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
import trading_api.deps as deps
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from trading_api.app import create_app
from trading_core.data.database import Base
from trading_core.data.models import Position, TradingAccount, TradingSession


def _open_pos(pid, risk):
    return Position(
        position_id=pid,
        symbol="EURUSD",
        position_type="BUY",
        status="OPEN",
        entry_price=1.0,
        stop_loss=0.99,
        take_profit=1.02,
        volume=0.1,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        risk_amount_usd=risk,
    )


def _closed_pos(pid, session_id, pnl, is_winner):
    return Position(
        position_id=pid,
        session_id=session_id,
        symbol="EURUSD",
        position_type="BUY",
        status="CLOSED",
        entry_price=1.0,
        stop_loss=0.99,
        take_profit=1.02,
        volume=0.1,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        realized_pnl_usd=pnl,
        is_winner=is_winner,
    )


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        s.add_all(
            [
                TradingAccount(
                    account_id="acc1",
                    broker_name="DemoCent",
                    account_number="12345",
                    account_type="DEMO",
                    balance=2000.0,
                    equity=1985.0,
                    leverage=500,
                    currency="USD",
                    is_active=True,
                ),
                _open_pos("o1", 10.0),
                _open_pos("o2", 12.5),
                # Stored counters are stale (10/40%); real derived stats come
                # from the 3 linked closed positions below: 2 wins / 1 loss.
                _closed_pos("c1", "sess1", 20.0, True),
                _closed_pos("c2", "sess1", 10.0, True),
                _closed_pos("c3", "sess1", -15.0, False),
                TradingSession(
                    session_id="sess1",
                    account_id="acc1",
                    status="CLOSED",
                    trading_type="day_trading",
                    start_time=datetime(2026, 6, 1, tzinfo=UTC).replace(tzinfo=None),
                    total_trades=10,
                    winning_trades=4,
                    losing_trades=6,
                    win_rate=40.0,
                    total_pnl_usd=-15.0,
                    profit_factor=0.8,
                    max_drawdown=20.0,
                ),
            ]
        )
        await s.commit()

    async def override_session():
        async with sm() as s:
            yield s

    monkeypatch.setattr("trading_api.routers.account.currency_unit", lambda: "USD")
    monkeypatch.setattr("trading_api.routers.sessions.currency_unit", lambda: "USD")
    monkeypatch.setattr("trading_api.app._engine", lambda: engine)
    app = create_app()
    app.dependency_overrides[deps.get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_account_summary(client):
    body = (await client.get("/api/v1/account/summary")).json()
    assert body["balance"] == 2000.0
    assert body["equity"] == 1985.0
    assert body["open_count"] == 2
    assert body["total_exposure"] == 22.5  # 10 + 12.5
    assert body["currency_unit"] == "USD"


@pytest.mark.asyncio
async def test_sessions_paginated(client):
    body = (await client.get("/api/v1/sessions")).json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["session_id"] == "sess1"
    # Derived from the 3 linked closed positions, NOT the stale stored counters.
    assert row["total_trades"] == 3
    assert row["winning_trades"] == 2
    assert row["win_rate"] == 66.7
    assert row["total_pnl_usd"] == 15.0
    assert row["profit_factor"] == 2.0  # gross_profit 30 / gross_loss 15


@pytest.mark.asyncio
async def test_current_session_none_when_no_active(client):
    # All seeded sessions are CLOSED → no active session.
    body = (await client.get("/api/v1/sessions/current")).json()
    assert body is None
