# Environment Setup Guide

## Overview

Trading Bot mendukung environment-specific configuration files (`.env.dev` dan `.env.prd`) yang akan otomatis dimuat berdasarkan environment yang dijalankan.

## Environment Files

### File Structure

```
trading-bot/
├── .env.dev          # Development environment (auto-loaded dengan --config development)
├── .env.prd          # Production environment (auto-loaded dengan --config production)
└── .env.test         # Test environment (optional)
```

### Priority Loading

1. **Environment-specific file** (`.env.dev`, `.env.prd`, `.env.test`)
2. **Default `.env` file** (fallback jika file specific tidak ada)
3. **System environment variables**

## Setup Instructions

### 1. Development Environment Setup

Buat file `.env.dev`:

```bash
# Copy template
cat > .env.dev << 'EOF'
# =============================================================================
# Database Configuration - DEVELOPMENT
# =============================================================================
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db

# =============================================================================
# MetaTrader5 Configuration - DEVELOPMENT
# =============================================================================
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo

# =============================================================================
# Telegram Notifications - DEVELOPMENT
# =============================================================================
TELEGRAM_BOT_TOKEN=your_dev_bot_token
TELEGRAM_CHAT_ID=your_dev_chat_id
TELEGRAM_ENABLED=true

# =============================================================================
# Trading Configuration - DEVELOPMENT
# =============================================================================
TRADING_RISK_PER_TRADE=0.001  # 0.1% - Conservative
TRADING_MAX_POSITIONS=3
TRADING_CONFLUENCE_THRESHOLD=70.0

# =============================================================================
# Logging - DEVELOPMENT
# =============================================================================
LOG_LEVEL=DEBUG
LOG_FILE_PATH=./logs/trading_bot_dev.log

# =============================================================================
# Application Settings
# =============================================================================
ENVIRONMENT=development
DEBUG=true
DRY_RUN=true
EOF
```

### 2. Production Environment Setup

Buat file `.env.prd`:

```bash
# Copy template
cat > .env.prd << 'EOF'
# ⚠️ WARNING: LIVE TRADING with REAL MONEY

# =============================================================================
# Database Configuration - PRODUCTION
# =============================================================================
DATABASE_URL=postgresql+asyncpg://trading_bot_user:strong_password@localhost:5432/trading_bot_prd

# =============================================================================
# MetaTrader5 Configuration - PRODUCTION
# =============================================================================
MT5_LOGIN=your_real_login
MT5_PASSWORD=your_real_password
MT5_SERVER=YourBroker-Real

# =============================================================================
# Telegram Notifications - PRODUCTION
# =============================================================================
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_CHAT_ID=your_production_chat_id
TELEGRAM_ENABLED=true

# =============================================================================
# Trading Configuration - PRODUCTION
# =============================================================================
TRADING_RISK_PER_TRADE=0.005  # 0.5%
TRADING_MAX_POSITIONS=5
TRADING_CONFLUENCE_THRESHOLD=65.0

# Emergency settings
EMERGENCY_STOP_ENABLED=true
DAILY_LOSS_LIMIT_PERCENT=5.0

# =============================================================================
# Logging - PRODUCTION
# =============================================================================
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/trading_bot_prd.log

# =============================================================================
# Application Settings
# =============================================================================
ENVIRONMENT=production
DEBUG=false
DRY_RUN=false  # ⚠️ LIVE TRADING ENABLED
EOF
```

## Usage

### Running with Different Environments

```bash
# Development (loads .env.dev)
uv run trading-bot --config development start

# Production (loads .env.prd)
uv run trading-bot --config production start

# Test (loads .env.test)
uv run trading-bot --config test start
```

### Environment Variable Override

Environment variables dapat di-override:

```bash
# Override specific variable
DATABASE_URL="postgresql://other_db" uv run trading-bot --config development start

# Override multiple variables
MT5_LOGIN=12345 MT5_PASSWORD=pass uv run trading-bot --config development start
```

## Configuration Priority

Configuration loading mengikuti priority (highest to lowest):

1. **Command-line environment variables**
2. **Environment-specific .env file** (`.env.dev`, `.env.prd`)
3. **Environment-specific YAML** (`config/development.yaml`, `config/production.yaml`)
4. **Default YAML** (`config/default.yaml`)
5. **Hardcoded defaults**

