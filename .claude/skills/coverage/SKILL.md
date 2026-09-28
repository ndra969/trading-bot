---
name: coverage
description: Test coverage report for the Python trading bot packages (term, html, critical risk/position modules).
argument-hint: [html|term|critical]
---

# Coverage Report

| Arg | Command |
|-----|---------|
| (none) or `term` | `uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-report=term-missing` |
| `html` | `uv run pytest tests/ --cov=packages/core/src/trading_core --cov=packages/worker/src/trading_worker --cov-report=html` → `htmlcov/index.html` |
| `critical` | `uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95` |

## Targets

- Overall: 85%
- Critical (risk/position): 95%
- New features: 100%
