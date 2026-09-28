---
name: commit
description: Pre-commit validation for the Python trading bot: tests, black/ruff/mypy, dry-run. Use before committing changes under packages/ or tests/.
argument-hint: [quick|full]
---

# Pre-Commit Validation

| Arg | Steps |
|-----|-------|
| (none) or `full` | tests + quality + dry-run |
| `quick` | tests + quality (skip dry-run) |

```bash
uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-fail-under=85
uv run black packages/ tests/ --check
uv run ruff check packages/ tests/
uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker
uv run trading-bot start --dry-run    # Skip for quick
```

Checklist: tests 85%+ (critical 95%) | Black/Ruff/mypy clean | dry-run OK | no hardcoded values | TDD followed | docs updated

Commit types: feat | fix | refactor | test | docs | config | perf
