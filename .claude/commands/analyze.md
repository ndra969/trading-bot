---
description: Analyze symbol with foundation strategy
argument-hint: <symbol> [--timeframe <tf>] [--trading-type <type>]
---

# Foundation Strategy Analysis

Analyze a trading symbol using the Foundation Strategy (Supply & Demand zones) with optional Price Action layer.

## Arguments

- **symbol** (required): Trading symbol to analyze (e.g., EURUSD, XAUUSD)
- `--timeframe <tf>`: Timeframe for analysis (default: H1)
- `--trading-type <type>`: Trading type (scalping, day_trading, swing_trading, position_trading)

## Implementation Steps

1. **Parse arguments** - Extract symbol, timeframe, and trading type
2. **Run foundation analysis** - Detect supply and demand zones
3. **Display results** - Show zones, confluence scores, and signals

## Commands to Execute

```bash
# Basic analysis
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1

# With price action layer
uv run trading-bot foundation price-action EURUSD --timeframe H1 --trading-type day_trading

# Multi-timeframe analysis
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H4 --trading-type swing_trading
```

## Timeframe Matrix by Trading Type

- **Scalping**: M1, M5, M15 (ultra-short term)
- **Day Trading**: M15, H1, H4 (intraday focus)
- **Swing Trading**: H4, D1, W1 (multi-day trends)
- **Position Trading**: D1, W1, MN1 (long-term trends)

## Examples

- `/analyze EURUSD` → Analyze EURUSD on H1 timeframe
- `/analyze XAUUSD --timeframe H4 --trading-type swing_trading` → Gold analysis for swing trading

## Related

- `/backtest` → Run backtesting on strategy
- `/dry-run` → Validate complete system
- `/rules` → Display project rules

## Foundation Strategy Components

The Foundation Strategy includes:
- ✅ Supply & Demand zones (30% confluence weight)
- ✅ Trendline confluence (20%)
- ✅ Price Action patterns (15%)
- ✅ Fibonacci levels (12%)
- ✅ Breakout/Retest (12%)
- ✅ Market Structure BOS/CHoCH (8%)
- ✅ RSI Analysis (10%)
- ✅ Moving Average (8%)
