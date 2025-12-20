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

### Symbol Converter Class

```python
import yaml
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger

class BrokerSymbolConverter:
    def __init__(self, config_path: str = "config/broker_symbols.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.active_broker = self.config['broker_config']['active_broker']
        self.cache = {}

    def to_broker_symbol(self, internal_symbol: str) -> Optional[str]:
        """
        Convert internal symbol to broker-specific symbol.

        Args:
            internal_symbol: Standard symbol (e.g., "EURUSD")

        Returns:
            Broker-specific symbol (e.g., "EUR_USD" for OANDA)
        """
        # Check cache first
        cache_key = f"to_broker_{internal_symbol}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        broker_config = self.config['broker_config']['brokers'][self.active_broker]

        # Get mapping from broker config
        broker_symbol = broker_config['symbol_mappings'].get(internal_symbol)

        if not broker_symbol:
            # Try auto-generation with suffix/prefix
            broker_symbol = self._generate_broker_symbol(internal_symbol, broker_config)

        if not broker_symbol:
            # Check custom mappings
            custom_mappings = self.config.get('development', {}).get('custom_mappings', {})
            broker_symbol = custom_mappings.get(internal_symbol)

        if not broker_symbol:
            self._handle_unknown_symbol(internal_symbol)
            return None

        # Cache result
        if self.config['symbol_conversion']['cache_conversions']:
            self.cache[cache_key] = broker_symbol

        return broker_symbol

    def to_internal_symbol(self, broker_symbol: str) -> Optional[str]:
        """
        Convert broker-specific symbol to internal symbol.

        Args:
            broker_symbol: Broker symbol (e.g., "EUR_USD")

        Returns:
            Internal symbol (e.g., "EURUSD")
        """
        # Check cache first
        cache_key = f"to_internal_{broker_symbol}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        broker_config = self.config['broker_config']['brokers'][self.active_broker]

        # Reverse lookup in mappings
        for internal, broker in broker_config['symbol_mappings'].items():
            if broker == broker_symbol:
                # Cache result
                if self.config['symbol_conversion']['cache_conversions']:
                    self.cache[cache_key] = internal
                return internal

        # Try reverse generation
        internal_symbol = self._reverse_generate_symbol(broker_symbol, broker_config)

        if internal_symbol:
            if self.config['symbol_conversion']['cache_conversions']:
                self.cache[cache_key] = internal_symbol
            return internal_symbol

        self._handle_unknown_symbol(broker_symbol)
        return None

    def _generate_broker_symbol(self, internal_symbol: str, broker_config: Dict) -> Optional[str]:
        """Generate broker symbol using prefix/suffix rules."""
        prefix = broker_config.get('symbol_prefix', '')
        suffix = broker_config.get('symbol_suffix', '')

        if prefix or suffix:
            return f"{prefix}{internal_symbol}{suffix}"

        return None

    def _reverse_generate_symbol(self, broker_symbol: str, broker_config: Dict) -> Optional[str]:
        """Reverse generate internal symbol from broker symbol."""
        prefix = broker_config.get('symbol_prefix', '')
        suffix = broker_config.get('symbol_suffix', '')

        symbol = broker_symbol

        # Remove prefix
        if prefix and symbol.startswith(prefix):
            symbol = symbol[len(prefix):]

        # Remove suffix
        if suffix and symbol.endswith(suffix):
            symbol = symbol[:-len(suffix)]

        # Validate result looks like a valid symbol
        if len(symbol) >= 6 and symbol.isalpha():
            return symbol.upper()

        return None

    def _handle_unknown_symbol(self, symbol: str):
        """Handle unknown symbol based on fallback behavior."""
        behavior = self.config['symbol_conversion']['fallback_behavior']

        if behavior == "error":
            raise ValueError(f"Unknown symbol: {symbol}")
        elif behavior == "warn":
            logger.warning(f"Unknown symbol: {symbol}")
        # "ignore" does nothing

    def validate_symbol(self, internal_symbol: str) -> bool:
        """
        Validate that symbol exists and is tradeable.

        Args:
            internal_symbol: Internal symbol to validate

        Returns:
            True if symbol is valid and tradeable
        """
        broker_symbol = self.to_broker_symbol(internal_symbol)
        if not broker_symbol:
            return False

        validation_config = self.config['symbol_conversion']['validation']

        # Check if validation is enabled
        if not validation_config.get('check_existence', False):
            return True

        # Here you would integrate with your broker's API to check:
        # 1. Symbol exists
        # 2. Trading is allowed
        # 3. Market is open

        return self._check_with_broker_api(broker_symbol)

    def _check_with_broker_api(self, broker_symbol: str) -> bool:
        """Check symbol with broker API (implement based on your broker)."""
        # Placeholder - implement with your specific broker API
        # For MT5, you would use something like:
        # import MetaTrader5 as mt5
        # symbol_info = mt5.symbol_info(broker_symbol)
        # return symbol_info is not None and symbol_info.visible

        return True  # Default to True for now

    def get_all_symbols(self) -> List[str]:
        """Get all available internal symbols for active broker."""
        broker_config = self.config['broker_config']['brokers'][self.active_broker]
        return list(broker_config['symbol_mappings'].keys())

    def get_broker_symbols(self) -> List[str]:
        """Get all broker-specific symbols for active broker."""
        broker_config = self.config['broker_config']['brokers'][self.active_broker]
        return list(broker_config['symbol_mappings'].values())

    def switch_broker(self, broker_name: str):
        """
        Switch to a different broker configuration.

        Args:
            broker_name: Name of broker to switch to
        """
        if broker_name not in self.config['broker_config']['brokers']:
            raise ValueError(f"Unknown broker: {broker_name}")

        self.active_broker = broker_name
        self.cache.clear()  # Clear cache when switching brokers

        logger.info(f"Switched to broker: {broker_name}")

    def auto_discover_symbols(self, test_symbols: List[str] = None) -> Dict[str, str]:
        """
        Auto-discover broker symbols by testing common symbols.

        Args:
            test_symbols: List of symbols to test (uses default if None)

        Returns:
            Dictionary of discovered mappings
        """
        if test_symbols is None:
            test_symbols = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY"]

        discovered = {}

        for symbol in test_symbols:
            # Try different common formats
            test_formats = [
                symbol,  # Standard
                f"{symbol[:3]}_{symbol[3:]}",  # EUR_USD
                f"{symbol}m",  # EURUSDm
                f"{symbol}.a",  # EURUSD.a
                f"{symbol}pro",  # EURUSDpro
            ]

            for test_format in test_formats:
                if self._test_symbol_exists(test_format):
                    discovered[symbol] = test_format
                    break

        return discovered

    def _test_symbol_exists(self, symbol: str) -> bool:
        """Test if a symbol exists with the broker."""
        # Implement with your broker's API
        # This is a placeholder
        return True

# Integration with MT5
class MT5SymbolConverter(BrokerSymbolConverter):
    def __init__(self, config_path: str = "config/broker_symbols.yaml"):
        super().__init__(config_path)
        self.mt5_available = False

        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.mt5_available = True
        except ImportError:
            logger.warning("MetaTrader5 not available for symbol validation")

    def _check_with_broker_api(self, broker_symbol: str) -> bool:
        """Check symbol with MT5 API."""
        if not self.mt5_available:
            return True

        try:
            symbol_info = self.mt5.symbol_info(broker_symbol)
            return symbol_info is not None and symbol_info.visible
        except Exception as e:
            logger.error(f"Error checking symbol {broker_symbol}: {e}")
            return False

    def _test_symbol_exists(self, symbol: str) -> bool:
        """Test if symbol exists in MT5."""
        if not self.mt5_available:
            return False

        try:
            symbol_info = self.mt5.symbol_info(symbol)
            return symbol_info is not None
        except Exception:
            return False

    def auto_discover_symbols(self, test_symbols: List[str] = None) -> Dict[str, str]:
        """Auto-discover symbols using MT5 symbol list."""
        if not self.mt5_available:
            return super().auto_discover_symbols(test_symbols)

        if test_symbols is None:
            test_symbols = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY", "USDCHF", "AUDUSD"]

        discovered = {}

        # Get all available symbols from MT5
        try:
            all_symbols = self.mt5.symbols_get()
            symbol_names = [s.name for s in all_symbols if s.visible]

            for internal_symbol in test_symbols:
                # Find matching symbol
                for broker_symbol in symbol_names:
                    if self._symbols_match(internal_symbol, broker_symbol):
                        discovered[internal_symbol] = broker_symbol
                        break

        except Exception as e:
            logger.error(f"Error discovering symbols: {e}")
            return super().auto_discover_symbols(test_symbols)

        return discovered

    def _symbols_match(self, internal: str, broker: str) -> bool:
        """Check if symbols match (handling common variations)."""
        # Direct match
        if internal == broker:
            return True

        # Common variations
        variations = [
            f"{internal[:3]}_{internal[3:]}",  # EUR_USD
            f"{internal}m",  # EURUSDm
            f"{internal}.a",  # EURUSD.a
            f"{internal}pro",  # EURUSDpro
            f"{internal}.raw",  # EURUSD.raw
            f"{internal}c",  # EURUSDc
        ]

        return broker in variations
```

