"""Shared FastAPI dependencies: read-only DB session, config, currency unit.

The API is a separate process from the bot. It opens its OWN read-only async
engine against the same database the bot writes to — short-lived sessions,
no writes, never holding transactions that could block the bot.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from functools import lru_cache

from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from trading_core.config import Configuration

# ---------------------------------------------------------------------------
# Config (loaded once at startup)
# ---------------------------------------------------------------------------


@lru_cache
def get_config() -> Configuration:
    """Load the bot configuration once (same YAML the worker reads)."""
    import os

    return Configuration(env=os.getenv("TRADING_ENV", "development"))


@lru_cache
def _engine():
    cfg = get_config()
    url = cfg.get("database.url")
    if not url:
        raise RuntimeError("database.url not configured")
    # Read-only intent: no pooling surprises, short-lived sessions.
    return create_async_engine(url, echo=False, pool_pre_ping=True)


@lru_cache
def _sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a short-lived read-only async session."""
    async with _sessionmaker()() as session:
        yield session


# ---------------------------------------------------------------------------
# Currency unit (USC for cent accounts, else USD)
# ---------------------------------------------------------------------------


@lru_cache
def currency_unit() -> str:
    """Display unit derived from the broker name (cent accounts report USC)."""
    cfg = get_config()
    broker = (cfg.get("active_broker") or "").lower()
    return "USC" if "cent" in broker else "USD"


@lru_cache
def dashboard_token() -> str | None:
    """Optional shared secret for the API.

    Returns the configured token (env ``DASHBOARD_API_TOKEN`` or
    ``dashboard.api_token`` in YAML), or None. When None (the localhost
    default) the API is open; when set, every request except health/docs
    must send a matching ``X-Dashboard-Token`` header — the gate to enable
    before exposing the API beyond localhost.
    """
    import os

    return os.getenv("DASHBOARD_API_TOKEN") or get_config().get("dashboard.api_token")


# ---------------------------------------------------------------------------
# Shared query params
# ---------------------------------------------------------------------------


class TimeRange:
    """Optional since/until window (ISO-8601), applied by each endpoint."""

    def __init__(
        self,
        since: datetime | None = Query(None, description="ISO-8601 lower bound (inclusive)"),
        until: datetime | None = Query(None, description="ISO-8601 upper bound (exclusive)"),
    ) -> None:
        self.since = since
        self.until = until


class Pagination:
    """limit (<=500) + offset for list endpoints."""

    def __init__(
        self,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> None:
        self.limit = limit
        self.offset = offset
