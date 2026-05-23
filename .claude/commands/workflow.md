---
description: Development workflow guide
argument-hint: [phase]
---

# Development Workflow

Complete workflow from analysis to deployment.

## Arguments

- `no arg` - Overview
- `analysis` - Phase 1: Requirements
- `design` - Phase 2: Planning
- `implement` - Phase 3: TDD
- `migrate` - Phase 4: Database
- `validate` - Phase 5: Quality
- `commit` - Phase 6: Docs & commit

## Quick Reference

```
/docs [topic]     # Read docs
/rules [format]    # Project rules
/tdd [feature]     # TDD guidance
/test [type]       # Run tests
/quality [fix]     # Code quality
/dry-run           # Final validation
/commit [type]     # Commit changes
```

## Phase 1: Analysis

1. Read requirements carefully
2. Identify affected components
3. Review relevant docs: `/docs architecture`, `/rules`
4. Check dependencies (DB, config, MT5)

## Phase 2: Design

1. Follow Clean Architecture
2. Design DB schema (if needed): `/docs database-erd`
3. Plan configuration changes
4. Review `/docs coding-standards`

## Phase 3: TDD Implementation

**CRITICAL**: Tests FIRST (Red-Green-Refactor)

```bash
# 1. Write failing test
tests/unit/<module>/test_<feature>.py

# 2. Write minimal code to pass
src/<module>/<feature>.py

# 3. Refactor while tests green

# 4. Verify coverage
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
```

**Coverage**: New features 100%, critical 95%, overall 85%

## Phase 4: Database (if needed)

```bash
alembic revision -m "description"
# Write upgrade() + downgrade()
alembic upgrade head
/migrate verify
```

Update: `docs/diagrams/database-erd.md`

## Phase 5: Validation

```bash
/quality fix       # Format, lint, type-check
/test              # All tests
/dry-run           # MANDATORY before commit
```

**Exit Checklist**:
- [ ] Tests passing (85%+ coverage)
- [ ] Black formatted
- [ ] Ruff clean
- [ ] mypy clean
- [ ] Dry-run successful

## Phase 6: Commit

```bash
git add .
git commit -m "feat: description

- Implementation detail
- 100% coverage

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Types**: feat, fix, refactor, test, docs, config, perf

## Related

- `/rules` - Project rules
- `/docs coding-standards` - Code standards
- `/tdd` - TDD details
