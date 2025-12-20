# 📊 Pip Calculation & Position Sizing Guide

The trading bot includes an advanced pip calculator that automatically detects asset classes and provides accurate position sizing based on risk management principles.

## Overview

The `PipCalculator` provides:
- **Automatic Asset Detection**: Regex-based symbol classification
- **Multi-Asset Support**: Different pip values for Forex, Commodities, Crypto
- **Risk-Based Position Sizing**: Calculate volume based on account risk percentage
- **Volume Validation**: Ensure positions stay within broker limits
- **Account Currency Support**: Handle different account currencies

## Asset Classes & Pip Values

### 🌍 Forex Major Pairs
**Symbols**: EURUSD, GBPUSD, USDCHF, AUDUSD, USDCAD, NZDUSD

- **Pip Size**: 0.0001
- **Digits**: 5 decimal places
- **Pip Value**: $10.00 per standard lot (100,000 units)
- **Min Volume**: 0.01 lots (micro lot)
- **Max Volume**: 100.0 lots
- **Volume Step**: 0.01 lots

### 🗾 Forex JPY Pairs
**Symbols**: USDJPY, EURJPY, GBPJPY, AUDJPY

- **Pip Size**: 0.01
- **Digits**: 3 decimal places
- **Pip Value**: $10.00 per standard lot (approximate)
- **Min Volume**: 0.01 lots
- **Max Volume**: 100.0 lots
- **Volume Step**: 0.01 lots

### 🥇 Commodities
**Symbols**: XAUUSD (Gold), XAGUSD (Silver), Oil

- **Pip Size**: 0.1
- **Digits**: 2 decimal places
- **Pip Value**: $10.00 per lot (100 oz for Gold)
- **Min Volume**: 0.1 lots
- **Max Volume**: 50.0 lots
- **Volume Step**: 0.1 lots

### ₿ Cryptocurrency
**Symbols**: BTCUSD, ETHUSD, ADAUSD

- **Pip Size**: 1.0
- **Digits**: 1 decimal place
- **Pip Value**: $1.00 per unit
- **Min Volume**: 0.001 units
- **Max Volume**: 10.0 units
- **Volume Step**: 0.001 units

## CLI Usage

### Get Pip Information

```bash
# Get pip info for any symbol
uv run trading-bot pip info EURUSD
uv run trading-bot pip info XAUUSD
uv run trading-bot pip info BTCUSD
uv run trading-bot pip info USDJPY
```

### Calculate Position Size

```bash
# Calculate position based on risk management
uv run trading-bot pip size SYMBOL -b BALANCE -r RISK% -e ENTRY -s STOP

# Examples:
uv run trading-bot pip size EURUSD -b 10000 -r 1.5 -e 1.0850 -s 1.0820
uv run trading-bot pip size XAUUSD -b 50000 -r 2.0 -e 1985.50 -s 1975.00
uv run trading-bot pip size BTCUSD -b 25000 -r 1.0 -e 42000 -s 41500
```

### Example Outputs

#### Pip Information
```
Pip Information - EURUSD
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property      ┃ Value                                    ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Symbol        │ EURUSD                                   │
│ Asset Class   │ Forex Major                              │
│ Pip Size      │ 0.0001                                   │
│ Pip Value/Lot │ $10.00                                   │
│ Digits        │ 5                                        │
│ Min Volume    │ 0.01                                     │
│ Max Volume    │ 100.0                                    │
│ Volume Step   │ 0.01                                     │
│ Description   │ Major Forex pairs (EURUSD, GBPUSD, etc.) │
└───────────────┴──────────────────────────────────────────┘
```

#### Position Size Calculation
```
Position Size Calculation - EURUSD
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Property        ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Symbol          │ EURUSD      │
│ Asset Class     │ Forex Major │
│ Account Balance │ $10,000.00  │
│ Risk Percentage │ 1.5%        │
│ Risk Amount     │ $150.00     │
│ Entry Price     │ 1.085       │
│ Stop Loss Price │ 1.082       │
│ Stop Loss Pips  │ 30.0        │
│ Pip Value/Lot   │ $10.00      │
│ Position Size   │ 0.500 lots  │
└─────────────────┴─────────────┘
✅ Volume is valid
```

