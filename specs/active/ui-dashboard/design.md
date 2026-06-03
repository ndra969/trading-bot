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

## Monorepo layout

The [monorepo-restructure](../../archive/2026-05/monorepo-restructure/)
already landed: the repo is split into `packages/core` (shared data +
config), `packages/worker` (bot engine), `packages/api` (FastAPI
skeleton), and `apps/dashboard` (empty frontend dir). This spec FILLS the
`api` and `dashboard` skeletons.

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
│           ├── analytics.py   rejections.py  config.py
├── apps/
│   └── dashboard/                  # ← THIS SPEC fills it (Next.js)
│       ├── app/                    # App Router pages
│       │   ├── page.tsx            # overview
│       │   ├── positions/page.tsx
│       │   ├── history/page.tsx
│       │   ├── analytics/page.tsx  # by asset / symbol / session / reason
│       │   ├── tuning/page.tsx      # ← confluence distribution + thresholds
│       │   └── rejections/page.tsx  # ← why setups were blocked (Goal 9)
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

### Shared conventions (apply to every endpoint)

- **Time window**: any endpoint over historical data accepts optional
  `since` and `until` (ISO-8601, applied to `close_time` for closed
  trades / `created_at` for rejections). Omitted = all-time. This is what
  lets the operator compare *before vs after* a tuning change.
- **Symbol filter**: list/analytics endpoints accept optional `symbol=`.
- **Pagination** (list endpoints — `positions/closed`, `sessions`,
  `rejections/recent`): `limit` (default 50, max 500) + `offset`
  (default 0). Response is an envelope:
  `{ "items": [...], "total": <int>, "limit": <int>, "offset": <int> }`.
  Analytics/aggregate endpoints are not paginated (bounded by buckets).
- **Empty data**: return `200` with an empty `items`/series (`[]`), never
  `404`, except `positions/{id}` which returns `404` for an unknown id.
- **Currency**: every response carrying money includes a top-level
  `currency_unit` ("USC" | "USD"); see below.

### Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/positions/open` | Live open positions (symbol, type, entry, SL, TP, current price, P&L, pips, confluence) |
| `GET /api/v1/positions/closed?limit=&offset=&symbol=&since=&until=&exit_type=&close_reason=` | Paginated closed-trade history (envelope) with close_reason, exit_type, P&L, holding time |
| `GET /api/v1/positions/{position_id}` | **Single-trade drill-down**: full quality metrics (MAE/MFE, slippage, entry→SL/TP pips, max_profit/drawdown, breakeven/trailing activated, holding time) + confluence breakdown (foundation_share, enhancement_share, per-layer raw confidences, active layers). `404` if unknown |
| `GET /api/v1/account/summary` | Balance, equity, currency unit, open count, total exposure (= Σ `risk_amount_usd` of open positions = capital at risk if every open SL hits) |
| `GET /api/v1/sessions?limit=&offset=&since=&until=` | Paginated trading sessions (envelope) with aggregations (trades, win_rate, P&L) |
| **Analytics** (all accept `since`/`until`/`symbol`) | |
| `GET /api/v1/analytics/by-asset` | Per-asset-class WR, avg P&L, count |
| `GET /api/v1/analytics/by-symbol` | **Per-symbol** WR, total + avg P&L, count, avg confluence — the granularity tuning rounds actually use (e.g. XAU/XAG vs forex) |
| `GET /api/v1/analytics/by-session` | Per-market-session WR (tokyo/london/ny/overlap) |
| `GET /api/v1/analytics/by-close-reason` | Breakdown by CloseReason enum |
| `GET /api/v1/analytics/by-exit-type` | Counts + P&L by WIN / LOSS / BREAKEVEN (sanity-check classification & R-multiple) |
| `GET /api/v1/analytics/equity-curve?since=&until=&symbol=` | Cumulative realized P&L series for chart |
| **Tuning** (all accept `asset_class`/`symbol`/`since`/`until`) | |
| `GET /api/v1/analytics/confluence-distribution?asset_class=&bucket=` | Histogram of `confluence_score` (+ min/p50/max), for overlaying the threshold line |
| `GET /api/v1/analytics/confluence-vs-outcome?asset_class=` | WR + avg P&L per confluence bucket, and WIN-avg vs LOSS-avg confluence — "does confluence predict outcome?" (it didn't pre-fix) |
| `GET /api/v1/analytics/layer-contribution?asset_class=` | Per enhancement layer: participation rate + avg contribution (exposes dead layers like rsi/structure/breakout). Reads the persisted confluence breakdown (Goal 7); rows without it are excluded and the response reports `coverage` (= fraction of trades that carried a breakdown) |
| **Rejections** (Goal 9; all accept `symbol`/`asset_class`/`since`/`until`) | |
| `GET /api/v1/rejections/by-reason` | Count of rejected setups grouped by stage/reason (climax, pa_wrong_direction, anti_chase, confluence_too_low, counter_trend_gate, …), with avg confluence-at-rejection per reason |
| `GET /api/v1/rejections/by-symbol` | Rejection counts per symbol × reason — "which gate blocks the most setups on XAGUSD?" |
| `GET /api/v1/rejections/recent?limit=&offset=` | Paginated recent rejection samples (ts, symbol, direction, reason, confluence, light context) |
| **Config** | |
| `GET /api/v1/config/thresholds` | Current `signal_generation` tuning knobs from the loaded YAML, read-only, so the UI can draw the active gates over the distributions: `quality_thresholds`, `confluence_weights`, `volatility_filter` (climax multipliers), and `commodity_gates` (per-direction wick / colour / volatility-trend gates) |
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
existing repositories (`SessionRepository`, `AccountRepository`, new thin
`PositionReadRepository` / `RejectionReadRepository` for the aggregate +
time-windowed + paginated queries). Aggregation (GROUP BY asset/symbol/
bucket/reason) is pushed to SQL, not done in Python over full table scans.

### Auth (phase 1)

Default bind `127.0.0.1` only — no auth for localhost. Document a
single-token header check (`X-Dashboard-Token`) as the gate that MUST be
added before binding to `0.0.0.0` / exposing remotely. Not implemented
in phase 1, but the middleware hook is stubbed.

## Frontend design

- **Next.js App Router** + TypeScript.
- Data fetching: a small `usePoll(endpoint, intervalMs)` hook wrapping
  `fetch` with `setInterval` + cleanup. **Tiered intervals** — live data
  polls fast, slow-moving analytics poll lazily (or on demand) to avoid
  hammering the DB:
  - Overview / Positions (live): **3 s**
  - History list: **15 s**
  - Analytics / Tuning / Rejections: **60 s** (or manual "Refresh")
  No SWR/React Query required for phase 1 (can add later).
- A shared **time-range picker** (since/until, with presets: 24h / 7d /
  30d / since-date / all) lives in the page header for History, Analytics,
  Tuning, Rejections and threads `since`/`until` into their fetches — the
  before/after-a-tuning-change comparison is a first-class interaction.
- Charts: `lightweight-charts` (TradingView) for equity curve / price;
  `recharts` for bar/pie analytics. Pick one primary to limit deps.
- Nav menu (left rail), ordered for a position-analysis workflow:
  **Overview → Positions → History → Analytics → Tuning → Rejections**.
- Pages:
  - **Overview**: account summary cards (balance/equity/open count/
    exposure), open positions table, equity curve, today's P&L.
  - **Positions**: live open positions with P&L + confluence; row click
    opens the trade drill-down drawer.
  - **History**: paginated closed trades with filters (symbol,
    `exit_type`, `close_reason`, time range); close_reason + exit_type
    breakdown charts; row click → **trade drill-down** (`/positions/{id}`)
    showing every quality metric + the confluence/per-layer breakdown.
  - **Analytics**: WR + P&L by asset / **symbol** / session / close_reason
    / exit_type; equity curve. Per-symbol table is the headline (sortable
    by P&L) since tuning is symbol-driven.
  - **Tuning** (the strategy-tuning surface): asset-class selector, then
    (1) confluence-score histogram with the **current threshold drawn as
    a vertical line** (from `/config/thresholds`); (2) win-rate per
    confluence bucket + WIN-avg vs LOSS-avg confluence (does it predict?);
    (3) per-layer contribution bars (which layers actually fire) with a
    `coverage` note when historical rows lack the breakdown; (4) a
    read-only panel echoing the *active* gates (climax multipliers +
    per-direction `commodity_gates`) so the operator sees every knob.
  - **Rejections** (Goal 9): by-reason bar chart + per-symbol×reason
    matrix + a recent-rejections table, all time-windowed. Answers "what
    is blocking trades, and is it costing me good setups?".
  - Read-only banner on Tuning/Rejections: "values are edited in
    `config/strategy_parameters.yaml`; this view is read-only".
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

### Rejection telemetry (Goal 9, worker + core change)

New lightweight table `signal_rejections` (alembic migration + a model in
`trading_core.data.models`):

| column | notes |
|--------|-------|
| `id` | PK |
| `created_at` | indexed (time-window queries) |
| `symbol`, `asset_class` | indexed |
| `direction` | BUY / SELL |
| `stage` | which gate: `climax`, `pa_wrong_direction`, `anti_chase`, `confluence_too_low`, `counter_trend_gate`, `volume_burst`, `color_match`, `rejection_wick`, `rsi_gate`, `structure_gate`, … (stable enum of strings) |
| `confluence_score` | confluence at the moment of rejection (nullable — some gates fire before scoring) |
| `details` | JSON: small context (e.g. `{current_range, avg_range, threshold}`) |

Write path: a single `record_rejection(stage, position_ctx)` helper called
at each existing `return None` rejection site in the signal path. It MUST
be fire-and-forget — wrapped so any telemetry error is swallowed and never
propagates into the trade loop, and gated by config
`telemetry.rejections_enabled` (default true). The reason strings are a
shared enum reused by the API grouping so the two never drift.

Retention: prune rows older than `telemetry.rejection_retention_days`
(default 30) — a cheap periodic `DELETE`, or a capped row count. This keeps
the table bounded on a long-running bot.

Volume note: every enabled symbol can reject every loop (~1/min/symbol).
At ~10 symbols that is ~14k rows/day → trivial for Postgres with the
30-day prune. If profiling shows the INSERT adds material loop latency,
batch the writes (accumulate per cycle, one executemany at cycle end).

Coverage caveat: like the confluence breakdown, rejection telemetry only
exists from the moment Goal 9 ships — historical analysis starts empty and
fills forward. The Rejections view states the data start date.

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
  WR-by-bucket + active gates for a selected asset class.
- A closed trade can be drilled to its full quality + confluence
  breakdown.
- Analytics shows a sortable per-symbol P&L/WR table; every analytics,
  tuning and rejection view respects the time-range picker.
- History + sessions are paginated (envelope with `total`).
- Rejections page shows by-reason + per-symbol×reason + recent samples.
- Backend tests pass; bot tests unchanged — signal-path snapshot proves
  neither the breakdown write (Goal 7) nor the rejection telemetry
  (Goal 9) altered scoring or which setups are taken/rejected.
- README/docs note how to run the dashboard.
