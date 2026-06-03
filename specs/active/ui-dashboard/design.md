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
│           ├── signals.py     analytics.py  config.py
├── apps/
│   └── dashboard/                  # ← THIS SPEC fills it (Next.js)
│       ├── app/                    # App Router pages
│       │   ├── page.tsx            # overview
│       │   ├── positions/page.tsx
│       │   ├── history/page.tsx
│       │   ├── analytics/page.tsx
│       │   └── tuning/page.tsx     # ← confluence distribution + thresholds
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
| `GET /api/v1/positions/closed?limit=&symbol=&since=&exit_type=&close_reason=` | Closed-trade history with close_reason, exit_type, P&L, holding time |
| `GET /api/v1/positions/{position_id}` | **Single-trade drill-down**: full quality metrics (MAE/MFE, slippage, entry→SL/TP pips, max_profit/drawdown, breakeven/trailing activated, holding time) + confluence breakdown (foundation_share, enhancement_share, per-layer raw confidences, active layers) |
| `GET /api/v1/account/summary` | Balance, equity, currency unit, open count, total exposure |
| `GET /api/v1/sessions?limit=` | Trading sessions with aggregations (trades, win_rate, P&L) |
| `GET /api/v1/signals/recent?limit=` | Recent signals (if persisted) or last-N from positions |
| `GET /api/v1/analytics/by-asset` | Per-asset-class WR, avg P&L, count |
| `GET /api/v1/analytics/by-session` | Per-market-session WR (tokyo/london/ny) |
| `GET /api/v1/analytics/by-close-reason` | Breakdown by CloseReason enum |
| `GET /api/v1/analytics/by-exit-type` | Counts + P&L by WIN / LOSS / BREAKEVEN (sanity-check classification & R-multiple) |
| `GET /api/v1/analytics/equity-curve?since=` | Cumulative realized P&L series for chart |
| **Tuning endpoints** | |
| `GET /api/v1/analytics/confluence-distribution?asset_class=&bucket=` | Histogram of `confluence_score` per asset class (+ overall min/p50/max), for overlaying the threshold line |
| `GET /api/v1/analytics/confluence-vs-outcome?asset_class=` | Win-rate + avg P&L per confluence bucket, and WIN-avg vs LOSS-avg confluence — answers "does confluence predict outcome?" (it didn't pre-fix) |
| `GET /api/v1/analytics/layer-contribution?asset_class=` | Per enhancement layer: how often it participated + its avg contribution (exposes dead layers like rsi/structure/breakout) |
| `GET /api/v1/config/thresholds` | Current `quality_thresholds` + `volatility_filter` + `confluence_weights` from the loaded YAML (read-only) so the UI can draw the active gate over the distribution |
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
- Nav menu (left rail), ordered for a position-analysis workflow:
  **Overview → Positions → History → Analytics → Tuning**.
- Pages:
  - **Overview**: account summary cards, open positions table, equity
    curve, today's P&L.
  - **Positions**: live open positions with P&L + confluence; row click
    opens the trade drill-down drawer.
  - **History**: closed trades table with filters (symbol, `exit_type`,
    `close_reason`, date); close_reason + exit_type breakdown charts; row
    click → **trade drill-down** (`/positions/{id}`) showing every
    quality metric + the confluence/per-layer breakdown for that trade.
  - **Analytics**: WR + P&L by asset / session / close_reason /
    exit_type; equity curve.
  - **Tuning** (the strategy-tuning surface): asset-class selector, then
    (1) confluence-score histogram with the **current threshold drawn as
    a vertical line** (from `/config/thresholds`); (2) win-rate per
    confluence bucket + WIN-avg vs LOSS-avg confluence (does it predict?);
    (3) per-layer contribution bars (which layers actually fire). Purely
    read-only — surfaces the evidence; the operator edits YAML by hand.
- Trade drill-down is a shared component (drawer/modal) used by both
  Positions and History, backed by `GET /positions/{id}`.
- Env: `NEXT_PUBLIC_API_BASE` points at the FastAPI host
  (`http://localhost:8000`).

## Data source notes

- Bot already persists positions, sessions, accounts to PostgreSQL.
- `market_session`, `confluence_score`, `close_reason`, `exit_type`,
  `is_winner`, `slippage_pips`, `mae_pips`, `mfe_pips`,
  `holding_time_seconds`, `entry_to_sl_pips`, `entry_to_tp_pips`,
  `breakeven_activated`, `trailing_activated` are all columns on
  `positions` → analytics + drill-down endpoints use them directly.
- Equity curve = cumulative sum of closed `realized_pnl_usd` ordered by
  `close_time` (use the frozen realized value, not the mutable
  `current_pnl_usd`).
- **Confluence breakdown persistence (Goal 7, worker change).** The
  per-layer split is NOT in the DB today — `meta_data.strategy_scores`
  only echoes the total. The worker must, at signal creation (where
  `_build_strategy_result` assembles `meta_data`), also store:
  `meta_data["confluence_breakdown"] = {foundation_share,
  enhancement_share, raw_confidences: {layer: conf}, active_layers: [...]}`.
  `/positions/{id}` and `/analytics/layer-contribution` read this.
  Backfill is impossible for old rows (data is gone) → those simply show
  "breakdown unavailable"; new trades carry it. Snapshot-test the signal
  path to prove scoring math is unchanged by the added write.
- `/config/thresholds` reads the same loaded YAML the worker uses
  (`config/strategy_parameters.yaml` → `signal_generation`), surfaced
  read-only. Do NOT re-read files per request — load once at app start.

## Test impact

The API is a first-class testable component — not an afterthought. The
bot has tests; the API must too.

- **API unit tests are mandatory** (`packages/api/tests/` or
  `tests/api/`), gating the same way bot tests gate. Target ≥85%
  coverage on `trading_api`.
- **FastAPI `TestClient`** for endpoint tests.
- **Mock the data layer** — patch repositories / DB session so API tests
  never hit a real DB. Each endpoint: happy path, empty-data, error,
  and currency-unit assertions.
- **syrupy snapshot assertions** for JSON response shapes. Add `syrupy`
  to the dev deps; assert each endpoint's serialized response against a
  stored snapshot so schema drift is caught automatically. Combine with
  explicit assertions for dynamic/business-critical fields (P&L math,
  currency unit) that snapshots shouldn't mask.
- **Maintainable + testable design**: thin routers, logic in small
  testable functions/services, dependency-injected DB session so it's
  trivially mockable. No business logic inline in route handlers.
- Frontend: component tests optional in phase 1 (not gating), but the
  `lib/api.ts` client should be structured to allow them later.

## Rollback plan

Dashboard is purely additive. To remove: delete `packages/api/`,
`apps/dashboard/`, their tests, and the gitignore lines. Worker untouched.

## What "done" looks like

- `uv run uvicorn trading_api.app:app --port 8000` serves all endpoints
  with live data.
- `cd apps/dashboard && npm run dev` renders the overview with real
  positions and a working equity curve.
- New positions/closes appear within one poll interval.
- Tuning page shows the confluence histogram + current threshold line +
  WR-by-bucket for a selected asset class.
- A closed trade can be drilled to its full quality + confluence
  breakdown.
- Backend tests pass; bot tests unchanged (signal-path snapshot proves
  the breakdown write didn't alter scoring).
- README/docs note how to run the dashboard.
