# 🕐 Market Hours Validation Guide

The trading bot includes a comprehensive market hours validation system that ensures trades are only executed during appropriate market sessions for each asset class.

## Overview

The `MarketHoursValidator` provides intelligent trading session management with:
- **Multi-Asset Support**: Different schedules for Forex, Commodities, and Crypto
- **Timezone Awareness**: All times managed in UTC with proper conversion
- **Holiday Support**: US market holidays for commodities trading
- **Buffer Periods**: Configurable buffers to avoid spread widening during session transitions
- **Real-Time Status**: Current market status with next open/close predictions

## Asset Classes & Sessions

### 🌍 Forex Major Pairs (24/5 Market)
**Symbols**: EURUSD, GBPUSD, USDCHF, AUDUSD, USDCAD, NZDUSD

**Trading Sessions** (UTC):
- **Sydney**: 22:00 - 07:00
- **Tokyo**: 00:00 - 09:00
- **London**: 08:00 - 17:00
- **New York**: 13:00 - 22:00

**Weekend Break**: Saturday 22:00 - Sunday 22:00 UTC
**Buffer**: 5 minutes from session start/end
**Holidays**: None (Forex markets typically don't observe holidays)

### 🗾 Forex JPY Pairs
**Symbols**: USDJPY, EURJPY, GBPJPY, AUDJPY

**Trading Sessions** (UTC):
- **Tokyo** (main): 00:00 - 09:00
- **London**: 08:00 - 17:00
- **New York**: 13:00 - 22:00

**Weekend Break**: Saturday 22:00 - Sunday 22:00 UTC
**Buffer**: 5 minutes from session start/end

### 🥇 Commodities
**Symbols**: XAUUSD, XAGUSD, Oil, etc.

**Trading Sessions** (UTC):
- **Electronic Trading**: 01:00 - 21:00 (23 hours)

**Weekend Break**: Friday 21:00 - Monday 01:00 UTC
**Buffer**: 10 minutes (larger buffer due to volatility)
**Holidays**: US Federal Holidays
- New Year's Day
- Martin Luther King Jr. Day
- Presidents Day
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving
- Christmas Day

### ₿ Cryptocurrency (24/7 Market)
**Symbols**: BTCUSD, ETHUSD, etc.

**Trading Sessions** (UTC):
- **Continuous**: 00:00 - 23:59 (24/7)

**Weekend Break**: None
**Buffer**: 1 minute (minimal buffer)
**Holidays**: None

## CLI Usage

### Check Market Hours

```bash
# Check different asset classes
uv run trading-bot market hours --asset forex_major
uv run trading-bot market hours --asset forex_jpy
uv run trading-bot market hours --asset commodities
uv run trading-bot market hours --asset crypto
```

### Example Output

```
Market Hours - Forex Major
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property       ┃ Value                     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Status         │ Open                      │
│ Timezone       │ UTC                       │
│ 24/7 Market    │ No                        │
│ Buffer Minutes │ 5                         │
│ Next Close     │ 2025-10-05T22:00:00+00:00 │
└────────────────┴───────────────────────────┘

Trading Sessions
┏━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ Start ┃ End   ┃ Timezone ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ 22:00 │ 07:00 │ UTC      │
│ 00:00 │ 09:00 │ UTC      │
│ 08:00 │ 17:00 │ UTC      │
│ 13:00 │ 22:00 │ UTC      │
└───────┴───────┴──────────┘
```

## Programmatic Usage

### Import and Initialize

```python
from trading_bot.utils import get_market_validator, MarketStatus
from trading_bot.data.models import AssetClass
from datetime import datetime

# Get validator instance
validator = get_market_validator()
```

### Check Market Status

```python
# Check if market is open now
is_open = validator.is_market_open(AssetClass.FOREX_MAJOR)

# Get detailed status
status = validator.get_market_status(AssetClass.FOREX_MAJOR)
print(f"Market status: {status.value}")  # open, closed, weekend, holiday

# Check specific time
specific_time = datetime(2025, 10, 7, 14, 30)  # Monday 14:30 UTC
is_open_then = validator.is_market_open(AssetClass.FOREX_MAJOR, specific_time)
```

### Get Next Open/Close Times

```python
# Get next market open time
next_open = validator.get_next_market_open(AssetClass.COMMODITIES)
if next_open:
    print(f"Next open: {next_open}")

# Get next market close time
next_close = validator.get_next_market_close(AssetClass.FOREX_MAJOR)
if next_close:
    print(f"Next close: {next_close}")
```

### Validate Trading Time

```python
# Get validation with detailed reason
is_valid, reason = validator.validate_trading_time(AssetClass.FOREX_MAJOR)
print(f"Can trade: {is_valid}")
print(f"Reason: {reason}")
```

### Get Complete Summary

```python
# Get comprehensive market information
summary = validator.get_trading_hours_summary(AssetClass.FOREX_MAJOR)
print(f"Current Status: {summary['current_status']}")
print(f"24/7 Market: {summary['is_24_7']}")
print(f"Sessions: {summary['sessions']}")
```

## Market Status Types

| Status | Description | Trading Allowed |
|--------|-------------|-----------------|
| `OPEN` | Market is currently open | ✅ Yes |
| `CLOSED` | Market is closed during normal hours | ❌ No |
| `WEEKEND` | Weekend break | ❌ No |
| `HOLIDAY` | Market holiday | ❌ No |
| `PRE_MARKET` | Before market opens | ❌ No |
| `POST_MARKET` | After market closes | ❌ No |

## Buffer Periods

Buffer periods prevent trading too close to session transitions when spreads typically widen:

- **Forex**: 5 minutes buffer
- **Commodities**: 10 minutes buffer (higher volatility)
- **Crypto**: 1 minute buffer (continuous market)

### Example with Buffer

```
London Session: 08:00 - 17:00 UTC
With 5-minute buffer: 08:05 - 16:55 UTC (actual trading window)
```

## Integration with Trading Bot

The market hours validator is automatically integrated into the trading bot:

```python
# In trading cycle
if not self.market_validator.is_market_open(asset_class):
    logger.debug(f"Market closed for {symbol}, skipping analysis")
    return

# Before placing trades
is_valid, reason = self.market_validator.validate_trading_time(asset_class)
if not is_valid:
    logger.warning(f"Cannot trade {symbol}: {reason}")
    return
```

## Configuration

Market hours can be customized by modifying the `MarketHours` configurations in `market_hours.py`:

```python
# Example: Custom commodities hours
commodities = MarketHours(
    asset_class=AssetClass.COMMODITIES,
    sessions=[
        TradingSession(time(1, 0), time(21, 0), "UTC"),
    ],
    timezone="UTC",
    weekend_days=[5, 6],  # Saturday, Sunday
    holidays=["2025-12-25"],  # Christmas
    buffer_minutes=15  # Custom buffer
)
```

## Best Practices

1. **Always Validate**: Check market hours before any trading operation
2. **Use Buffers**: Respect buffer periods to avoid poor execution
3. **Monitor Holidays**: Be aware of upcoming holidays for commodities
4. **Test Thoroughly**: Verify market hours logic with your broker's schedule
5. **Handle Edge Cases**: Consider what happens during daylight saving time transitions

## Troubleshooting

### Market Shows Closed When It Should Be Open
- Check timezone configuration
- Verify system time is accurate
- Compare with broker's trading hours
- Consider daylight saving time effects

### Wrong Holiday Detection
- Update holiday list in configuration
- Check if broker observes different holidays
- Consider regional variations

### Buffer Too Restrictive
- Adjust buffer minutes in configuration
- Monitor spread behavior during session transitions
- Consider different buffers for different symbols
