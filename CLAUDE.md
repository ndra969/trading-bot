# CLAUDE.md

Trading bot guidance for Claude Code.

## Project

Multi-asset trading bot (Forex/Commodities/Crypto) with MT5. Python 3.12+, UV, Click, SQLAlchemy 2.0, async-first. **Production Ready** (1605+ tests, 98% coverage).

## Commands

### Development
| Cmd | Purpose |
|-----|---------|
| `/workflow` | Dev workflow (START HERE) |
| `/rules` / `/claude` | This file |
| `/docs [topic]` | Browse docs |
| `/tdd [feat]` | TDD guidance |
| `/test [type]` | Run tests |
| `/coverage [opt]` | Coverage report |
| `/quality [fix]` | Format/lint/type-check |
| `/dry-run` | Validate bot (MANDATORY pre-commit) |
| `/commit [quick\|full]` | Pre-commit validation |
| `/new <cat>/<name>` | New doc |
| `/spec <name>` | New 3-file spec (requirements/design/tasks) |

### Operations
| Cmd | Purpose |
|-----|---------|
| `/status [type]` | Bot/MT5/positions/account/risk status |
| `/logs [filter]` | View/filter logs |
| `/analyze <sym>` | Strategy analysis |
| `/backtest <sym>` | Backtest |
| `/migrate [cmd]` | DB migration |

```bash
uv run trading-bot start --dry-run                # Safe test
uv run trading-bot start --config production      # Live
uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-fail-under=85
uv run black packages/ tests/ && uv run ruff check packages/ tests/ --fix && uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker
```

## Critical Rules

### Position Rules
- **Max 1 trade per symbol** across all strategies
- **Asset-specific** breakeven/trailing (forex 15p, gold 500p, crypto $50)
- **Min 65% confluence** required for signal
- **Market hours validated** before execution

### Pip Values
```python
PIP_VALUES = {
    "forex_major": 0.0001,   # EURUSD
    "forex_jpy": 0.01,        # USDJPY
    "commodities": 0.1,       # XAUUSD
    "crypto": 1.0,            # BTCUSD
}
```

### Strategy (Foundation-First)
Foundation (S&D 30%) + 7 layers. Min 65% to signal.
```
foundation: 0.30 | trendline: 0.20 | price_action: 0.15
fibonacci: 0.12  | breakout: 0.12  | structure: 0.08
rsi: 0.10        | ma: 0.08
```

### Risk
- Max 2% portfolio risk, 1% daily loss, 15% emergency stop
- Layered: position → portfolio → account

## Code Standards

- **Python 3.12+**, type hints required (mypy)
- **Async-first** (SQLAlchemy 2.0, asyncio)
- **No hardcoded values** - use YAML
- **TDD** - tests first (Red-Green-Refactor)
- **Black** (100 char), **Ruff**, **mypy** clean

Full standards: `docs/guides/coding-standards.md`

## Testing

- Coverage: 85% min, 95% critical, 100% new features
- Types: unit / integration / property (Hypothesis)

### Pre-Commit
```bash
/test && /quality fix && /dry-run
```

**Docs/specs-only commits**: when a commit touches ONLY `docs/`, `specs/`,
`.claude/`, or `*.md` files (no `src/` or `tests/` changes), commit with
`--no-verify` — the pre-commit hook runs the full test suite which is
irrelevant for documentation and just wastes time / risks the stash-restore
conflict. Code/test changes always run the full hook.

## Debugging & Monitoring

For runtime issues, use these commands instead of running CLI manually:

| Task | Command |
|------|---------|
| Check bot/MT5/positions | `/status` |
| View/filter logs | `/logs [errors\|signals\|trades\|risk]` |
| Validate config | `/dry-run` |
| See troubleshooting | `/docs troubleshooting` |

## Performance Targets

- Trading loop <55s | DB queries <100ms | RAM <2GB | MT5 ops <1s

## Structure

```
packages/
  core/src/trading_core/    shared: config.py  data/ (models, db, repositories)
                            enums/ (close_reason)  utils/ (logger, market_session,
                            config_hasher)
  worker/src/trading_worker/  bot engine: cli.py  main.py  connectors/  executors/
                              position/  risk/  strategies/  services/  exceptions/
                              utils/   (CLI entry: `trading-bot`)
  api/src/trading_api/      read-only FastAPI BFF (dashboard backend)
apps/dashboard/   Next.js dashboard (frontend)
tests/    1550+ tests (unit, integration, utils)
config/   YAML configs (loaded relative to repo root)
docs/     User docs
specs/    active/ (3-file specs: requirements+design+tasks) · archive/
alembic/  DB migrations
```

> Monorepo (uv workspace). Root `pyproject.toml` is a virtual workspace root
> (`[tool.uv] package = false`); each package has its own `pyproject.toml`.
> `trading_core` depends on nothing internal; `trading_worker`/`trading_api`
> depend only on `trading_core`, never on each other.

> New planned work → scaffold a spec with `/spec <name>` (creates
> `specs/active/<name>/{requirements,design,tasks}.md`). Archive to
> `specs/archive/YYYY-MM/` when resolved.

## Configuration

Priority: ENV → env YAML → specific YAML → default YAML → code defaults

## Database

- Dev: SQLite | Prod: PostgreSQL (asyncpg)
- Migrations: Alembic
- Use `/migrate` for management

## Documentation

- [Index](docs/README.md) - Start here
- [Architecture](docs/architecture/architecture-guide.md)
- [Database ERD](docs/architecture/database-erd.md)
- [Coding Standards](docs/guides/coding-standards.md) ⚠️ READ FIRST
- [Troubleshooting](docs/guides/troubleshooting-guide.md)

Or use `/docs [topic]` command.

## Requirements

- **Windows 10/11** (MT5 limitation)
- **Python 3.12+**
- **MetaTrader5** terminal installed & logged in

## Workflow

1. `/workflow` - Dev guidance
2. `/docs coding-standards` - Standards first
3. `/tdd` - TDD methodology
4. `/dry-run` - Validate before commit
5. `/commit` - Pre-commit checks
