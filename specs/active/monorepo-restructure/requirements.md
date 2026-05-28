# Monorepo Restructure (Opsi 3) — Requirements

**Status**: 📋 Planned
**Priority**: 🟠 Medium (prerequisite for ui-dashboard, also cleans architecture)
**Date**: 2026-05-28

## Context

The repo is a single Python package (`src/trading_bot/`) that mixes the
trading engine ("worker"), the data layer (models/db/repositories), and
config loading. Planned work (the UI dashboard) needs a second consumer
of the data layer (a FastAPI backend) plus a frontend app.

User wants a **full monorepo (Opsi 3)** with clear separation:

```
packages/core    — shared data + config (no business logic)
packages/worker  — the trading bot engine (current trading_bot, minus core)
packages/api     — dashboard backend (FastAPI), consumes core
apps/dashboard   — Next.js frontend
```

The bot is "really a worker" — a long-running process. The API is a
separate deployable. Both share the same DB schema via `core`.

## Goals

1. Split the codebase into uv-workspace packages: `core`, `worker`,
   `api` (api may be stubbed/empty until the dashboard spec runs).
2. `worker` and `api` both depend on `core`; they do NOT depend on each
   other.
3. `apps/dashboard` reserved for the Next.js frontend.
4. Bot behaviour, CLI entry point, tests, and alembic all keep working
   after the move.

## Non-goals

- No new features — pure restructure (imports + packaging only).
- No dashboard implementation here (separate ui-dashboard spec).
- No change to trading logic, strategy, risk math, or DB schema.
- No deployment/CI pipeline changes in this phase.

## What goes where

**packages/core/ → `trading_core`** (shared, no strategy logic):
- `data/models.py`, `data/database.py`, `data/repositories/`,
  `data/services/` (account sync / selector — they're data-layer)
- `config.py` (Configuration loader)
- `utils/logger.py` (everyone logs)
- `position/close_reason.py` (enum used in queries by both worker & api)
- `utils/market_session.py` (used in analytics + worker)

**packages/worker/ → `trading_worker`** (engine, imports trading_core):
- `main.py`, `cli.py`
- `strategies/`, `position/` (minus close_reason), `risk/`,
  `connectors/`, `executors/`, `services/`
- remaining `utils/` (market_hours, symbol_resolver, mock_data,
  notification_manager, config_validator, timeframe_manager, config_hasher)
- `exceptions/`

**packages/api/ → `trading_api`** (FastAPI, imports trading_core):
- empty scaffold now; filled by ui-dashboard spec.

**apps/dashboard/**: Next.js (ui-dashboard spec).

## Success criteria

- `uv sync` resolves the workspace (core + worker + api).
- `uv run trading-bot ...` CLI still works (entry point repointed to
  `trading_worker.cli:cli`).
- `uv run pytest` — all 1534+ tests pass (imports updated).
- `uv run alembic upgrade head` works (env imports `trading_core.models`).
- `uv run trading-bot --config test start` reaches the trading loop.
- No circular imports between packages (`core` imports nothing from
  `worker`/`api`).

## Constraints

- Bot is **live** — do the restructure in a planned restart window;
  the running process keeps the old layout until restart.
- Must be done in ONE focused session — half-migrated imports leave the
  repo unrunnable.
- Decide import-name strategy up front (`trading_core`, `trading_worker`,
  `trading_api`) and apply consistently — this is the irreversible-ish
  part (touches ~50 files).
- Keep `config/` YAML, `docs/`, `specs/`, `alembic/` at repo root
  (shared across packages).

## Risk register

| Risk | Mitigation |
|------|------------|
| ~50 files change import paths; easy to miss one | Use grep-driven sweep + `uv run python -c "import trading_worker"` smoke + full pytest before commit |
| Circular import core↔worker | Strict rule: core imports only stdlib + sqlalchemy/pydantic; worker/api import core. Verify with import-linter or manual check |
| Alembic env breaks (model import path) | Update `alembic/env.py` target_metadata import; test `alembic upgrade head` on a scratch DB |
| CLI entry point breaks | Update `[project.scripts]` to `trading_worker.cli:cli`; test `uv run trading-bot version` |
| Test fixtures import `trading_bot.*` | Sweep tests too; they move with their package or stay at root with updated imports |
| Live bot can't restart cleanly post-move | Tag a known-good commit before starting; restructure on a branch; verify dry-run before declaring done |

## Open questions

- uv workspace single-venv vs per-package venvs? → design.md (single
  workspace venv).
- Do tests split per-package (`packages/*/tests`) or stay at root
  `tests/`? → design.md.
- Package import names final: `trading_core` / `trading_worker` /
  `trading_api`? → design.md confirms.

## Related

- [ui-dashboard](../ui-dashboard/requirements.md) — the consumer driving this
- uv workspaces: https://docs.astral.sh/uv/concepts/workspaces/
