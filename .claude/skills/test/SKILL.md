---
name: test
description: Run the Python trading bot test suite with coverage (unit, integration, critical, fast).
argument-hint: [unit|integration|critical|coverage|fast]
---

# Run Tests

| Arg | Command |
|-----|---------|
| (none) | `uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-fail-under=85` |
| `unit` | `uv run pytest tests/unit/ -v` |
| `integration` | `uv run pytest tests/integration/ --mt5` |
| `critical` | `uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95` |
| `coverage` | `uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-report=term-missing` |
| `fast` | `uv run pytest tests/ -v --no-cov` |

Coverage: 85% min, 95% critical, 100% new features.

On failure: identify failing tests and provide fix guidance.
