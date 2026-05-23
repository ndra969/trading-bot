---
description: Run trading bot in dry-run mode for validation
argument-hint: [config-name]
---

# Dry Run Validation

Run the trading bot in dry-run mode to validate the system without executing real trades. This is **MANDATORY** after any code changes.

## Arguments

- **no argument**: Run dry-run with default configuration
- `config-name`: Run dry-run with specific configuration (e.g., production, development)

## Implementation Steps

1. **Validate environment** - Check if MT5 is available (optional for dry-run)
2. **Run dry-run mode** - Execute bot without real trading
3. **Monitor output** - Check for errors, warnings, or issues
4. **Provide feedback** - Report validation results

## Commands to Execute

```bash
# Default dry-run
uv run trading-bot start --dry-run

# With specific config
uv run trading-bot start --config production --dry-run

# With verbose output
uv run trading-bot start --dry-run --verbose
```

## Critical Validation Checks

The dry-run validates:
- ✅ Configuration loading
- ✅ Database connectivity
- ✅ Strategy initialization
- ✅ Risk management setup
- ✅ Position management system
- ✅ MT5 connector (optional)
- ✅ Trading loop execution
- ✅ No errors or exceptions

## When to Run Dry-Run

**MANDATORY** after:
- Any code changes to core trading logic
- Configuration file updates
- Database schema changes
- New feature implementation
- Bug fixes

## Examples

- `/dry-run` → Validate with default config
- `/dry-run production` → Validate with production config

## Related

- `/test` → Run test suite before dry-run
- `/quality` → Run code quality checks before dry-run
- `/analyze` → Analyze symbols with foundation strategy

## Commit Workflow

```bash
# Before any commit
/test          # All tests must pass
/quality fix   # Fix any code quality issues
/dry-run       # Final validation
```
