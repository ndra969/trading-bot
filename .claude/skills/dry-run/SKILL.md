---
name: dry-run
description: Validate the Python trading bot with dry-run mode. Mandatory after code/config changes under packages/.
argument-hint: [config-name]
---

# Dry Run Validation

**MANDATORY** after any code changes.

```bash
uv run trading-bot start --dry-run                  # Default
uv run trading-bot start --config production --dry-run
uv run trading-bot start --dry-run --verbose
```

Validates: config loading, DB connectivity, strategy/risk/position init, MT5 connector, trading loop.

Required after: code changes, config updates, DB schema changes, new features, bug fixes.
