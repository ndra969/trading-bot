---
description: Check bot status (MT5, positions, account, risk)
argument-hint: [bot|mt5|positions|account|risk|all]
---

# Bot Status Check

| Arg | Action |
|-----|--------|
| (none) or `all` | Full status (bot + MT5 + positions + account + risk) |
| `bot` | `uv run trading-bot status` |
| `mt5` | `uv run trading-bot mt5 status` |
| `positions` | `uv run trading-bot positions active` |
| `account` | `uv run trading-bot account info` |
| `risk` | `uv run trading-bot risk status` |

## Full Status (all)

Runs all checks in parallel:

```bash
uv run trading-bot status
uv run trading-bot mt5 status
uv run trading-bot account info
uv run trading-bot positions active
uv run trading-bot risk status
```

## When to Use

- Before starting trading
- After bot restart
- When debugging issues
- Daily health check

## Related

- `/logs` - View recent logs
- `/dry-run` - Validate full system
