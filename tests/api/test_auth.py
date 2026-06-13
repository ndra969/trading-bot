"""Tests for the optional X-Dashboard-Token gate."""

import httpx
import pytest
import pytest_asyncio
import trading_api.deps as deps
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from trading_api.app import create_app
from trading_core.data.database import Base


@pytest_asyncio.fixture
async def make_client(monkeypatch):
    """Return a builder that yields a client with an optional configured token."""
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with sm() as s:
            yield s

    monkeypatch.setattr("trading_api.routers.positions.currency_unit", lambda: "USD")
    monkeypatch.setattr("trading_api.app._engine", lambda: engine)

    def build(token):
        monkeypatch.setattr("trading_api.app.dashboard_token", lambda: token)
        app = create_app()
        app.dependency_overrides[deps.get_session] = override_session
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://t"
        )

    yield build
    await engine.dispose()


@pytest.mark.asyncio
async def test_no_token_configured_is_open(make_client):
    async with make_client(None) as c:
        assert (await c.get("/api/v1/positions/open")).status_code == 200


@pytest.mark.asyncio
async def test_token_required_rejects_missing_header(make_client):
    async with make_client("secret") as c:
        r = await c.get("/api/v1/positions/open")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_token_required_rejects_wrong_header(make_client):
    async with make_client("secret") as c:
        r = await c.get("/api/v1/positions/open", headers={"X-Dashboard-Token": "nope"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_token_accepts_correct_header(make_client):
    async with make_client("secret") as c:
        r = await c.get("/api/v1/positions/open", headers={"X-Dashboard-Token": "secret"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_exempt_even_with_token(make_client):
    async with make_client("secret") as c:
        assert (await c.get("/api/v1/health")).status_code == 200
