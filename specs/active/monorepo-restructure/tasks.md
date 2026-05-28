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

## Phase 2 — COPY files (old tree stays as reference) (~30 min)

⚠️ COPY, don't move. `src/trading_bot/` stays intact + live until Phase 5
cutover. This lets us diff old-vs-new to prove no logic change.

### Copy into trading_core
- [ ] `cp -r src/trading_bot/data packages/core/src/trading_core/data`
- [ ] `cp src/trading_bot/config.py packages/core/src/trading_core/config.py`
- [ ] `cp src/trading_bot/utils/logger.py packages/core/src/trading_core/utils/logger.py`
- [ ] `cp src/trading_bot/utils/market_session.py packages/core/src/trading_core/utils/market_session.py`
- [ ] `cp src/trading_bot/position/close_reason.py packages/core/src/trading_core/enums/close_reason.py`
      (create `enums/__init__.py`)

### Copy into trading_worker (everything else)
- [ ] `cp -r` remaining `src/trading_bot/*` →
      `packages/worker/src/trading_worker/` (main.py, cli.py,
      strategies, position, risk, connectors, executors, services,
      exceptions, remaining utils). Skip the files already copied to core.
- [ ] Do NOT delete `src/trading_bot/` yet — removed at cutover (Phase 5).

## Phase 3 — Import sweep on COPIES only (~45 min)

Rewrite imports ONLY inside `packages/` (the copies). Leave `tests/` and
`alembic/` on `trading_bot` for now — they still serve the live old tree
until cutover. Order matters — core-bound prefixes FIRST, then blanket.

- [ ] In `packages/` only, rewrite core-bound imports:
      - `trading_bot.data` → `trading_core.data`
      - `trading_bot.config` → `trading_core.config`
      - `trading_bot.utils.logger` → `trading_core.utils.logger`
      - `trading_bot.utils.market_session` → `trading_core.utils.market_session`
      - `trading_bot.position.close_reason` → `trading_core.enums.close_reason`
- [ ] In `packages/` only, blanket rewrite remaining `trading_bot.` →
      `trading_worker.` + bare `import trading_bot`.
- [ ] Grep guard: `grep -rn "trading_bot" packages` → empty.

## Phase 4 — Verify NEW packages (old tree still intact) (~30 min)

- [ ] `uv sync` clean (workspace + old src coexist).
- [ ] Smoke imports:
      `uv run python -c "import trading_core, trading_worker, trading_api"`.
- [ ] Circular-import check: importing `trading_core` must NOT pull in
      worker/api.
- [ ] Temp CLI alias works: `uv run trading-bot-new version`.
- [ ] **Source diff old-vs-new** (the verification artifact):
      `diff -r src/trading_bot packages/worker/src/trading_worker` (and
      core) — expect ONLY import lines + moved-file paths to differ, no
      logic changes. Eyeball it.
- [ ] Quick functional check: `uv run trading-bot-new --config test start`
      ~2 min → `/tmp/restructure_after.log`; diff behaviour vs
      `/tmp/restructure_before.log` (only timestamps differ).

## Phase 5 — Cutover + commit (~30 min)

Now flip everything to the new tree and remove the old.

- [ ] Rewrite `tests/` imports: core-bound first, then blanket
      `trading_bot.` → `trading_worker.`.
- [ ] `alembic/env.py`: model Base import → `trading_core.data.models`.
- [ ] Flip `[project.scripts]`: `trading-bot = "trading_worker.cli:cli"`;
      remove the temporary `trading-bot-new` alias.
- [ ] Delete `src/trading_bot/`.
- [ ] Grep guard: `grep -rn "trading_bot" packages tests alembic` →
      only the user-facing CLI command string may remain.
- [ ] `uv sync`; `uv run trading-bot version`.
- [ ] `uv run pytest tests/unit/ -q` → same count as baseline, green.
- [ ] `uv run pytest tests/integration/ -q` (minus known flakes).
- [ ] `uv run alembic upgrade head` on a scratch DB.
- [ ] `uv run trading-bot --config test start` dry-run clean.
- [ ] Coverage targets met.
- [ ] Single commit (FULL hooks — this is code):
      `refactor: split into monorepo packages (core/worker/api)`.
- [ ] Merge branch once green + dry-run verified.
- [ ] Update specs/README.md; move this spec to archive after the
      follow-on refactor-main-services phase (they share the session).

## Effort estimate

- Total: ~3-3.5 hours focused, single session.
- Do NOT split across sessions — partial import state is unrunnable.

## Tests-to-watch

- Entire `tests/` suite (imports change everywhere).
- `alembic upgrade head` (model import path).
- CLI: `uv run trading-bot version` / `start`.
