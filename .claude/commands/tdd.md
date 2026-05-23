---
description: TDD workflow guidance for new features
argument-hint: [feature-name]
---

# Test-Driven Development Workflow

Guide for implementing features using TDD methodology (Red-Green-Refactor cycle).

## Arguments

- **no argument**: Display TDD workflow guidance
- `feature-name`: Provide TDD workflow for specific feature

## TDD Process

### Phase 1: Red (Write Failing Test)
1. Write test for the feature you want to implement
2. Run test - it should fail
3. Confirm test failure is expected

### Phase 2: Green (Make Test Pass)
1. Write minimal code to make the test pass
2. Run test - it should now pass
3. No more, no less

### Phase 3: Refactor (Improve Code)
1. Improve code while keeping tests green
2. Run tests again - must still pass
3. Repeat until code is clean

### Phase 4: Repeat
Repeat for all features and components

## TDD Commands

```bash
# 1. Write test (in editor)
# 2. Run test (should fail)
uv run pytest tests/unit/new_feature_test.py -v

# 3. Write implementation (in editor)
# 4. Run test (should pass)
uv run pytest tests/unit/new_feature_test.py -v

# 5. Run full test suite
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# 6. Code quality
/quality fix

# 7. Final validation
/dry-run
```

## Testing Standards

From CLAUDE.md:
- **Minimum coverage**: 85% overall
- **Critical components**: 95% (risk, position sizing)
- **New features**: 100% coverage required
- **One test file per module**: No redundant files

## Testing Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **Property Tests**: Mathematical invariants with Hypothesis
4. **End-to-End Tests**: Complete workflow testing

## Examples

- `/tdd` → Display TDD workflow guidance
- `/tdd new-risk-feature` → Get TDD guidance for new risk feature

## Related

- `/test` → Run test suite
- `/quality` → Code quality checks
- `/coverage` → Check test coverage

## TDD Checklist

Before committing any feature:
- [ ] Tests written first (Red phase)
- [ ] Implementation makes tests pass (Green phase)
- [ ] Code refactored (Refactor phase)
- [ ] All tests passing (85%+ coverage)
- [ ] Code quality checks passing
- [ ] Dry-run validation successful
