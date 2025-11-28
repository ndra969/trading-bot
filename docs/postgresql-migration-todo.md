# PostgreSQL Migration Todo List & Checklist

This document provides a comprehensive todo list and step-by-step guide for migrating the trading bot from SQLite to PostgreSQL production database.

## 🎯 Migration Overview

### 📋 Pre-Migration Checklist

#### ✅ Environment Setup
- [ ] **Install PostgreSQL Server**
  - [ ] PostgreSQL 14+ installed on system
  - [ ] Service running and accessible
  - [ ] Network connectivity verified

- [ ] **Create Database and User**
  ```sql
  -- Connect as postgres superuser
  CREATE DATABASE trading_bot_db;
  CREATE USER trading_bot_user WITH PASSWORD 'secure_password';
  GRANT ALL PRIVILEGES ON DATABASE trading_bot_db TO trading_bot_user;
  ```

- [ ] **Verify Connection**
  ```bash
  psql -h localhost -U trading_bot_user -d trading_bot_db -c "SELECT version();"
  ```

#### ✅ Dependencies Check
- [ ] **Python Dependencies**
  - [ ] `uv sync` (includes asyncpg, sqlalchemy[postgresql])
  - [ ] `psycopg2-binary` or `asyncpg` installed
  - [ ] All dependencies resolved without errors

- [ ] **Alembic Setup**
  - [ ] Alembic configuration file ready (`alembic.ini`)
  - [ ] Migration environment configured (`alembic/env.py`)
  - [ ] Initial migration script prepared (`001_initial_migration.py`)

#### ✅ Backup Strategy
- [ ] **Current SQLite Backup**
  - [ ] Backup existing `trading_bot.db` file
  - [ ] Store backup in safe location
  - [ ] Verify backup integrity

- [ ] **Data Export Plan**
  - [ ] Review existing data structure
  - [ ] Identify critical data to migrate
  - [ ] Prepare data validation plan

### 🚀 Migration Execution

#### Phase 1: Database Setup
- [ ] **Configure Environment Variables**
  ```bash
  # Set PostgreSQL connection
  export DATABASE_URL="postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db"

  # Or update .env file
  echo "DATABASE_URL=postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db" >> .env
  ```

- [ ] **Test Database Connection**
  ```bash
  # Test connection with trading bot
  uv run trading-bot postgresql status
  ```

#### Phase 2: Schema Migration
- [ ] **Run Alembic Migration**
  ```bash
  # Create database schema
  uv run alembic upgrade head

  # Or use CLI command
  uv run trading-bot postgresql migrate --command migrate
  ```

- [ ] **Verify Schema Creation**
  ```sql
  -- Connect to PostgreSQL and verify tables
  \dt
  \d trades
  \d market_data
  \d system_health
  ```

#### Phase 3: Data Migration
- [ ] **Backup SQLite Data**
  ```bash
  # Using migration helper
  uv run trading-bot postgresql migrate --command backup

  # Manual backup alternative
  cp trading_bot.db trading_bot_backup_$(date +%Y%m%d_%H%M%S).db
  ```

- [ ] **Transfer Data to PostgreSQL**
  ```bash
  # Using automated migration
  uv run trading-bot postgresql migrate --command transfer

  # Or complete migration
  uv run trading-bot postgresql migrate
  ```

- [ ] **Verify Data Transfer**
  ```bash
  # Check migration results
  uv run trading-bot postgresql migrate --command verify

  # Manual verification
  uv run python -c "
  from trading_bot.services import create_database_service
  from trading_bot.config import DatabaseConfig
  import asyncio

  async def verify():
      config = DatabaseConfig(url='postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db')
      async with create_database_service(config) as db:
          info = await db.get_database_info()
          print(f'Trades: {info[\"total_trades\"]}')
          print(f'Market Data: {info[\"total_market_data\"]}')
          print(f'Health Records: {info[\"total_health_records\"]}')

  asyncio.run(verify())
  "
  ```

### 🔍 Post-Migration Validation

#### ✅ Functional Testing
- [ ] **Basic Operations Test**
  ```bash
  # Test trading bot with PostgreSQL
  uv run trading-bot start --dry-run --config production

  # Verify no database errors
  uv run trading-bot start --config production --dry-run --verbose
  ```

