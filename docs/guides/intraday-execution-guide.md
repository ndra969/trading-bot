# Intraday Execution Guide

## Overview

The **Intraday Executor** implements day trading strategies with multi-timeframe analysis. It's designed for short-term trades that close within the same trading day.

### Key Characteristics

| Feature | Description |
|---------|-------------|
| **Trading Type** | Day Trading (30 min - 24 hours) |
| **Zone Detection** | H1 timeframe (1-hour candles) |
| **Entry Signals** | M30 timeframe (30-min candles) |
| **Trend Filter** | H1 EMA for commodities (Sniper Gate) |
| **Position Closure** | All positions closed before day end |
| **Scan Frequency** | Every M30 candle close (~30 minutes) |

---

## Architecture

### Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Intraday Executor                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. ZONE DETECTION (H1)                                     │
│     ┌────────────────────────────────────────┐              │
│     │ • Scan H1 supply/demand zones          │              │
│     │ • Cache zones for 60 minutes           │              │
│     │ • Score zones by freshness & strength  │              │
│     └────────────────────────────────────────┘              │
│                      │                                       │
│                      ▼                                       │
│  2. ENTRY SIGNAL (M30)                                      │
│     ┌────────────────────────────────────────┐              │
│     │ • Wait for M30 candle close            │              │
│     │ • Check price at H1 zone               │              │
│     │ • Validate M30 price action            │              │
│     └────────────────────────────────────────┘              │
│                      │                                       │
│                      ▼                                       │
│  3. TREND FILTER (H1) - Commodities Only                   │
│     ┌────────────────────────────────────────┐              │
│     │ • EMA 50/20 crossover (Sniper Gate)    │              │
│     │ • Price vs EMA 50 position            │              │
│     │ • Momentum confirmation (2 candles)   │              │
│     └────────────────────────────────────────┘              │
│                      │                                       │
│                      ▼                                       │
│  4. SIGNAL GENERATION                                      │
│     ┌────────────────────────────────────────┐              │
│     │ • Combine zone + entry + trend         │              │
│     │ • Calculate confluence score           │              │
│     │ • Generate trading signal if > 65%     │              │
│     └────────────────────────────────────────┘              │
│                      │                                       │
│                      ▼                                       │
│  5. POSITION MANAGEMENT                                    │
│     ┌────────────────────────────────────────┐              │
│     │ • Breakeven at 70% of R:R              │              │
│     │ • Trailing stop after 30 pips          │              │
│     │ • Close all before day end             │              │
│     └────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Timeframe Configuration

### Multi-Timeframe Analysis

| Purpose | Timeframe | Usage |
|---------|-----------|-------|
| **Zone Detection** | H1 | Supply & demand zones |
| **Entry Signals** | M30 | Entry confirmation |
| **Trend Filter** | H1 | EMA trend bias (commodities) |

### Cache Strategy

```python
# Zone cache configuration
zone_cache_duration_minutes = 60  # Refresh H1 zones every hour

# Scan frequency
scan_interval_minutes = 30         # Scan every M30 candle close
```

---

## Technical Indicators

### EMA Configuration (Sniper Gate)

| EMA | Period | Purpose |
|-----|--------|---------|
| Fast | 20 | Short-term trend |
| Slow | 50 | Medium-term trend |
| Trend | 200 | Long-term trend |

### RSI Settings

| Parameter | Value | Usage |
|-----------|-------|-------|
| Period | 14 | Overbought/oversold detection |
| Overbought | 70 | Potential reversal zone |
| Oversold | 30 | Potential reversal zone |

### Automation Settings

| Feature | Trigger | Value |
|---------|---------|-------|
| Breakeven | 70% of R:R reached | Move SL to entry + 2 pips |
| Trailing | 30 pips profit | Trail by 10 pips |

---

## Usage

### Basic Setup

```python
from trading_bot.executors.factory import ExecutorFactory

# Create intraday executor
executor = ExecutorFactory.create_executor(
    trading_type="day_trading",
    config=config,
    foundation_engine=foundation_engine,
    position_manager=position_manager
)

# Initialize executor
await executor.initialize()

# Execute trading loop
await executor.execute_trading_loop(symbols=["EURUSD", "XAUUSD"])
```

### Symbol Analysis

```python
# Analyze a single symbol
signal = await executor.analyze_symbol(
    symbol="XAUUSD",
    current_time=datetime.now(UTC)
)

if signal:
    print(f"Signal: {signal['action']} {signal['symbol']}")
    print(f"Confidence: {signal['confidence']}%")
else:
    print("No entry conditions met")
```

---

## Trading Logic

### 1. Zone Detection (H1)

Supply and demand zones are detected on the H1 timeframe:

```python
# Zones are cached for 60 minutes
if symbol not in self.zone_cache:
    zones = await self._detect_h1_zones(symbol)
    self.zone_cache[symbol] = (zones, datetime.now(UTC))

# Filter zones by quality
quality_zones = [z for z in zones if z.strength >= 0.7]
```

### 2. Entry Confirmation (M30)

Entry is confirmed on M30 timeframe:

```python
# Check if price is at H1 zone
if self._price_at_zone(current_price, h1_zones):
    # Validate M30 price action
    if self._validate_m30_price_action(symbol):
        return self._generate_signal()
```

