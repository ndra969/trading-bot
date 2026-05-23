---
description: Run test suite with appropriate coverage requirements
argument-hint: [unit|integration|critical|coverage|fast]
---

# Run Trading Bot Tests

Execute the test suite with proper coverage requirements based on the TDD workflow.

## Arguments

- **no argument**: Run all tests with 85% coverage requirement
- `unit`: Run only unit tests
- `integration`: Run integration tests (including MT5 tests)
- `critical`: Run critical component tests (risk management, position sizing) with 95% coverage
- `coverage`: Run tests with detailed coverage report
- `fast`: Run quick tests without coverage (for development iteration)

## Implementation Steps

1. **Check current test status** by running the appropriate pytest command
2. **Analyze test results** and provide summary
3. **If tests fail**: Provide guidance on which tests need fixing
4. **If coverage insufficient**: Show which files need more test coverage

## Commands to Execute

```bash
# All tests (default)
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests
uv run pytest tests/integration/ --mt5

# Critical components (95% coverage required)
uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95

# With detailed coverage report
uv run pytest tests/ --cov=src/trading_bot --cov-report=term-missing

# Fast mode (no coverage)
uv run pytest tests/ -v --no-cov
```

## Examples

- `/test` → Run all tests with 85% coverage
- `/test unit` → Run unit tests only
- `/test critical` → Run risk management tests with 95% coverage
- `/test fast` → Quick test run for development

## Related

- `/quality` → Run code quality checks
- `/tdd` → TDD workflow guidance
- `/dry-run` → Validate bot with dry-run mode

## Testing Requirements Reference

From CLAUDE.md:
- **Minimum coverage**: 85% overall
- **Critical components**: 95% (risk management, position sizing)
- **New features**: 100% coverage required
