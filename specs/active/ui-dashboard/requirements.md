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
   + Next.js frontend in one repo.
2. Read-only REST API over the existing PostgreSQL data the bot writes.
3. Dashboard pages: live positions, closed-trade history, account /
   equity summary, recent signals, per-asset/per-session analytics.
4. Cent-account aware display (USC vs USD) consistent with the bot's
   `account_currency_unit` logic.

## Non-goals

- No control/mutation endpoints (close, modify, start, stop). Read-only.
- No WebSocket / live tick streaming (polling only).
- No multi-user accounts / RBAC (single-operator dashboard).
- No change to bot trading logic — dashboard is a pure consumer.
- No cloud deployment automation in this phase (run locally first).

## Success criteria

- `uv run uvicorn trading_bot.api.app:app` serves read-only JSON
  endpoints backed by the live DB.
- `cd frontend && npm run dev` serves the dashboard; it shows real data
  from the running bot's PostgreSQL.
- Dashboard reflects new positions / closes within one poll interval.
- Backend has unit tests (≥85% coverage on new `api/` code), reusing
  existing repositories where possible.
- Zero impact on bot: starting/stopping the dashboard never touches MT5
  or bot process state.
- P&L / balance figures show the correct currency unit (USC for cent).

## Constraints

- Bot is **live** — the API must be strictly read-only against the DB;
  no writes, no locks that could block the bot's writes.
- Reuse existing SQLAlchemy models + repositories
  (`data/repositories/*`) rather than duplicating queries.
- Monorepo restructure must not break existing imports, tests, alembic,
  or the `trading-bot` CLI entry point.
- Next.js build artifacts (`frontend/.next`, `node_modules`) must be
  gitignored — don't bloat the repo.
- Keep Python and JS toolchains independent (uv for Python, npm/pnpm
  for frontend); no cross-coupling in build.

## Risk register

| Risk | Mitigation |
|------|------------|
| Dashboard DB reads contend with bot writes | Use a separate read-only connection pool; short-lived queries; never hold transactions |
| Monorepo restructure breaks bot imports/CLI | No move of `src/trading_bot/`; only ADD `api/` submodule + `frontend/` dir. Run full test suite after |
| Frontend secrets (DB creds) leak to client | BFF pattern — frontend only talks to FastAPI, never DB directly. DB creds stay server-side |
| Currency unit shown wrong (USC vs USD) | API returns both raw value + unit; reuse bot's cent-detection logic |
| Scope creep into control features | Hard non-goal; revisit control in a separate spec after read-only ships |
| Exposing API on network without auth | Default bind to localhost; add simple token auth before any non-local exposure (flagged in design) |

## Open questions

- Where does FastAPI live: `src/trading_bot/api/` (shares package) or a
  separate top-level `backend/`? → design.md.
- Auth needed for localhost-only phase 1? → design.md (likely none, but
  document the gate for later remote exposure).
- Chart library for equity curve / candles? → design.md.
- Does the API read the SAME PostgreSQL the live bot uses, or a replica?
  → design.md (same DB, read-only pool for phase 1).

## Related

- Existing repositories: `src/trading_bot/data/repositories/`
- Cent-account logic: `TradingBot.account_currency_unit` (commit `484d995`)
- Deps already present: `fastapi`, `uvicorn` in `pyproject.toml`
- [database-erd](../../docs/architecture/database-erd.md) — schema reference