### 3. Trend Filter (H1) - Commodities

For commodities (XAUUSD, XAGUSD), apply EMA trend filter:

```python
if self._is_commodity(symbol):
    trend_bias = await self._get_h1_trend_bias(symbol, current_time)

    # Only trade in direction of trend
    if signal["action"] == "BUY" and trend_bias != "BULLISH":
        return None  # Reject signal
    if signal["action"] == "SELL" and trend_bias != "BEARISH":
        return None  # Reject signal
```

**Sniper Gate Logic** (from run_mtf_backtest.py):
1. Price > EMA 50 → Bullish bias
2. Price < EMA 50 → Bearish bias
3. EMA 20 > EMA 50 → Bullish momentum
4. EMA 20 < EMA 50 → Bearish momentum
5. Require 2 consecutive candles for confirmation

---

## End-of-Day Closure

All positions must be closed before the trading day ends:

```python
async def _close_end_of_day_positions(self):
    """Close all positions before end of trading day."""
    for position in self.position_manager.get_active_positions():
        # Calculate time until day end
        time_remaining = self._get_time_until_day_end()

        if time_remaining <= timedelta(minutes=30):
            # Close position
            await self.position_manager.close_position(
                position_id=position.position_id,
                reason="END_OF_DAY"
            )
```

**Default Closure Times** (by symbol):
- Forex: 17:00 NY time (Friday close)
- Commodities: 17:00 NY time
- Crypto: 00:00 UTC

---

## Configuration

### Trading Type Parameters

Located in `config/trading_types.yaml`:

```yaml
day_trading:
  timeframes:
    zone_detection: "H1"
    entry_signal: "M30"
    trend_filter: "H1"

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
```

---

## Sniper Gate Trend Filter

### Purpose

The Sniper Gate is a trend confirmation filter for commodity day trading. It prevents entries against the dominant H1 trend.

### Logic

```python
def _get_h1_trend_bias(self, symbol: str, h1_data: pd.DataFrame) -> str:
    """
    Determine H1 trend bias using EMA 50/20.

    Returns: 'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    # Calculate EMAs
    ema_50 = h1_data['close'].ewm(span=50).iloc[-1]
    ema_20 = h1_data['close'].ewm(span=20).iloc[-1]
    price = h1_data['close'].iloc[-1]

    # Trend bias based on price vs EMA 50
    if price > ema_50:
        trend = "BULLISH"
    elif price < ema_50:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    # Momentum confirmation (EMA 20 vs EMA 50)
    if trend == "BULLISH" and ema_20 < ema_50:
        return "NEUTRAL"  # No bullish momentum
    if trend == "BEARISH" and ema_20 > ema_50:
        return "NEUTRAL"  # No bearish momentum

    return trend
```

### Application

```python
# Only apply to commodities
if symbol in ["XAUUSD", "XAGUSD"]:
    trend = await self._get_h1_trend_bias(symbol, current_time)

    if signal["action"] == "BUY" and trend != "BULLISH":
        logger.info(f"Rejected BUY signal - trend is {trend}")
        return None

    if signal["action"] == "SELL" and trend != "BEARISH":
        logger.info(f"Rejected SELL signal - trend is {trend}")
        return None
```

---

## Best Practices

### 1. Timeframe Alignment

- Always use H1 for zone detection (lower TFs = too much noise)
- Always use M30 for entry (confirmation of H1 zones)
- Don't mix timeframes across trading types

### 2. Zone Freshness

- Prefer zones tested < 12 hours ago
- Discard zones older than 72 hours
- Prioritize fresh zones (tested 1-4 times)

### 3. Trend Filter Discipline

- **Always** apply Sniper Gate for commodities
- Don't override trend filter manually
- If trend is NEUTRAL, skip the trade

### 4. End-of-Day Management

- Set reminders 30 minutes before day end
- Don't hold positions overnight (unless specifically planned)
- Close positions in profit first, then losses

---

## Performance Optimization

### Caching Strategy

```python
# Cache H1 zones to avoid repeated calculations
if self._should_refresh_zones(symbol):
    zones = await self._detect_h1_zones(symbol)
    self.zone_cache[symbol] = (zones, datetime.now(UTC))
```

### Parallel Processing

```python
# Analyze multiple symbols in parallel
tasks = [
    self.analyze_symbol(symbol, current_time)
    for symbol in symbols
]

results = await asyncio.gather(*tasks)
```

---

## Monitoring

### Key Metrics

Track these metrics for intray performance:

1. **Zone Quality**: Average zone strength score
2. **Entry Accuracy**: % of signals that reach TP
3. **Trend Filter Effectiveness**: % of filtered signals that would have failed
4. **End-of-Day Slippage**: Pips lost from day-end closure

### Logging

```python
logger.info(
    f"Intraday scan complete: "
    f"{len(signals)} signals, "
    f"{len(filtered_by_trend)} filtered by trend, "
    f"{len(executed)} executed"
)
```

---

## Related Documentation

- [Trading Types Guide](../trading-types-guide.md) - All trading type configurations
- [Multi-Timeframe Guide](../guides/multi-timeframe-guide.md) - MTF analysis patterns
- [Position Management Architecture](../position-management-architecture.md) - Position lifecycle
