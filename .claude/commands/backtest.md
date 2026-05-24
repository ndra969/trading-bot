---
description: Run backtesting on strategies
argument-hint: <symbol> [--period <days>] [--strategy <name>]
---

# Backtest

> **Status**: 📋 CLI command not yet implemented.
> Backtest scripts exist in `scripts/` directory.

## Planned Command

```bash
uv run trading-bot backtest --symbol <SYMBOL> --period <DAYS>
```

## Current Method

Backtest reports are generated and stored in:
```
scripts/reports/backtest_<symbol>_<date>.json
```

Use existing scripts in `scripts/` for backtesting (not CLI integrated yet).

## Metrics Tracked

trades, win rate, profit factor, max drawdown, Sharpe ratio
