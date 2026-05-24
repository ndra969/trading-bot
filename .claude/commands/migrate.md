---
description: Database migration management
argument-hint: [revision|upgrade|downgrade|current]
---

# DB Migration

> **Status**: Use Alembic directly. CLI wrapper (`trading-bot postgresql`) is 📋 planned.

## Alembic Commands (Current)

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check current revision
alembic current

# Show migration history
alembic history
```

## DB URLs

Configure via `DATABASE_URL` in `.env`:

- Dev: `sqlite+aiosqlite:///trading_bot.db`
- Prod: `postgresql+asyncpg://user:pass@localhost:5432/dbname`

## Planned CLI Wrapper

```bash
# 📋 Not yet implemented
uv run trading-bot postgresql migrate
uv run trading-bot postgresql status
uv run trading-bot postgresql reset  # WARNING
```