## Available Environment Variables

### Database Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection URL | `sqlite+aiosqlite:///./trading_bot.db` |
| `DATABASE_POOL_SIZE` | Connection pool size | `10` |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `20` |

### MT5 Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `MT5_LOGIN` | MT5 account login | `12345678` |
| `MT5_PASSWORD` | MT5 account password | `your_password` |
| `MT5_SERVER` | MT5 server name | `Broker-Demo` |
| `MT5_TERMINAL_PATH` | MT5 terminal path (optional) | `C:\Program Files\MetaTrader 5\terminal64.exe` |
| `MT5_CONNECTION_TIMEOUT` | Connection timeout (seconds) | `30` |
| `MT5_RETRY_ATTEMPTS` | Retry attempts | `3` |
| `MT5_AUTO_RECONNECT` | Auto reconnect | `true` |

### Telegram Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Telegram chat ID | `-1001234567890` |
| `TELEGRAM_ENABLED` | Enable telegram | `true` |

### Trading Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `TRADING_RISK_PER_TRADE` | Risk per trade (decimal) | `0.005` (0.5%) |
| `TRADING_MAX_POSITIONS` | Max concurrent positions | `5` |
| `TRADING_CONFLUENCE_THRESHOLD` | Confluence threshold | `65.0` |

### Logging Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO`, `DEBUG`, `WARNING` |
| `LOG_FILE_PATH` | Log file path | `./logs/trading_bot.log` |

## Security Best Practices

### 1. Never Commit Credentials

```bash
# Files sudah ada di .gitignore:
.env.dev
.env.prd
.env.test
.env.local
```

### 2. Use Strong Passwords

- Database passwords: minimum 16 characters
- MT5 passwords: use broker-generated passwords
- Telegram tokens: never share or expose

### 3. Separate Development and Production

- **Development**: Demo account, SQLite database, conservative settings
- **Production**: Real account, PostgreSQL database, production settings

### 4. Backup Credentials Securely

```bash
# Encrypt credential backups
gpg --encrypt .env.prd

# Store in secure location
# Never store in version control
```

## Troubleshooting

### Issue: Environment file not loaded

**Solution**: Check file path and naming

```bash
# Verify file exists
ls -la .env.dev

# Check current directory
pwd

# Should be in project root: /path/to/trading-bot/
```

### Issue: Wrong database URL

**Solution**: Verify environment variable priority

```bash
# Check what's loaded
uv run trading-bot config-cmd show

# Force specific environment
uv run trading-bot --config development status
```

### Issue: MT5 connection fails

**Solution**: Verify credentials and server

```bash
# Test connection
uv run trading-bot --config development mt5 connect

# Check credentials in .env file
cat .env.dev | grep MT5
```

## Examples

### Example 1: Development with SQLite

`.env.dev`:
```env
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db
MT5_LOGIN=demo_account
MT5_PASSWORD=demo_password
MT5_SERVER=Broker-Demo
DRY_RUN=true
```

Run:
```bash
uv run trading-bot --config development start
```

### Example 2: Production with PostgreSQL

`.env.prd`:
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trading_bot
MT5_LOGIN=real_account
MT5_PASSWORD=real_password
MT5_SERVER=Broker-Real
DRY_RUN=false
TELEGRAM_ENABLED=true
```

Run:
```bash
uv run trading-bot --config production start
```

### Example 3: Testing with Mock Data

`.env.test`:
```env
DATABASE_URL=sqlite+aiosqlite:///./test.db
MT5_LOGIN=test
MT5_PASSWORD=test
DRY_RUN=true
LOG_LEVEL=DEBUG
```

Run:
```bash
uv run trading-bot --config test start
```

## Next Steps

1. ✅ Create your `.env.dev` file
2. ✅ Test with development environment
3. ✅ Setup PostgreSQL for production (optional)
4. ✅ Create `.env.prd` when ready for live trading
5. ✅ Enable Telegram notifications

## References

- [Configuration Guide](configuration-guide.md)
- [PostgreSQL Migration Guide](postgresql-migration-guide.md)
- [Windows Setup Guide](windows-setup-guide.md)
