# Fix: Disable Notifications in Dry-Run Mode

**Date**: 2026-01-13
**Severity**: 🟡 **MEDIUM**
**Status**: ✅ **FIXED**

## 🐛 Problem Description

### Issue
User menerima notifikasi update posisi (breakeven, trailing stop) saat bot berjalan di **dry-run mode**, padahal seharusnya tidak ada notifikasi di dry-run karena tidak ada trading real yang terjadi.

### Impact
- **Noise**: Notifikasi tidak perlu di dry-run mode
- **Confusion**: User mungkin mengira ada trading real yang terjadi
- **Telegram Spam**: Banyak notifikasi yang tidak relevan

### Root Cause
Di beberapa tempat di `main.py`, notifikasi dikirim baik di live trading maupun dry-run mode:
1. **Breakeven notifications** (line ~1532): Dikirim jika `is_dry_run` atau `mt5_modified`
2. **Trailing stop activation** (line ~1576): Dikirim tanpa check dry-run
3. **Trailing stop update** (line ~1692): Dikirim di dry-run mode dengan status "🧪 Dry-run mode"

## ✅ Solution Implemented

### 1. Breakeven Notifications

**Location**: `src/trading_bot/main.py` - `_check_position_automation()` method

**Before**:
```python
if (mt5_modified or is_dry_run) and not is_already_at_breakeven:
    # ... save position ...
    await self.notification_manager.send_message(...)  # Always sent
```

**After**:
```python
if mt5_modified and not is_already_at_breakeven:
    # ... save position ...
    # Only send notification in LIVE trading (not dry-run)
    if not is_dry_run and self.notification_manager:
        await self.notification_manager.send_message(...)

elif is_dry_run and not is_already_at_breakeven:
    # Dry-run: Save to DB but skip notification
    logger.info("BREAKEVEN (DRY-RUN): ... (no notification)")
    await self.position_manager.save_position(position)
```

### 2. Trailing Stop Activation Notifications

**Location**: `src/trading_bot/main.py` - `_check_position_automation()` method

**Before**:
```python
# Notify trailing activation
if self.notification_manager:
    await self.notification_manager.send_message(...)  # Always sent
```

**After**:
```python
# Notify trailing activation (only in LIVE trading, skip in dry-run)
if not is_dry_run and self.notification_manager:
    await self.notification_manager.send_message(...)
```

### 3. Trailing Stop Update Notifications

**Location**: `src/trading_bot/main.py` - `_check_position_automation()` method

**Before**:
```python
if is_dry_run:
    # Dry-run: always notify for testing
    should_notify = True
    mt5_status = "🧪 Dry-run mode"
elif mt5_modified:
    should_notify = True
    mt5_status = "✅ MT5 Updated"

if self.notification_manager and should_notify:
    await self.notification_manager.send_message(...)
```

**After**:
```python
if is_dry_run:
    # Dry-run: Skip notification (user doesn't want dry-run notifications)
    should_notify = False
    mt5_status = "🧪 Dry-run mode (notification skipped)"
    logger.debug("Dry-run mode: Skipping trailing stop notification")
elif mt5_modified:
    should_notify = True
    mt5_status = "✅ MT5 Updated"

if not is_dry_run and self.notification_manager and should_notify:
    await self.notification_manager.send_message(...)
```

## ✅ Validation

### Tests Run
```bash
uv run pytest tests/unit/ -k "test_main" -v
# Result: All tests passed ✅
```

### Linting
```bash
uv run ruff check src/trading_bot/main.py --fix
# Result: All checks passed! ✅
```

### Code Formatting
```bash
uv run black src/trading_bot/main.py
# Result: 1 file reformatted ✅
```

## 📊 Behavior After Fix

### Dry-Run Mode
```
✅ Position updates saved to database
✅ Logs still show all activity
❌ NO Telegram notifications sent
```

### Live Trading Mode
```
✅ Position updates saved to database
✅ Logs show all activity
✅ Telegram notifications sent (as before)
```

## 📝 Notification Types Affected

### Skipped in Dry-Run:
1. **Breakeven Secured** notifications
2. **Trailing Stop Activated** notifications
3. **Trailing Stop Updated** notifications

### Still Sent in Dry-Run (if needed):
- **Dry-Run Order** notifications (line 576) - Can be disabled separately if needed
- **Error notifications** - Still sent for debugging

## 🎯 Benefits

1. **Cleaner Notifications**: No spam in dry-run mode
2. **Clear Separation**: Live trading vs testing clearly separated
3. **User Preference**: Respects user's request for no dry-run notifications
4. **Database Still Updated**: All position updates still saved (just no notifications)

## ⚠️ Important Notes

1. **Database Updates**: Position updates are still saved to database in dry-run mode
2. **Logs**: All activity is still logged (check logs for dry-run activity)
3. **Dry-Run Orders**: Order execution notifications (line 576) are still sent (can be disabled separately)
4. **Error Notifications**: Error notifications are still sent for debugging

## 🔧 Related Code Files

- `src/trading_bot/main.py` - Main fix implementation
  - `_check_position_automation()` - Line ~1532 (breakeven), ~1576 (trailing activation), ~1686 (trailing update)

## 🚀 Deployment

**Status**: ✅ Ready for Production

**Files Modified**:
- `src/trading_bot/main.py` (3 sections, ~15 lines changed)

**Testing**: ✅ All tests passed

**Rollback**: If issues occur, revert changes to `_check_position_automation()` method

---

**Implemented by**: AI Assistant
**Reviewed**: Pending
**Deployed**: Ready
