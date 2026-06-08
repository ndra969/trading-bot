"""FastAPI app factory for the read-only dashboard BFF.

Bind to 127.0.0.1 only in phase 1 (no auth). A single-token header check is
the documented gate to add before any non-local exposure.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from trading_api.deps import _engine, dashboard_token
from trading_api.routers import account, analytics, config, positions, rejections, sessions
from trading_api.schemas import Health

# Paths reachable without a token even when one is configured (liveness + docs).
_AUTH_EXEMPT = ("/api/v1/health", "/docs", "/redoc", "/openapi.json")


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

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        """Enforce X-Dashboard-Token only when a token is configured.

        No token (localhost default) → open. Set DASHBOARD_API_TOKEN before
        exposing the API beyond localhost.
        """
        token = dashboard_token()
        if token and not request.url.path.startswith(_AUTH_EXEMPT):
            if request.headers.get("X-Dashboard-Token") != token:
                return JSONResponse(
                    {"detail": "invalid or missing X-Dashboard-Token"}, status_code=401
                )
        return await call_next(request)

    app.include_router(positions.router)
    app.include_router(analytics.router)
    app.include_router(rejections.router)
    app.include_router(account.router)
    app.include_router(sessions.router)
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
