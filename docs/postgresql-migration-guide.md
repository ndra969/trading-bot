# PostgreSQL Migration Guide

This guide covers migrating from SQLite to PostgreSQL for production trading bot deployment.

## Prerequisites

1. **PostgreSQL Server** - Install PostgreSQL 14+ on your system
2. **Database User** - Create a dedicated user for the trading bot
3. **Python Dependencies** - Required packages are already included

```bash
# PostgreSQL installation (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# PostgreSQL installation (Windows)
# Download and install from https://www.postgresql.org/download/windows/

# Python dependencies (already added)
uv sync  # Includes asyncpg and sqlalchemy[postgresql]
```

## Database Setup

### 1. Create Database and User

```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database
CREATE DATABASE trading_bot_db;

-- Create user with password
CREATE USER trading_bot_user WITH PASSWORD 'password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_bot_db TO trading_bot_user;

-- Exit PostgreSQL
\q
```

### 2. Configure Environment

Update your `.env` file to use PostgreSQL:

```bash
# .env
DATABASE_URL=postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db
```

Or set environment variable:

```bash
export DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db"
```

## Migration Process

### Option 1: Automated Migration (Recommended)

Use the migration helper script:

```bash
# Complete migration process
python scripts/migrate_to_postgresql.py all

# Or step by step:
python scripts/migrate_to_postgresql.py setup    # Setup PostgreSQL database
python scripts/migrate_to_postgresql.py backup    # Backup SQLite data
python scripts/migrate_to_postgresql.py migrate   # Run Alembic migration
python scripts/migrate_to_postgresql.py transfer  # Transfer data
python scripts/migrate_to_postgresql.py verify    # Verify success
```

### Option 2: Manual Migration

#### Step 1: Run Alembic Migration

```bash
# Initialize database schema
uv run alembic upgrade head
```

#### Step 2: Transfer Data (Optional)

If you want to migrate existing SQLite data:

```bash
# Use the transfer script
python scripts/migrate_to_postgresql.py backup
python scripts/migrate_to_postgresql.py transfer
```

#### Step 3: Verify Migration

```bash
# Test connection
uv run trading-bot start --dry-run

# Check database tables
python scripts/migrate_to_postgresql.py verify
```

## Configuration Options

### Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `POSTGRES_HOST` - PostgreSQL server host (default: localhost)
- `POSTGRES_PORT` - PostgreSQL server port (default: 5432)
- `POSTGRES_DB` - Database name (default: trading_bot_db)
- `POSTGRES_USER` - Database user (default: trading_bot_user)
- `POSTGRES_PASSWORD` - Database password

### Connection Pool Settings

PostgreSQL configuration in `config/postgresql.yaml`:

```yaml
database:
  url: "postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db"
  echo: false
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
```

## Testing the Migration

### 1. Dry Run Test

```bash
# Test with PostgreSQL configuration
DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db" \
uv run trading-bot start --dry-run
```

### 2. Database Connection Test

```bash
# Test database connection
python -c "
import asyncio
from src.trading_bot.data.database import initialize_database
from src.trading_bot.config import DatabaseConfig

async def test():
    config = DatabaseConfig(
        url='postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db'
    )
    await initialize_database(config)
    print('✅ PostgreSQL connection successful!')

asyncio.run(test())
"
```

### 3. Schema Verification

```bash
# Check if all tables exist
psql -U trading_bot_user -d trading_bot_db -c "\dt"

# Verify table structures
psql -U trading_bot_user -d trading_bot_db -c "\d trades"
psql -U trading_bot_user -d trading_bot_db -c "\d market_data"
```

## Production Considerations

### Security

1. **Strong Passwords** - Use strong database passwords
2. **SSL Connection** - Enable SSL for production
3. **Network Security** - Restrict database access to application server
4. **User Privileges** - Grant minimum required privileges

```bash
# SSL Connection Example
DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db?ssl=true"
```

### Performance

1. **Connection Pooling** - Optimize pool size for your workload
2. **Index Optimization** - Monitor and optimize database indexes
3. **Query Monitoring** - Enable slow query logging
4. **Regular Maintenance** - Schedule vacuum and analyze operations

### Backup Strategy

1. **Regular Backups** - Schedule automated database backups
2. **Point-in-Time Recovery** - Configure WAL archiving
3. **Testing Restores** - Regularly test backup restoration

```bash
# Manual backup
pg_dump -U trading_bot_user -h localhost trading_bot_db > backup.sql

# Automated backup (add to cron)
0 2 * * * pg_dump -U trading_bot_user -h localhost trading_bot_db | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### High Availability

1. **Replication** - Set up read replicas for scaling
2. **Failover** - Configure automatic failover
3. **Monitoring** - Monitor database health and performance

## Troubleshooting

### Common Issues

#### Connection Errors

```bash
# Error: FATAL: database "trading_bot_db" does not exist
# Solution: Create the database
createdb -U postgres trading_bot_db

# Error: FATAL: password authentication failed for user "trading_bot_user"
# Solution: Check password and user creation
psql -U postgres -c "ALTER USER trading_bot_user PASSWORD 'new_password';"
```

#### Migration Errors

```bash
# Error: relation "trades" already exists
# Solution: Reset migration state
uv run alembic stamp head

# Error: could not translate host name "localhost" to address
# Solution: Check PostgreSQL service status
sudo systemctl status postgresql
sudo systemctl start postgresql
```

#### Permission Issues

```bash
# Error: permission denied for relation trades
# Solution: Grant proper privileges
psql -U postgres -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_bot_user;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_bot_user;"
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Enable SQLAlchemy echo
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db?echo=true" \
uv run trading-bot start --dry-run
```

## Rollback

If you need to rollback to SQLite:

```bash
# Stop the bot
pkill -f "trading-bot"

# Update .env to use SQLite
sed -i 's/postgresql+asyncpg/sqlite+aiosqlite/' .env

# Restart with SQLite
uv run trading-bot start --dry-run
```

## Support

For issues with PostgreSQL migration:

1. Check PostgreSQL logs: `/var/log/postgresql/postgresql-*.log`
2. Verify network connectivity: `telnet localhost 5432`
3. Test connection with psql: `psql -U trading_bot_user -h localhost -d trading_bot_db`
4. Check Alembic status: `uv run alembic current`
5. Review migration history: `uv run alembic history`

## Next Steps

After successful migration:

1. **Monitor Performance** - Track database performance metrics
2. **Optimize Queries** - Review and optimize slow queries
3. **Set Up Monitoring** - Configure database monitoring alerts
4. **Document Procedures** - Document your specific setup and procedures
5. **Test Backup/Restore** - Verify your backup and restore procedures