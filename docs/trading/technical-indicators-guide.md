# Technical Indicators Guide

RSI and Moving Average indicators used in strategy analysis.

## Overview

Technical indicators are **enhancement layers** providing confluence:
- **RSI** (Layer 6): 10% weight
- **Moving Average** (Layer 7): 8% weight

Foundation (S&D zones) remains mandatory at 30%.

## RSI Analysis

### Configuration by Timeframe

| Timeframe | Period | Overbought | Oversold |
|-----------|--------|------------|----------|
| M15 | 14 | 80 | 20 |
| H1 | 14 | 70 | 30 |
| H4 | 14 | 70 | 30 |
| D1 | 14 | 65 | 35 |

### Signal Generation

```python
# RSI signal logic
if rsi < oversold:
    signal = "POTENTIAL_BUY"
elif rsi > overbought:
    signal = "POTENTIAL_SELL"
elif divergence_detected:
    signal = "DIVERGENCE_REVERSAL"
```

### Divergence Detection

The bot detects RSI divergence:

| Type | Price | RSI | Signal |
|------|-------|-----|--------|
| **Bullish Divergence** | Lower lows | Higher lows | Buy |
| **Bearish Divergence** | Higher highs | Lower highs | Sell |

### Asset-Specific RSI

```yaml
# config/technical_indicators.yaml
rsi:
  forex_major:
    period: 14
    overbought: 70
    oversold: 30
  forex_jpy:
    period: 14
    overbought: 75  # More volatile
    oversold: 25
  commodities:
    period: 14
    overbought: 80  # Gold is volatile
    oversold: 20
  crypto:
    period: 14
    overbought: 80
    oversold: 20
```

## Moving Average Analysis

### MA Configuration

| MA | Period | Type | Purpose |
|----|--------|------|---------|
| Fast | 9 | EMA | Short-term momentum |
| Medium | 21 | EMA | Medium-term trend |
| Slow | 50 | EMA | Long-term trend |
| Trend | 200 | SMA | Major trend filter |

### Signal Generation

```python
# Trend alignment check
if ema_9 > ema_21 > ema_50:
    trend = "BULLISH"
elif ema_9 < ema_21 < ema_50:
    trend = "BEARISH"
else:
    trend = "NEUTRAL"

# Price vs MA position
if price > ema_50:
    bias = "BULLISH"
elif price < ema_50:
    bias = "BEARISH"
```

### MA Crossovers

| Crossover | Signal |
|-----------|--------|
| EMA 9 crosses above EMA 21 | Bullish (short-term) |
| EMA 9 crosses below EMA 21 | Bearish (short-term) |
| EMA 21 crosses above EMA 50 | Bullish (medium-term) |
| Price crosses SMA 200 | Major trend change |

## Multi-Timeframe Analysis

Indicators analyzed across timeframes:

```
H1 RSI (40% weight) + H4 RSI (35%) + D1 RSI (25%)
                        ↓
              Combined RSI Score
```

**Confluence**: Higher TFs given more weight for trend; lower TFs for entry timing.

## Library Fallback

The bot uses libraries in priority order:

```
1. pandas-ta (preferred - pure Python)
   ↓ (fallback)
2. TA-Lib (if installed - faster)
   ↓ (fallback)
3. ta library (alternative)
   ↓ (fallback)
4. Manual calculation
```

## Configuration

`config/technical_indicators.yaml`:

```yaml
rsi:
  enabled: true
  period: 14
  overbought: 70
  oversold: 30
  divergence_detection: true
  multi_timeframe: true

moving_averages:
  enabled: true
  fast_ema: 9
  medium_ema: 21
  slow_ema: 50
  trend_sma: 200
  crossover_detection: true

confluence_weights:
  rsi: 0.10
  ma: 0.08
```

## CLI Commands

> **Note**: All `technical` CLI commands are 📋 planned. Indicators run automatically during strategy analysis.

```bash
# 📋 Planned (not yet implemented):
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot technical analyze --symbol EURUSD --indicator ma
uv run trading-bot technical test-libraries
uv run trading-bot technical rsi --symbol EURUSD --multi-tf
```

**Current**: Indicators are calculated automatically during signal generation. Inspect via dry-run logs.

## Installation (Optional Performance)

For faster calculations, install TA-Lib:

```bash
# Windows (requires Visual Studio Build Tools)
conda install -c conda-forge ta-lib

# Or use pandas-ta (pure Python, always works)
uv add pandas-ta
```

## Performance

| Library | Speed | Reliability |
|---------|-------|-------------|
| TA-Lib | Fastest | Excellent (if installed) |
| pandas-ta | Fast | Excellent (default) |
| ta | Medium | Good |
| Manual | Slow | Always works |

## Related Documentation

- [Strategy Guide](../guides/strategy-guide.md) - Strategy architecture
- [Multi-Timeframe Guide](../guides/multi-timeframe-guide.md) - MTF analysis
- [Trading Types](trading-types-guide.md) - Trading type configs
