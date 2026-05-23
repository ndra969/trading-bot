# Fix: Ticket Column INTEGER to BIGINT

**Date**: 2026-01-13
**Severity**: 🔴 **CRITICAL**
**Status**: ✅ **FIXED**

## 🐛 Problem Description

### Issue
MT5 ticket numbers dapat melebihi batas INT32 (2,147,483,647), menyebabkan error saat menyimpan position ke database PostgreSQL:

```
ERROR: invalid input for query argument $5: 2504462968 (value out of int32 range)
[SQL: UPDATE positions SET ... ticket=$5::INTEGER ...]
```

### Impact
- **Database Error**: Position tidak bisa disimpan ke database
- **Data Loss**: Position tracking gagal
- **Bot Crash**: Potential bot failure saat update position
- **MT5 Integration**: Ticket numbers > 2.1B tidak bisa disimpan

### Root Cause
Column `ticket` di table `positions` menggunakan `INTEGER` (INT32) dengan range:
- **Min**: -2,147,483,648
- **Max**: 2,147,483,647

MT5 ticket numbers bisa lebih besar dari 2.1B, contoh: `2504462968`

## ✅ Solution Implemented

### Database Schema Change

**Changed Column Type**: `INTEGER` → `BIGINT`

**BIGINT Range**:
- **Min**: -9,223,372,036,854,775,808
- **Max**: 9,223,372,036,854,775,807

Ini cukup untuk menampung semua MT5 ticket numbers.

### Code Changes

**File**: `src/trading_bot/data/models.py`

**Before**:
```python
from sqlalchemy import JSON, Boolean, CheckConstraint, Float, Index, Integer, String

class Position(Base):
    ticket: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, unique=True
    )  # MT5 ticket number for order tracking
```

**After**:
```python
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    Index,
    Integer,
    String,
)

class Position(Base):
    ticket: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, unique=True
    )  # MT5 ticket number for order tracking (BIGINT for large ticket numbers)
```

### Migration Applied

**Migration File**: `alembic/versions/0b9ebafd26aa_change_ticket_to_bigint_for_large_mt5_.py`

**SQL Executed**:
```sql
ALTER TABLE positions
ALTER COLUMN ticket TYPE BIGINT;
```

**Migration Command**:
```bash
uv run alembic revision --autogenerate -m "change ticket to bigint for large mt5 ticket numbers"
uv run alembic upgrade head
```

**Result**:
```
INFO  [alembic.runtime.migration] Running upgrade 04389f39116e -> 0b9ebafd26aa
INFO  [alembic.autogenerate.compare] Detected type change from INTEGER() to BigInteger() on 'positions.ticket'
```

## ✅ Validation

### Tests Run
```bash
uv run pytest tests/unit/data/ -v
# Result: 38 passed ✅
```

### Linting
```bash
uv run ruff check src/trading_bot/data/models.py --fix
# Result: All checks passed! ✅
```

### Code Formatting
```bash
uv run black src/trading_bot/data/models.py
# Result: 1 file left unchanged ✅
```

### Database Verification
```sql
-- Check column type in PostgreSQL
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'positions' AND column_name = 'ticket';

-- Result:
-- column_name | data_type | character_maximum_length
-- ticket      | bigint    | NULL
```

## 📊 Ticket Number Examples

### Valid Ticket Numbers (After Fix)

| Ticket Number | Status | Notes |
|---------------|--------|-------|
| 12345 | ✅ Valid | Small ticket |
| 2147483647 | ✅ Valid | INT32 max (old limit) |
| 2504462968 | ✅ Valid | **Previously failed** |
| 9223372036854775807 | ✅ Valid | BIGINT max |

### Before vs After

**Before (INTEGER)**:
```python
ticket = 2504462968  # > INT32_MAX
# ERROR: value out of int32 range ❌
```

**After (BIGINT)**:
```python
ticket = 2504462968  # < BIGINT_MAX
# SUCCESS: Saved to database ✅
```

## 🔍 Technical Details

### PostgreSQL Data Types

| Type | Storage | Range |
|------|---------|-------|
| INTEGER (INT4) | 4 bytes | -2,147,483,648 to 2,147,483,647 |
| BIGINT (INT8) | 8 bytes | -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807 |

### Python Type Mapping

```python
# SQLAlchemy mapping
Integer → PostgreSQL INTEGER (4 bytes)
BigInteger → PostgreSQL BIGINT (8 bytes)

# Python int has unlimited precision
# So Python side has no issues, only database constraint
```

### Index Impact

**Index Remains Valid**: PostgreSQL automatically updates index when column type changes.

```sql
-- Index still works after migration
CREATE UNIQUE INDEX idx_position_ticket ON positions(ticket);
```

**Performance**: BIGINT index is slightly larger (8 bytes vs 4 bytes per entry), but impact is negligible for typical position volumes.

## ⚠️ Important Notes

1. **Backward Compatibility**: All existing ticket values remain valid (they're within BIGINT range).

2. **No Data Loss**: Migration preserves all existing data.

3. **Index Rebuild**: PostgreSQL may rebuild index during migration (brief lock on table).

4. **Application Restart**: Recommended after migration to ensure ORM uses new type.

5. **MT5 Ticket Range**: MT5 ticket numbers are positive integers, typically in range 1 to 10 billion.

## 🚀 Deployment

**Status**: ✅ Deployed to Database

**Files Modified**:
- `src/trading_bot/data/models.py` - Changed Integer to BigInteger
- `alembic/versions/0b9ebafd26aa_*.py` - Migration file (auto-generated)

**Database Changes**:
- `positions.ticket` column: INTEGER → BIGINT

**Testing**: ✅ All tests passed (38 passed)

**Rollback**:
```sql
-- If needed (NOT RECOMMENDED unless tickets < INT32_MAX)
ALTER TABLE positions ALTER COLUMN ticket TYPE INTEGER;
```

## 📝 Related Issues

- **Error Message**: `value out of int32 range`
- **Affected Tickets**: Any ticket > 2,147,483,647
- **First Occurrence**: 2026-01-13 12:31:55
- **Example Ticket**: 2504462968

## 🎯 Benefits

1. **No More Errors**: All MT5 ticket numbers can be saved
2. **Future-Proof**: Handles tickets up to 9.2 quintillion
3. **Data Integrity**: No ticket truncation or loss
4. **Reliability**: Bot won't crash on large tickets

---

**Implemented by**: AI Assistant
**Reviewed**: Pending
**Deployed**: ✅ Production Database
