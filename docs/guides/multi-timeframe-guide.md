# Multi-Timeframe Analysis Guide

Analyze markets across multiple timeframes for higher-confidence signals.

## Overview

Multi-timeframe (MTF) analysis confirms signals using multiple timeframes:
- **Lower timeframe**: Entry signals
- **Mid timeframe**: Trend confirmation
- **Higher timeframe**: Overall trend direction

## Timeframe Configuration

### By Trading Type

| Trading Type | Lower TF | Mid TF | Higher TF |
|--------------|----------|--------|-----------|
| **Scalping** | M1 | M5 | M15 |
| **Day Trading** | M15 | H1 | H4 |
| **Swing** | H4 | D1 | W1 |
| **Position** | D1 | W1 | MN1 |

### Weights

```yaml
multi_timeframe:
  day_trading:
    primary: H1            # Main analysis (weight: 40%)
    secondary: H4          # Trend confirmation (weight: 35%)
    tertiary: D1           # Major trend (weight: 25%)
    min_alignment: 65      # Minimum alignment score
```

## How It Works

### 1. Trend Analysis

Each timeframe contributes to trend direction:

```
D1 trend: BULLISH (weight: 3)
H4 trend: BULLISH (weight: 2)
H1 trend: NEUTRAL (weight: 1)
─────────────────────────────
Total: 5 BULLISH (min 4 required) ✓
```

### 2. Zone Detection

Zones detected on higher timeframes are stronger:

| TF | Zone Strength Multiplier |
|----|--------------------------|
| D1 | 1.5x |
| H4 | 1.3x |
| H1 | 1.0x |
| M15 | 0.7x |

### 3. Entry Confirmation

Lower timeframe confirms entry at higher timeframe zones:

```
H1 Zone identified  → Higher TF setup
    ↓
M15 Entry pattern   → Lower TF entry
    ↓
Execute trade       → All TF aligned
```

## Trading Type Examples

### Day Trading

```
Higher TF (D1):   Strong uptrend confirmed
Mid TF (H4):      Pullback to demand zone
Lower TF (H1):    Bullish engulfing pattern
                  ↓
        Strong BUY signal
```

### Scalping

```
Higher TF (M15):  Bullish momentum
Mid TF (M5):      Demand zone holding
Lower TF (M1):    Reversal pattern
                  ↓
        Quick BUY entry
```

## Cache Strategy

Analysis cached to avoid redundant calculations:

| Trading Type | Cache Duration |
|--------------|----------------|
| Scalping | 5 seconds |
| Day Trading | 30 seconds |
| Swing | 1 hour |
| Position | 1 day |

## Configuration

`config/strategy_parameters.yaml`:

```yaml
multi_timeframe:
  enabled: true
  cache_enabled: true

  day_trading:
    timeframes: [M15, H1, H4]
    weights:
      M15: 25
      H1: 40
      H4: 35
    min_alignment_score: 65
    cache_duration_seconds: 30

  scalping:
    timeframes: [M1, M5, M15]
    weights:
      M1: 35
      M5: 35
      M15: 30
    cache_duration_seconds: 5
```

## Signal Generation Flow

```
1. Determine trading type
   ↓
2. Select timeframes (per type)
   ↓
3. Analyze each timeframe (parallel)
   ├─ Zone detection
   ├─ Trend analysis
   └─ Pattern recognition
   ↓
4. Calculate confluence
   ├─ Weight by timeframe
   └─ Combine scores
   ↓
5. Validate alignment (≥ 65%)
   ↓
6. Generate signal
```

## CLI Commands

```bash
# Analyze with default timeframes
uv run trading-bot foundation analyze --symbol EURUSD

# Specify trading type
uv run trading-bot foundation analyze --symbol EURUSD --trading-type day_trading

# Specific timeframe
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1
```

## Best Practices

1. **Match TF to Trading Type** - Don't use M1 for swing trading
2. **Wait for Alignment** - Require all 3 TFs to agree
3. **Higher TF Wins** - When conflicting, follow higher TF
4. **Use Cache** - Enable caching for performance
5. **Verify Manually** - Spot-check signals on chart

## Common Issues

### No Signals Generated

**Cause**: Timeframes not aligned

**Solution**:
1. Lower `min_alignment_score`
2. Reduce timeframe count
3. Check log for analysis details

### Slow Performance

**Cause**: Cache disabled or too many timeframes

**Solution**:
1. Enable cache
2. Reduce timeframes per analysis
3. Use longer cache duration

## Related Documentation

- [Strategy Guide](strategy-guide.md) - Strategy architecture
- [Trading Types](../trading/trading-types-guide.md) - Trading type configs
- [Technical Indicators](../trading/technical-indicators-guide.md) - Indicators
