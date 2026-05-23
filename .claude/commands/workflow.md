---
description: Development workflow guide
argument-hint: [phase]
---

# Dev Workflow

Phases: `analysis` → `design` → `implement` → `migrate` → `validate` → `commit`

## Quick Refs
`/docs [topic]` `/rules` `/tdd` `/test` `/quality` `/dry-run` `/commit`

## Phase 1: Analysis
- Read requirements
- Identify affected components
- Review `/docs architecture`, `/rules`

## Phase 2: Design
- Clean Architecture
- DB schema if needed: `/docs database-erd`
- Review `/docs coding-standards`

## Phase 3: TDD (Red-Green-Refactor)

```bash
# 1. Write failing test → tests/unit/<module>/test_<feature>.py
# 2. Write minimal code → src/<module>/<feature>.py
# 3. Refactor while green
# 4. Verify coverage
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
```

Coverage: new 100%, critical 95%, overall 85%

## Phase 4: Database

```bash
alembic revision -m "description"   # Write upgrade()+downgrade()
alembic upgrade head
/migrate verify
```

Update: `docs/architecture/database-erd.md`

## Phase 5: Validation

```bash
/quality fix       # Format/lint/type
/test              # All tests
/dry-run           # MANDATORY
```

Exit checklist: tests passing | Black/Ruff/mypy clean | dry-run OK

## Phase 6: Commit

```
git commit -m "feat: description

- Implementation detail
- Coverage

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Types: feat | fix | refactor | test | docs | config | perf
