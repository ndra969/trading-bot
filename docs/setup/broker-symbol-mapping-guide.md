# Broker Symbol Mapping Guide

Configure symbol mapping for different brokers.

## Why Symbol Mapping?

Different brokers use different symbol naming:

| Broker | EURUSD Symbol |
|--------|---------------|
| Standard | `EURUSD` |
| Exness Standard | `EURUSDm` |
| Exness Cent | `EURUSDc` |
| OANDA | `EUR_USD` |
| AxiTrader | `EURUSD.a` |
| FxPro | `EURUSDm` |

The bot uses **internal symbols** (e.g., `EURUSD`) and automatically converts to **broker-specific symbols**.

## Configuration

`config/symbol_mapping.yaml`:

```yaml
# Active broker
active_broker: exness_standard

# Broker mappings
brokers:
  exness_standard:
    suffix: "m"           # EURUSD → EURUSDm
    special_mappings: {}

  exness_cent:
    suffix: "c"           # EURUSD → EURUSDc
    special_mappings: {}

  oanda:
    format: "underscore"  # EURUSD → EUR_USD

  xm:
    suffix: ""
    special_mappings:
      XAUUSD: GOLD        # Gold uses special name
      XAGUSD: SILVER

  axitrader:
    suffix: ".a"          # EURUSD → EURUSD.a
```

## Supported Brokers

Pre-configured brokers:

- Exness (Standard, Cent, Pro, Zero)
- IC Markets
- Pepperstone
- OANDA
- FxPro
- AxiTrader
- Tickmill
- XM
- FBS
- HotForex
- InstaForex
- OctaFX
- RoboForex

## Usage

> **Note**: All `broker` CLI commands are 📋 planned. Currently configure via `config/symbol_mapping.yaml`.

### Switch Broker (Currently)

Edit `config/symbol_mapping.yaml`:
```yaml
active_broker: exness_standard
```

### Planned CLI Commands

```bash
# 📋 Not yet implemented:
uv run trading-bot broker switch --name exness_standard
uv run trading-bot broker status
uv run trading-bot broker convert --symbol EURUSD --to-broker
uv run trading-bot broker discover
```

## Adding a New Broker

1. Edit `config/symbol_mapping.yaml`:

```yaml
brokers:
  your_broker:
    suffix: ".x"          # Or prefix, or special format
    special_mappings:
      XAUUSD: GOLD
      XAGUSD: SILVER
```

2. Set as active:

```yaml
active_broker: your_broker
```

3. Test: Start bot in dry-run mode and verify symbol conversion in logs.

## Symbol Conversion Examples

| Internal | Exness Std | Exness Cent | OANDA | AxiTrader |
|----------|-----------|-------------|-------|-----------|
| EURUSD | EURUSDm | EURUSDc | EUR_USD | EURUSD.a |
| USDJPY | USDJPYm | USDJPYc | USD_JPY | USDJPY.a |
| XAUUSD | XAUUSDm | XAUUSDc | XAU_USD | XAUUSD.a |
| BTCUSD | BTCUSDm | BTCUSDc | BTC_USD | BTCUSD.a |

## Special Cases

### XM Broker

XM uses special names for metals:
- `XAUUSD` → `GOLD`
- `XAGUSD` → `SILVER`

### Crypto Symbols

Some brokers add prefix/suffix:
- Exness: `BTCUSDm`
- IC Markets: `BTCUSD`
- AxiTrader: `BTCUSD.a`

## Troubleshooting

### Symbol Not Found

**Error**: `Symbol EURUSDm not found in Market Watch`

**Solutions**:
1. Add symbol to MT5 Market Watch manually
2. Check broker uses correct suffix
3. Run auto-discovery

### Wrong Symbol Used

**Symptom**: Bot tries to trade symbol that doesn't exist

**Solutions**:
1. Verify `active_broker` in config
2. Re-run `broker switch` command
3. Check symbol_mapping.yaml has correct mappings

### Cannot Convert Symbol

Check `config/symbol_mapping.yaml` for correct `active_broker` setting. Test via dry-run mode and verify symbol conversion in logs.

## Related Documentation

- [Configuration Guide](configuration-guide.md) - General config
- [Asset Configuration](asset-configuration-guide.md) - Per-asset settings
- [MT5 Connection](mt5-connection-guide.md) - MT5 integration
