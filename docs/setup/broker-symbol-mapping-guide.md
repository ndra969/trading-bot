# Broker Symbol Mapping Guide

This guide covers the broker-specific symbol mapping system that allows the trading bot to work with different brokers that use different symbol naming conventions.

## Table of Contents
1. [Overview](#overview)
2. [Supported Brokers](#supported-brokers)
3. [Configuration](#configuration)
4. [Implementation](#implementation)
5. [Symbol Auto-Discovery](#symbol-auto-discovery)
6. [CLI Commands](#cli-commands)
7. [Integration Examples](#integration-examples)
8. [Troubleshooting](#troubleshooting)

## Overview

Different forex brokers use different symbol naming conventions. For example:
- **Standard**: `EURUSD`
- **OANDA**: `EUR_USD`
- **FxPro**: `EURUSDm`
- **AxiTrader**: `EURUSD.a`

The broker symbol mapping system automatically converts between the bot's internal symbol names and broker-specific symbols, ensuring compatibility across different trading platforms.

### Key Features

✅ **Universal Compatibility**: Works with any broker symbol format
✅ **Automatic Conversion**: Seamless symbol translation in real-time
✅ **Configurable Mappings**: Easy to add new brokers or custom mappings
✅ **Auto-Discovery**: Automatically detect broker symbols
✅ **Fallback Handling**: Graceful handling of unknown symbols
✅ **Performance Optimized**: Cached conversions for speed
✅ **Validation**: Symbol existence and trading availability checks

## Supported Brokers

### Pre-configured Brokers

| Broker | Symbol Format | Example | Suffix/Prefix |
|--------|---------------|---------|---------------|
| **Pepperstone** | Standard | `EURUSD` | None |
| **IC Markets** | Standard | `EURUSD` | None |
| **Exness Standard** | Micro Suffix | `EURUSDm` | `m` suffix |
| **Exness Cent** | Cent Suffix | `EURUSDc` | `c` suffix |
| **Exness Pro** | Standard | `EURUSD` | None |
| **Exness Zero** | Standard | `EURUSD` | None |
| **OANDA** | Underscore | `EUR_USD` | None |
| **FxPro** | Micro Suffix | `EURUSDm` | `m` suffix |
| **AxiTrader** | Dot Suffix | `EURUSD.a` | `.a` suffix |
| **Tickmill** | Pro Suffix | `EURUSDpro` | `pro` suffix |
| **XM** | Standard + Special | `EURUSD`, `GOLD` | Special for metals |
| **FBS** | Standard | `EURUSD` | None |
| **HotForex** | Standard | `EURUSD` | None |
| **InstaForex** | Standard | `EURUSD` | None |
| **OctaFX** | Standard | `EURUSD` | None |
| **RoboForex** | Standard | `EURUSD` | None |

### Exness Account Types

Exness offers different account types with specific symbol formats:

| Account Type | Configuration Key | Symbol Example | Description |
|--------------|------------------|----------------|-------------|
| **Standard** | `exness_standard` | `EURUSDm` | Standard accounts with 'm' suffix |
| **Cent** | `exness_cent` | `EURUSDc` | Cent accounts with 'c' suffix |
| **Pro** | `exness_pro` | `EURUSD` | Professional accounts, no suffix |
| **Zero** | `exness_zero` | `EURUSD` | Zero spread accounts, no suffix |

**Usage Examples:**
```bash
# Switch to Exness Standard account
uv run trading-bot broker switch --name exness_standard

# Switch to Exness Cent account
uv run trading-bot broker switch --name exness_cent

# Convert symbol for different Exness accounts
uv run trading-bot broker convert --symbol EURUSD --to-broker
# Standard: EURUSD → EURUSDm
# Cent: EURUSD → EURUSDc
# Pro/Zero: EURUSD → EURUSD
```

### Special Broker Cases

**XM Broker** - Uses special names for metals:
- `XAUUSD` → `GOLD`
- `XAGUSD` → `SILVER`

### Broker Configuration Structure

```yaml
# config/broker_symbols.yaml
broker_config:
  active_broker: "exness_standard"  # Currently active broker

  brokers:
    exness_standard:
      name: "Exness Standard"
      symbol_suffix: "m"  # Standard accounts use 'm' suffix
      symbol_prefix: ""
      symbol_mappings:
        "EURUSD": "EURUSDm"
        "GBPUSD": "GBPUSDm"
        # ... more mappings

    exness_cent:
      name: "Exness Cent"
      symbol_suffix: "c"  # Cent accounts use 'c' suffix
      symbol_prefix: ""
      symbol_mappings:
        "EURUSD": "EURUSDc"
        "GBPUSD": "GBPUSDc"
        # ... more mappings

    xm:
      name: "XM"
      symbol_suffix: ""
      symbol_prefix: ""
      symbol_mappings:
        "EURUSD": "EURUSD"
        "XAUUSD": "GOLD"  # Special mapping for XM
        "XAGUSD": "SILVER"  # Special mapping for XM
```

## Configuration

### Basic Configuration

```yaml
# Set active broker
broker_config:
  active_broker: "your_broker_name"

# Symbol conversion settings
symbol_conversion:
  auto_convert: true
  fallback_behavior: "warn"  # Options: "error", "warn", "ignore"
  cache_conversions: true

  validation:
    check_existence: true
    check_trading_allowed: true
    check_market_hours: true
```

### Adding a New Broker

```yaml
brokers:
  your_broker:
    name: "Your Broker Name"
    symbol_suffix: "your_suffix"
    symbol_prefix: "your_prefix"
    symbol_mappings:
      "EURUSD": "YourBrokerEURUSD"
      "GBPUSD": "YourBrokerGBPUSD"
      # Add all symbols your broker supports
```

### Custom Symbol Mappings

```yaml
development:
  custom_mappings_enabled: true
  custom_mappings:
    "CUSTOM1": "BROKER_CUSTOM1"
    "CUSTOM2": "BROKER_CUSTOM2"
```

## Implementation

> **Note**: For implementation details, see `src/trading_bot/connectors/symbol_converter.py`

The broker symbol mapping system is implemented through the `BrokerSymbolConverter` class which handles:

- **Symbol Conversion**: Automatic conversion between internal and broker-specific symbols
- **Caching**: Performance optimization through cached conversions
- **Validation**: Symbol existence and trading availability checks
- **Auto-Discovery**: Automatic detection of broker symbols
- **Fallback Handling**: Graceful handling of unknown symbols

### Key Features

1. **Automatic Conversion**: Symbols are automatically converted when trading
2. **Configuration-Based**: All mappings stored in `config/broker_symbols.yaml`
3. **MT5 Integration**: Direct validation through MetaTrader5 API
4. **Performance**: Cached conversions for minimal overhead

## CLI Commands

### Symbol Management Commands

```bash
# Check current broker and symbols
uv run trading-bot broker status
uv run trading-bot broker symbols list

# Switch between different brokers and account types
uv run trading-bot broker switch --name pepperstone
uv run trading-bot broker switch --name oanda
uv run trading-bot broker switch --name exness_standard
uv run trading-bot broker switch --name exness_cent
uv run trading-bot broker switch --name exness_pro
uv run trading-bot broker switch --name xm

# Test symbol conversion for different account types
uv run trading-bot broker convert --symbol EURUSD --to-broker
# With exness_standard: EURUSD → EURUSDm
# With exness_cent: EURUSD → EURUSDc
# With xm: XAUUSD → GOLD

uv run trading-bot broker convert --symbol EURUSDm --to-internal
# Output: EURUSDm → EURUSD

# Validate symbols across different account types
uv run trading-bot broker validate --symbol EURUSD
uv run trading-bot broker validate --all

# List available brokers and account types
uv run trading-bot broker list-brokers

# Auto-discovery with account type detection
uv run trading-bot broker discover --save
uv run trading-bot broker discover --test-only

# Account type specific operations
uv run trading-bot broker detect-account-type
uv run trading-bot broker compare-account-types --broker exness

# Symbol mapping management
uv run trading-bot broker add-mapping --internal CUSTOM1 --broker BROKER_CUSTOM1
uv run trading-bot broker remove-mapping --internal CUSTOM1

# Generate reports with account type information
uv run trading-bot broker report --format markdown --include-account-types
uv run trading-bot broker report --format json --output symbols_report.json
```

### Exness-Specific CLI Commands

```bash
# Quick switch between Exness account types
uv run trading-bot broker exness-standard
uv run trading-bot broker exness-cent
uv run trading-bot broker exness-pro
uv run trading-bot broker exness-zero

# Compare symbol formats across Exness account types
uv run trading-bot broker exness-compare --symbol EURUSD
# Output:
# Standard: EURUSD → EURUSDm
# Cent: EURUSD → EURUSDc
# Pro: EURUSD → EURUSD
# Zero: EURUSD → EURUSD

# Validate Exness account type
uv run trading-bot broker exness-validate-account
```

### CLI Implementation

> **Note**: For CLI implementation details, see `src/trading_bot/cli.py`

The broker management CLI provides commands for switching brokers, converting symbols, validation, and reporting.

## Integration Examples

### Trading Bot Integration

> **Note**: For implementation details, see `src/trading_bot/core/trading_bot.py` and `src/trading_bot/connectors/`

The trading bot automatically integrates symbol conversion when:
- Analyzing symbols (converts to broker symbol for MT5 operations)
- Executing trades (uses broker-specific symbols)
- Validating symbols (checks trading availability)
- Retrieving trading symbols (returns internal format)

## Troubleshooting

### Common Issues

**1. Symbol Not Found**
```python
# Problem: Symbol conversion returns None
# Solution: Check broker configuration and add missing mapping

converter = BrokerSymbolConverter()
symbol = converter.to_broker_symbol("CUSTOM1")
if not symbol:
    print("Add to config/broker_symbols.yaml:")
    print('    "CUSTOM1": "YourBrokerCustom1"')
```

**2. Broker Switch Issues**
```python
# Problem: Error switching brokers
# Solution: Ensure broker exists in configuration

try:
    converter.switch_broker("new_broker")
except ValueError as e:
    print(f"Add broker to config: {e}")
```

**3. Symbol Validation Fails**
```python
# Problem: Valid symbols showing as invalid
# Solution: Check MT5 connection and symbol visibility

converter = MT5SymbolConverter()
if not converter._check_with_broker_api("EURUSD"):
    print("Check MT5 connection and symbol visibility")
```

**4. Performance Issues**
```python
# Problem: Slow symbol conversion
# Solution: Enable caching

# In config/broker_symbols.yaml:
symbol_conversion:
  cache_conversions: true  # Enable caching
```

### Debug Mode

```python
# Enable debug logging for symbol conversion
from loguru import logger

# Test symbol conversion with debug info
converter = BrokerSymbolConverter()

broker_symbol = converter.to_broker_symbol("EURUSD")
print(f"Converted EURUSD → {broker_symbol}")
```

The broker symbol mapping system ensures seamless compatibility across different forex brokers while maintaining the bot's universal symbol standards throughout the codebase.
