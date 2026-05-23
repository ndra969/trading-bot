---
description: Complete development workflow guide for trading bot project
argument-hint: [phase|all]
---

# Trading Bot Development Workflow

Complete workflow guide from analysis to deployment for the trading bot project.

## Arguments

- **no argument**: Display complete workflow overview
- `phase`: Show specific phase (analysis, design, implement, test, deploy, monitor)
- `all`: Show all phases in detail

## Development Phases

### Phase 1: Analysis & Requirements 📊

**Objective**: Understand what needs to be built

**Steps**:
1. **Understand the requirement**
   - Read issue/ticket/user story carefully
   - Identify affected components (strategies, risk, position, database)
   - Clarify ambiguities with questions

2. **Review existing codebase**
   - Use `/docs` to read relevant architecture docs
   - Use `/rules` to review critical implementation rules
   - Check existing code patterns in the codebase

3. **Identify dependencies**
   - Database schema changes needed?
   - New configuration parameters?
   - MT5 API changes?
   - External dependencies?

**Commands**:
```bash
/docs architecture          # Review system architecture
/docs risk-management       # Review risk management if related
/docs position-management   # Review position management if related
/docs database-erd          # Check database schema
/rules rules-only          # Review critical rules
```

**Output**: Clear understanding of requirements and dependencies

---

### Phase 2: Design & Planning 🎯

**Objective**: Plan the implementation approach

**Steps**:
1. **Design the solution**
   - Follow Clean Architecture principles
   - Apply Foundation-First approach (strategies)
   - Use ORM + Repository pattern
   - Ensure async-first architecture

2. **Database design** (if schema changes needed)
   - Design tables/columns following existing patterns
   - Create Alembic migration file
   - Update ERD documentation
   - Plan data migration if needed

3. **Configuration design**
   - Add YAML configuration entries
   - Document in relevant guides
   - Ensure environment-specific configs work

4. **API/Integration design** (if MT5 or external APIs)
   - Review connector patterns
   - Plan error handling
   - Design retry logic

**Commands**:
```bash
/docs database-erd          # Review database design
/docs coding-standards      # MUST review before coding
/docs configuration         # Review config patterns
```

**Output**: Implementation plan with database design and configuration

---

### Phase 3: TDD Implementation 🧪

**Objective**: Build features using Test-Driven Development

**CRITICAL RULE**: Tests MUST be written FIRST (Red-Green-Refactor)

**Steps**:

#### 3.1 Red Phase - Write Failing Test
```bash
# Create test file
tests/unit/trading_bot/<module>/test_<feature>.py

# Write test cases
- Happy path scenarios
- Edge cases and error conditions
- Property-based tests with Hypothesis (for mathematical logic)
- Integration tests for component interaction

# Run test (MUST FAIL)
uv run pytest tests/unit/<module>/test_<feature>.py -v
```

#### 3.2 Green Phase - Write Implementation
```bash
# Write minimal code to pass test
src/trading_bot/<module>/<feature>.py

# Requirements:
- Type hints for all functions (mypy clean)
- Async-first architecture
- SQLAlchemy 2.0 async syntax
- No hardcoded values (use YAML config)
- Follow Clean Architecture

# Run test (MUST PASS)
uv run pytest tests/unit/<module>/test_<feature>.py -v
```

#### 3.3 Refactor Phase - Improve Code
```bash
# Refactor while keeping tests green
- Extract repeated code
- Improve naming
- Add docstrings
- Apply design patterns

# Verify tests still pass
uv run pytest tests/unit/<module>/test_<feature>.py -v

# Run full test suite
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
```

**Commands**:
```bash
/tdd feature-name           # Get TDD guidance
/test critical              # Run critical component tests (95% coverage)
/test unit                  # Run unit tests only
```

**Coverage Requirements**:
- New features: **100% coverage** (MANDATORY)
- Critical components (risk, position sizing): **95% coverage**
- Overall codebase: **85% coverage**

---

### Phase 4: Database Migration (if needed) 🐘

**Objective**: Apply database schema changes safely

**Steps**:
1. **Create migration file**
```bash
# Using Alembic
alembic revision --autogenerate -m "description of changes"

# Or create manually
alembic revision -m "description of changes"
```

2. **Write migration code**
```python
# File: alembic/versions/XXXX_<description>.py

def upgrade():
    # Apply schema changes
    # Example: create table, add column, create index

def downgrade():
    # Revert changes (rollback capability)
```

3. **Test migration locally**
```bash
# Test with SQLite
DATABASE_URL=sqlite+aiosqlite:///test.db uv run alembic upgrade head

# Test with PostgreSQL (if applicable)
DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head
```

