# CLI Reference Guide

Quick reference for common trading bot commands. See [CLAUDE.md](../../CLAUDE.md) for project rules.

## Quick Reference - Common Commands

### Bot Operations

```bash
# Start/Stop
uv run trading-bot start --config production  # ✅ Production
uv run trading-bot start --dry-run           # ✅ Test mode
uv run trading-bot stop

# Status
uv run trading-bot status
uv run trading-bot health
```

### Position Management

```bash
# Active positions
uv run trading-bot positions active
uv run trading-bot positions close --ticket 123456
uv run trading-bot positions partial-close --ticket 123456 --percentage 50
```

### Market Analysis

```bash
# Foundation strategy
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1
uv run trading-bot foundation zones --symbol EURUSD --strength-min 40

# Market status
uv run trading-bot market status --symbol EURUSD
uv run trading-bot market hours --symbol XAUUSD
```

### Configuration

```bash
# View and manage
uv run trading-bot config show
uv run trading-bot config show --file trading_parameters
uv run trading-bot config validate --all
```

### Development

```bash
# Code quality
uv run black src/ tests/
uv run ruff check --fix src/ tests/
uv run mypy src/trading_bot/

# Testing
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
```

## Status Indicators

| Status | Meaning |
|--------|---------|
| ✅ | Implemented & tested |
| ⚠️ | Partial implementation |
| ❌ | Not implemented |

## Full Command Reference

### Bot Control

```bash
uv run trading-bot init --config development
uv run trading-bot start --config production
uv run trading-bot start --dry-run
uv run trading-bot start --ignore-market-hours
uv run trading-bot stop --force
uv run trading-bot status --detailed
uv run trading-bot info --platform-check
```

### Database Management

```bash
# PostgreSQL migration
uv run trading-bot postgresql migrate
uv run trading-bot postgresql status
uv run trading-bot postgresql migrate --command verify
uv run trading-bot postgresql reset  # WARNING: deletes data

# SQLite operations
uv run trading-bot db backup
uv run trading-bot db restore --file backup.db
uv run trading-bot db stats
```

### Strategy Management

```bash
uv run trading-bot strategy status
uv run trading-bot strategy test supply_demand
uv run trading-bot strategy weights --show
uv run trading-bot strategy config --name supply_demand --show
```

### Technical Analysis

```bash
# RSI
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot technical rsi --symbol EURUSD --timeframes H1,H4,D1

# Moving Averages
uv run trading-bot technical analyze --symbol EURUSD --indicator ma
uv run trading-bot technical ma-alignment --symbol EURUSD --timeframes H1,H4

# Foundation Strategy
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1
uv run trading-bot foundation price-action EURUSD --timeframe H1 --trading-type day_trading
```

### Trading Operations

```bash
# Signals
uv run trading-bot signal analyze --symbol EURUSD --show-layers
uv run trading-bot signal validate --symbol EURUSD --confidence-min 70

# Positions
uv run trading-bot positions active --symbol EURUSD
uv run trading-bot positions history --days 7
uv run trading-bot positions analyze --ticket 123456
```

### Analytics

```bash
uv run trading-bot analytics performance --days 30
uv run trading-bot analytics risk --current
uv run trading-bot analytics correlation --symbols EURUSD,GBPUSD
```

### Windows/MT5

```bash
uv run trading-bot mt5 status
uv run trading-bot mt5 check-connection
uv run trading-bot windows status
```

### Notifications

```bash
uv run trading-bot notifications status
uv run trading-bot notifications test
uv run trading-bot notifications enable --type trade_opened
```

## Configuration Commands

```bash
# Environment management
uv run trading-bot config set-env --environment production
uv run trading-bot config list-environments

# Backup and restore
uv run trading-bot config backup --version "pre_optimization"
uv run trading-bot config restore --hash "abc123"
```

## Global Options

Most commands support these options:

```bash
--config CONFIG_NAME     # Configuration environment
--verbose, -v           # Verbose output
--dry-run               # Simulation mode
--symbol SYMBOL         # Filter by symbol
--timeframe TIMEFRAME   # Filter by timeframe
--days DAYS            # Filter by days
--format FORMAT        # Output: json, csv, yaml, table
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid command/arguments
- `3`: Configuration error
- `4`: Database error
- `5`: MT5 connection error

## Environment Variables

```bash
export TRADING_BOT_CONFIG=production
export TRADING_BOT_DB_URL="postgresql+asyncpg://..."
export TRADING_BOT_MT5_PATH="/custom/mt5/path"
export TRADING_BOT_LOG_LEVEL=INFO
```

For complete implementation details, see [`src/trading_bot/cli.py`](../../src/trading_bot/cli.py).
