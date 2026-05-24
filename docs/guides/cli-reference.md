# CLI Reference Guide

Complete reference for `uv run trading-bot` commands.

> **Status Legend**: ✅ Implemented · 📋 Planned · ⚠️ Partial

## Available Commands (Implemented)

### Bot Control

```bash
# Start trading bot
uv run trading-bot start                              # Default config
uv run trading-bot start --config production          # Production config
uv run trading-bot start --dry-run                    # Safe testing mode
uv run trading-bot start --dry-run --connect-mt5      # MT5 data, no real orders

# Stop trading bot (graceful Ctrl+C or)
uv run trading-bot stop

# Show status
uv run trading-bot status

# Show version
uv run trading-bot version
```

### MT5 Operations

```bash
# Connect to MT5 terminal
uv run trading-bot mt5 connect

# Disconnect
uv run trading-bot mt5 disconnect

# Check connection status
uv run trading-bot mt5 status
```

### Account

```bash
# Show account information
uv run trading-bot account info
```

### Configuration

```bash
# Show configuration
uv run trading-bot config show

# Validate configuration
uv run trading-bot config validate
```

### Project Info

```bash
# Display project rules from CLAUDE.md
uv run trading-bot rules
uv run trading-bot rules --format summary
uv run trading-bot rules --format rules-only

# Alias
uv run trading-bot claude
```

---

## Planned Commands (Not Yet Implemented)

These commands are referenced in some documentation but not implemented yet:

### 📋 Position Management

```bash
# Planned
uv run trading-bot positions active                    # List active positions
uv run trading-bot positions close --ticket <id>       # Close position
uv run trading-bot positions partial-close --ticket <id> --percent 50
```

### 📋 Market Analysis

```bash
# Planned
uv run trading-bot foundation analyze --symbol EURUSD
uv run trading-bot foundation zones --symbol EURUSD
uv run trading-bot market status --symbol EURUSD
uv run trading-bot market hours --symbol XAUUSD
```

### 📋 Account Management

```bash
# Planned
uv run trading-bot account list                       # List all accounts
uv run trading-bot account switch --account-id <id>   # Switch active
uv run trading-bot account sync                        # Force sync with MT5
```

### 📋 Trading Type Management

```bash
# Planned (only day_trading currently works)
uv run trading-bot type switch --type day_trading
uv run trading-bot type status
uv run trading-bot type compare --types scalping,day_trading
```

### 📋 Broker Symbol Management

```bash
# Planned
uv run trading-bot broker switch --name exness_standard
uv run trading-bot broker convert --symbol EURUSD --to-broker
uv run trading-bot broker status
```

### 📋 Database Migration

```bash
# Planned (use alembic directly for now)
uv run trading-bot postgresql migrate
uv run trading-bot postgresql status

# Use this instead:
alembic upgrade head
alembic current
```

### 📋 Risk & Performance

```bash
# Planned
uv run trading-bot risk status
uv run trading-bot performance
uv run trading-bot health
```

### 📋 Notifications

```bash
# Planned
uv run trading-bot notifications test
uv run trading-bot notifications status
```

### 📋 Technical Analysis

```bash
# Planned
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot symbol info --symbol EURUSD
```

### 📋 Backtest

```bash
# Planned
uv run trading-bot backtest --symbol EURUSD --period 30d
```

---

## Development Commands (External Tools)

These use external Python tools, not the trading-bot CLI:

```bash
# Code quality
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/trading_bot/

# Testing
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ --mt5

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic current
```

---

## Quick Workflow

```bash
# 1. Test in dry-run first
uv run trading-bot start --dry-run

# 2. Test with real market data (no real trades)
uv run trading-bot start --dry-run --connect-mt5

# 3. Live trading (REAL MONEY)
uv run trading-bot start --config production
```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project rules
- [Configuration Guide](../setup/configuration-guide.md) - Config files
- [Windows Setup](../setup/windows-setup-guide.md) - Installation
- [Troubleshooting](troubleshooting-guide.md) - Common issues