- [ ] **Repository Pattern Test**
  ```bash
  # Test repository pattern with PostgreSQL
  uv run python scripts/test_repository_pattern.py
  ```

- [ ] **Zone Storage Test**
  ```bash
  # Test zone detection and storage
  uv run trading-bot foundation analyze EURUSD --timeframe H1
  ```

#### ✅ Performance Validation
- [ ] **Query Performance Test**
  - [ ] Trade queries performant (< 100ms)
  - [ ] Market data queries efficient (< 50ms)
  - [ ] Health monitoring queries fast (< 10ms)

- [ ] **Connection Pool Test**
  - [ ] Multiple concurrent connections handled
  - [ ] Connection recycling works correctly
  - [ ] Pool timeout settings appropriate

#### ✅ Data Integrity Check
- [ ] **Record Count Verification**
  ```sql
  -- Compare with SQLite backup
  SELECT COUNT(*) FROM trades;
  SELECT COUNT(*) FROM market_data;
  SELECT COUNT(*) FROM system_health;
  ```

- [ ] **Data Quality Check**
  - [ ] All trades have valid symbols
  - [ ] Market data timestamps are correct
  - [ ] Health records have valid components

### 🛠️ Production Configuration

#### ✅ PostgreSQL Optimization
- [ ] **Connection Pool Settings**
  ```yaml
  # config/postgresql.yaml
  database:
    url: "postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db"
    pool_size: 20
    max_overflow: 30
    pool_timeout: 30
    pool_recycle: 3600
  ```

- [ ] **Performance Tuning**
  - [ ] `shared_buffers` configured (25% of RAM)
  - [ ] `effective_cache_size` set (75% of RAM)
  - [ ] `work_mem` configured per connection
  - [ ] `maintenance_work_mem` set for maintenance

- [ ] **Index Optimization**
  ```sql
  -- Create optimized indexes
  CREATE INDEX CONCURRENTLY idx_trades_symbol_status ON trades(symbol, status);
  CREATE INDEX CONCURRENTLY idx_market_data_symbol_timeframe_time ON market_data(symbol, timeframe, timestamp);
  CREATE INDEX CONCURRENTLY idx_system_health_component_timestamp ON system_health(component, timestamp);
  ```

#### ✅ Security Configuration
- [ ] **SSL Configuration**
  ```bash
  # Enable SSL for production
  export DATABASE_URL="postgresql+asyncpg://trading_bot_user:secure_password@localhost:5432/trading_bot_db?ssl=true"
  ```

- [ ] **User Permissions**
  ```sql
  -- Revoke unnecessary privileges
  REVOKE CREATE ON SCHEMA public FROM PUBLIC;
  REVOKE ALL ON SCHEMA public FROM PUBLIC;
  GRANT USAGE ON SCHEMA public TO trading_bot_user;
  GRANT CREATE ON SCHEMA public TO trading_bot_user;
  ```

#### ✅ Backup Strategy
- [ ] **Automated Backups**
  ```bash
  # Create backup script
  #!/bin/bash
  pg_dump -h localhost -U trading_bot_user -d trading_bot_db | gzip > /backups/trading_bot_$(date +%Y%m%d_%H%M%S).sql.gz
  ```

- [ ] **Point-in-Time Recovery**
  - [ ] WAL archiving configured
  - [ ] Archive retention policy set
  - [ ] Recovery procedures documented

### 📊 Monitoring & Maintenance

#### ✅ Health Monitoring
- [ ] **Database Health Checks**
  ```bash
  # Monitor database connections
  uv run trading-bot postgresql status

  # Check system health
  uv run trading-bot postgresql migrate --command verify
  ```

- [ ] **Performance Monitoring**
  - [ ] Query execution times tracked
  - [ ] Connection pool usage monitored
  - [ ] Database size growth tracked

#### ✅ Regular Maintenance
- [ ] **Automated Cleanup**
  - [ ] Old system health records cleaned
  - [ ] Expired session data removed
  - [ ] Log rotation configured

- [ ] **Statistics Updates**
  ```sql
  -- Update table statistics
  ANALYZE trades;
  ANALYZE market_data;
  ANALYZE system_health;
  ```