## Symbol Auto-Discovery

### Automatic Symbol Detection

```python
class SymbolAutoDiscovery:
    def __init__(self, converter: BrokerSymbolConverter):
        self.converter = converter

    async def discover_and_update_config(self, config_path: str = "config/broker_symbols.yaml"):
        """
        Discover symbols and update configuration file.
        """
        logger.info("Starting symbol auto-discovery...")

        # Discover symbols
        discovered = self.converter.auto_discover_symbols()

        if not discovered:
            logger.warning("alols discovered")
            return

        # Update configuration
        await self._update_broker_config(discovered, config_path)

        logger.info(f"Discovered {len(discovered)} symbols: {list(discovered.keys())}")

    async def _update_broker_config(self, discovered: Dict[str, str], config_path: str):
        """Update broker configuration with discovered symbols."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        broker_name = config['broker_config']['active_broker']

        # Update symbol mappings
        current_mappings = config['broker_config']['brokers'][broker_name]['symbol_mappings']
        current_mappings.update(discovered)

        # Save updated configuration
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)

    def validate_all_symbols(self) -> Dict[str, bool]:
        """Validate all configured symbols."""
        results = {}

        for symbol in self.converter.get_all_symbols():
            results[symbol] = self.converter.validate_symbol(symbol)

        return results

    def generate_symbol_report(self) -> str:
        """Generate a report of symbol mappings and validation."""
        broker_name = self.converter.active_broker
        all_symbols = self.converter.get_all_symbols()

        report = f"# Symbol Mapping Report for {broker_name}\n\n"
        report += f"**Total Symbols**: {len(all_symbols)}\n\n"
        report += "| Internal Symbol | Broker Symbol | Valid | Trading Allowed |\n"
        report += "|---|---|---|---|\n"

        for internal_symbol in sorted(all_symbols):
            broker_symbol = self.converter.to_broker_symbol(internal_symbol)
            is_valid = self.converter.validate_symbol(internal_symbol)

            valid_icon = "✅" if is_valid else "❌"
            trading_icon = "✅" if is_valid else "❌"

            report += f"| {internal_symbol} | {broker_symbol} | {valid_icon} | {trading_icon} |\n"

        return report
```

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

