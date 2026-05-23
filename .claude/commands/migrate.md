---
description: Database migration management
argument-hint: [status|migrate|reset|verify]
---

# DB Migration

| Arg | Action |
|-----|--------|
| (none) or `status` | `uv run trading-bot postgresql status` |
| `migrate` | `uv run trading-bot postgresql migrate` |
| `verify` | `uv run trading-bot postgresql migrate --command verify` |
| `reset` | `uv run trading-bot postgresql reset` ⚠️ DELETES DATA |

## Step-by-Step Migration

```bash
uv run trading-bot postgresql migrate --command setup
uv run trading-bot postgresql migrate --command backup
uv run trading-bot postgresql migrate --command migrate
uv run trading-bot postgresql migrate --command transfer
uv run trading-bot postgresql migrate --command verify
```

## DB URLs

- Dev: `sqlite+aiosqlite:///trading_bot.db`
- Prod: `postgresql+asyncpg://user:pass@localhost:5432/dbname`

Configure via `DATABASE_URL` in `.env`.

## Alembic (Manual)

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic current
```
