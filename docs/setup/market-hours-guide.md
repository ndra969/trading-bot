# Market Hours Guide

Trading hours validation for different asset classes.

## Trading Sessions

### Forex Major Pairs (24/5)

**Symbols**: EURUSD, GBPUSD, USDCHF, AUDUSD, USDCAD, NZDUSD

| Session | UTC Time |
|---------|----------|
| Sydney | 22:00 - 07:00 |
| Tokyo | 00:00 - 09:00 |
| London | 08:00 - 17:00 |
| New York | 13:00 - 22:00 |

**Weekend**: Closed Saturday 22:00 - Sunday 22:00 UTC

### Forex JPY Pairs

**Symbols**: USDJPY, EURJPY, GBPJPY, AUDJPY

Sessions same as Forex Major, but **Tokyo session preferred** for best liquidity.

### Commodities (Gold, Silver)

**Symbols**: XAUUSD, XAGUSD

| Trading | UTC Time |
|---------|----------|
| Electronic | 01:00 - 21:00 (23 hours) |
| Best Liquidity | London + NY overlap (13:00 - 17:00 UTC) |

**Weekend**: Closed Friday 21:00 - Monday 01:00 UTC

**Holidays**: US Federal Holidays observed
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

### Crypto (24/7)

**Symbols**: BTCUSD, ETHUSD

**Trading**: 24/7, no holidays

## Best Trading Times

| Pair | Best Session (UTC) | Reason |
|------|-------------------|--------|
| EURUSD | London (08:00-17:00) | Highest liquidity |
| GBPUSD | London (08:00-17:00) | Native session |
| USDJPY | Tokyo + London overlap | Asian + EU activity |
| AUDUSD | Sydney + Tokyo | Asian session |
| XAUUSD | London + NY overlap | Maximum activity |

## Buffer Periods

To avoid spread widening, the bot uses buffer periods:

| Asset Class | Buffer |
|-------------|--------|
| Forex | 5 minutes |
| Commodities | 10 minutes |
| Crypto | 0 (24/7) |

**Behavior**: No new trades opened within buffer of session start/end.

## Configuration

`config/market_hours.yaml`:

```yaml
forex_major:
  sessions:
    sydney: { open: "22:00", close: "07:00" }
    tokyo: { open: "00:00", close: "09:00" }
    london: { open: "08:00", close: "17:00" }
    new_york: { open: "13:00", close: "22:00" }
  buffer_minutes: 5
  weekend_close: "Saturday 22:00 UTC"

commodities:
  sessions:
    electronic: { open: "01:00", close: "21:00" }
  buffer_minutes: 10
  holidays_enabled: true

crypto:
  sessions: "24/7"
  buffer_minutes: 0
```

## Implementation

The bot validates market hours before:
1. Generating signals
2. Opening positions
3. Modifying existing positions

```python
# Check if symbol is tradeable now
is_tradeable = await market_hours.is_market_open(
    symbol="EURUSD",
    current_time=datetime.now(UTC)
)

if not is_tradeable:
    logger.info(f"Market closed for {symbol}, skipping")
    return
```

## CLI Commands

> **Note**: All `market` CLI commands are 📋 planned. Currently market hours validation runs automatically inside the bot.

```bash
# 📋 Planned (not yet implemented):
uv run trading-bot market status --symbol EURUSD
uv run trading-bot market next --symbol XAUUSD
uv run trading-bot market list
```

**Current**: Market hours validation is automatic during bot operation. Check logs for status.

## Common Issues

### No Trades Despite Open Market

**Check**:
1. Is symbol in buffer period?
2. Is it weekend?
3. Is it a holiday (commodities)?

### Holiday Calendar Outdated

Holiday calendar updates yearly. Check `config/holidays.yaml`.

## Related Documentation

- [Configuration Guide](configuration-guide.md) - General config
- [Asset Configuration](asset-configuration-guide.md) - Asset settings
- [Trading Types Guide](../trading/trading-types-guide.md) - Trading types
