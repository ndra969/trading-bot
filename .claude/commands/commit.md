---
description: Pre-commit validation
argument-hint: [quick|full]
---

# Pre-Commit Validation

| Arg | Steps |
|-----|-------|
| (none) or `full` | tests + quality + dry-run |
| `quick` | tests + quality (skip dry-run) |

```bash
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
uv run black src/ tests/ --check
uv run ruff check src/ tests/
uv run mypy src/trading_bot/
uv run trading-bot start --dry-run    # Skip for quick
```

Checklist: tests 85%+ (critical 95%) | Black/Ruff/mypy clean | dry-run OK | no hardcoded values | TDD followed | docs updated

Commit types: feat | fix | refactor | test | docs | config | perf
