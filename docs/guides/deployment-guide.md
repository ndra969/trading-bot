# Deployment Guide

Deploy trading bot from development to production.

> **Quick Commands**: Use `/workflow` for complete development workflow, `/quality` for quality checks, `/commit` for pre-commit validation.

## Prerequisites

- **OS**: Windows 10/11 (required for MT5)
- **Python**: 3.12+
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB SSD
- **MT5 Terminal**: Installed and logged in

## Development Setup

```bash
# Clone and install
git clone <repository-url>
cd trading-bot
uv sync

# Setup environment
cp .env.example .env.dev
# Edit .env.dev with development credentials

# Run in dry-run
uv run trading-bot start --dry-run
```

See [Windows Setup Guide](../setup/windows-setup-guide.md) for detailed installation.

## Pre-Production Checklist

Before deploying to production:

- [ ] All tests passing: `/test` or `uv run pytest`
- [ ] Code quality clean: `/quality` or `uv run ruff check`
- [ ] Dry-run successful: `/dry-run`
- [ ] Backtest validated: `/backtest <symbol>`
- [ ] Configuration reviewed
- [ ] Risk parameters confirmed
- [ ] Telegram notifications configured
- [ ] Database backed up

## Production Configuration

### 1. Environment File

Create `.env.prd`:

```bash
# Production credentials
MT5_LOGIN=live_account_number
MT5_PASSWORD=live_password
MT5_SERVER=YourBroker-MT5Real

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trading_bot_prd

# Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Conservative settings for production
TRADING_RISK_PER_TRADE=0.005  # 0.5%
TRADING_MAX_POSITIONS=5
DAILY_LOSS_LIMIT_PERCENT=1.0
EMERGENCY_STOP_ENABLED=true

# Mode
DRY_RUN=false  # ⚠️ LIVE TRADING
```

### 2. Production Config

Edit `config/production.yaml`:

```yaml
trading:
  dry_run: false
  max_positions: 5

risk:
  max_portfolio_risk: 0.02
  daily_loss_limit: 0.01
  emergency_stop_drawdown: 0.10

mt5:
  server: "YourBroker-MT5Real"  # CRITICAL: explicit server
```

### 3. Database Migration

> **Note**: `trading-bot postgresql` CLI is 📋 planned. Use Alembic directly:

```bash
# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

Configure `DATABASE_URL` in `.env` for PostgreSQL:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

## Deployment

### Manual Start

```bash
# Start production bot
uv run trading-bot start --config production
```

### Background Process (Windows)

```powershell
# Start as background process
Start-Process -FilePath "uv" -ArgumentList "run","trading-bot","start","--config","production" -WindowStyle Hidden
```

### Auto-Restart on Boot (Windows)

1. Create scheduled task:
   - Task Scheduler → Create Basic Task
   - Trigger: At system startup
   - Action: Start program
   - Program: `uv`
   - Arguments: `run trading-bot start --config production`
   - Working directory: `D:\Workspaces\trading-bot`

## Monitoring

### Real-Time Status

```bash
# Check status
uv run trading-bot status

# View live logs
tail -f logs/trading_bot.log
```

### Telegram Notifications

Production should always have Telegram enabled:
- Trade open/close notifications
- Risk alerts
- Error notifications
- Daily summaries

See [Notifications Guide](../trading/notifications-guide.md).

## Safety Procedures

### Emergency Stop

```bash
# Graceful stop (Ctrl+C in terminal)
# Or send SIGTERM signal

# Force stop all positions
uv run trading-bot stop --emergency
```

### Backup Strategy

```bash
# Daily database backup
copy trading_bot.db backups\trading_bot_%date%.db

# Weekly config backup
copy config\production.yaml backups\
```

## Updates

### Updating the Bot

```bash
# 1. Stop bot gracefully
# Ctrl+C in terminal

# 2. Backup current state
copy trading_bot.db backups\

# 3. Pull updates
git pull origin main

# 4. Update dependencies
uv sync

# 5. Run migrations if needed
alembic upgrade head

# 6. Validate
/quality
/dry-run

# 7. Restart
uv run trading-bot start --config production
```

## Troubleshooting

Common deployment issues:

| Issue | Solution |
|-------|----------|
| MT5 not connecting | Check server in config, restart MT5 |
| Database locked | Stop all Python processes |
| High memory usage | Restart bot, reduce symbols |
| Server mismatch | Set explicit server in config |

See [Troubleshooting Guide](troubleshooting-guide.md) for details.

## Related Documentation

- [Windows Setup](../setup/windows-setup-guide.md) - Initial setup
- [Configuration Guide](../setup/configuration-guide.md) - Config options
- [Notifications Guide](../trading/notifications-guide.md) - Alert setup
- [Troubleshooting](troubleshooting-guide.md) - Common issues
