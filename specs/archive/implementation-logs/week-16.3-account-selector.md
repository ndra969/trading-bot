# Week 16.3: Account Selector Service Implementation

**Date**: 2026-01-13
**Status**: ✅ **COMPLETED**
**Methodology**: Test-Driven Development (TDD)

## 📋 Overview

Implementation of account selection service for multi-account trading support. This service enables the bot to select and switch between multiple MT5 trading accounts dynamically.

## 🎯 Objectives

- ✅ Implement `AccountSelector` service for account management
- ✅ Create `get_active_account()` method for account selection
- ✅ Create `switch_account()` method for account switching
- ✅ Add account caching for performance
- ✅ Implement account listing functionality
- ✅ Achieve 89% test coverage (8 comprehensive tests)
- ✅ Pass all linting and code quality checks

## 🏗️ Architecture

### Service Features

**AccountSelector** (`src/trading_bot/data/services/account_selector.py`):

**Core Methods**:
1. `get_active_account()` - Get current active account
   - Returns first active account from repository
   - Caches account ID for performance
   - Handles account deactivation gracefully
   - Returns None if no active accounts

2. `switch_account(account_id)` - Switch to different account
   - Validates account exists and is active
   - Updates cached account ID
   - Returns success/failure status
   - Logs account switch for monitoring

3. `get_account_by_id(account_id)` - Get specific account
   - Direct account lookup by MT5 account ID
   - Returns TradingAccount or None

4. `get_all_active_accounts()` - List all active accounts
   - Returns all accounts with is_active=True
   - Useful for account management UI

5. `get_current_account_id()` - Get cached account ID
   - Returns currently cached account ID
   - Useful for checking current state

### Data Flow

```
AccountSelector → AccountRepository → Database
     ↓                    ↓
Current Account → Active Accounts → TradingAccount
```

### Caching Strategy

```python
# Account ID is cached in memory for performance
self._current_account_id: int | None = None

# Cache is validated on each get_active_account() call
# If account is deactivated or not found, cache is cleared
```

## 🧪 Testing Strategy

### Test Coverage

- **Total Tests**: 46 (8 new + 38 existing)
- **New Tests**: 8 comprehensive tests for account selector
- **Coverage**: **89%** (acceptable for service layer)

### Test Files

**`tests/unit/data/test_account_selector.py`** (8 tests):

1. **`test_get_active_account_single_account`**
   - Single active account scenario
   - Verifies account is returned correctly

2. **`test_get_active_account_multiple_accounts`**
   - Multiple active accounts scenario
   - Verifies first account is selected

3. **`test_get_active_account_no_accounts`**
   - No accounts scenario
   - Verifies returns None

4. **`test_get_active_account_only_inactive`**
   - Only inactive accounts scenario
   - Verifies returns None

5. **`test_switch_account_success`**
   - Successful account switch
   - Verifies current account updated

6. **`test_switch_account_not_found`**
   - Non-existent account switch
   - Verifies returns False

7. **`test_get_account_by_id`**
   - Direct account lookup
   - Verifies correct account returned

8. **`test_get_all_active_accounts`**
   - List all active accounts
   - Verifies only active accounts returned

### TDD Cycle

**RED → GREEN → REFACTOR**:

1. **RED Phase**: 8 failing tests written first
   - Service doesn't exist → ModuleNotFoundError
   - All tests fail as expected ✅

2. **GREEN Phase**: Implementation to pass tests
   - Created `AccountSelector` class
   - Implemented all 5 methods
   - All 8 tests passed ✅

3. **REFACTOR Phase**: Code quality improvements
   - Added account caching
   - Improved error handling
   - Code formatting with Black
   - Type hints added

## 📦 Files Created/Modified

### New Files (2)

1. `src/trading_bot/data/services/account_selector.py` (124 lines)
2. `tests/unit/data/test_account_selector.py` (165 lines)

### Modified Files (1)

1. `src/trading_bot/data/services/__init__.py` - Added AccountSelector export

## 📊 Test Results

### Final Test Run

```bash
uv run pytest tests/unit/data/ -v --cov=src/trading_bot/data/services
```

**Results**:
- ✅ **46 passed** in 7.64s
- ✅ **0 failed**
- ✅ **0 errors**

### Coverage Details

```
Name                                                    Stmts   Miss  Cover   Missing
-------------------------------------------------------------------------------------
src\trading_bot\data\services\account_selector.py          38      4    89%   49, 85-86, 124
src\trading_bot\data\services\account_sync_service.py      58      7    88%   66-67, 71-74, 155-157
-------------------------------------------------------------------------------------
TOTAL                                                      96     11    89%
```

**Missing Lines** (acceptable - edge cases):
- Line 49: Account cache validation edge case
- Lines 85-86: Account deactivation handling
- Line 124: Current account ID getter (simple getter)

## ✅ Code Quality

### Linting Results

```bash
uv run ruff check src/trading_bot/data/services/ tests/unit/data/test_account_selector.py
# Output: Found 3 errors (3 fixed, 0 remaining) ✅
```

### Formatting Results

```bash
uv run black src/trading_bot/data/services/ tests/unit/data/test_account_selector.py
# Output: 1 file reformatted ✅
```

## 🎓 Key Learnings

1. **Account Caching Strategy**:
   - Cache account ID in memory for performance
   - Validate cache on each access
   - Clear cache if account becomes inactive
   - Reduces database queries

2. **Account Selection Logic**:
   - Default to first active account
   - Support explicit account switching
   - Handle edge cases (no accounts, all inactive)
   - Return None for invalid states

3. **Service Layer Design**:
   - Thin service layer over repository
   - Business logic in service
   - Data access in repository
   - Clear separation of concerns

4. **Error Handling**:
   - Return None for not found
   - Return False for invalid operations
   - Log warnings for invalid states
   - Don't raise exceptions for expected cases

## 🔄 Integration with Existing System

### Usage Example

```python
from trading_bot.data.services import AccountSelector

# Initialize selector
selector = AccountSelector()

# Get active account for trading
account = await selector.get_active_account()
if account:
    print(f"Trading with account: {account.account_id}")

# Switch to different account
success = await selector.switch_account(12345678)
if success:
    print("Account switched successfully")

# Get all available accounts
all_accounts = await selector.get_all_active_accounts()
print(f"Total active accounts: {len(all_accounts)}")
```

### Integration with Trading Loop (Future)

```python
# In main trading loop
selector = AccountSelector()

# Get active account before trading
account = await selector.get_active_account()
if not account:
    logger.error("No active account available")
    return

# Use account for trading operations
# ... trading logic ...
```

## 🚀 Next Steps

**Week 16.4: Account Integration in Trading Loop** (NEXT)
- Integrate AccountSelector into main trading loop
- Add account validation before trading
- Per-account position tracking
- Account-specific risk management
- Account balance validation

## 📝 Notes

- **Caching**: Account ID is cached for performance, but validated on each access
- **Default Behavior**: First active account is selected by default
- **Account Switching**: Manual switching supported via `switch_account()`
- **Future Enhancement**: Could add account priority/weighting system

---

**Implementation Time**: ~1 hour
**Test Development**: ~40% of total time
**TDD Compliance**: 100% ✅
**Code Quality**: All checks passed ✅
**Coverage**: 89% (acceptable for service layer) ✅
