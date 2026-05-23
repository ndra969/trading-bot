# Strategy Guide

Trading strategy architecture and signal generation.

> **Quick Commands**: Use `/analyze <symbol>` to analyze a symbol with foundation strategy.

## Strategy Architecture

The bot uses a **foundation-first approach** with 7 enhancement layers:

```
Foundation (S&D) → Enhancement Layers → Signal Aggregation → Execution
     30%               7 layers              65% threshold       MT5
```

## Confluence Weights

| Layer | Weight | Purpose |
|-------|--------|---------|
| Supply & Demand (Foundation) | 30% | Zone-based entries |
| Trendline Confluence | 20% | Trendline validation |
| Price Action Patterns | 15% | Candlestick patterns |
| Fibonacci Levels | 12% | Key retracement levels |
| Breakout Retest | 12% | Validated breakouts |
| Market Structure | 8% | BOS/CHoCH alignment |
| RSI Analysis | 10% | Momentum confirmation |
| Moving Average | 8% | Trend alignment |
| **Total** | **120%** | **Min 65% to execute** |

## Foundation: Supply & Demand

### Zone Detection

The bot identifies 3 types of zones:
- **Rejection zones** - Strong price rejection
- **Consolidation zones** - Accumulation/distribution
- **Breakout origin zones** - Pre-breakout consolidation

### Zone Quality Criteria

| Parameter | Default |
|-----------|---------|
| Minimum strength | 35.0 |
| Minimum grade | C |
| Max age | 72 hours |
| Freshness bonus | +15.0 (fresh zones) |
| Volume factor | 0.8x average |

### Entry Validation

```
Price approaches zone
    ↓
Zone quality check (strength, age)
    ↓
Entry score calculation
    ↓
Score ≥ 50? → Pass to enhancement layers
```

## Enhancement Layers

### Trendline Confluence (20%)

Validates trendline support/resistance:
- Minimum 3 touches for confirmation
- Multi-timeframe analysis
- Break/bounce probability scoring

### Price Action Patterns (15%)

Detects key candlestick patterns:
- Engulfing patterns
- Pin bars (rejection)
- Inside bars (consolidation)
- Doji (indecision)
- Flag and pennant

### Fibonacci Levels (12%)

Key levels: 38.2%, 50%, 61.8%, 78.6%

Zones at these levels get bonus score.

### Breakout Retest (12%)

Validates breakout entries:
- Volume confirmation (>1.5x average)
- Momentum scoring
- False breakout filtering

### Market Structure (8%)

Tracks:
- **BOS** (Break of Structure) - Trend continuation
- **CHoCH** (Change of Character) - Trend reversal
- Higher highs / Lower lows

### RSI Analysis (10%)

- Overbought/oversold levels (70/30)
- Divergence detection (bullish/bearish)
- Multi-timeframe RSI confluence

### Moving Average (8%)

- EMA 9, 21, 50, 200
- Trend alignment (price vs MA)
- MA crossovers

## Signal Generation

### Confluence Calculation

```python
total_score = (
    foundation_score * 0.30 +
    trendline_score * 0.20 +
    price_action_score * 0.15 +
    fibonacci_score * 0.12 +
    breakout_score * 0.12 +
    structure_score * 0.08 +
    rsi_score * 0.10 +
    ma_score * 0.08
)

if total_score >= 0.65:
    generate_signal()
```

### Signal Validation

Before execution:
1. Confluence score ≥ 65%
2. Risk validation passes
3. Market hours valid
4. No existing position for symbol
5. Portfolio limits OK

## Multi-Timeframe Analysis

Timeframes adapt to trading type:

| Trading Type | Timeframes |
|--------------|------------|
| Scalping | M1, M5, M15 |
| Day Trading | M15, H1, H4 |
| Swing | H4, D1, W1 |
| Position | D1, W1, MN1 |

See [Multi-Timeframe Guide](multi-timeframe-guide.md).

## Configuration

`config/strategy_parameters.yaml`:

```yaml
foundation:
  min_zone_strength: 35.0
  min_zone_grade: C
  max_zone_age_hours: 72

confluence:
  min_total_score: 0.65
  weights:
    foundation: 0.30
    trendline: 0.20
    price_action: 0.15
    fibonacci: 0.12
    breakout_retest: 0.12
    market_structure: 0.08
    rsi: 0.10
    ma: 0.08

multi_timeframe:
  day_trading:
    primary: H1
    secondary: H4
    tertiary: D1
```

## CLI Commands

```bash
# Analyze symbol with foundation strategy
uv run trading-bot foundation analyze --symbol EURUSD

# Multi-timeframe analysis
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1

# Backtest strategy
uv run trading-bot backtest --symbol EURUSD --period 30d
```

## Related Documentation

- [Multi-Timeframe Guide](multi-timeframe-guide.md) - MTF analysis
- [Technical Indicators](../trading/technical-indicators-guide.md) - RSI, MA details
- [Risk Management](../trading/risk-management-guide.md) - Risk validation
- [Trading Types](../trading/trading-types-guide.md) - Trading type configs
