# Dry-Run Guide

Test the trading bot without risking real money.

> **Quick Command**: Use `/dry-run` for fast dry-run validation.

## What is Dry-Run?

Dry-run simulates trading operations without sending real orders:
- ✅ Full strategy execution
- ✅ Signal generation with real market data
- ✅ Risk validation
- ✅ Position tracking (in-memory)
- ❌ No real orders sent
- ❌ No real money at risk

## Usage

### Three Modes

```bash
# Mode 1: Fully simulated (no MT5 required)
uv run trading-bot start --dry-run

# Mode 2: Real MT5 data, simulated orders
uv run trading-bot start --dry-run --connect-mt5

# Mode 3: Specific config
uv run trading-bot start --dry-run --config development
```

### Via Environment

```bash
# .env file
DRY_RUN=true
```

### Via Config

```yaml
# config/development.yaml
trading:
  dry_run: true
```

**Priority**: CLI flag > Environment > Config file

## What Happens in Dry-Run

| Operation | Behavior |
|-----------|----------|
| Market data | Real (with `--connect-mt5`) or simulated |
| Signal generation | Full execution |
| Risk validation | Full validation |
| Order execution | Simulated only |
| Position tracking | In-memory |
| Database saving | Disabled by default |
| Telegram notifications | Disabled by default |

## Log Output

Dry-run logs are marked clearly:

```
[INFO] Trading bot started (DRY-RUN mode)
[INFO] Signal generated: BUY EURUSD @ 1.0850
[DRY-RUN] Would execute order: 0.01 lots, SL 1.0800, TP 1.0950
[DRY-RUN] Order simulated: Ticket DRY_abc123
```

## Common Use Cases

### Strategy Testing

```bash
# Test new strategy
uv run trading-bot start --dry-run --connect-mt5
```

Monitor logs to validate signal quality.

### Configuration Validation

```bash
# Test new config without risk
uv run trading-bot start --dry-run --config new_strategy
```

### Development & Debugging

```bash
# Debug with verbose logging
DRY_RUN=true LOG_LEVEL=DEBUG uv run trading-bot start
```

## Enabling Optional Features in Dry-Run

### Save to Database

```yaml
# config/development.yaml
trading:
  dry_run: true
  dry_run_save_db: true  # Save positions with is_dry_run=true
```

### Enable Notifications

```yaml
monitoring:
  telegram:
    enabled: true
    send_in_dry_run: true  # Override default
```

## Migration to Live Trading

Pre-flight checklist:

- [ ] Dry-run completed (minimum 1 week)
- [ ] Signal quality validated
- [ ] Risk parameters confirmed
- [ ] No errors in logs
- [ ] Configuration reviewed
- [ ] Backup procedures tested
- [ ] Emergency stop tested

Then switch to live:

```bash
# Set dry_run: false in production config
# Start live trading
uv run trading-bot start --config production
```

## Troubleshooting

### Dry-Run Still Executing Orders

Verify dry-run is enabled:
```bash
# Check logs for "DRY-RUN" tags
grep "DRY-RUN" logs/trading_bot.log
```

If orders are executing, check:
1. `dry_run: true` in config
2. No `--live` flag in command
3. Logs show "DRY-RUN" messages

### No Signals Generated

```bash
# Use --connect-mt5 for real data
uv run trading-bot start --dry-run --connect-mt5
```

Without `--connect-mt5`, simulated data may not generate signals.

## Related Documentation

- [Configuration Guide](../setup/configuration-guide.md) - Config options
- [Deployment Guide](deployment-guide.md) - Production deployment
- [Troubleshooting](troubleshooting-guide.md) - Common issues