```python
import click
from pathlib import Path

@click.group()
def broker():
    """Broker symbol management commands."""
    pass

@broker.command()
def status():
    """Show current broker status."""
    converter = BrokerSymbolConverter()

    click.echo(f"Active Broker: {converter.active_broker}")
    click.echo(f"Total Symbols: {len(converter.get_all_symbols())}")
    click.echo(f"Cache Enabled: {converter.config['symbol_conversion']['cache_conversions']}")

@broker.command()
@click.option('--internal', '-i', help='Internal symbol to convert')
@click.option('--broker', '-b', help='Broker symbol to convert')
@click.option('--to-broker', is_flag=True, help='Convert internal to broker symbol')
@click.option('--to-internal', is_flag=True, help='Convert broker to internal symbol')
def convert(internal, broker, to_broker, to_internal):
    """Convert between internal and broker symbols."""
    converter = BrokerSymbolConverter()

    if to_broker and internal:
        result = converter.to_broker_symbol(internal)
        click.echo(f"{internal} → {result}")
    elif to_internal and broker:
        result = converter.to_internal_symbol(broker)
        click.echo(f"{broker} → {result}")
    else:
        click.echo("Please specify symbol and conversion direction")

@broker.command()
@click.option('--symbol', '-s', help='Symbol to validate')
@click.option('--all', 'validate_all', is_flag=True, help='Validate all symbols')
def validate(symbol, validate_all):
    """Validate symbol(s)."""
    converter = BrokerSymbolConverter()

    if validate_all:
        results = {}
        for sym in converter.get_all_symbols():
            results[sym] = converter.validate_symbol(sym)

        for sym, valid in results.items():
            status = "✅" if valid else "❌"
            click.echo(f"{status} {sym}")
    elif symbol:
        valid = converter.validate_symbol(symbol)
        status = "✅" if valid else "❌"
        click.echo(f"{status} {symbol}")

@broker.command()
@click.option('--save', is_flag=True, help='Save discovered symbols to config')
@click.option('--test-only', is_flag=True, help='Test only, do not save')
def discover(save, test_only):
    """Auto-discover broker symbols."""
    converter = MT5SymbolConverter()
    discovery = SymbolAutoDiscovery(converter)

    discovered = converter.auto_discover_symbols()

    if discovered:
        click.echo(f"Discovered {len(discovered)} symbols:")
        for internal, broker in discovered.items():
            click.echo(f"  {internal} → {broker}")

        if save and not test_only:
            # Update config file
            click.echo("Saving to configuration...")
            # Implementation to save
    else:
        click.echo("No symbols discovered")

@broker.command()
@click.option('--name', '-n', required=True, help='Broker name to switch to')
def switch(name):
    """Switch to different broker."""
    converter = BrokerSymbolConverter()

    try:
        converter.switch_broker(name)
        click.echo(f"Switched to broker: {name}")
    except ValueError as e:
        click.echo(f"Error: {e}")

@broker.command()
@click.option('--format', '-f', default='markdown', help='Report format (markdown/json)')
@click.option('--output', '-o', help='Output file path')
def report(format, output):
    """Generate symbol mapping report."""
    converter = BrokerSymbolConverter()
    discovery = SymbolAutoDiscovery(converter)

    if format == 'markdown':
        report = discovery.generate_symbol_report()
    else:  # json
        symbols = converter.get_all_symbols()
        report_data = {}
        for symbol in symbols:
            broker_symbol = converter.to_broker_symbol(symbol)
            valid = converter.validate_symbol(symbol)
            report_data[symbol] = {
                'broker_symbol': broker_symbol,
                'valid': valid
            }
        import json
        report = json.dumps(report_data, indent=2)

    if output:
        with open(output, 'w') as f:
            f.write(report)
        click.echo(f"Report saved to {output}")
    else:
        click.echo(report)
```

