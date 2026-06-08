"""Endpoint tests for analytics + rejections routers (in-memory SQLite)."""

from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
import trading_api.deps as deps
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from trading_api.app import create_app
from trading_core.data.database import Base
from trading_core.data.models import Position, SignalRejection


def _pos(pid, symbol, asset, exit_type, pnl, conf, ts, **meta):
    return Position(
        position_id=pid,
        symbol=symbol,
        position_type="SELL",
        status="CLOSED",
        entry_price=1.0,
        stop_loss=1.1,
        take_profit=0.8,
        volume=0.1,
        pip_size=0.0001,
        pip_value_per_lot=10.0,
        asset_class=asset,
        exit_type=exit_type,
        close_reason="STOP_LOSS" if pnl < 0 else "TAKE_PROFIT",
        is_winner=pnl > 0,
        realized_pnl_usd=pnl,
        realized_profit_pips=pnl,
        confluence_score=conf,
        holding_time_seconds=3600,
        close_time=datetime(2026, 6, ts, tzinfo=UTC).replace(tzinfo=None),
        meta_data=meta or {},
    )


def _seed_positions():
    return [
        _pos("p1", "XAGUSD", "commodities", "LOSS", -20.0, 61.0, 1,
             market_session="london",
             confluence_breakdown={"raw_confidences": {"ma": 50.0, "price_action": 70.0}}),
        _pos("p2", "XAGUSD", "commodities", "WIN", 12.0, 66.0, 2,
             market_session="ny",
             confluence_breakdown={"raw_confidences": {"ma": 40.0}}),
        _pos("p3", "EURUSD", "forex_major", "LOSS", -5.0, 44.0, 3, market_session="london"),
        _pos("p4", "EURUSD", "forex_major", "WIN", 8.0, 63.0, 4),  # no breakdown, no session
    ]


def _seed_rejections():
    mk = lambda sym, stage, conf, ac="commodities": SignalRejection(  # noqa: E731
        symbol=sym, asset_class=ac, direction="SELL", stage=stage, confluence_score=conf, details={}
    )
    return [
        mk("XAGUSD", "climax", 55.0),
        mk("XAGUSD", "climax", 57.0),
        mk("XAGUSD", "confluence_too_low", 40.0),
        mk("EURUSD", "confluence_too_low", 41.0, ac="forex_major"),
    ]


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        s.add_all(_seed_positions() + _seed_rejections())
        await s.commit()

    async def override_session():
        async with sm() as s:
            yield s

    monkeypatch.setattr("trading_api.routers.analytics.currency_unit", lambda: "USD")
    monkeypatch.setattr("trading_api.app._engine", lambda: engine)
    app = create_app()
    app.dependency_overrides[deps.get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_by_symbol_sorted_worst_first(client):
    r = await client.get("/api/v1/analytics/by-symbol")
    rows = r.json()
    assert r.status_code == 200
    assert rows[0]["key"] == "XAGUSD"  # net -8 worst
    assert rows[0]["total_pnl"] == -8.0
    assert rows[0]["win_rate"] == 50.0


@pytest.mark.asyncio
async def test_by_asset_and_session(client):
    assert {r["key"] for r in (await client.get("/api/v1/analytics/by-asset")).json()} == {
        "commodities",
        "forex_major",
    }
    sessions = {r["key"] for r in (await client.get("/api/v1/analytics/by-session")).json()}
    assert "london" in sessions and "unknown" in sessions  # p4 has no session


@pytest.mark.asyncio
async def test_equity_curve_cumulative(client):
    r = await client.get("/api/v1/analytics/equity-curve")
    pts = r.json()
    assert [p["cumulative_pnl"] for p in pts] == [-20.0, -8.0, -13.0, -5.0]


@pytest.mark.asyncio
async def test_confluence_distribution_and_vs_outcome(client):
    d = (await client.get("/api/v1/analytics/confluence-distribution")).json()
    assert d["max"] == 66.0 and d["min"] == 44.0
    b60 = next(b for b in d["buckets"] if b["bucket"] == "60-70")
    assert b60["count"] == 3  # 61, 66, 63

    vo = (await client.get("/api/v1/analytics/confluence-vs-outcome")).json()
    assert vo["win_avg_confluence"] == 64.5  # (66+63)/2
    assert vo["loss_avg_confluence"] == 52.5  # (61+44)/2


@pytest.mark.asyncio
async def test_layer_contribution_coverage(client):
    r = (await client.get("/api/v1/analytics/layer-contribution")).json()
    assert r["sample"] == 2  # p1, p2 have breakdown
    assert r["coverage"] == round(2 / 4, 3)
    ma = next(row for row in r["rows"] if row["layer"] == "ma")
    assert ma["participation_rate"] == 1.0


@pytest.mark.asyncio
async def test_rejections_by_reason(client):
    rows = (await client.get("/api/v1/rejections/by-reason")).json()
    climax = next(r for r in rows if r["stage"] == "climax")
    assert climax["count"] == 2
    assert climax["avg_confluence"] == 56.0


@pytest.mark.asyncio
async def test_rejections_by_symbol_and_filter(client):
    rows = (await client.get("/api/v1/rejections/by-symbol")).json()
    assert any(r["symbol"] == "XAGUSD" and r["stage"] == "climax" and r["count"] == 2 for r in rows)
    # asset_class filter
    fx = (await client.get("/api/v1/rejections/by-symbol", params={"asset_class": "forex_major"})).json()
    assert {r["symbol"] for r in fx} == {"EURUSD"}


@pytest.mark.asyncio
async def test_rejections_recent_paginated(client):
    body = (await client.get("/api/v1/rejections/recent", params={"limit": 2})).json()
    assert body["total"] == 4
    assert len(body["items"]) == 2
    assert body["limit"] == 2
