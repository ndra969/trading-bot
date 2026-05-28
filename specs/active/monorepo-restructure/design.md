# Monorepo Restructure (Opsi 3) — Design

## Target layout

```
trading-bot/                         # workspace root
├── pyproject.toml                   # [tool.uv.workspace] members
├── packages/
│   ├── core/
│   │   ├── pyproject.toml           # name: trading-core
│   │   └── src/trading_core/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── data/
│   │       │   ├── models.py
│   │       │   ├── database.py
│   │       │   ├── repositories/
│   │       │   └── services/
│   │       ├── enums/close_reason.py   (moved from position/)
│   │       └── utils/
│   │           ├── logger.py
│   │           └── market_session.py
│   ├── worker/
│   │   ├── pyproject.toml           # name: trading-worker (dep: trading-core)
│   │   └── src/trading_worker/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── cli.py
│   │       ├── strategies/  position/  risk/
│   │       ├── connectors/  executors/  services/
│   │       ├── exceptions/
│   │       └── utils/       (market_hours, symbol_resolver, mock_data,
│   │                          notification_manager, config_validator,
│   │                          timeframe_manager, config_hasher)
│   └── api/
│       ├── pyproject.toml           # name: trading-api (dep: trading-core)
│       └── src/trading_api/
│           └── __init__.py          (stub now; ui-dashboard fills it)
├── apps/
│   └── dashboard/                   # Next.js (ui-dashboard spec)
├── alembic/                         # env imports trading_core.models
├── config/   docs/   specs/         # shared, repo root
└── tests/                           # see "Test layout" below
```

## Package boundaries (the invariant)

```
trading_core   → imports only: stdlib, sqlalchemy, pydantic, yaml, dotenv
trading_worker → imports: trading_core + its own modules
trading_api    → imports: trading_core + its own modules
```

`trading_core` must NEVER import `trading_worker` or `trading_api`.
Worker and api never import each other. This keeps the dependency graph
a clean tree and lets worker + api deploy independently later.

## Import-name decision

| Package | Import name | Distribution name |
|---------|-------------|-------------------|
| core | `trading_core` | `trading-core` |
| worker | `trading_worker` | `trading-worker` |
| api | `trading_api` | `trading-api` |

The old `trading_bot` name retires. CLI command stays `trading-bot`
(user-facing), but its entry point becomes `trading_worker.cli:cli`.

## Dependency policy

When writing each package's `pyproject.toml`, pin to **latest stable**
versions of mainstream libs (SQLAlchemy 2.0, pydantic v2, asyncpg,
fastapi, uvicorn, etc.). Prefer the most-widely-used option between
equivalents. Carry forward versions from the current root
`pyproject.toml`, bumping to latest stable where safe.

## uv workspace

Root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
trading-core = { workspace = true }
trading-worker = { workspace = true }
trading-api = { workspace = true }
```

Single shared venv at root. `uv sync` installs all members editable.

## What moves where (file-level)

### → trading_core
- `data/**` (models, database, repositories, services)
- `config.py`
- `utils/logger.py`
- `position/close_reason.py` → `trading_core/enums/close_reason.py`
- `utils/market_session.py`

### → trading_worker (everything else currently in trading_bot)
- `main.py`, `cli.py`
- `strategies/**`, `position/**` (minus close_reason),
  `risk/**`, `connectors/**`, `executors/**`, `services/**`,
  `exceptions/**`
- remaining `utils/**`

### → trading_api
- new empty package, `__init__.py` only.

## Import rewrite map

Mechanical find/replace across the repo:

| Old | New |
|-----|-----|
| `from trading_bot.data...` | `from trading_core.data...` |
| `from trading_bot.config import` | `from trading_core.config import` |
| `from trading_bot.utils.logger import` | `from trading_core.utils.logger import` |
| `from trading_bot.position.close_reason import` | `from trading_core.enums.close_reason import` |
| `from trading_bot.utils.market_session import` | `from trading_core.utils.market_session import` |
| `from trading_bot.<rest>` | `from trading_worker.<rest>` |
| `import trading_bot...` | (split per above) |

Order matters: rewrite the **core-bound** prefixes FIRST (data, config,
logger, close_reason, market_session), THEN blanket-rewrite the
remaining `trading_bot.` → `trading_worker.`.

## Alembic

`alembic/env.py`: change `from trading_bot.data.models import Base` →
`from trading_core.data.models import Base`. Migration files reference
table names (strings), not Python imports — no change needed there.

## CLI entry point

Root or worker `pyproject.toml`:
```toml
[project.scripts]
trading-bot = "trading_worker.cli:cli"
```

## Test layout

**Decision**: keep a single root `tests/` for now (less churn), with
imports rewritten. Subdivide into `tests/core/`, `tests/worker/`,
`tests/api/` only if it becomes unwieldy later. Conftest/fixtures move
with their imports.

## Migration sequence — COPY first, verify, then remove

**Strategy decision**: COPY files into the new packages (don't `git mv`).
The old `src/trading_bot/` stays intact as a reference until the new
structure is proven, so we can diff old-vs-new to confirm zero logic
change. Only after verification do we delete the old tree.

Tradeoff: git sees the copied files as new (per-file history resets at
the new path). Accepted for the safety + diffability benefit.

### Coexistence rule (critical during transition)

While both trees exist:
- The **running bot keeps using old `trading_bot`** — CLI entry point
  stays `trading_bot.cli:cli` until the explicit cutover step.
- New code imports `trading_core` / `trading_worker`; old code imports
  `trading_bot`. **No file imports both.**
- Verify against the NEW packages; old tests keep passing against old
  code until cutover.

### Steps (detail in tasks.md)

1. Branch + tag known-good commit.
2. Create package skeletons + root uv workspace config (old
   `src/trading_bot` still the live package).
3. **COPY** files into new homes (split core vs worker during copy).
4. Rewrite imports in the COPIES only (core-bound first, then worker).
5. Fix alembic env (point at `trading_core.data.models`) + add a
   temporary `trading-bot-new = trading_worker.cli:cli` script so the
   old `trading-bot` keeps working in parallel.
6. `uv sync`; smoke-import each new package.
7. Run the suite against the NEW packages; diff old-vs-new source to
   confirm ONLY import lines + paths changed (the verification artifact).
8. **Cutover**: flip `trading-bot` to `trading_worker.cli`, delete
   `src/trading_bot/`, drop the temp `trading-bot-new` alias.
9. Full pytest + dry-run on the cutover state.
10. Commit (full hooks — this is code).

## Rollback plan

Done on a branch, two safety nets:
1. Pre-cutover: old `src/trading_bot/` still present + live — delete the
   new `packages/` and you're back instantly.
2. Post-cutover: `git checkout main` / reset to the pre-restructure tag.

Copy + import-rewrite means a source diff old-vs-new shows ONLY import
lines + file paths differing — that diff IS the proof of no logic change.

## What "done" looks like

- `uv sync` clean; three workspace packages installed editable.
- `uv run trading-bot version` and `--config test start` work.
- `uv run pytest` 1534+ green.
- `uv run alembic upgrade head` works.
- No `trading_bot` import remains (`grep -rn "trading_bot" src packages tests`
  returns nothing except maybe the user-facing CLI string).
- `apps/dashboard/` + `packages/api/` exist as empty-but-valid scaffolds
  ready for the ui-dashboard spec.
