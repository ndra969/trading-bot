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
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
uv run black src/ tests/ && uv run ruff check src/ tests/ --fix && uv run mypy src/trading_bot/
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
src/trading_bot/
  cli.py  config.py  main.py
  connectors/  data/  executors/  position/
  risk/  strategies/  utils/
  exceptions/  analytics/
tests/    1611+ tests (unit, integration, utils)
config/   YAML configs
docs/     User docs
specs/    Internal specs (archived)
alembic/  DB migrations
```

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
