# UI Dashboard — Requirements

**Status**: 📋 Planned
**Priority**: 🟠 Medium (visibility into live bot)
**Date**: 2026-05-28

## Context

The trading bot currently exposes state only through CLI commands, logs,
and Telegram notifications. The user wants a visual dashboard to monitor
positions, P&L, signals, and account health at a glance. `pyproject.toml`
already carries `fastapi` + `uvicorn` deps (tagged "optional dashboard"),
so the intent predates this spec.

This requires turning the single-package Python repo into a **monorepo**
that also houses a frontend, without disrupting the live bot.

## Decisions locked (from user)

- **Scope**: Read-only monitoring. No control actions (no start/stop,
  no close-position buttons) in this phase. Bot stays CLI-controlled.
- **Data freshness**: Polling (frontend fetches every few seconds). No
  WebSocket / real-time push in this phase.
- **Frontend**: React via **Next.js** (App Router).

## Goals

1. Monorepo structure: Python bot + FastAPI backend-for-frontend (BFF)
   + Next.js frontend in one repo. **(DONE — `monorepo-restructure`
   landed; `packages/{core,worker,api}` + `apps/dashboard` exist.)**
2. Read-only REST API over the existing PostgreSQL data the bot writes.
3. Dashboard pages: live positions, closed-trade history, account /
   equity summary, recent signals, per-asset/per-session analytics.
4. Cent-account aware display (USC vs USD) consistent with the bot's
   `account_currency_unit` logic.
5. **Deep position analysis**: every closed trade is drillable to its
   full quality metrics — `exit_type` (WIN/LOSS/BREAKEVEN),
   `close_reason`, MAE/MFE, holding time, slippage, entry→SL/TP pips,
   breakeven/trailing activation, confluence + per-layer breakdown.
6. **Strategy-tuning visibility (read-only)**: surface the data needed to
   tune thresholds *without guessing from logs/DB by hand*. Specifically a
   "Tuning" view showing, per asset class: the confluence-score
   distribution with the **current config threshold drawn as a line**,
   win-rate by confluence bucket (does confluence predict outcome?), and
   per-layer contribution (which layers actually fire). This directly
   serves [confluence-scoring-investigation](../confluence-scoring-investigation/requirements.md)
   and [strategy-tuning](../strategy-tuning.md): we lowered thresholds
   blind once and bled — the UI must make the next tune evidence-based.
7. **Persist the confluence breakdown** the tuning view needs. Today only
   the total `confluence_score` (+ a `strategy_scores` blob that just
   echoes the total) reaches the DB; the foundation-vs-enhancement split
   and per-layer raw confidences live only in transient logs. The worker
   must write `foundation_share`, `enhancement_share`, per-layer raw
   confidences, and the list of active layers into `positions.meta_data`
   at signal creation so the API can serve them. This is the
   observability gap that forced the manual log-spelunking during the
   2026-06-02 loss investigation.

## Non-goals

- No control/mutation endpoints (close, modify, start, stop). Read-only.
- No WebSocket / live tick streaming (polling only).
- No multi-user accounts / RBAC (single-operator dashboard).
- No change to bot trading **logic** — the only worker change allowed is
  *observability* (Goal 7: persist the confluence breakdown to
  `meta_data`). Signal generation, scoring math, and execution behaviour
  stay byte-for-byte identical.
- No editing config / thresholds from the UI in this phase. The Tuning
  view is **read-only**: it shows distributions + the current YAML
  threshold so the operator decides the value, then edits the YAML by
  hand. Write-back to config is a deliberate later phase (own spec).
- No cloud deployment automation in this phase (run locally first).

## Success criteria

- `uv run uvicorn trading_api.app:app` serves read-only JSON
  endpoints backed by the live DB.
- `cd apps/dashboard && npm run dev` serves the dashboard; it shows real
  data from the running bot's PostgreSQL.
- Dashboard reflects new positions / closes within one poll interval.
- **Tuning view**: for a chosen asset class, the operator can read the
  confluence distribution, see the current threshold line, and read
  win-rate per confluence bucket — enough to decide the next threshold
  without touching logs or the DB directly.
- **Trade drill-down**: clicking a closed trade shows its full quality
  metrics + confluence/per-layer breakdown.
- Backend has unit tests (≥85% coverage on `trading_api`), gating like
  the bot's tests — FastAPI TestClient, mocked data layer, and syrupy
  snapshot assertions on response shapes. The API is NOT exempt from
  tests. Code maintainable + testable: thin routers, DI'd DB session,
  logic in small mockable functions (no business logic inline in handlers).
- Zero impact on bot: starting/stopping the dashboard never touches MT5
  or bot process state.
- P&L / balance figures show the correct currency unit (USC for cent).

## Constraints

- Bot is **live** — the API must be strictly read-only against the DB;
  no writes, no locks that could block the bot's writes.
- Reuse existing SQLAlchemy models + repositories
  (`packages/core/src/trading_core/data/repositories/*`) rather than
  duplicating queries.
- Monorepo restructure must not break existing imports, tests, alembic,
  or the `trading-bot` CLI entry point.
- Next.js build artifacts (`apps/dashboard/.next`, `node_modules`) must
  be gitignored — don't bloat the repo.
- Keep Python and JS toolchains independent (uv for Python, npm/pnpm
  for frontend); no cross-coupling in build.

## Risk register

| Risk | Mitigation |
|------|------------|
| Dashboard DB reads contend with bot writes | Use a separate read-only connection pool; short-lived queries; never hold transactions |
| Worker observability write (Goal 7) regresses signal logic | Persist breakdown only where `meta_data` is already assembled at signal creation; no change to scoring/branching. Snapshot-test the signal path before/after |
| Frontend secrets (DB creds) leak to client | BFF pattern — frontend only talks to FastAPI, never DB directly. DB creds stay server-side |
| Currency unit shown wrong (USC vs USD) | API returns both raw value + unit; reuse bot's cent-detection logic |
| Scope creep into control features | Hard non-goal; revisit control in a separate spec after read-only ships |
| Exposing API on network without auth | Default bind to localhost; add simple token auth before any non-local exposure (flagged in design) |

## Open questions

- Auth needed for localhost-only phase 1? → design.md (likely none, but
  document the gate for later remote exposure).
- Chart library for equity curve / candles? → design.md.
- Does the API read the SAME PostgreSQL the live bot uses, or a replica?
  → design.md (same DB, read-only pool for phase 1).
- ~~Where does FastAPI live?~~ **Resolved**: `packages/api/src/trading_api/`
  (skeleton already exists from the monorepo restructure).

## Related

- Existing repositories:
  `packages/core/src/trading_core/data/repositories/`
- Cent-account logic: `TradingBot.account_currency_unit` (commit `484d995`)
- Deps already present: `fastapi`, `uvicorn` in `pyproject.toml`
- [confluence-scoring-investigation](../confluence-scoring-investigation/requirements.md)
  — the analysis the Tuning view operationalises
- [strategy-tuning](../strategy-tuning.md) — tuning rounds this view supports
- [database-erd](../../../docs/architecture/database-erd.md) — schema reference
