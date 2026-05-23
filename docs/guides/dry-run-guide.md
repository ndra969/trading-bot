# Dry-Run Mode Guide

## Overview

**Dry-run mode** allows you to test the trading bot without risking real money. It simulates trading operations while using real market data, making it essential for:

- **Strategy Testing**: Validate strategies before live trading
- **Configuration Validation**: Test settings without risk
- **Development**: Debug and test new features safely
- **Paper Trading**: Practice trading with real market conditions

---

## What Dry-Run Does

### ✅ What Works in Dry-Run

| Feature | Behavior |
|---------|----------|
| **Market Data** | Real MT5 data (if `--connect-mt5` used) |
| **Strategy Analysis** | Full strategy execution |
| **Signal Generation** | Real trading signals generated |
| **Risk Validation** | Complete risk checks |
| **Position Tracking** | Positions tracked in database |
| **Logging** | Full logging output |
| **Notifications** | Disabled by default |

### ❌ What Doesn't Work

| Feature | Behavior |
|---------|----------|
| **Order Execution** | No real orders sent to MT5 |
| **Position Opening** | Simulated only (no MT5 tickets) |
| **Balance Changes** | No real money affected |
| **Database Saving** | Positions not saved to DB (by default) |

---

## Usage

### Basic Dry-Run (No MT5)

```bash
# Start with simulated data only (no MT5 connection)
uv run trading-bot start --dry-run
```

**Use Case**: Testing bot logic without MT5 installed

### Dry-Run with MT5 Data

```bash
# Connect to MT5 for real market data, but don't trade
uv run trading-bot start --dry-run --connect-mt5
```

**Use Case**: Test strategies with real market data

### Dry-Run with Specific Config

```bash
# Use specific configuration
uv run trading-bot start --dry-run --config development
```

### Dry-Run from Python

```python
from trading_bot.main import TradingBot

# Create bot with dry-run enabled
bot = TradingBot(
    config_path="config/development.yaml",
    dry_run=True  # Enable dry-run
)

# Start bot (will not execute real trades)
await bot.start()
```

---

## Configuration

### Via Config File

In `config/development.yaml`:

```yaml
trading:
  dry_run: true  # Enable dry-run mode
```

### Via Environment Variable

```bash
# .env file
DRY_RUN=true
```

### Via Command Line

```bash
uv run trading-bot start --dry-run
```

**Priority**: Command line > Environment > Config file

---

## Dry-Run Wrapper

The bot uses a `DryRunWrapper` to intercept MT5 operations:

```python
class DryRunWrapper:
    """
    Wraps MT5 operations for dry-run mode.

    All order operations are simulated:
    - Orders return success but don't execute
    - Positions are tracked in memory only
    - No real money at risk
    """

    async def send_order(self, order_request: OrderRequest) -> OrderResult:
        """Simulate order execution without sending to MT5."""
        # Simulate execution delay
        await asyncio.sleep(0.1)

        # Return simulated success
        return OrderResult(
            success=True,
            ticket=f"DRY_{uuid.uuid4()}",
            message="Dry-run: Order simulated"
        )
```

---

## Output Differences

### Live Mode Output

```
[INFO] Trading bot started (LIVE mode)
[INFO] MT5 connected: Account 159394302 (Exness)
[INFO] Signal generated: BUY EURUSD @ 1.0850
[INFO] Executing order: 0.01 lots, SL 1.0800, TP 1.0950
[SUCCESS] Order executed: Ticket #12345
[INFO] Position opened: #12345 BUY EURUSD
```

### Dry-Run Mode Output

```
[INFO] Trading bot started (DRY-RUN mode)
[INFO] MT5 connected: Account 159394302 (Exness)
[INFO] Signal generated: BUY EURUSD @ 1.0850
[DRY-RUN] Would execute order: 0.01 lots, SL 1.0800, TP 1.0950
[DRY-RUN] Order simulated: Ticket DRY_abc123
[INFO] Dry-run: Position would be opened
```

---

## Database Behavior

### Live Mode

```sql
-- Positions are saved to database
INSERT INTO positions (
    position_id, symbol, action, volume, sl, tp, ...
) VALUES (
    12345, 'EURUSD', 'BUY', 0.01, 1.0800, 1.0950, ...
);
```

### Dry-Run Mode

```sql
-- By default, positions are NOT saved
-- To enable database saving in dry-run:
-- Set dry_run_save_db: true in config

INSERT INTO positions (
    position_id, symbol, action, volume, sl, tp, ...
    is_dry_run  -- Marked as dry-run
) VALUES (
    'DRY_abc123', 'EURUSD', 'BUY', 0.01, 1.0800, 1.0950, ...
    TRUE  -- Dry-run flag
);
```

### Enable Database Saving

```yaml
# config/development.yaml
trading:
  dry_run: true
  dry_run_save_db: true  # Save dry-run positions to DB
```

