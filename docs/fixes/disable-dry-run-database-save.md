# Fix: Disable Database Saves in Dry-Run Mode

**Date**: 2026-01-13
**Severity**: 🟡 **MEDIUM**
**Status**: ✅ **FIXED**

## 🐛 Problem Description

### Issue
Positions dari dry-run mode masih disimpan ke database, padahal seharusnya tidak karena:
- Dry-run adalah untuk testing, bukan real trading
- Database seharusnya hanya berisi data real trading
- Data test mengotori database production

### Impact
- **Database Pollution**: Database berisi data test yang tidak relevan
- **Data Integrity**: Sulit membedakan data real vs test
- **Storage Waste**: Database membesar dengan data yang tidak perlu
- **Analytics Confusion**: Analisis performance jadi tidak akurat

### Root Cause
Method `save_position()` di `PositionManager` tidak check dry-run mode sebelum menyimpan ke database.

## ✅ Solution Implemented

### Method Update

**File**: `src/trading_bot/position/position_manager.py`

**Before**:
```python
async def save_position(self, position: Position):
    """Save or update position in database."""
    try:
        # ... save logic ...
```

**After**:
```python
async def save_position(self, position: Position, is_dry_run: bool = False):
    """
    Save or update position in database.

    Args:
        position: Position to save
        is_dry_run: If True, skip saving to database (dry-run mode)
    """
    # CRITICAL: Skip saving to database in dry-run mode
    if is_dry_run:
        logger.debug(
            f"🧪 Dry-run mode: Skipping database save for position {position.position_id}"
        )
        return

    try:
        # ... save logic ...
```

### All Call Sites Updated

**File**: `src/trading_bot/main.py`

Semua 16 calls ke `save_position()` di-update untuk pass `is_dry_run` parameter:

```python
# Before
await self.position_manager.save_position(position)

# After
await self.position_manager.save_position(position, is_dry_run=is_dry_run)
```

**Locations Updated**:
1. Line 624: Position creation after signal execution
2. Line 916: Position closed in MT5 (sync reconciliation)
3. Line 961: Position closed during update
4. Line 1034: Position closed (orphaned position)
5. Line 1165: Position closed during update
6. Line 1237: Position closed (sync reconciliation)
7. Line 1282: Position price update
8. Line 1536: Breakeven secured (live trading)
9. Line 1555: Breakeven (dry-run - now skipped)
10. Line 1564: Breakeven already set
11. Line 1569: Breakeven (MT5 not modified)
12. Line 1587: Trailing stop activated
13. Line 1646: Trailing stop (suspicious movement)
14. Line 1695: Trailing stop updated
15. Line 1802: Partial profit taken
16. Line 1873: Position closed (final)

## ✅ Validation

### Tests Run
```bash
uv run pytest tests/unit/position/ -v
# Result: 267 passed ✅
```

### Linting
```bash
uv run ruff check src/trading_bot/position/position_manager.py src/trading_bot/main.py --fix
# Result: All checks passed! ✅
```

### Code Formatting
```bash
uv run black src/trading_bot/position/position_manager.py src/trading_bot/main.py
# Result: Files formatted ✅
```

## 📊 Behavior After Fix

### Dry-Run Mode
```
✅ Position created in memory
✅ Position tracked and updated in memory
✅ Logs show all activity
❌ NO database saves
❌ NO Telegram notifications
```

### Live Trading Mode
```
✅ Position created in memory
✅ Position saved to database
✅ Position tracked and updated
✅ Database updated on every change
✅ Telegram notifications sent
```

## 📝 What Still Works in Dry-Run

1. **In-Memory Tracking**: Positions masih di-track di memory
2. **Position Updates**: Price updates, breakeven, trailing stop semua masih jalan
3. **Logging**: Semua activity masih di-log
4. **Strategy Testing**: Strategy logic tetap bisa di-test
5. **Risk Calculation**: Risk management tetap jalan

## 🎯 Benefits

1. **Clean Database**: Database hanya berisi data real trading
2. **Data Integrity**: Tidak ada mixing antara test dan production data
3. **Storage Efficiency**: Database tidak membesar dengan data test
4. **Accurate Analytics**: Analisis performance hanya dari data real
5. **Clear Separation**: Test vs Production jelas terpisah

## ⚠️ Important Notes

1. **In-Memory Only**: Dry-run positions hanya ada di memory, hilang saat bot restart
2. **No Persistence**: Dry-run positions tidak persist across restarts
3. **Testing Impact**: Jika perlu test dengan persistence, harus disable dry-run
4. **Logs Still Available**: Semua activity masih di-log untuk debugging

## 🔧 Related Code Files

- `src/trading_bot/position/position_manager.py` - Main fix implementation
  - `save_position()` method - Added `is_dry_run` parameter and skip logic
- `src/trading_bot/main.py` - All call sites updated
  - 16 locations updated to pass `is_dry_run` parameter

## 🚀 Deployment

**Status**: ✅ Ready for Production

**Files Modified**:
- `src/trading_bot/position/position_manager.py` (1 method, ~5 lines added)
- `src/trading_bot/main.py` (16 call sites updated + 1 method fix)

**Testing**: ✅ All tests passed (1066 passed)

**Rollback**: If issues occur, revert changes to `save_position()` method and remove `is_dry_run` parameter from all calls

## 📝 Additional Fixes

### Partial Close Notification
Also disabled partial close notifications in dry-run mode (line ~1803).

### Missing is_dry_run Variable
Fixed undefined `is_dry_run` variable in `_check_position_closure()` method by adding dry-run check at method start.

---

**Implemented by**: AI Assistant
**Reviewed**: Pending
**Deployed**: Ready
