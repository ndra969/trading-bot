---
description: Analyze symbol with foundation strategy
argument-hint: <symbol> [--timeframe <tf>] [--trading-type <type>]
---

# Strategy Analysis

> **Status**: 📋 Planned. CLI command not yet implemented.
> Currently analyze via `uv run trading-bot start --dry-run` and inspect logs.

## Planned Commands

```bash
uv run trading-bot foundation analyze --symbol <SYMBOL> --timeframe <TF>
uv run trading-bot foundation price-action <SYMBOL> --timeframe <TF> --trading-type <TYPE>
```

## Timeframes by Type

- day_trading: M15, H1, H4 (✅ implemented)
- scalping: M1, M5, M15 (📋 planned)
- swing_trading: H4, D1, W1 (📋 planned)
- position_trading: D1, W1, MN1 (📋 planned)

## Strategy Layers (min 65% confluence)

Foundation 30% | Trendline 20% | Price Action 15% | Fibonacci 12% | Breakout 12% | Structure 8% | RSI 10% | MA 8%

## Current Workaround

```bash
# Run dry-run and inspect signals in logs
uv run trading-bot start --dry-run --connect-mt5
grep -i "signal\|zone" logs/trading_bot.log
```