---

## Notification Behavior

### Default (Disabled)

In dry-run mode, notifications are **disabled by default**:

```python
# NotificationManager checks dry-run status
if config.trading.dry_run:
    logger.info("🧪 Dry-run mode: Skipping notification")
    return
```

### Enable Notifications in Dry-Run

```yaml
# config/development.yaml
monitoring:
  telegram:
    enabled: true
    send_in_dry_run: true  # Override default
```

---

## Testing Scenarios

### Scenario 1: Strategy Validation

```bash
# Test new strategy configuration
uv run trading-bot start --dry-run --config test_strategy
```

**Expected**:
- Full strategy execution
- Signals generated and logged
- No real orders sent

### Scenario 2: Risk Management Testing

```bash
# Test risk limits with dry-run
uv run trading-bot start --dry-run --connect-mt5
```

**Expected**:
- Real market data
- Risk validation active
- Positions tracked in memory

### Scenario 3: Development Debugging

```bash
# Debug new feature with dry-run
DRY_RUN=true LOG_LEVEL=DEBUG uv run trading-bot start
```

**Expected**:
- Verbose logging output
- Stack traces on errors
- No risk to capital

---

## Validating Dry-Run Behavior

### Check 1: No Real Orders

```bash
# Start dry-run mode
uv run trading-bot start --dry-run --connect-mt5

# In another terminal, check MT5 terminal
# Expected: No new positions appear
```

### Check 2: Database Status

```bash
# Check database for dry-run positions
sqlite3 trading_bot.db "SELECT * FROM positions WHERE is_dry_run = 1;"

# Expected: Only dry-run positions have is_dry_run = 1
```

### Check 3: Log Messages

```bash
# Check logs for dry-run indicators
grep "DRY-RUN\|Dry-run\|dry_run" logs/trading_bot.log

# Expected: Multiple dry-run log messages
```

---

## Migration to Live Trading

### Pre-Live Checklist

Before switching from dry-run to live mode:

- [ ] Dry-run testing completed (minimum 1 week)
- [ ] Strategy performance validated
- [ ] Risk parameters confirmed
- [ ] Configuration reviewed
- [ ] Backup/recovery procedures tested
- [ ] Emergency stop procedures verified
- [ ] Account balance sufficient
- [ ] Broker settings verified (lot size, leverage)

### Switching to Live Mode

```bash
# Step 1: Stop dry-run bot
# Press Ctrl+C in terminal

# Step 2: Review configuration
# Ensure dry_run: false in config

# Step 3: Start live bot
uv run trading-bot start --config production

# Step 4: Monitor first trade closely
# Check Telegram notifications for execution
```

---

## Troubleshooting

### Dry-Run Still Executing Orders

**Problem**: Orders appearing in MT5 terminal

**Solutions**:
1. Verify `dry_run: true` in config
2. Check command line doesn't have `--live` flag
3. Review logs for "DRY-RUN" messages

### No Signals Generated

**Problem**: Dry-run mode generates no signals

**Solutions**:
1. Check `--connect-mt5` flag (need real data)
2. Verify market hours for symbols
3. Review strategy configuration
4. Check logs for errors

### Database Not Saving

**Problem**: Dry-run positions not appearing in database

**Solutions**:
1. Set `dry_run_save_db: true` in config
2. Check database connection
3. Verify database file permissions

---

## Best Practices

### 1. Always Start with Dry-Run

- Test new strategies in dry-run first
- Validate configuration changes
- Develop features in dry-run mode

### 2. Use Dry-Run with Real Data

- Use `--connect-mt5` for realistic testing
- Test across different market conditions
- Validate with live market data

### 3. Monitor Dry-Run Performance

- Track signal quality in dry-run
- Compare dry-run vs live results
- Adjust parameters based on dry-run results

### 4. Document Dry-Run Results

- Keep dry-run trading logs
- Record strategy performance
- Note any issues or improvements

---

## Advanced Usage

### Custom Dry-Run Wrapper

```python
from trading_bot.connectors.dry_run_wrapper import DryRunWrapper

# Create custom wrapper with behavior override
wrapper = DryRunWrapper(mt5_connector=mt5)

# Override order simulation
async def custom_send_order(order_request):
    # Custom simulation logic
    return OrderResult(success=True, ticket="CUSTOM_123")

wrapper.send_order = custom_send_order
```

### Dry-Run with Slippage Simulation

```yaml
# config/development.yaml
trading:
  dry_run: true
  dry_run_slippage_pips: 2  # Simulate 2 pip slippage
  dry_run_slippage_percent: 0.1  # Or 0.1% slippage
```

---

## Related Documentation

- [Configuration Guide](../configuration-guide.md) - Config file setup
- [Testing Guide](../testing-guide.md) - Testing procedures
- [Risk Management Guide](../risk-management-guide.md) - Risk in live trading
