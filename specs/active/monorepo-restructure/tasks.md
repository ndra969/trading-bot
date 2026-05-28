# Monorepo Restructure (Opsi 3) — Task Breakdown

⚠️ Do this in ONE focused session during a bot restart window. A
half-migrated import tree leaves the repo unrunnable. Work on a branch.

## Phase 0 — Safety net (~10 min)

- [ ] `git status` clean; commit/stash any pending work.
- [ ] Tag current good state: `git tag pre-monorepo-restructure`.
- [ ] Create branch: `git checkout -b refactor/monorepo`.
- [ ] Baseline: `uv run pytest tests/unit/ -q` green; save count.
- [ ] Snapshot dry-run: `uv run trading-bot --config test start` ~2 min
      → `/tmp/restructure_before.log`.

## Phase 1 — Package skeletons (~30 min)

- [ ] Create dirs: `packages/core/src/trading_core`,
      `packages/worker/src/trading_worker`,
      `packages/api/src/trading_api`, `apps/dashboard/`.
- [ ] Write `packages/core/pyproject.toml` (name trading-core, deps:
      sqlalchemy, pydantic, pydantic-settings, pyyaml, python-dotenv,
      loguru, aiosqlite, asyncpg).
- [ ] Write `packages/worker/pyproject.toml` (name trading-worker,
      dep trading-core + the trading/MT5/strategy deps).
- [ ] Write `packages/api/pyproject.toml` (name trading-api, dep
      trading-core + fastapi, uvicorn).
- [ ] Root `pyproject.toml`: `[tool.uv.workspace] members=["packages/*"]`
      + `[tool.uv.sources]` workspace refs + `[project.scripts]`
      trading-bot → trading_worker.cli:cli.
- [ ] `__init__.py` in each new package.
- [ ] `uv sync` resolves (even with empty packages).

## Phase 2 — Move files (git mv, preserves history) (~30 min)

### Into trading_core
- [ ] `git mv src/trading_bot/data packages/core/src/trading_core/data`
- [ ] `git mv src/trading_bot/config.py packages/core/src/trading_core/config.py`
- [ ] `git mv src/trading_bot/utils/logger.py packages/core/src/trading_core/utils/logger.py`
- [ ] `git mv src/trading_bot/utils/market_session.py packages/core/src/trading_core/utils/market_session.py`
- [ ] `git mv src/trading_bot/position/close_reason.py packages/core/src/trading_core/enums/close_reason.py`
      (create `enums/__init__.py`)

### Into trading_worker (everything else)
- [ ] `git mv` remaining `src/trading_bot/*` →
      `packages/worker/src/trading_worker/` (main.py, cli.py,
      strategies, position, risk, connectors, executors, services,
      exceptions, remaining utils).
- [ ] Remove the now-empty `src/trading_bot/`.

## Phase 3 — Import sweep (~45 min)

Order matters — core-bound prefixes FIRST, then blanket.

- [ ] Rewrite core-bound imports across `packages/`, `tests/`,
      `alembic/`:
      - `trading_bot.data` → `trading_core.data`
      - `trading_bot.config` → `trading_core.config`
      - `trading_bot.utils.logger` → `trading_core.utils.logger`
      - `trading_bot.utils.market_session` → `trading_core.utils.market_session`
      - `trading_bot.position.close_reason` → `trading_core.enums.close_reason`
- [ ] Blanket rewrite remaining `trading_bot.` → `trading_worker.`
      and bare `import trading_bot` occurrences.
- [ ] `alembic/env.py`: model Base import → `trading_core.data.models`.
- [ ] Grep guard: `grep -rn "trading_bot" packages tests alembic` →
      only the user-facing CLI string (if any) may remain.

## Phase 4 — Verify (~30 min)

- [ ] `uv sync` clean.
- [ ] Smoke imports:
      `uv run python -c "import trading_core, trading_worker, trading_api"`.
- [ ] Circular-import check: `uv run python -c "import trading_core"`
      must NOT pull in worker/api (inspect or use import-linter).
- [ ] `uv run trading-bot version` works.
- [ ] `uv run pytest tests/unit/ -q` → same count as baseline, green.
- [ ] `uv run pytest tests/integration/ -q` (minus known flakes).
- [ ] `uv run alembic upgrade head` on a scratch DB.
- [ ] `uv run trading-bot --config test start` ~2 min →
      `/tmp/restructure_after.log`; diff vs before (only timestamps).
- [ ] Coverage targets still met.

## Phase 5 — Commit & close (~15 min)

- [ ] Single commit (run FULL hooks — this is code, not docs):
      `refactor: split into monorepo packages (core/worker/api)`.
- [ ] If hooks pass and bot dry-run clean → merge branch.
- [ ] Update `ui-dashboard` spec: api now lives in `packages/api`,
      frontend in `apps/dashboard` (already aligned).
- [ ] Move this spec to `specs/archive/YYYY-MM/`; update specs/README.md.

## Effort estimate

- Total: ~3-3.5 hours focused, single session.
- Do NOT split across sessions — partial import state is unrunnable.

## Tests-to-watch

- Entire `tests/` suite (imports change everywhere).
- `alembic upgrade head` (model import path).
- CLI: `uv run trading-bot version` / `start`.
