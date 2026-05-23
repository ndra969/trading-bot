# Intraday Execution Guide

Day trading executor for short-term trades within same trading day.

## Overview

| Feature | Configuration |
|---------|---------------|
| Trading Type | Day Trading (30 min - 24 hours) |
| Zone Detection | H1 timeframe |
| Entry Signals | M30 timeframe |
| Trend Filter | H1 EMA (Sniper Gate for commodities) |
| Position Closure | Before day end |
| Scan Frequency | Every 30 minutes (M30 close) |

## Execution Flow

```
1. Zone Detection (H1)
   - Scan H1 supply/demand zones
   - Cache for 60 minutes
   ↓
2. Entry Signal (M30)
   - Wait for M30 candle close
   - Check price at H1 zone
   - Validate M30 price action
   ↓
3. Trend Filter (H1) - Commodities only
   - EMA 50/20 crossover (Sniper Gate)
   - Confirm with 2 consecutive candles
   ↓
4. Signal Generation
   - Combine zone + entry + trend
   - Min 65% confluence
   ↓
5. Position Management
   - Breakeven at 70% of R:R
   - Trailing stop after 30 pips
   - Close before day end
```

## Sniper Gate (Trend Filter)

For commodities only (XAUUSD, XAGUSD):

```python
# Calculate H1 EMAs
ema_50 = h1_data['close'].ewm(span=50).iloc[-1]
ema_20 = h1_data['close'].ewm(span=20).iloc[-1]
price = h1_data['close'].iloc[-1]

# Determine trend bias
if price > ema_50 and ema_20 > ema_50:
    trend = "BULLISH"
elif price < ema_50 and ema_20 < ema_50:
    trend = "BEARISH"
else:
    trend = "NEUTRAL"  # No trade
```

**Rules**:
- BUY only if trend = BULLISH
- SELL only if trend = BEARISH
- NEUTRAL = skip the trade

## Configuration

`config/trading_types.yaml`:

```yaml
day_trading:
  timeframes:
    zone_detection: H1
    entry_signal: M30
    trend_filter: H1

  scan:
    interval_minutes: 30
    zone_cache_minutes: 60

  position:
    max_holding_hours: 24
    close_before_day_end: true
    closure_buffer_minutes: 30

  automation:
    breakeven:
      trigger_rr_ratio: 0.7
      offset_pips: 2.0
    trailing:
      activation_pips: 30.0
      trail_pips: 10.0

  sniper_gate:
    enabled: true
    apply_to: [XAUUSD, XAGUSD]
    ema_fast: 20
    ema_slow: 50
    confirmation_candles: 2
```

## Position Closure

All positions close before trading day end:

| Asset | Closure Time (UTC) |
|-------|-------------------|
| Forex | 17:00 (NY close) |
| Commodities | 17:00 (NY close) |
| Crypto | 00:00 (UTC) |

**Buffer**: Close 30 minutes before day end to avoid spread widening.

## Cache Strategy

H1 zones cached for performance:

```python
if symbol not in zone_cache or cache_expired(symbol):
    zones = await detect_h1_zones(symbol)
    zone_cache[symbol] = (zones, datetime.now(UTC))

# Use cached zones for M30 analysis
```

## Usage

```python
from trading_bot.executors.factory import ExecutorFactory

# Create intraday executor
executor = ExecutorFactory.create_executor(
    trading_type="day_trading",
    config=config,
    foundation_engine=foundation_engine,
    position_manager=position_manager,
)

# Initialize and run
await executor.initialize()
await executor.execute_trading_loop(symbols=["EURUSD", "XAUUSD"])
```

## Best Practices

1. **Always use H1 for zones** - Lower TFs have too much noise
2. **Apply Sniper Gate for commodities** - Reduces false signals
3. **Close before day end** - Avoid overnight gaps
4. **Use M30 entries** - Confirms H1 zone validity
5. **Cache zones** - Performance optimization

## Monitoring

Track these metrics:
- Zone quality (average strength)
- Entry accuracy (% reaching TP)
- Sniper Gate effectiveness
- End-of-day slippage

## Related Documentation

- [Trading Types Guide](../trading/trading-types-guide.md) - Day trading config
- [Multi-Timeframe Guide](multi-timeframe-guide.md) - MTF analysis
- [Position Management](../trading/position-management-architecture.md) - Lifecycle
