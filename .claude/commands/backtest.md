---
description: Run backtesting on strategies
argument-hint: <symbol> [--period <days>] [--strategy <name>]
---

# Backtest

```bash
uv run trading-bot backtest --symbol <SYMBOL> --period <DAYS>
uv run trading-bot backtest --symbol <SYMBOL> --strategy <NAME> --period <DAYS>
```

## Defaults

- Period: 30 days
- Strategy: foundation (S&D + 7 layers)
- Capital: $10,000

## Output

`scripts/reports/backtest_<symbol>_<date>.json`

Metrics: trades, win rate, profit factor, max drawdown, Sharpe ratio.

## Examples

```
/backtest EURUSD
/backtest XAUUSD --period 90
/backtest BTCUSD --strategy foundation --period 60
```
