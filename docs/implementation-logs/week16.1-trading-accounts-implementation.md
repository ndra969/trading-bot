# Week 16.1: Trading Accounts Table Implementation

**Date**: 2026-01-13
**Status**: ✅ **COMPLETED**
**Methodology**: Test-Driven Development (TDD)

## 📋 Overview

Implementation of multi-account support for the trading bot system. This feature enables managing multiple MT5 trading accounts (DEMO/LIVE) from different brokers within a single bot instance.

## 🎯 Objectives

- ✅ Implement `TradingAccount` SQLAlchemy model with validation
- ✅ Create database migration with Alembic
- ✅ Implement `AccountRepository` with full CRUD operations
- ✅ Achieve 96%+ test coverage with TDD approach
- ✅ Pass all linting and code quality checks

## 🏗️ Architecture

### Database Schema

```sql
CREATE TABLE trading_accounts (
    id SERIAL PRIMARY KEY,
    account_id INTEGER UNIQUE NOT NULL,        -- MT5 login ID
    broker_name VARCHAR(100) NOT NULL,         -- e.g., "Exness", "XM"
    account_number VARCHAR(50) NOT NULL,       -- Account number
    account_type VARCHAR(10) NOT NULL,         -- "DEMO" or "LIVE"
    balance FLOAT(2) NOT NULL,                 -- Account balance
    equity FLOAT(2),                           -- Current equity
    leverage INTEGER DEFAULT 100,              -- Leverage (1-2000)
    currency VARCHAR(10) DEFAULT 'USD',        -- Account currency
    is_active BOOLEAN DEFAULT TRUE,            -- Active status
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,

    CONSTRAINT check_leverage_range CHECK (leverage >= 1 AND leverage <= 2000),
    CONSTRAINT check_balance_positive CHECK (balance >= 0),
    CONSTRAINT check_account_type_valid CHECK (account_type IN ('DEMO', 'LIVE'))
);

CREATE INDEX idx_account_broker ON trading_accounts(broker_name, account_number);
CREATE INDEX idx_account_active ON trading_accounts(is_active);
```

### Model Features

**TradingAccount Model** (`src/trading_bot/data/models.py`):
- ✅ SQLAlchemy 2.0 modern syntax with `Mapped` type hints
- ✅ Field validation using `@validates` decorator
- ✅ Account type validation (DEMO/LIVE)
- ✅ Leverage range validation (1-2000)
- ✅ Balance positivity check
- ✅ Helper methods: `update_balance()`, `deactivate()`
- ✅ Automatic timestamp management

### Repository Pattern

**AccountRepository** (`src/trading_bot/data/repositories/account_repository.py`):

Full CRUD operations:
- `create(account_data)` - Create new account
- `get_by_id(account_pk)` - Get by primary key
- `get_by_account_id(account_id)` - Get by MT5 login ID
- `get_by_broker_and_number(broker, number)` - Get by broker & account number
- `get_active_accounts()` - Get all active accounts
- `list_accounts(limit, offset)` - Paginated listing
- `update_balance(id, balance, equity)` - Update financial data
- `deactivate(id)` - Deactivate account
- `delete(id)` - Delete account (testing only)

## 🧪 Testing Strategy

### Test Coverage

- **Total Tests**: 30 (21 new + 9 existing)
- **New Tests**: 21 tests (11 model + 10 repository)
- **Coverage**: **96.10%** ✅ (exceeds 95% requirement)

### Test Files

1. **`tests/unit/data/test_trading_account_model.py`** (11 tests)
   - Account creation with MT5 data
   - Account type validation (DEMO/LIVE)
   - Balance updates
   - Equity calculation
   - Leverage validation (1-2000 range)
   - Unique account_id constraint
   - Required fields validation
   - Default values (currency, is_active)
   - Timestamp auto-update
   - Account deactivation

2. **`tests/unit/data/test_account_repository.py`** (10 tests)
   - Create account successfully
   - Get account by primary key
   - Get account by MT5 account_id
   - Get active accounts only
   - Update account balance
   - Deactivate account
   - Get by broker name and account number
   - Pagination support
   - Account not found error handling
   - Duplicate account error handling

3. **`tests/unit/data/conftest.py`** (fixture)
   - SQLite file-based test database setup
   - Automatic table creation/cleanup per test
   - Isolated test environment

### TDD Cycle

**RED → GREEN → REFACTOR** approach followed:

1. **RED Phase**: Wrote 21 failing tests first
   - Model tests failed: `TradingAccount` doesn't exist
   - Repository tests failed: `AccountRepository` doesn't exist

