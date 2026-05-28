# UI Dashboard — Design

## Architecture

Backend-for-frontend (BFF) pattern. Frontend never touches the DB or MT5
directly — it only calls the FastAPI read-only API, which queries the
same PostgreSQL the bot writes to.

```
┌──────────────┐   HTTP/JSON (poll)   ┌─────────────────┐   read-only   ┌────────────┐
│  Next.js     │ ───────────────────▶ │  FastAPI BFF    │ ────────────▶ │ PostgreSQL │
│  dashboard   │ ◀─────────────────── │  (api/)         │ ◀──────────── │ (bot's DB) │
└──────────────┘                      └─────────────────┘               └────────────┘
        ▲                                                                      ▲
        │ browser (localhost)                                  writes │  TradingBot (live)
                                                                      └────────────
```

The bot process and the dashboard process are fully independent. Killing
either never affects the other. They share only the database.

## Monorepo layout (Opsi 3)

⚠️ **Depends on [monorepo-restructure](../monorepo-restructure/requirements.md)**
landing first. That spec splits the repo into `packages/core` (shared
data + config), `packages/worker` (bot engine), `packages/api`
(FastAPI), and `apps/dashboard` (frontend). This dashboard spec FILLS
the `api` and `dashboard` skeletons created there.

```
trading-bot/
├── packages/
│   ├── core/src/trading_core/      # shared models/db/repositories/config
│   ├── worker/src/trading_worker/  # bot engine (unchanged behaviour)
│   └── api/src/trading_api/        # ← THIS SPEC fills it
│       ├── __init__.py
│       ├── app.py                  # FastAPI app factory + router mount
│       ├── deps.py                 # read-only DB session dependency
│       ├── schemas.py              # Pydantic response models
│       └── routers/
│           ├── positions.py  account.py  sessions.py
│           ├── signals.py     analytics.py
├── apps/
│   └── dashboard/                  # ← THIS SPEC fills it (Next.js)
│       ├── app/                    # App Router pages
│       │   ├── page.tsx            # overview
│       │   ├── positions/page.tsx
│       │   ├── history/page.tsx
│       │   └── analytics/page.tsx
│       ├── lib/api.ts              # typed fetch client + poll hook
│       ├── components/
│       └── package.json
└── packages/api/tests/             # backend tests (or tests/api/)
```

**Decision**: `trading_api` imports `trading_core.data.repositories` and
`trading_core.data.models` — both api and worker depend only on core,
never on each other (clean dependency tree). DB creds stay server-side
(BFF); the frontend only ever talks to the API.

## Tech stack (latest, mainstream)

Use current stable, widely-adopted versions — no bleeding edge, no
abandoned libs.

- **Backend**: FastAPI (latest stable) + uvicorn. Swagger UI is built in
  — FastAPI auto-serves interactive OpenAPI docs at `/docs` (and ReDoc at
  `/redoc`). Pydantic v2 response models drive the schema. No extra docs
  tooling needed.
- **DB access**: existing SQLAlchemy 2.0 async + asyncpg (reused from core).
- **Frontend**: Next.js (latest stable, App Router) + TypeScript +
  React 18+. Charts: `lightweight-charts` (TradingView) for equity/price;
  `recharts` for bar/pie analytics. Data fetching: native fetch + a small
  poll hook (add TanStack Query only if polling grows complex).
- Pin to latest stable at implementation time; prefer the most-downloaded
  option when choosing between equivalents.

## API design (read-only)

All endpoints `GET`, JSON, no mutations. Versioned under `/api/v1`.
Interactive Swagger docs auto-served at `/docs`, ReDoc at `/redoc`.

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/positions/open` | Live open positions (symbol, type, entry, SL, TP, current price, P&L, pips, confluence) |
| `GET /api/v1/positions/closed?limit=&symbol=&since=` | Closed-trade history with close_reason, P&L, holding time |
| `GET /api/v1/account/summary` | Balance, equity, currency unit, open count, total exposure |
| `GET /api/v1/sessions?limit=` | Trading sessions with aggregations (trades, win_rate, P&L) |
| `GET /api/v1/signals/recent?limit=` | Recent signals (if persisted) or last-N from positions |
| `GET /api/v1/analytics/by-asset` | Per-asset-class WR, avg P&L, count |
| `GET /api/v1/analytics/by-session` | Per-market-session WR (tokyo/london/ny) |
| `GET /api/v1/analytics/by-close-reason` | Breakdown by CloseReason enum |
| `GET /api/v1/analytics/equity-curve?since=` | Cumulative P&L series for chart |
| `GET /api/v1/health` | API + DB reachability |

### Currency unit in responses

Every monetary field returns the raw number plus a top-level
`currency_unit` ("USC" | "USD") so the frontend labels correctly. Unit
derived from the bot's broker-name cent detection (reuse the same
helper, factored into `api/deps.py` or a shared util).

### Read-only DB access

`api/deps.py` provides a FastAPI dependency yielding a SQLAlchemy async
session from a **separate engine** configured read-only where possible
(or at minimum: short-lived, autocommit-off, never writing). Reuses
existing repositories (`SessionRepository`, `AccountRepository`, a new
thin `PositionReadRepository` if needed for aggregate queries).

### Auth (phase 1)

Default bind `127.0.0.1` only — no auth for localhost. Document a
single-token header check (`X-Dashboard-Token`) as the gate that MUST be
added before binding to `0.0.0.0` / exposing remotely. Not implemented
in phase 1, but the middleware hook is stubbed.

## Frontend design

- **Next.js App Router** + TypeScript.
- Data fetching: a small `usePoll(endpoint, intervalMs)` hook wrapping
  `fetch` with `setInterval` + cleanup; default 3 s. No SWR/React Query
  required for phase 1 (can add later).
- Charts: `lightweight-charts` (TradingView) for equity curve / price;
  `recharts` for bar/pie analytics. Pick one primary to limit deps.
- Pages:
  - **Overview**: account summary cards, open positions table, equity
    curve, today's P&L.
  - **Positions**: full open positions + closed history with filters.
  - **History**: closed trades table, close_reason breakdown.
  - **Analytics**: WR by asset / session / close_reason, confluence
    distribution.
- Env: `NEXT_PUBLIC_API_BASE` points at the FastAPI host
  (`http://localhost:8000`).

## Data source notes

- Bot already persists positions, sessions, accounts to PostgreSQL.
- `market_session`, `confluence_score`, `close_reason`, `slippage_pips`
  are on positions → analytics endpoints can use them directly.
- Equity curve = cumulative sum of closed `current_pnl_usd` ordered by
  `close_time`.

## Test impact

- New `tests/unit/api/` with FastAPI `TestClient`, mocking the DB
  session / repositories. Target ≥85% on `api/`.
- No change to existing bot tests.
- Frontend: optional component tests later; not gating phase 1.

## Rollback plan

Dashboard is purely additive. To remove: delete `src/trading_bot/api/`,
`frontend/`, `tests/unit/api/`, and the gitignore lines. Bot untouched.

## What "done" looks like

- `uv run uvicorn trading_bot.api.app:app --port 8000` serves all
  endpoints with live data.
- `cd frontend && npm run dev` renders the overview with real positions
  and a working equity curve.
- New positions/closes appear within one poll interval.
- Backend tests pass; bot tests unchanged.
- README/docs note how to run the dashboard.
