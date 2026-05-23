---
description: Check and display test coverage report
argument-hint: [report|html|fail-under]
---

# Test Coverage Report

Display detailed test coverage information for the trading bot codebase.

## Arguments

- **no argument**: Show coverage summary with missing lines
- `report`: Show detailed coverage report with missing lines
- `html`: Generate HTML coverage report
- `fail-under <percentage>`: Check if coverage meets requirement (default: 85)

## Implementation Steps

1. **Run pytest with coverage** - Generate coverage data
2. **Parse results** - Extract coverage metrics
3. **Display report** - Show coverage by module
4. **Identify gaps** - Highlight files below threshold

## Commands to Execute

```bash
# Coverage summary with missing lines (default)
uv run pytest tests/ --cov=src/trading_bot --cov-report=term-missing

# HTML report
uv run pytest tests/ --cov=src/trading_bot --cov-report=html

# Check specific coverage threshold
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# Critical components (95% required)
uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95
uv run pytest tests/unit/position/ --cov-fail-under=95
```

## Coverage Requirements

From CLAUDE.md:
- **Minimum coverage**: 85% overall
- **Critical components**: 95% (risk management, position sizing, volume calculation)
- **New features**: 100% coverage required

## Coverage Report Format

```
Name                                         Stmts   Miss  Cover   Missing
------------------------------------------------------------------------
src/trading_bot/config.py                      45      2    96%   23-24
src/trading_bot/main.py                       120     15    88%   45-50, 78-82
src/trading_bot/strategies/foundation/        250      0   100%
src/trading_bot/risk/exposure_manager.py        80      1    99%   145
------------------------------------------------------------------------
TOTAL                                         850     50    94%
```

## Examples

- `/coverage` → Show coverage summary
- `/coverage report` → Detailed report with missing lines
- `/coverage html` → Generate HTML report in `htmlcov/`
- `/coverage fail-under 90` → Check if 90% coverage met

## Related

- `/test` → Run test suite
- `/tdd` → TDD workflow guidance
- `/commit` → Pre-commit validation

## Improving Coverage

To improve coverage:
1. Run `/coverage report` to find missing lines
2. Write tests for uncovered code paths
3. Use `/tdd` workflow for new tests
4. Re-run coverage to verify improvement
