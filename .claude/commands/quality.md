---
description: Code quality checks (format/lint/type)
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
uv run black src/ tests/ --check
uv run ruff check src/ tests/
uv run mypy src/trading_bot/

# Fix
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/trading_bot/
```

Standards: type hints required, async-first, no hardcoded values, SQLAlchemy 2.0.
