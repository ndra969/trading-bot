---
name: quality
description: Code quality checks for the Python trading bot: black, ruff, mypy (check or fix).
argument-hint: [fix|check]
---

# Code Quality

Run in order: Black → Ruff → mypy

| Arg | Action |
|-----|--------|
| (none) or `check` | Check only |
| `fix` | Auto-fix |

```bash
# Check
uv run black packages/ tests/ --check
uv run ruff check packages/ tests/
uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker

# Fix
uv run black packages/ tests/
uv run ruff check packages/ tests/ --fix
uv run mypy packages/core/src/trading_core packages/worker/src/trading_worker
```

Standards: type hints required, async-first, no hardcoded values, SQLAlchemy 2.0.
