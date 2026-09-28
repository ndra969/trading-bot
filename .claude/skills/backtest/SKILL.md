---
name: backtest
description: Run or locate backtests for the Python trading bot strategies (scripts/). Not for the MQL5 SDBot EA — that uses MT5 Strategy Tester (see the sdbot-ea skill).
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