### 🔧 Troubleshooting Guide

#### ✅ Common Issues

**Issue 1: Connection Failed**
```
Error: could not connect to server
```
- [ ] Check PostgreSQL service status: `sudo systemctl status postgresql`
- [ ] Verify network connectivity: `telnet localhost 5432`
- [ ] Check connection string format
- [ ] Verify user credentials

**Issue 2: Migration Failed**
```
Error: relation "trades" already exists
```
- [ ] Reset migration state: `uv run alembic stamp head`
- [ ] Or run downgrade: `uv run alembic downgrade base`
- [ ] Re-run migration: `uv run alembic upgrade head`

**Issue 3: Data Transfer Failed**
```
Error: invalid input syntax for type json
```
- [ ] Check SQLite data for invalid JSON
- [ ] Clean up corrupted records
- [ ] Re-run data transfer

**Issue 4: Performance Issues**
```
Error: query timeout
```
- [ ] Check query execution plan: `EXPLAIN ANALYZE`
- [ ] Add missing indexes
- [ ] Optimize connection pool settings
- [ ] Increase query timeout

#### ✅ Rollback Procedures

**Complete Rollback to SQLite:**
```bash
# 1. Stop all trading bot processes
pkill -f "trading-bot"

# 2. Update environment to use SQLite
export DATABASE_URL="sqlite+aiosqlite:///trading_bot.db"

# 3. Verify SQLite database works
uv run trading-bot start --dry-run

# 4. Update configuration files
# Edit .env to use SQLite URL
```

**Partial Data Recovery:**
```bash
# Restore from backup
gunzip -c /backups/trading_bot_YYYYMMDD_HHMMSS.sql.gz | psql -h localhost -U trading_bot_user -d trading_bot_db

# Verify data integrity
uv run trading-bot postgresql migrate --command verify
```

### 📋 Migration Checklist Summary

#### Pre-Migration (Must Complete)
- [ ] PostgreSQL installed and running
- [ ] Database and user created
- [ ] Dependencies installed (asyncpg, sqlalchemy[postgresql])
- [ ] SQLite database backed up
- [ ] Environment variables configured
- [ ] Connection tested successfully

#### Migration Execution
- [ ] Alembic migration run successfully
- [ ] Schema verified in PostgreSQL
- [ ] SQLite data backed up
- [ ] Data transferred to PostgreSQL
- [ ] Data integrity verified

#### Post-Migration (Must Complete)
- [ ] Trading bot functional with PostgreSQL
- [ ] Performance benchmarks met
- [ ] All tests passing
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Documentation updated

#### Production Ready
- [ ] SSL/TLS configured
- [ ] Connection pool optimized
- [ ] Security settings applied
- [ ] Monitoring alerts configured
- [ ] Backup automation active
- [ ] Recovery procedures tested
- [ ] Team trained on new system

---

## 🎯 Success Criteria

### ✅ Migration Success Indicators
- **Zero Data Loss**: All data successfully transferred
- **Functionality Preserved**: All trading bot features work
- **Performance Improved**: Query times better than SQLite
- **High Availability**: Database uptime > 99.9%
- **Security Enhanced**: SSL, proper authentication, access controls
- **Monitoring Active**: Health checks and alerts working
- **Documentation Complete**: All procedures documented

### 📊 Performance Benchmarks
- **Trade Queries**: < 100ms average response time
- **Market Data Queries**: < 50ms average response time
- **Concurrent Connections**: Handle 20+ simultaneous connections
- **Data Transfer**: Complete migration in < 5 minutes
- **Uptime**: 99.9% availability during migration

---

## 📞 Support & Contacts

### Migration Team
- **Database Administrator**: PostgreSQL setup and optimization
- **Development Team**: Code changes and testing
- **Operations Team**: Production deployment and monitoring
- **QA Team**: Testing and validation

### Emergency Contacts
- **Database Issues**: [DBA Contact]
- **Application Issues**: [Dev Lead Contact]
- **Production Issues**: [Ops Lead Contact]

---

## 📝 Notes & Lessons Learned

*Document any issues encountered, solutions implemented, and lessons learned during the migration process for future reference.*

---

**Last Updated**: 2025-10-28
**Version**: 1.0
**Status**: Ready for Execution