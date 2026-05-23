---
description: Analyze symbol with foundation strategy
argument-hint: <symbol> [--timeframe <tf>] [--trading-type <type>]
---

# Strategy Analysis

```bash
uv run trading-bot foundation analyze --symbol <SYMBOL> --timeframe <TF>
uv run trading-bot foundation price-action <SYMBOL> --timeframe <TF> --trading-type <TYPE>
```

## Timeframes by Type

- scalping: M1, M5, M15
- day_trading: M15, H1, H4
- swing_trading: H4, D1, W1
- position_trading: D1, W1, MN1

## Strategy Layers (min 65% confluence)

Foundation 30% | Trendline 20% | Price Action 15% | Fibonacci 12% | Breakout 12% | Structure 8% | RSI 10% | MA 8%

## Examples

```
/analyze EURUSD
/analyze XAUUSD --timeframe H4 --trading-type swing_trading
```
