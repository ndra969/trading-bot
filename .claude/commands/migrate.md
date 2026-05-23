---
description: Database migration management
argument-hint: [status|migrate|reset|verify]
---

# Database Migration Management

Manage database migrations for SQLite (development) and PostgreSQL (production).

## Arguments

- **no argument**: Show migration status
- `status`: Show current migration status
- `migrate`: Run complete migration (SQLite → PostgreSQL)
- `reset`: Reset PostgreSQL database (WARNING: deletes data)
- `verify`: Verify migration success

## Implementation Steps

1. **Check current status** of database and migrations
2. **Execute command** based on argument
3. **Verify results** and provide feedback

## Commands to Execute

```bash
# Check status (default)
uv run trading-bot postgresql status

# Complete migration process
uv run trading-bot postgresql migrate

# Step-by-step migration
uv run trading-bot postgresql migrate --command setup     # Setup PostgreSQL
uv run trading-bot postgresql migrate --command backup    # Backup SQLite
uv run trading-bot postgresql migrate --command migrate   # Run Alembic
uv run trading-bot postgresql migrate --command transfer  # Transfer data
uv run trading-bot postgresql migrate --command verify    # Verify success

# Reset database (WARNING!)
uv run trading-bot postgresql reset

# Verify migration
uv run trading-bot postgresql migrate --command verify
```

## Database Options

- **SQLite** (default): Development and testing
  - URL: `sqlite+aiosqlite:///trading_bot.db`
- **PostgreSQL** (production): High-performance production database
  - URL: `postgresql+asyncpg://user:pass@localhost:5432/dbname`

## Environment Configuration

Set via `.env` file:
```bash
DATABASE_URL=postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db
```

## Examples

- `/migrate` → Show migration status
- `/migrate migrate` → Run complete migration
- `/migrate verify` → Verify migration success

## Related

- `/dry-run` → Validate database connectivity
- `/rules` → Database schema information

## PostgreSQL Features

- ✅ ENUM types for trade_status, position_update_type
- ✅ JSONB support for zones and indicators
- ✅ GIN indexes for JSONB columns
- ✅ Sequences for auto-incrementing IDs
- ✅ Foreign keys for referential integrity
