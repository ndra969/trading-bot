# Troubleshooting Guide

Common issues and solutions for the trading bot.

## Quick Diagnostics

```bash
# Check bot status
uv run trading-bot status

# Test MT5 connection
uv run trading-bot mt5 connect

# Validate configuration
uv run trading-bot config validate

# View recent logs
tail -f logs/trading_bot.log
```

---

## MT5 Connection Issues

### Cannot Connect to MT5

**Symptoms**: `MT5 not initialized` or connection timeout

**Solutions**:
1. **Ensure MT5 terminal is running and logged in**
2. **Check credentials in `.env`**:
   ```bash
   MT5_LOGIN=your_account_number
   MT5_PASSWORD=your_password
   MT5_SERVER=YourBroker-Server
   ```
3. **Run terminal as Administrator**
4. **Check firewall** - allow Python-MT5 connection

### Server Mismatch

**Symptoms**: Bot stops with "Server mismatch detected"

**Solutions**:
1. Set explicit server in config:
   ```yaml
   # config/production.yaml
   mt5:
     server: "YourBroker-MT5Real"  # Explicit server
   ```
2. Login to correct server in MT5 terminal
3. Restart bot

### Auto-Switching to Test Server

**Cause**: MT5 reconnects to last logged-in account

**Solution**: Always specify `server` in config (never leave commented out)

---

## Trading Issues

### No Signals Generated

**Check**:
1. **Market hours** - Most symbols only trade during certain hours
2. **Symbol availability** - Check broker symbol mapping
3. **Confluence threshold** - Default 65% may be too high
4. **Strategy logs**:
   ```bash
   grep "Signal\|Zone\|Strategy" logs/trading_bot.log
   ```

### Orders Not Executing

**Common Causes**:
- **Dry-run mode enabled** - Check `--dry-run` flag
- **Insufficient margin** - Account balance too low
- **Symbol disabled** - Check broker symbol settings
- **Spread too high** - Wait for normal market conditions

```bash
# Check execution logs
grep "Order\|Execute" logs/trading_bot.log
```

### Wrong Position Size

**Causes**:
1. **Pip value calculation** - Verify asset class is correct
2. **Risk percent too low** - Default 0.5%, may result in 0.01 lot minimum
3. **Account currency** - Different currencies affect pip values

Check pip calculation in dry-run mode logs (`symbol info` CLI is 📋 planned).

---

## Risk Management Issues

### Bot Stopped Unexpectedly

**Check for emergency stops**:
```bash
grep -i "emergency\|drawdown\|stop" logs/trading_bot.log
```

**Common triggers**:
- Daily loss limit reached (1% default)
- Drawdown exceeded 10%
- Maximum positions reached
- Correlation limits exceeded

### Risk Alerts Not Sent

**Check**:
1. Telegram bot token in `.env`
2. Notification settings in config:
   ```yaml
   monitoring:
     telegram:
       enabled: true
   ```
3. Rate limiting (max 5/minute by default)

---

## Database Issues

### Database Locked

**Symptoms**: `database is locked` error

**Solutions**:
```bash
# Stop all bot instances
Get-Process python* | Stop-Process -Force  # Windows

# Or use kill script
uv run python scripts/kill_trading_bot.py
```

### Slow Database Queries

**Solutions**:
1. Optimize SQLite:
   ```sql
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   ```
2. Migrate to PostgreSQL for production:
   - Set `DATABASE_URL=postgresql+asyncpg://...` in `.env`
   - Run `alembic upgrade head`

### Database Migration Failed

```bash
# Check current state
alembic current

# Rollback last migration
alembic downgrade -1

# Re-apply
alembic upgrade head
```

---

## Performance Issues

### High Memory Usage

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep python  # Linux
Get-Process python* | Select-Object WorkingSet  # Windows
```

**Solutions**:
1. **Reduce active symbols** - Trade fewer symbols
2. **Enable cache cleanup** - Reduces memory over time
3. **Restart bot daily** - Clear accumulated state

### Slow Trading Loop

**Target**: <55 seconds per cycle

**Solutions**:
1. **Check MT5 latency** - Network issues can slow data fetching
2. **Optimize timeframes** - Use longer timeframes for slower trading
3. **Disable unused strategies** - Reduce confluence layers

---

## Notification Issues

### No Telegram Notifications

**Check**:
1. Bot token correct in `.env`
2. Chat ID correct (test with `/getUpdates`)
3. Notifications enabled in config
4. Not in dry-run mode (disabled by default)

Test notifications by running bot in dry-run mode with `send_in_dry_run: true` in config. (`notifications test` CLI is 📋 planned).

---

## Process Management

### Multiple Bot Instances Running

**Symptoms**: `Log file is locked` error

**Solutions**:
```powershell
# Windows: Kill all Python processes
Get-Process python* | Stop-Process -Force

# Or use kill script
uv run python scripts/kill_trading_bot.py
```

### Bot Not Starting

**Check**:
1. Configuration valid: `uv run trading-bot config validate`
2. Database accessible
3. No port conflicts
4. Logs for startup errors

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `MT5 not initialized` | MT5 not running | Start MT5 terminal |
| `Server mismatch detected` | Wrong MT5 server | Set explicit server in config |
| `Database is locked` | Multiple instances | Kill all Python processes |
| `Insufficient margin` | Account balance low | Add funds or reduce position size |
| `Symbol not found` | Wrong broker mapping | Check broker symbol config |
| `Risk limit exceeded` | Too many positions | Wait for positions to close |
| `Daily loss limit reached` | Reached daily limit | Bot will resume next day |

---

## Getting Help

### Check Documentation
1. [Configuration Guide](../setup/configuration-guide.md)
2. [MT5 Connection Guide](../setup/mt5-connection-guide.md)
3. [Risk Management Guide](../trading/risk-management-guide.md)

### Check Logs
```bash
# All logs
tail -f logs/trading_bot.log

# Filtered by level
grep "ERROR\|WARNING" logs/trading_bot.log

# Last 100 lines
tail -n 100 logs/trading_bot.log
```

### Reset to Clean State
```bash
# Stop bot
# Backup database
cp trading_bot.db trading_bot_backup.db

# Reset database (WARNING: deletes data)
rm trading_bot.db
alembic upgrade head

# Restart in dry-run mode
uv run trading-bot start --dry-run
```
