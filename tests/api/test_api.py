"""Read-only dashboard API tests (in-memory SQLite, no real DB)."""

from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
import trading_api.deps as deps
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from trading_api.app import create_app
from trading_core.data.database import Base
from trading_core.data.models import Position


def _position(**over):
    base = {
        "position_id": "pos_open",
        "symbol": "EURUSD",
        "position_type": "BUY",
        "status": "OPEN",
        "entry_price": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1150,
        "current_price": 1.1020,
        "volume": 0.1,
        "pip_size": 0.0001,
        "pip_value_per_lot": 10.0,
        "current_pnl_usd": 20.0,
        "current_profit_pips": 20.0,
        "confluence_score": 66.0,
        "asset_class": "forex_major",
        "open_time": datetime(2026, 6, 1, tzinfo=UTC).replace(tzinfo=None),
    }
    base.update(over)
    return Position(**base)


def _sample():
    return [
        _position(),
        _position(
            position_id="pos_closed",
            symbol="XAGUSD",
            position_type="SELL",
            status="CLOSED",
            asset_class="commodities",
            exit_type="LOSS",
            close_reason="STOP_LOSS",
            is_winner=False,
            realized_pnl_usd=-18.5,
            realized_profit_pips=-30.0,
            confluence_score=61.7,
            holding_time_seconds=3600,
            close_time=datetime(2026, 6, 2, tzinfo=UTC).replace(tzinfo=None),
            meta_data={
                "market_session": "london_ny_overlap",
                "confluence_breakdown": {
                    "foundation_share": 45.3,
                    "enhancement_share": 16.4,
                    "raw_confidences": {"ma": 50.0, "price_action": 70.0},
                    "active_layers": ["ma", "price_action"],
                },
            },
        ),
    ]


@pytest_asyncio.fixture
async def client(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as s:
        s.add_all(_sample())
        await s.commit()

    async def override_session():
        async with sm() as s:
            yield s

    monkeypatch.setattr("trading_api.routers.positions.currency_unit", lambda: "USD")
    monkeypatch.setattr("trading_api.app._engine", lambda: engine)

    class _Cfg:
        def get(self, key, default=None):
            return {
                "signal_generation": {
                    "quality_thresholds": {"forex_major": {"min_confluence_score": 62.0}},
                    "volatility_filter": {"forex_major": {"climax_multiplier": 2.0}},
                    "commodity_gates": {"rejection_wick": {"buy": {"min_ratio": 0.15}}},
                },
                "confluence_weights": {"foundation": 0.30},
            }.get(key, default)

    monkeypatch.setattr("trading_api.routers.config.get_config", lambda: _Cfg())

    app = create_app()
    app.dependency_overrides[deps.get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["database"] is True


@pytest.mark.asyncio
async def test_open_positions(client):
    r = await client.get("/api/v1/positions/open")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["position_id"] == "pos_open"
    assert data[0]["currency_unit"] == "USD"


@pytest.mark.asyncio
async def test_closed_positions_paginated(client):
    r = await client.get("/api/v1/positions/closed")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["items"][0]["exit_type"] == "LOSS"


@pytest.mark.asyncio
async def test_closed_filter_by_exit_type(client):
    r = await client.get("/api/v1/positions/closed", params={"exit_type": "WIN"})
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_position_detail_with_breakdown(client):
    r = await client.get("/api/v1/positions/pos_closed")
    assert r.status_code == 200
    body = r.json()
    assert body["market_session"] == "london_ny_overlap"
    assert body["confluence_breakdown"]["active_layers"] == ["ma", "price_action"]


@pytest.mark.asyncio
async def test_position_detail_without_breakdown(client):
    r = await client.get("/api/v1/positions/pos_open")
    assert r.status_code == 200
    assert r.json()["confluence_breakdown"] is None


@pytest.mark.asyncio
async def test_position_detail_404(client):
    r = await client.get("/api/v1/positions/nope")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_config_thresholds(client):
    r = await client.get("/api/v1/config/thresholds")
    assert r.status_code == 200
    body = r.json()
    assert body["quality_thresholds"]["forex_major"]["min_confluence_score"] == 62.0
    assert body["commodity_gates"]["rejection_wick"]["buy"]["min_ratio"] == 0.15
