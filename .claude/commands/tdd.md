---
description: TDD workflow guidance
argument-hint: [feature-name]
---

# TDD Workflow

Red → Green → Refactor

## Process

1. **Red**: Write failing test
2. **Green**: Minimal code to pass
3. **Refactor**: Clean while green
4. **Repeat**

```bash
# Write test, then:
uv run pytest tests/unit/<feature>_test.py -v  # Should fail
# Write implementation, then:
uv run pytest tests/unit/<feature>_test.py -v  # Should pass
# Full suite:
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
/quality fix
/dry-run
```

## Standards

- Coverage: 85% min, 95% critical, 100% new features
- One test file per module
- Types: unit | integration | property (Hypothesis) | e2e

## Checklist

- [ ] Tests first (Red)
- [ ] Implementation passes (Green)
- [ ] Refactored (clean)
- [ ] Coverage met
- [ ] `/quality` clean
- [ ] `/dry-run` OK