## Programmatic Usage

### Import and Initialize

```python
from trading_bot.utils import get_pip_calculator
from trading_bot.data.models import AssetClass

# Get calculator instance
calculator = get_pip_calculator()
```

### Automatic Asset Detection

```python
# Detect asset class from symbol
asset_class = calculator.detect_asset_class("EURUSD")
print(asset_class)  # AssetClass.FOREX_MAJOR

asset_class = calculator.detect_asset_class("XAUUSD")
print(asset_class)  # AssetClass.COMMODITIES

asset_class = calculator.detect_asset_class("BTCUSD")
print(asset_class)  # AssetClass.CRYPTO
```

### Get Pip Information

```python
# Get pip value info
pip_info = calculator.get_pip_value("EURUSD")
print(f"Pip size: {pip_info.pip_size}")
print(f"Pip value per lot: ${pip_info.pip_value_per_lot}")
print(f"Asset class: {pip_info.asset_class.value}")
```

### Calculate Pips Between Prices

```python
# Calculate pip difference
pips = calculator.calculate_pips_between_prices(
    symbol="EURUSD",
    price1=1.0850,
    price2=1.0820
)
print(f"Pip difference: {pips}")  # 30.0 pips
```

### Position Size Calculation

```python
# Calculate optimal position size
position = calculator.calculate_position_size(
    symbol="EURUSD",
    account_balance=10000.0,
    risk_percent=1.5,
    entry_price=1.0850,
    stop_loss_price=1.0820
)

print(f"Position size: {position.volume} lots")
print(f"Risk amount: ${position.risk_amount}")
print(f"Stop loss: {position.stop_loss_pips} pips")
```

### Volume Validation

```python
# Validate if volume is acceptable
is_valid, reason = calculator.validate_volume("EURUSD", 0.5)
print(f"Valid: {is_valid}, Reason: {reason}")

# Check min/max volumes
min_vol = calculator.get_minimum_volume(AssetClass.FOREX_MAJOR)
max_vol = calculator.get_maximum_volume(AssetClass.FOREX_MAJOR)
print(f"Volume range: {min_vol} - {max_vol} lots")
```

## Position Sizing Formula

The position size is calculated using this risk management formula:

```
Position Size = Risk Amount ÷ (Stop Loss Pips × Pip Value per Lot)
```

### Example Calculation

```
Account Balance: $10,000
Risk Percentage: 1.5%
Risk Amount: $10,000 × 1.5% = $150

Entry Price: 1.0850
Stop Loss: 1.0820
Stop Loss Pips: (1.0850 - 1.0820) ÷ 0.0001 = 30 pips

Pip Value per Lot: $10.00 (for EURUSD)

Position Size = $150 ÷ (30 pips × $10) = $150 ÷ $300 = 0.5 lots
```

## Symbol Pattern Detection

The calculator uses regex patterns to automatically detect asset classes:

### Forex Major Patterns
```python
patterns = [
    r"^(EUR|GBP|AUD|NZD|USD|CHF|CAD)(USD|EUR|GBP|CHF|CAD|AUD|NZD)$",
    r"^(EUR|GBP|AUD|NZD)(USD|CHF|CAD)$",
    r"^USD(CHF|CAD)$"
]
exclusions = [r".*JPY.*"]  # Exclude JPY pairs
```

### Forex JPY Patterns
```python
patterns = [
    r".*(JPY).*",
    r"^(USD|EUR|GBP|AUD|NZD|CHF|CAD)JPY$"
]
```

### Commodities Patterns
```python
patterns = [
    r"^XAU.*",  # Gold
    r"^XAG.*",  # Silver
    r"^XPD.*",  # Palladium
    r"^XPT.*",  # Platinum
    r"^(WTI|BRENT|OIL).*",  # Oil
    r"^(GOLD|SILVER).*"
]
```

