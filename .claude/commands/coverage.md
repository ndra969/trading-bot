---
description: Test coverage report
argument-hint: [html|term|critical]
---

# Coverage Report

| Arg | Command |
|-----|---------|
| (none) or `term` | `uv run pytest tests/ --cov=src/trading_bot --cov-report=term-missing` |
| `html` | `uv run pytest tests/ --cov=src/trading_bot --cov-report=html` → `htmlcov/index.html` |
| `critical` | `uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95` |

## Targets

- Overall: 85%
- Critical (risk/position): 95%
- New features: 100%
