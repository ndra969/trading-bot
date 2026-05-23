---
description: Pre-commit validation workflow
argument-hint: [quick|full]
---

# Pre-Commit Validation

Complete validation workflow before committing changes. This ensures all tests pass, code quality is maintained, and the system works correctly.

## Arguments

- **no argument**: Run full validation workflow
- `quick`: Quick validation (tests + quality, skip dry-run)
- `full`: Full validation (tests + quality + dry-run)

## Implementation Steps

1. **Run all tests** with coverage requirements
2. **Run code quality checks** (format, lint, type-check)
3. **Run dry-run validation** (skip for `quick` mode)
4. **Provide summary** and approval status

## Commands to Execute

```bash
# 1. Run all tests with coverage
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# 2. Run code quality checks
uv run black src/ tests/ --check
uv run ruff check src/ tests/
uv run mypy src/trading_bot/

# 3. Dry-run validation (skip for quick mode)
uv run trading-bot start --dry-run
```

## Validation Checklist

Before committing, ensure:
- [ ] All tests passing (85%+ coverage, 95% for critical components)
- [ ] Code formatted with Black
- [ ] No Ruff linting errors
- [ ] No mypy type errors
- [ ] Dry-run successful (no errors or exceptions)
- [ ] No hardcoded values (use YAML configuration)
- [ ] TDD methodology followed (tests written first)
- [ ] Documentation updated (if needed)

## Exit Codes

- **0**: All validations passed, ready to commit
- **1**: Tests failed
- **2**: Code quality issues
- **3**: Dry-run failed

## Examples

- `/commit` → Full validation workflow
- `/commit quick` → Quick validation (no dry-run)
- `/commit full` → Full validation (same as no argument)

## Typical Workflow

```bash
# After making changes
/commit quick    # Quick validation during development

# Before final commit
/commit full     # Full validation including dry-run

# If validation passes
git add .
git commit -m "feat: your commit message"
```

## Related

- `/test` → Run test suite only
- `/quality` → Run code quality checks only
- `/dry-run` → Run dry-run validation only
- `/tdd` → TDD workflow guidance

## Commit Message Style

Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `test:` Test updates
- `docs:` Documentation changes
- `config:` Configuration changes
