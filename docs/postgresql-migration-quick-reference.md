# PostgreSQL Migration Quick Reference

## 🚀 Quick Commands

### Setup (5 minutes)
```bash
# 1. Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE trading_bot_db;"
psql -U postgres -c "CREATE USER trading_bot_user WITH PASSWORD 'secure_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE trading_bot_db TO trading_bot_user;"

# 2. Configure environment
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db"

# 3. Test connection
uv run trading-bot postgresql status
```

### Migration (2 minutes)
```bash
# Complete migration (recommended)
uv run trading-bot postgresql migrate

# Step-by-step alternative
uv run trading-bot postgresql migrate --command setup
uv run trading-bot postgresql migrate --command backup
uv run trading-bot postgresql migrate --command migrate
uv run trading-bot postgresql migrate --command transfer
uv run trading-bot postgresql migrate --command verify
```

### Verification (1 minute)
```bash
# Test trading bot with PostgreSQL
uv run trading-bot start --dry-run --config production

# Check migration status
uv run trading-bot postgresql status

# Verify data integrity
uv run trading-bot postgresql migrate --command verify
```

## 📋 Essential Checklists

### ✅ Pre-Migration Checklist
- [ ] PostgreSQL 14+ installed
- [ ] Database created: `trading_bot_db`
- [ ] User created: `trading_bot_user`
- [ ] Dependencies installed: `uv sync`
- [ ] SQLite backed up: `cp trading_bot.db backup.db`
- [ ] Environment variable set: `DATABASE_URL`

### ✅ Post-Migration Checklist
- [ ] Migration completed without errors
- [ ] Trading bot starts with PostgreSQL
- [ ] All data transferred correctly
- [ ] Performance benchmarks met
- [ ] Backup strategy configured
- [ ] Monitoring active

## 🛠️ Common Commands

### Database Management
```bash
# Reset PostgreSQL (WARNING: deletes all data)
uv run trading-bot postgresql reset

# Check migration status
uv run trading-bot postgresql status

# Manual Alembic commands
uv run alembic current
uv run alembic upgrade head
uv run alembic downgrade base
```

### Environment Management
```bash
# Use SQLite (fallback)
export DATABASE_URL="sqlite+aiosqlite:///trading_bot.db"

# Use PostgreSQL (production)
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db"

# Check current database
echo $DATABASE_URL
```

### Verification Commands
```bash
# Test repository pattern
uv run python scripts/test_repository_pattern.py

# Test trading bot functionality
uv run trading-bot start --dry-run --verbose

# Test zone detection
uv run trading-bot foundation analyze EURUSD --timeframe H1
```

## 🔧 Troubleshooting

### Connection Issues
```bash
# Check PostgreSQL service
sudo systemctl status postgresql
sudo systemctl start postgresql

# Test connection manually
psql -h localhost -U trading_bot_user -d trading_bot_db -c "SELECT version();"

# Check network connectivity
telnet localhost 5432
```

### Migration Issues
```bash
# Reset migration state
uv run alembic stamp head

# Force re-run migration
uv run alembic downgrade base
uv run alembic upgrade head

# Check migration history
uv run alembic history
```

### Performance Issues
```bash
# Enable query logging
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db?echo=true"

# Check database connections
SELECT * FROM pg_stat_activity WHERE datname = 'trading_bot_db';

# Analyze table statistics
ANALYZE trades;
ANALYZE market_data;
ANALYZE system_health;
```

## 📊 Database Verification

### SQL Queries for Verification
```sql
-- Check table counts
SELECT 'trades' as table_name, COUNT(*) as record_count FROM trades
UNION ALL
SELECT 'market_data', COUNT(*) FROM market_data
UNION ALL
SELECT 'system_health', COUNT(*) FROM system_health;

-- Check latest records
SELECT 'trades', MAX(created_at) as latest FROM trades
UNION ALL
SELECT 'market_data', MAX(timestamp) FROM market_data
UNION ALL
SELECT 'system_health', MAX(timestamp) FROM system_health;

-- Check data quality
SELECT COUNT(*) as trades_without_symbol FROM trades WHERE symbol IS NULL OR symbol = '';
SELECT COUNT(*) as market_data_without_price FROM market_data WHERE close_price IS NULL;
SELECT COUNT(*) as health_without_component FROM system_health WHERE component IS NULL OR component = '';
```

### Python Verification Script
```python
# Quick verification script
import asyncio
from trading_bot.services import create_database_service
from trading_bot.config import DatabaseConfig

async def verify_postgresql():
    config = DatabaseConfig(
        url="postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db"
    )

    async with create_database_service(config) as db:
        info = await db.get_database_info()
        print(f"✅ Database connected successfully")
        print(f"📊 Total trades: {info['total_trades']}")
        print(f"📈 Market data records: {info['total_market_data']}")
        print(f"🏥 Health records: {info['total_health_records']}")

        # Test basic operations
        active_trades = await db.get_active_trades(limit=1)
        print(f"🔄 Active trades: {len(active_trades)}")

        health_summary = await db.get_component_health_summary()
        print(f"💚 Components monitored: {len(health_summary)}")

if __name__ == "__main__":
    asyncio.run(verify_postgresql())
```

## 🚨 Emergency Procedures

### Rollback to SQLite
```bash
# 1. Stop trading bot
pkill -f "trading-bot"

# 2. Switch to SQLite
export DATABASE_URL="sqlite+aiosqlite:///trading_bot.db"

# 3. Verify SQLite works
uv run trading-bot start --dry-run

# 4. Start trading bot with SQLite
uv run trading-bot start --config production
```

### Restore PostgreSQL Backup
```bash
# Restore from backup file
gunzip -c backup_20251028_120000.sql.gz | psql -h localhost -U trading_bot_user -d trading_bot_db

# Verify restore
uv run trading-bot postgresql migrate --command verify
```

### Reset PostgreSQL Completely
```bash
# WARNING: This deletes all data
uv run trading-bot postgresql reset

# Re-run migration
uv run trading-bot postgresql migrate
```

## 📞 Quick Help

### Environment Variables
```bash
# Required for PostgreSQL
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db"

# Optional for SSL
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db?ssl=true"

# Optional for connection pool
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db?pool_size=20&max_overflow=30"
```

### File Locations
```
# Migration files
alembic/
├── versions/
│   └── 001_initial_migration.py
├── env.py
└── script.py.mako

# Configuration
config/postgresql.yaml
.env
alembic.ini

# Documentation
docs/postgresql-migration-guide.md
docs/postgresql-migration-todo.md
```

### CLI Commands Reference
```bash
# PostgreSQL commands
uv run trading-bot postgresql migrate
uv run trading-bot postgresql status
uv run trading-bot postgresql reset

# Sub-commands
uv run trading-bot postgresql migrate --command setup
uv run trading-bot postgresql migrate --command backup
uv run trading-bot postgresql migrate --command migrate
uv run trading-bot postgresql migrate --command transfer
uv run trading-bot postgresql migrate --command verify

# Alembic commands (alternative)
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic current
uv run alembic history
```

---

## 🎯 Success Metrics

### Migration Success
- ✅ Zero data loss
- ✅ All features working
- ✅ Performance improved
- ✅ Monitoring active

### Performance Benchmarks
- ✅ Queries < 100ms
- ✅ Connections > 20 concurrent
- ✅ Uptime > 99.9%
- ✅ Data transfer < 5 minutes

---

**Ready for Production Migration! 🚀**