4. **Verify migration**
```bash
/migrate verify
```

**Commands**:
```bash
/migrate status             # Check migration status
/migrate migrate            # Run migration
/migrate verify             # Verify success
```

**Documentation**:
- Update `docs/diagrams/database-erd.md` (includes mermaid diagram)
- Document breaking changes

---

### Phase 5: Code Quality & Validation ✅

**Objective**: Ensure code meets all quality standards

**Steps**:
1. **Run code quality checks**
```bash
# Format check
uv run black src/ tests/ --check

# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/trading_bot/
```

2. **Fix any issues**
```bash
/quality fix                # Auto-fix format and linting
```

3. **Run complete test suite**
```bash
/test                       # All tests with 85% coverage
/test critical              # Critical components 95% coverage
```

4. **Final validation - DRY RUN (MANDATORY)**
```bash
/dry-run                    # MUST PASS before commit
```

**Commands**:
```bash
/quality fix                # Fix code quality issues
/test                       # Run all tests
/dry-run                    # Final validation
/coverage report            # Check coverage gaps
```

**Exit Checklist**:
- [ ] All tests passing (85%+ coverage, 95% for critical)
- [ ] Black formatted (no changes)
- [ ] Ruff clean (no errors)
- [ ] mypy clean (no type errors)
- [ ] Dry-run successful (no errors)

---

### Phase 6: Documentation & Commit 📝

**Objective**: Document changes and commit properly

**Steps**:
1. **Update documentation** (if needed)
   - Update relevant guides in `docs/guides/`
   - Update CLAUDE.md if critical rules changed
   - Update README.md for user-facing changes
   - Update API/docs if public APIs changed

2. **Commit changes**
```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat: add new feature description

- Implement feature X with TDD approach
- Add database migration for Y table
- Update configuration for Z parameter
- 100% test coverage achieved

🤖 Generated with Claude Code

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

3. **Commit message types**:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `refactor:` - Code refactoring (no behavior change)
   - `test:` - Test updates
   - `docs:` - Documentation only
   - `config:` - Configuration changes
   - `perf:` - Performance improvements

**Commands**:
```bash
/commit full                # Full validation before commit
```

---

### Phase 7: Testing & Monitoring 🚀

**Objective**: Validate in staging before production

**Steps**:
1. **Backtesting** (if strategy changes)
```bash
/backtest EURUSD            # Test strategy performance
/backtest --strategy mtf    # Multi-timeframe backtest
```

2. **Paper Trading** (if available)
   - Run in dry-run mode for extended period
   - Monitor logs for issues
   - Validate signals and positions

3. **Staging Deployment** (if applicable)
   - Deploy to staging environment
   - Monitor with reduced risk
   - Test with real market data

4. **Production Deployment** (with approval)
   - Get approval for production changes
   - Deploy during low-activity hours
   - Monitor closely for first 24 hours

**Commands**:
```bash
/backtest EURUSD            # Strategy validation
/dry-run                    # Extended dry-run testing
```

---

## Quick Reference Commands

### Planning
```bash
/docs [topic]               # Access documentation
/rules [format]             # Display project rules
```

### Development
```bash
/tdd [feature]              # TDD workflow guidance
/test [unit|critical]       # Run tests
/coverage [report]          # Check coverage
```

### Quality
```bash
/quality [fix]              # Code quality checks
/dry-run [config]           # Final validation
```

### Database
```bash
/migrate [status|migrate]   # Database migrations
```

### Analysis
```bash
/analyze <symbol>           # Foundation strategy analysis
/backtest <symbol>          # Run backtesting
```

### Commit
```bash
/commit [quick|full]        # Pre-commit validation
```

---

## Critical Rules Summary

⚠️ **MANDATORY RULES** (from CLAUDE.md):

1. **TDD-First Development**: Tests MUST be written before implementation
2. **100% Coverage**: All new features must have 100% test coverage
3. **Critical Components**: Risk management and position sizing need 95% coverage
4. **Code Quality**: All code must pass Black, Ruff, and mypy checks
5. **Dry-Run Validation**: MANDATORY before any commit
6. **No Hardcoded Values**: All configuration in YAML files
7. **Async-First**: Use async/await throughout
8. **Type Hints**: Required for all functions
9. **Clean Architecture**: Clear separation of concerns
10. **Documentation**: Update docs for any user-facing changes

---

## Examples

- `/workflow` → Display complete workflow
- `/workflow analysis` → Show analysis phase
- `/workflow implement` → Show TDD implementation phase
- `/workflow all` → Show all phases in detail

## Related

- `/rules` → Project rules and guidelines
- `/docs coding-standards` → Complete coding standards
- `/tdd` → TDD workflow guidance
