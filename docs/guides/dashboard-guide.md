# Dashboard Guide

Read-only web dashboard for monitoring the bot and tuning the strategy.
Two processes, fully independent of the trading bot — they share only the
database.

```
Next.js (apps/dashboard) ──/api/proxy/*──▶ FastAPI (packages/api) ──read-only──▶ PostgreSQL
        :3000                                      :8000                          (bot's DB)
```

The bot keeps running untouched; killing the dashboard or API never affects it.

## Run locally

**1. API** (read-only FastAPI BFF):

```bash
uv run uvicorn trading_api.app:app --port 8000
# Swagger: http://localhost:8000/docs
```

It reads `DATABASE_URL` from the active env (`.env.dev` by default; set
`TRADING_ENV=production` to point at prod).

**2. Frontend** (Next.js):

```bash
cd apps/dashboard
cp .env.local.example .env.local      # API_URL=http://localhost:8000
npm install
npm run dev                            # http://localhost:3000
```

The browser only ever talks to Next.js; the `/api/proxy/[...path]` route
forwards server-to-server to `API_URL`, so there is no CORS and the API URL
stays server-side.

## Pages

| Page | What it shows |
|------|---------------|
| Overview | Account cards (balance/equity/open/exposure) + open positions + unrealized P&L (3 s live) |
| Positions | Open positions; row → drill-down drawer |
| History | Paginated closed trades + symbol/outcome filters; row → drawer (MAE/MFE, slippage, confluence breakdown) |
| Analytics | Per-symbol P&L (worst-first), by-exit-type, equity curve |
| Tuning | Per-asset confluence histogram + active threshold line, WIN-vs-LOSS avg confluence, layer contribution |
| Rejections | Why setups were blocked: by-reason, per-symbol×reason, recent feed |

All analytics/tuning/rejection views accept a time range (24h/7d/30d/all).

## Tuning workflow

The dashboard surfaces both halves of the signal: **taken trades**
(confluence breakdown) and **rejected setups** (rejection telemetry). Use it
to decide threshold changes evidence-first:

1. **Tuning** → pick an asset class. Read the confluence distribution vs the
   current threshold line, and WIN-avg vs LOSS-avg confluence (if close,
   confluence isn't predicting outcome).
2. **Rejections** → see which gate blocks the most setups and at what
   confluence (e.g. high-confluence setups blocked by `price_action_required`).
3. Edit the values in `config/strategy_parameters.yaml`
   (`signal_generation.quality_thresholds` / `volatility_filter` /
   `commodity_gates`) and restart the bot. The Tuning view is **read-only** —
   it shows the evidence, you make the change.

> Both `confluence_breakdown` (per-trade) and `signal_rejections` only start
> filling from the moment that observability shipped — old rows show
> "breakdown unavailable" and analytics report a `coverage` fraction.

## Auth (before remote exposure)

Phase 1 binds localhost with no auth. Before exposing the API beyond
localhost, set a shared token:

```bash
# API side
export DASHBOARD_API_TOKEN=<random-secret>     # or dashboard.api_token in YAML
# Frontend side (server env for the proxy)
echo "DASHBOARD_API_TOKEN=<same-secret>" >> apps/dashboard/.env.local
```

When set, every request except `/api/v1/health` and the docs must carry a
matching `X-Dashboard-Token` header (the proxy adds it automatically).

## Tests

```bash
uv run pytest tests/api/                 # API (httpx + in-memory SQLite)
cd apps/dashboard && npm run build       # frontend type-check + build
```
