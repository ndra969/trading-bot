# Trading Types Configuration Guide

This guide covers the comprehensive trading types system that allows the bot to operate in different trading styles: Scalping, Day Trading, Swing Trading, and Position Trading.

## Table of Contents
1. [Overview](#overview)
2. [Trading Types Comparison](#trading-types-comparison)
3. [Configuration](#configuration)
4. [Implementation](#implementation)
5. [Switching Trading Types](#switching-trading-types)
6. [Performance Optimization](#performance-optimization)
7. [CLI Commands](#cli-commands)

## Overview

The trading types system allows the bot to adapt its strategy, risk management, and timeframe analysis based on different trading styles. Each trading type has optimized parameters for its specific holding duration and market approach.

### Available Trading Types

| Type | Hold Duration | Primary Timeframe | Risk Level | Max Daily Trades |
|------|---------------|-------------------|------------|------------------|
| **Scalping** | 1-240 minutes | M1/M5 | Low (0.2%) | 20 |
| **Day Trading** | 30-1440 minutes | M15/H1 | Medium (0.5%) | 8 |
| **Swing Trading** | 1-7 days | H4/D1 | High (0.8%) | 2 |
| **Position Trading** | 1-4 weeks | D1/W1 | Highest (1.2%) | 1 |

### Key Features

✅ **Adaptive Timeframes**: Each type uses optimal timeframes for analysis
✅ **Dynamic Risk Management**: Risk per trade adjusts based on holding duration
✅ **Optimized Position Management**: Stop losses and targets suited for each style
✅ **Technical Indicator Tuning**: Different RSI/MA parameters per trading type
✅ **Session Awareness**: Preferred trading sessions for each type
✅ **Performance Tracking**: Type-specific performance metrics

## Trading Types Comparison

### 1. Scalping Configuration

**Best for**: High-frequency, quick profit taking
**Market conditions**: Medium to high volatility, tight spreads

```yaml
scalping:
  hold_duration:
    target_minutes: 15        # Quick 15-minute trades

  timeframes:
    primary: "M1"             # 1-minute charts
    analysis: ["M1", "M5", "M15"]

  risk_management:
    risk_per_trade: 0.002     # Low risk (0.2%)
    max_concurrent_positions: 8
    max_daily_trades: 20

  position_management:
    forex_major:
      min_sl_pips: 5          # Tight stops
      breakeven_trigger_pips: 8
      partial_close_levels: [8, 12]

  strategy_weights:
    technical_indicators: 0.27  # Heavy emphasis on technicals
    foundation_sd_zones: 0.40
```

**Pros:**
- Quick profits, multiple opportunities
- Lower individual trade risk
- Active trading experience

**Cons:**
- Requires constant monitoring
- Higher spread costs
- Stressful for beginners

### 2. Day Trading Configuration

**Best for**: Balanced approach, same-day closes
**Market conditions**: Medium volatility, normal spreads

```yaml
day_trading:
  hold_duration:
    target_minutes: 240       # 4-hour average trades

  timeframes:
    primary: "M15"            # 15-minute charts
    analysis: ["M15", "H1", "H4"]

  risk_management:
    risk_per_trade: 0.005     # Standard risk (0.5%)
    max_concurrent_positions: 5
    max_daily_trades: 8

  position_management:
    forex_major:
      min_sl_pips: 15         # Moderate stops
      breakeven_trigger_pips: 15
      partial_close_levels: [20, 40, 60]

  strategy_weights:
    foundation_sd_zones: 0.35  # Balanced approach
    price_action: 0.15
    technical_indicators: 0.18
```

**Pros:**
- No overnight risk
- Good risk/reward balance
- Suitable for part-time traders

**Cons:**
- Requires intraday monitoring
- Limited to daily timeframes
- Can miss longer-term moves

### 3. Swing Trading Configuration

**Best for**: Multi-day trend captures
**Market conditions**: Any volatility, wider spreads acceptable

```yaml
swing_trading:
  hold_duration:
    target_minutes: 4320      # 3-day average trades

  timeframes:
    primary: "H4"             # 4-hour charts
    analysis: ["H4", "D1", "W1"]

  risk_management:
    risk_per_trade: 0.008     # Higher risk (0.8%)
    max_concurrent_positions: 3
    max_daily_trades: 2

  position_management:
    forex_major:
      min_sl_pips: 50         # Wider stops
      breakeven_trigger_pips: 80
      partial_close_levels: [80, 120, 160]

  strategy_weights:
    fibonacci: 0.18           # Emphasis on Fib levels
    breakout_retest: 0.15
    market_structure: 0.15
```

**Pros:**
- Captures larger moves
- Less time-intensive
- Better risk/reward ratios

**Cons:**
- Overnight/weekend risk
- Fewer trading opportunities
- Requires patience

### 4. Position Trading Configuration

**Best for**: Long-term trend following
**Market conditions**: Any conditions, focuses on major moves

```yaml
position_trading:
  hold_duration:
    target_minutes: 20160     # 2-week average trades

  timeframes:
    primary: "D1"             # Daily charts
    analysis: ["D1", "W1", "MN1"]

  risk_management:
    risk_per_trade: 0.012     # Highest risk (1.2%)
    max_concurrent_positions: 2
    max_daily_trades: 1

  position_management:
    forex_major:
      min_sl_pips: 150        # Very wide stops
      breakeven_trigger_pips: 200
      partial_close_levels: [200, 300, 400]

  strategy_weights:
    fibonacci: 0.25           # Heavy Fib emphasis
    breakout_retest: 0.20
    market_structure: 0.20
    rsi_analysis: 0.00        # Technical indicators less relevant
```

**Pros:**
- Captures major trends
- Minimal time commitment
- Best risk/reward potential

**Cons:**
- Highest individual risk
- Very few opportunities
- Requires strong conviction

## Configuration

### Basic Trading Type Setup

```yaml
# config/trading_types.yaml
trading_types:
  active_type: "day_trading"  # Current active type

  types:
    day_trading:
      # ... configuration as shown above
```

### Dynamic Type Switching

```yaml
# Switch based on market conditions
dynamic_switching:
  enabled: true

  conditions:
    low_volatility:
      switch_to: "swing_trading"
      volatility_threshold: 0.8

    high_volatility:
      switch_to: "scalping"
      volatility_threshold: 2.0

    news_events:
      switch_to: "position_trading"
      avoid_duration_hours: 2
```

## Implementation

> **Note**: For implementation details, see `src/trading_bot/core/trading_type_manager.py`

The trading type system manages different trading styles through:

1. **TradingTypeManager**: Handles switching and configuration
2. **Type-Aware Strategy Engine**: Applies type-specific weights and timeframes
3. **Dynamic Risk Adjustment**: Risk per trade scales with trading type
4. **Position Duration Management**: Automatic close based on holding period limits

## Switching Trading Types

### Manual Switching

```bash
# CLI commands for switching trading types
uv run trading-bot type switch --type scalping
uv run trading-bot type switch --type day_trading
uv run trading-bot type switch --type swing_trading
uv run trading-bot type switch --type position_trading

# Check current type
uv run trading-bot type status

# Compare types
uv run trading-bot type compare --types scalping,day_trading
```

### Automatic Switching (Optional)

> **Note**: For implementation details, see `src/trading_bot/core/dynamic_trading_type_manager.py`

Automatic switching evaluates market conditions (volatility, liquidity, session) and suggests optimal trading type:
- **High volatility + High liquidity**: Scalping
- **Medium volatility + Normal session**: Day trading
- **Low volatility or Poor liquidity**: Swing trading

## Performance Optimization

### Type-Specific Performance Tracking

> **Note**: For implementation details, see `src/trading_bot/core/performance_tracker.py`

Performance tracking metrics by trading type:
- Win rate and profit factor
- Average hold time
- Maximum favorable excursion (MFE)
- Maximum adverse excursion (MAE)
- Risk-adjusted returns comparison

This helps identify which trading type performs best for your account and market conditions.

## CLI Commands

### Trading Type Management

```bash
# View current trading type status
uv run trading-bot type status

# Switch trading types
uv run trading-bot type switch --type scalping
uv run trading-bot type switch --type day_trading
uv run trading-bot type switch --type swing_trading
uv run trading-bot type switch --type position_trading

# View type configuration
uv run trading-bot type config --type scalping
uv run trading-bot type config --current

# Compare trading types
uv run trading-bot type compare --types scalping,day_trading
uv run trading-bot type compare --all

# Performance by type
uv run trading-bot type performance --type scalping
uv run trading-bot type performance --all

# Test type configuration
uv run trading-bot type test --type scalping --symbol EURUSD
uv run trading-bot type validate --all

# Type-specific analysis
uv run trading-bot type analyze --symbol EURUSD --type day_trading
uv run trading-bot type optimize --type swing_trading --days 30
```

### Advanced Type Management

```bash
# Auto-switching (experimental)
uv run trading-bot type auto-switch --enable
uv run trading-bot type auto-switch --disable
uv run trading-bot type auto-switch --status

# Market condition analysis
uv run trading-bot type market-conditions --recommend
uv run trading-bot type volatility-analysis

# Type-specific backtesting
uv run trading-bot type backtest --type scalping --period 30d
uv run trading-bot type backtest --all --period 90d --compare

# Configuration management
uv run trading-bot type export-config --type scalping --output scalping_config.yaml
uv run trading-bot type import-config --file custom_day_trading.yaml
```

## Summary

The trading types system provides:

✅ **4 Complete Trading Styles**: Scalping, Day Trading, Swing Trading, Position Trading
✅ **Adaptive Parameters**: Risk, timeframes, and strategy weights per type
✅ **Dynamic Switching**: Manual or automatic type switching
✅ **Performance Tracking**: Type-specific performance metrics
✅ **Session Awareness**: Optimal trading sessions per type
✅ **Market Condition Matching**: Type recommendations based on volatility/liquidity

**Quick Start:**
```bash
# Set up day trading (recommended for beginners)
uv run trading-bot type switch --type day_trading

# Check configuration
uv run trading-bot type status

# Start trading with current type
uv run trading-bot start --config production
```

Each trading type is optimized for its specific market approach, ensuring the bot performs optimally regardless of your preferred trading style.