### Cryptocurrency Patterns
```python
patterns = [
    r"^BTC.*",
    r"^ETH.*",
    r"^ADA.*",
    r"^LTC.*",
    r"^XRP.*",
    r".*USDT$",
    r".*BUSD$"
]
```

## Risk Management Guidelines

### Conservative Risk (0.5% - 1.0%)
- **New traders** or **volatile markets**
- Smaller position sizes
- More room for drawdown

### Moderate Risk (1.0% - 2.0%)
- **Experienced traders** with **proven strategies**
- Standard institutional risk levels
- Good balance of growth and safety

### Aggressive Risk (2.0% - 5.0%)
- **Very experienced traders** only
- **High-confidence setups**
- Higher potential returns but much higher risk

### Example Risk Scenarios

```bash
# Conservative: 0.5% risk
uv run trading-bot pip size EURUSD -b 10000 -r 0.5 -e 1.0850 -s 1.0820

# Moderate: 1.5% risk
uv run trading-bot pip size EURUSD -b 10000 -r 1.5 -e 1.0850 -s 1.0820

# Aggressive: 3.0% risk
uv run trading-bot pip size EURUSD -b 10000 -r 3.0 -e 1.0850 -s 1.0820
```

## Volume Limits by Asset Class

| Asset Class | Min Volume | Max Volume | Step Size | Reasoning |
|-------------|------------|------------|-----------|-----------|
| Forex Major | 0.01 lots | 100.0 lots | 0.01 | Standard micro/mini/standard lots |
| Forex JPY | 0.01 lots | 100.0 lots | 0.01 | Same as major pairs |
| Commodities | 0.1 lots | 50.0 lots | 0.1 | Higher minimum due to contract size |
| Crypto | 0.001 units | 10.0 units | 0.001 | Fractional units common |

## Integration with Trading Bot

The pip calculator is automatically integrated into the trading bot:

```python
# In trading strategy
position_size = self.pip_calculator.calculate_position_size(
    symbol=symbol,
    account_balance=self.account_balance,
    risk_percent=self.config.risk.max_risk_per_trade_percent,
    entry_price=entry_price,
    stop_loss_price=stop_loss_price
)

# Validate volume
is_valid, reason = self.pip_calculator.validate_volume(symbol, position_size.volume)
if not is_valid:
    logger.warning(f"Invalid volume for {symbol}: {reason}")
    return
```

## Customization

### Adding New Asset Classes

```python
# Add to _pip_configurations
AssetClass.NEW_ASSET: {
    "pip_size": 0.01,
    "digits": 3,
    "lot_size": 10000,
    "description": "New asset class description"
}

# Add to _symbol_patterns
AssetClass.NEW_ASSET: {
    "patterns": [r"^NEW.*"],
    "exclusions": []
}
```

### Custom Pip Values

```python
# Override pip value for specific symbol
pip_info = calculator.get_pip_value("EURUSD")
custom_pip_value = pip_info.pip_value_per_lot * 1.5  # 50% higher pip value
```

## Best Practices

1. **Always Validate Risk**: Never risk more than you can afford to lose
2. **Use Stop Losses**: Every position should have a predetermined stop loss
3. **Consistent Risk**: Use the same risk percentage across all trades
4. **Verify Calculations**: Double-check position sizes before executing
5. **Account for Spreads**: Consider bid-ask spread in your calculations
6. **Test Thoroughly**: Validate calculations with your broker's specifications

## Troubleshooting

### Wrong Asset Class Detection
- Check symbol naming convention
- Add custom patterns if needed
- Manually specify asset class

### Incorrect Pip Values
- Verify with broker specifications
- Consider symbol variations (e.g., EURUSDm vs EURUSD)
- Check if using cent accounts or standard accounts

### Position Size Too Large/Small
- Verify account balance
- Check risk percentage
- Ensure stop loss is reasonable
- Validate minimum volume requirements

### Volume Validation Errors
- Check broker's minimum/maximum volume limits
- Verify step size requirements
- Consider account type (micro, mini, standard)
