---
description: Run test suite with coverage
argument-hint: [unit|integration|critical|coverage|fast]
---

# Run Tests

| Arg | Command |
|-----|---------|
| (none) | `uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85` |
| `unit` | `uv run pytest tests/unit/ -v` |
| `integration` | `uv run pytest tests/integration/ --mt5` |
| `critical` | `uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95` |
| `coverage` | `uv run pytest tests/ --cov=src/trading_bot --cov-report=term-missing` |
| `fast` | `uv run pytest tests/ -v --no-cov` |

Coverage: 85% min, 95% critical, 100% new features.

On failure: identify failing tests and provide fix guidance.
