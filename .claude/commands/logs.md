---
description: View/filter trading bot logs
argument-hint: [tail|errors|signals|trades|risk|N]
---

# View Logs

| Arg | Action |
|-----|--------|
| (none) or `tail` | `tail -f logs/trading_bot.log` (live) |
| `errors` | `grep -i "error\|exception" logs/trading_bot.log` |
| `signals` | `grep -i "signal\|zone\|strategy" logs/trading_bot.log` |
| `trades` | `grep -i "order\|position\|execute" logs/trading_bot.log` |
| `risk` | `grep -i "risk\|drawdown\|emergency" logs/trading_bot.log` |
| `N` (number) | `tail -n N logs/trading_bot.log` (last N lines) |

## Common Filters

```bash
# Multi-filter
grep -i "ERROR\|WARNING" logs/trading_bot.log

# Today's logs
grep "$(date +%Y-%m-%d)" logs/trading_bot.log

# Specific symbol
grep "EURUSD" logs/trading_bot.log
```

## Log Locations

- Main log: `logs/trading_bot.log`
- Daily rotation in `logs/`

## Related

- `/status` - Current bot status
- `/dry-run` - Validate system
