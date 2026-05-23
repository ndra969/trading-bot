---
description: Run code quality checks (format, lint, type-check)
argument-hint: [fix|check]
---

# Code Quality Checks

Run complete code quality workflow: formatting (Black), linting (Ruff), and type checking (mypy).

## Arguments

- **no argument**: Run all quality checks without fixing
- `fix`: Auto-fix formatting and linting issues
- `check`: Run checks only (same as no argument)

## Implementation Steps

1. **Run Black formatter** to check/fix code formatting
2. **Run Ruff linter** to check/fix code style and linting issues
3. **Run mypy** for type checking
4. **Provide summary** of any issues found and fixed

## Commands to Execute

```bash
# Check only (default)
uv run black src/ tests/ --check
uv run ruff check src/ tests/
uv run mypy src/trading_bot/

# Auto-fix issues
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/trading_bot/
```

## Order of Execution

Execute in this order:
1. Black (formatting)
2. Ruff (linting)
3. mypy (type checking)

## Quality Standards

From `docs/guides/coding-standards.md`:
- **Type hints** required for all functions
- **Async-first** architecture
- **SQLAlchemy 2.0** modern async syntax
- **Clean Architecture** principles
- **TDD-First Development** methodology

## Examples

- `/quality` → Check code quality without fixing
- `/quality fix` → Auto-fix formatting and linting issues

## Related

- `/test` → Run test suite
- `/dry-run` → Final validation with dry-run