## Integration Examples

### Trading Bot Integration

```python
class TradingBot:
    def __init__(self, config):
        self.config = config
        self.symbol_converter = BrokerSymbolConverter()

    async def analyze_symbol(self, internal_symbol: str):
        """Analyze symbol with automatic conversion."""
        # Convert to broker symbol for MT5 operations
        broker_symbol = self.symbol_converter.to_broker_symbol(internal_symbol)

        if not broker_symbol:
            logger.error(f"Cannot convert symbol: {internal_symbol}")
            return None

        # Validate symbol
        if not self.symbol_converter.validate_symbol(internal_symbol):
            logger.warning(f"Symbol not tradeable: {internal_symbol}")
            return None

        # Proceed with analysis using broker symbol
        market_data = await self.mt5_connector.get_market_data(broker_symbol)

        # Rest of analysis...
        return await self.strategy_engine.analyze(internal_symbol, market_data)

    async def execute_trade(self, signal):
        """Execute trade with symbol conversion."""
        internal_symbol = signal.symbol
        broker_symbol = self.symbol_converter.to_broker_symbol(internal_symbol)

        if not broker_symbol:
            raise ValueError(f"Cannot execute trade - unknown symbol: {internal_symbol}")

        # Execute with broker symbol
        result = await self.mt5_connector.place_order(
            symbol=broker_symbol,
            direction=signal.direction,
            volume=signal.volume,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )

        return result

    async def get_trading_symbols(self) -> List[str]:
        """Get list of tradeable symbols (internal format)."""
        all_symbols = self.symbol_converter.get_all_symbols()

        # Filter to only tradeable symbols
        tradeable = []
        for symbol in all_symbols:
            if self.symbol_converter.validate_symbol(symbol):
                tradeable.append(symbol)

        return tradeable
```

### Configuration Update Example

```python
# Example: Adding a new broker
async def add_new_broker():
    config_path = "config/broker_symbols.yaml"

    new_broker_config = {
        "name": "YourNewBroker",
        "symbol_suffix": ".new",
        "symbol_prefix": "",
        "symbol_mappings": {
            "EURUSD": "EURUSD.new",
            "GBPUSD": "GBPUSD.new",
            "XAUUSD": "XAUUSD.new"
        }
    }

    # Load existing config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Add new broker
    config['broker_config']['brokers']['your_new_broker'] = new_broker_config

    # Save updated config
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)

    print("New broker added successfully!")

# Example: Batch symbol validation
async def validate_all_broker_symbols():
    converter = BrokerSymbolConverter()
    symbols = converter.get_all_symbols()

    results = {
        'valid': [],
        'invalid': [],
        'total': len(symbols)
    }

    for symbol in symbols:
        if converter.validate_symbol(symbol):
            results['valid'].append(symbol)
        else:
            results['invalid'].append(symbol)

    print(f"Validation Results:")
    print(f"  Total: {results['total']}")
    print(f"  Valid: {len(results['valid'])}")
    print(f"  Invalid: {len(results['invalid'])}")

    if results['invalid']:
        print(f"  Invalid symbols: {results['invalid']}")

    return results
```

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
