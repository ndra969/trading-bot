"""FastAPI app factory for the read-only dashboard BFF.

Bind to 127.0.0.1 only in phase 1 (no auth). A single-token header check is
the documented gate to add before any non-local exposure.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from trading_api.deps import _engine
from trading_api.routers import config, positions
from trading_api.schemas import Health


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Bot Dashboard API",
        version="0.1.0",
        description="Read-only BFF over the bot's PostgreSQL. No mutations.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(positions.router)
    app.include_router(config.router)

    @app.get("/api/v1/health", response_model=Health, tags=["health"])
    async def health() -> Health:
        db_ok = True
        try:
            async with _engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        return Health(status="ok" if db_ok else "degraded", database=db_ok)

    return app


app = create_app()
