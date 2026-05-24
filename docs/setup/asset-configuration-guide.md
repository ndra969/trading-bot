# Asset Configuration Guide

Configure asset-specific trading parameters for Forex, Commodities, and Crypto.

## Asset Classes

| Class | Pip Value | Min SL | Breakeven | Examples |
|-------|-----------|--------|-----------|----------|
| **Forex Major** | 0.0001 | 15 pips | +15 pips | EURUSD, GBPUSD |
| **Forex JPY** | 0.01 | 150 pips | +150 pips | USDJPY, EURJPY |
| **Commodities** | 0.1 | 300 pips | +500 pips | XAUUSD, XAGUSD |
| **Crypto** | 1.0 | $500 | +$1000 | BTCUSD, ETHUSD |

## Configuration File

`config/trading_parameters.yaml`:

```yaml
forex_major:
  pip_value: 0.0001
  min_sl_pips: 15
  breakeven_pips: 15
  trailing_pips: 10

forex_jpy:
  pip_value: 0.01
  min_sl_pips: 150
  breakeven_pips: 150
  trailing_pips: 100

commodities:
  pip_value: 0.1
  min_sl_pips: 300
  breakeven_pips: 500
  trailing_pips: 300

crypto:
  pip_value: 1.0
  min_sl_pips: 500
  breakeven_pips: 1000
  trailing_pips: 500
```

## Position Sizing Formula

```
Volume = (Account Balance × Risk %) / (SL Distance × Pip Value per Lot)
```

**Example** (EURUSD, $10K account, 1% risk, 30 pip SL):
```
Volume = (10000 × 0.01) / (30 × 1) = 0.33 lots
```

## Automation Settings

### Breakeven
Moves SL to entry + buffer when in profit:
- **Forex**: 70% of SL distance → SL to entry + 2 pips
- **Commodities**: 50% of SL distance → SL to entry + 50 pips

### Trailing Stop
Trails SL as price moves favorably:
- **Forex**: Start at +30 pips, trail by 10 pips
- **Commodities**: Start at +500 pips, trail by 200 pips

## Trading Hours

| Market | Open (UTC) | Close (UTC) |
|--------|------------|-------------|
| Sydney | 21:00 | 06:00 |
| Tokyo | 23:00 | 08:00 |
| London | 08:00 | 17:00 |
| New York | 13:00 | 22:00 |
| Crypto | 00:00 | 24:00 (7 days) |

## Verification

```bash
# ✅ Available: Validate config
uv run trading-bot config validate

# 📋 Planned: symbol info CLI
# uv run trading-bot symbol info --symbol EURUSD
```

Currently: Test asset config via dry-run and inspect position sizing in logs.

## Related Docs

- [Broker Symbol Mapping Guide](broker-symbol-mapping-guide.md)
- [Market Hours Guide](market-hours-guide.md)
- [Risk Management Guide](risk-management-guide.md)