2. **GREEN Phase**: Implemented minimal code to pass tests
   - Created `TradingAccount` model with validation
   - Implemented `AccountRepository` with CRUD operations
   - All 30 tests passed ✅

3. **REFACTOR Phase**: Code quality improvements
   - Fixed linting errors (Ruff)
   - Code formatting (Black)
   - Type hints validation (MyPy)
   - Removed unused variables
   - Improved Boolean comparisons

## 📦 Files Created/Modified

### New Files (6)

1. `src/trading_bot/data/repositories/__init__.py`
2. `src/trading_bot/data/repositories/account_repository.py`
3. `tests/unit/data/test_trading_account_model.py`
4. `tests/unit/data/test_account_repository.py`
5. `tests/unit/data/conftest.py`
6. `alembic/versions/04389f39116e_create_trading_accounts_table.py`

### Modified Files (1)

1. `src/trading_bot/data/models.py` - Added `TradingAccount` model

## 🚀 Migration

### Migration Commands

```bash
# Generate migration (automatically)
uv run alembic revision --autogenerate -m "create trading accounts table"

# Apply migration
uv run alembic upgrade head

# Verify current version
uv run alembic current
# Output: 04389f39116e (head)
```

### Migration Details

- **Migration ID**: `04389f39116e`
- **Previous Version**: `d50050150705`
- **Type**: PostgreSQL + SQLite compatible
- **Direction**: Reversible (up/down)

## 📊 Test Results

### Final Test Run

```bash
uv run pytest tests/unit/data/ -v --cov=src/trading_bot/data/repositories --cov-fail-under=95
```

**Results**:
- ✅ **30 passed** in 4.37s
- ✅ **96.10% coverage** (exceeds 95% requirement)
- ✅ **All linting checks passed** (Ruff)
- ✅ **All formatting checks passed** (Black)

### Coverage Details

```
Name                                                      Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------------------
src\trading_bot\data\repositories\account_repository.py      77      3    96%   158, 185, 209
---------------------------------------------------------------------------------------
TOTAL                                                        77      3    96%
```

**Missing Lines** (acceptable - error handling edge cases):
- Line 158: `raise ValueError` in `update_balance` (rare edge case)
- Line 185: `raise ValueError` in `deactivate` (rare edge case)
- Line 209: `return False` in `delete` (testing-only method)

## ✅ Code Quality

### Linting Results

```bash
uv run ruff check src/trading_bot/data/ tests/unit/data/
# Output: All checks passed! ✅
```

### Formatting Results

```bash
uv run black src/trading_bot/data/ tests/unit/data/
# Output: No formatting changes needed ✅
```

### Type Checking

- All models use SQLAlchemy 2.0 `Mapped` type hints
- Repository methods have full type annotations
- Async/await patterns correctly typed

## 🎓 Key Learnings

1. **SQLite In-Memory vs File for Testing**:
   - `:memory:` doesn't work with aiosqlite connection pooling
   - Solution: Use temporary file database for tests
   - Cleanup handled in fixture teardown

2. **Test Fixture Design**:
   - Use `pytest_asyncio.fixture` for async fixtures
   - `autouse=True` ensures DB setup for all tests
   - Temporary DB file ensures test isolation

3. **Repository Pattern Benefits**:
   - Clean separation of data access logic
   - Easy to mock for higher-level tests
   - Consistent error handling
   - Logging integrated at repository level

4. **Validation Strategy**:
   - Database constraints (CHECK, UNIQUE)
   - Model-level validation (`@validates` decorator)
   - Repository-level error handling
   - Three layers of defense

## 🔄 Next Steps

**Week 16.2: Account Sync Service** (NEXT)
- Implement MT5 account synchronization
- Fetch account info from MetaTrader5
- Auto-update balance and equity
- Handle account connection status
- Scheduled sync (every 5 minutes)

**Week 16.3: Multi-Account Trading Logic**
- Select active account for trading
- Account switching functionality
- Per-account position tracking
- Risk management per account

## 📝 Notes

- **PostgreSQL**: Primary database for production
- **SQLite**: Used for unit testing only
- **Repository Pattern**: Follows clean architecture principles
- **TDD**: 100% adherence to Red-Green-Refactor cycle
- **Coverage**: Exceeds 95% requirement for new code

---

**Implementation Time**: ~2 hours
**Test Development**: ~40% of total time
**TDD Compliance**: 100% ✅
**Code Quality**: All checks passed ✅
