# pgAdmin4 Setup Guide for Trading Bot Database

This guide helps you set up pgAdmin4 and connect it to your trading bot PostgreSQL database.

## Prerequisites

- PostgreSQL server installed and running
- Python 3.11+ (for the setup script)
- pgAdmin4 installed

## Step 1: Install pgAdmin4

### Option A: Install via Python pip
```bash
# Install pgAdmin4
pip install pgadmin4

# Run pgAdmin4
python -m pgadmin4
```

### Option B: Download pgAdmin4 Desktop
1. Visit [https://www.pgadmin.org/download/](https://www.pgadmin.org/download/)
2. Download pgAdmin4 for Windows
3. Run the installer

## Step 2: Start PostgreSQL Service

### Windows
```bash
# Using PostgreSQL installer
net start postgresql-x64-15

# Or using Windows Services
# Open Services, find PostgreSQL, and click Start
```

### Check if PostgreSQL is running
```bash
# Test connection
psql -U postgres -h localhost -p 5432
```

## Step 3: Run the Trading Bot Setup Script

The setup script will create:
- `trading_bot_user` - Main application user (read/write)
- `trading_bot_readonly` - Read-only user for monitoring
- `trading_bot_db` - Main database

```bash
# Navigate to your project directory
cd D:\Workspaces\bot-trading

# Install required dependency
uv add asyncpg

# Set your PostgreSQL admin password (if different from default)
set POSTGRES_PASSWORD=your_admin_password

# Run the setup script
uv run python scripts/setup_postgresql_users.py
```

### Setup Script Output
The script will provide you with:
- Database connection details
- User credentials
- Connection URLs for your .env file
- pgAdmin4 connection parameters

## Step 4: Connect pgAdmin4 to the Database

### Method A: Quick Connection
1. Open pgAdmin4 in your browser (usually http://127.0.0.1:5050)
2. Click "Add New Server"
3. Fill in the connection details:

#### General Tab
- **Name**: `Trading Bot Database`

#### Connection Tab
- **Host name/address**: `localhost`
- **Port**: `5432`
- **Maintenance database**: `trading_bot_db`
- **Username**: `trading_bot_user`
- **Password**: `trading_bot_password` (from setup script output)

#### SSL Tab
- **SSL mode**: `prefer` (for development) or `require` (for production)

### Method B: Import Connection File
Create a JSON file `trading_bot_servers.json`:
```json
{
    "Servers": {
        "1": {
            "Name": "Trading Bot Database",
            "Group": "Trading Bot",
            "Host": "localhost",
            "Port": 5432,
            "MaintenanceDB": "trading_bot_db",
            "Username": "trading_bot_user",
            "SSLMode": "prefer",
            "Password": "trading_bot_password"
        }
    }
}
```

Import in pgAdmin4: `File → Import Servers`

## Step 5: Verify Connection in pgAdmin4

### Test Database Connection
1. Right-click on your server connection
2. Select "Connect"
3. Expand the server tree:
   - Databases → trading_bot_db → Schemas → public → Tables

### Expected Structure (After Migration)
```
trading_bot_db
├── Tables
│   ├── positions
│   ├── trades
│   ├── signals
│   ├── zones
│   ├── market_data
│   └── risk_metrics
├── Views
├── Functions
└── Extensions
    ├── uuid-ossp
    ├── pg_stat_statements
    └── pg_trgm
```

### Test Basic Operations
1. Click on the "Query Tool" (🔍 icon)
2. Run this test query:
```sql
SELECT current_database(), current_user, version();
```

Expected output:
```
current_database | current_user      | version
-----------------+-------------------+------------------------------
trading_bot_db   | trading_bot_user  | PostgreSQL 15.x on Windows
```

## Step 6: Run Database Migrations

After connecting pgAdmin4, run the migrations to create all tables:

```bash
# From your project directory
uv run trading-bot postgresql migrate
```

This will:
- Create all necessary tables
- Set up proper indexes
- Create initial data
- Verify everything works

## Step 7: Update Configuration Files

### 1. Update .env file
Create or update `.env`:
```bash
# PostgreSQL Connection
DATABASE_URL=postgresql+asyncpg://trading_bot_user:trading_bot_password@localhost:5432/trading_bot_db

# PostgreSQL Settings (optional)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_bot_db
POSTGRES_USER=trading_bot_user
POSTGRES_PASSWORD=trading_bot_password
```

### 2. Update config/postgresql.yaml
```yaml
postgresql:
  host: localhost
  port: 5432
  database: trading_bot_db
  username: trading_bot_user
  password: trading_bot_password

  # Connection pool settings
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30

  # SSL settings
  ssl_mode: prefer

  # Performance settings
  command_timeout: 60
  server_settings:
    application_name: trading_bot
```

## Step 8: Validate Everything Works

### Test Database Connection
```bash
# Check PostgreSQL status
uv run trading-bot postgresql status

# Verify migration
uv run trading-bot postgresql migrate --command verify
```

### Test Trading Bot with PostgreSQL
```bash
# Test dry run with PostgreSQL
uv run trading-bot start --dry-run --config production
```

### Test via pgAdmin4 Query Tool
```sql
-- Test table access
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Test user permissions
SELECT has_table_privilege('trading_bot_user', 'positions', 'INSERT') as can_insert,
       has_table_privilege('trading_bot_user', 'positions', 'SELECT') as can_select,
       has_table_privilege('trading_bot_user', 'positions', 'UPDATE') as can_update,
       has_table_privilege('trading_bot_user', 'positions', 'DELETE') as can_delete;
```

## Troubleshooting

### Common Issues

#### 1. "Connection refused" error
```bash
# Check if PostgreSQL is running
net start postgresql

# Check PostgreSQL service status
sc query postgresql-x64-15
```

#### 2. "Password authentication failed" error
- Verify the password from setup script output
- Check pg_hba.conf file for authentication method
- Try connecting with psql first

#### 3. "Database does not exist" error
```bash
# List all databases
psql -U postgres -l

# Recreate database
uv run python scripts/setup_postgresql_users.py
```

#### 4. "Permission denied" error
```sql
-- Check user permissions in pgAdmin4 Query Tool
SELECT usename, usecreatedb, usesuper, usecatupd
FROM pg_user
WHERE usename = 'trading_bot_user';
```

#### 5. pgAdmin4 won't start
```bash
# Clear pgAdmin4 cache
rmdir /s %APPDATA%\pgAdmin

# Reset pgAdmin4 password
python -c "from pgadmin4 import setup; setup.master_password()"
```

### pgAdmin4 Connection Issues

#### Connection Test in pgAdmin4
1. Right-click server → Properties
2. Click "Test Connection"
3. Check the error message

#### Check Connection Details
In pgAdmin4 Query Tool, run:
```sql
-- Show current connection details
SELECT
    inet_server_addr() as server_address,
    inet_server_port() as server_port,
    current_database() as database,
    current_user() as user,
    inet_client_addr() as client_address;

-- Show all databases
SELECT datname, datcollate, datctype FROM pg_database;

-- Show all users
SELECT usename, usecreatedb, usesuper FROM pg_user;
```

## Security Best Practices

### 1. Change Default Passwords
```sql
-- Connect as postgres user and change passwords
ALTER USER trading_bot_user WITH PASSWORD 'your_secure_password';
ALTER USER trading_bot_readonly WITH PASSWORD 'your_readonly_password';
```

### 2. Use Environment Variables
Never hardcode passwords in configuration files:
```bash
# Use environment variables in production
POSTGRES_PASSWORD_FILE=/path/to/secure/password/file
```

### 3. Enable SSL (Production)
In `postgresql.conf`:
```ini
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

### 4. Restrict Network Access
In `pg_hba.conf`:
```
# Local connections only
host    all             all             127.0.0.1/32            md5

# Specific IP ranges (if needed)
host    trading_bot_db  trading_bot_user 10.0.0.0/8            md5
```

## Maintenance

### Backup Database via pgAdmin4
1. Right-click database → Backup
2. Choose backup location
3. Select format (Custom or Directory)
4. Run backup

### Monitor Database Performance
```sql
-- Show active connections
SELECT * FROM pg_stat_activity WHERE datname = 'trading_bot_db';

-- Show table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Next Steps

After successful setup:

1. **Run the trading bot**: `uv run trading-bot start --dry-run`
2. **Configure notifications**: Set up Telegram alerts
3. **Monitor performance**: Use pgAdmin4 dashboards
4. **Set up backups**: Automated database backups
5. **Review logs**: Check PostgreSQL and application logs

## Quick Reference

### Connection Details (from setup script)
```
Host: localhost
Port: 5432
Database: trading_bot_db
Username: trading_bot_user
Password: trading_bot_password
```

### Database URL for .env
```
DATABASE_URL=postgresql+asyncpg://trading_bot_user:trading_bot_password@localhost:5432/trading_bot_db
```

### Useful pgAdmin4 Queries
```sql
-- List all tables
\dt

-- Show table structure
\d table_name

-- Check indexes
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'positions';
```

Your trading bot database is now ready! 🚀