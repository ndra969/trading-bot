---
description: Check bot status (MT5, account)
argument-hint: [bot|mt5|account|all]
---

# Bot Status Check

| Arg | Status | Action |
|-----|--------|--------|
| (none) or `all` | ✅ Partial | Run available checks |
| `bot` | ✅ | `uv run trading-bot status` |
| `mt5` | ✅ | `uv run trading-bot mt5 status` |
| `account` | ✅ | `uv run trading-bot account info` |
| `positions` | 📋 Planned | (not yet implemented) |
| `risk` | 📋 Planned | (not yet implemented) |

## Full Status (currently available)

```bash
uv run trading-bot status
uv run trading-bot mt5 status
uv run trading-bot account info
```

## When to Use

- Before starting trading
- After bot restart
- When debugging issues
- Daily health check

## Related

- `/logs` - View recent logs
- `/dry-run` - Validate full system
