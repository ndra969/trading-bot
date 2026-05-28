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

## Migration sequence (high level — detail in tasks.md)

1. Create branch + tag known-good commit.
2. Create package skeletons (`packages/core|worker|api`, pyproject each,
   root workspace config).
3. `git mv` files into their new homes (preserves history).
4. Sweep imports (core-bound first, then worker blanket).
5. Fix alembic env + CLI entry point.
6. `uv sync`; smoke-import each package.
7. Full pytest + dry-run.
8. Single commit (this is too big to bypass hooks — run full suite).

## Rollback plan

Done on a branch. If anything is off: `git checkout main` / reset to the
pre-restructure tag. Because it's pure move + import rewrite, revert is
total. No DB/data involvement.

## What "done" looks like

- `uv sync` clean; three workspace packages installed editable.
- `uv run trading-bot version` and `--config test start` work.
- `uv run pytest` 1534+ green.
- `uv run alembic upgrade head` works.
- No `trading_bot` import remains (`grep -rn "trading_bot" src packages tests`
  returns nothing except maybe the user-facing CLI string).
- `apps/dashboard/` + `packages/api/` exist as empty-but-valid scaffolds
  ready for the ui-dashboard spec.
