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

### Trading Type Manager

```python
import yaml
from typing import Dict, Optional
from enum import Enum
from datetime import datetime, timedelta

class TradingType(Enum):
    SCALPING = "scalping"
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    POSITION_TRADING = "position_trading"

class TradingTypeManager:
    def __init__(self, config_path: str = "config/trading_types.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.current_type = TradingType(self.config['trading_types']['active_type'])
        self.type_configs = self.config['trading_types']['types']

    def get_current_config(self) -> Dict:
        """Get configuration for current trading type."""
        return self.type_configs[self.current_type.value]

    def switch_trading_type(self, new_type: TradingType) -> bool:
        """Switch to a different trading type."""
        if new_type.value not in self.type_configs:
            return False

        old_type = self.current_type
        self.current_type = new_type

        # Update configuration file
        self.config['trading_types']['active_type'] = new_type.value
        self._save_config()

        print(f"Switched trading type: {old_type.value} → {new_type.value}")
        return True

    def get_timeframes(self) -> Dict[str, str]:
        """Get timeframes for current trading type."""
        config = self.get_current_config()
        return config['timeframes']

    def get_risk_parameters(self) -> Dict:
        """Get risk management parameters for current trading type."""
        config = self.get_current_config()
        return config['risk_management']

    def get_position_parameters(self, asset_class: str) -> Dict:
        """Get position management parameters for current trading type and asset class."""
        config = self.get_current_config()
        return config['position_management'].get(asset_class, {})

    def get_strategy_weights(self) -> Dict[str, float]:
        """Get strategy weights for current trading type."""
        config = self.get_current_config()
        return config['strategy_weights']

    def is_trade_allowed(self, symbol: str) -> bool:
        """Check if new trade is allowed based on current type limits."""
        config = self.get_current_config()
        risk_config = config['risk_management']

        # Check concurrent positions
        active_positions = self.get_active_positions_count(symbol)
        if active_positions >= risk_config['max_concurrent_positions']:
            return False

        # Check daily trade limit
        daily_trades = self.get_daily_trades_count()
        if daily_trades >= risk_config['max_daily_trades']:
            return False

        # Check session preferences
        if not self.is_preferred_session():
            return False

        return True

    def should_close_position(self, position) -> bool:
        """Check if position should be closed based on trading type duration limits."""
        config = self.get_current_config()
        hold_duration = config['hold_duration']

        position_age_minutes = (datetime.now() - position.open_time).total_seconds() / 60

        # Force close if exceeding max duration
        if position_age_minutes > hold_duration['max_minutes']:
            return True

        # Suggest close if past target duration and profitable
        if (position_age_minutes > hold_duration['target_minutes'] and
            position.unrealized_profit > 0):
            return True

        return False

    def get_optimal_lot_size(self, symbol: str, account_balance: float) -> float:
        """Calculate optimal lot size based on trading type risk parameters."""
        config = self.get_current_config()
        risk_per_trade = config['risk_management']['risk_per_trade']

        # Get position parameters for asset class
        asset_class = self.get_asset_class(symbol)
        position_params = self.get_position_parameters(asset_class)

        # Calculate lot size based on stop loss distance
        stop_loss_pips = position_params.get('min_sl_pips', 20)
        pip_value = self.get_pip_value(symbol)

        # Risk amount in account currency
        risk_amount = account_balance * risk_per_trade

        # Calculate lot size
        lot_size = risk_amount / (stop_loss_pips * pip_value)

        return round(lot_size, 2)

    def _save_config(self):
        """Save updated configuration to file."""
        with open("config/trading_types.yaml", 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)

# Integration with main trading system
class EnhancedTradingBot:
    def __init__(self, config):
        self.config = config
        self.trading_type_manager = TradingTypeManager()
        self.setup_trading_type()

    def setup_trading_type(self):
        """Configure bot based on current trading type."""
        current_config = self.trading_type_manager.get_current_config()

        # Update timeframes
        self.primary_timeframe = current_config['timeframes']['primary']
        self.analysis_timeframes = current_config['timeframes']['analysis']

        # Update risk parameters
        risk_params = current_config['risk_management']
        self.risk_per_trade = risk_params['risk_per_trade']
        self.max_concurrent_positions = risk_params['max_concurrent_positions']

        # Update strategy weights
        self.strategy_weights = current_config['strategy_weights']

        print(f"✅ Configured for {self.trading_type_manager.current_type.value}")
        print(f"📊 Primary timeframe: {self.primary_timeframe}")
        print(f"💰 Risk per trade: {self.risk_per_trade:.1%}")

    async def analyze_symbol(self, symbol: str):
        """Analyze symbol with trading type considerations."""
        # Check if trade is allowed for current type
        if not self.trading_type_manager.is_trade_allowed(symbol):
            return None

        # Get timeframes for current trading type
        timeframes = self.trading_type_manager.get_timeframes()

        # Perform analysis using type-specific timeframes
        signal = await self.strategy_engine.analyze_with_timeframes(
            symbol,
            timeframes['analysis']
        )

        if signal:
            # Apply trading type specific weights
            signal.apply_weights(self.strategy_weights)

            # Check confidence threshold for current type
            min_confidence = self.get_min_confidence_for_type()
            if signal.confidence >= min_confidence:
                return signal

        return None

    async def manage_positions(self):
        """Manage positions with trading type duration limits."""
        active_positions = await self.get_active_positions()

        for position in active_positions:
            # Check if position should be closed based on trading type
            if self.trading_type_manager.should_close_position(position):
                await self.close_position(position, reason="Trading type duration limit")

            # Apply trading type specific position management
            await self.apply_type_specific_management(position)
```

### Strategy Integration

```python
class TypeAwareStrategyEngine:
    def __init__(self, trading_type_manager: TradingTypeManager):
        self.trading_type_manager = trading_type_manager

    async def analyze_with_type_optimization(self, symbol: str):
        """Analyze symbol with trading type optimizations."""

        # Get type-specific configuration
        config = self.trading_type_manager.get_current_config()
        timeframes = config['timeframes']
        weights = config['strategy_weights']

        signal = EnhancedTradingSignal(symbol=symbol)

        # 1. Foundation analysis (always required)
        sd_zones = await self.analyze_supply_demand_zones(
            symbol,
            timeframes['primary']
        )

        if not sd_zones:
            return None

        signal.add_foundation_score(sd_zones, weights['foundation_sd_zones'])

        # 2. Apply enhancement layers based on trading type weights
        if weights.get('price_action', 0) > 0:
            pa_score = await self.analyze_price_action(symbol, timeframes['primary'])
            signal.add_enhancement_score('price_action', pa_score, weights['price_action'])

        if weights.get('technical_indicators', 0) > 0:
            tech_score = await self.analyze_technical_indicators(
                symbol,
                timeframes['analysis'],
                config['technical_indicators']
            )
            signal.add_enhancement_score('technical', tech_score, weights['technical_indicators'])

        # 3. Calculate final confidence
        signal.calculate_final_confidence()

        # 4. Check trading type specific requirements
        type_requirements = self.get_type_requirements()
        if signal.meets_requirements(type_requirements):
            return signal

        return None

    def get_type_requirements(self) -> Dict:
        """Get signal requirements for current trading type."""
        # Implementation based on trading type specific requirements
        pass
```

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

```python
class DynamicTradingTypeManager:
    def __init__(self, trading_type_manager: TradingTypeManager):
        self.ttm = trading_type_manager
        self.auto_switch_enabled = False

    async def evaluate_type_switch(self):
        """Evaluate if trading type should be switched based on market conditions."""
        if not self.auto_switch_enabled:
            return

        # Analyze current market conditions
        volatility = await self.get_current_volatility()
        liquidity = await self.get_current_liquidity()
        session = self.get_current_session()

        # Determine optimal trading type
        optimal_type = self.determine_optimal_type(volatility, liquidity, session)

        if optimal_type != self.ttm.current_type:
            await self.request_type_switch(optimal_type)

    def determine_optimal_type(self, volatility: float, liquidity: float, session: str) -> TradingType:
        """Determine optimal trading type based on market conditions."""

        # High volatility + high liquidity = good for scalping
        if volatility > 2.0 and liquidity > 0.8 and session in ['london', 'new_york']:
            return TradingType.SCALPING

        # Medium volatility + normal session = day trading
        elif 1.0 <= volatility <= 2.0 and session in ['london', 'new_york', 'overlap']:
            return TradingType.DAY_TRADING

        # Low volatility or poor liquidity = swing trading
        elif volatility < 1.0 or liquidity < 0.5:
            return TradingType.SWING_TRADING

        # Default
        return TradingType.DAY_TRADING
```

## Performance Optimization

### Type-Specific Performance Tracking

```python
class TradingTypePerformanceTracker:
    def __init__(self):
        self.performance_by_type = {}

    def track_trade_result(self, trading_type: TradingType, trade_result: Dict):
        """Track trade result for specific trading type."""
        if trading_type not in self.performance_by_type:
            self.performance_by_type[trading_type] = {
                'total_trades': 0,
                'winning_trades': 0,
                'total_profit': 0.0,
                'total_hold_time': 0,
                'max_favorable_excursion': 0.0,
                'max_adverse_excursion': 0.0
            }

        stats = self.performance_by_type[trading_type]
        stats['total_trades'] += 1

        if trade_result['profit'] > 0:
            stats['winning_trades'] += 1

        stats['total_profit'] += trade_result['profit']
        stats['total_hold_time'] += trade_result['hold_time_minutes']
        stats['max_favorable_excursion'] = max(
            stats['max_favorable_excursion'],
            trade_result['max_profit']
        )
        stats['max_adverse_excursion'] = max(
            stats['max_adverse_excursion'],
            abs(trade_result['max_loss'])
        )

    def get_performance_report(self, trading_type: TradingType) -> Dict:
        """Get performance report for specific trading type."""
        if trading_type not in self.performance_by_type:
            return {}

        stats = self.performance_by_type[trading_type]

        return {
            'win_rate': stats['winning_trades'] / stats['total_trades'] if stats['total_trades'] > 0 else 0,
            'profit_factor': self.calculate_profit_factor(stats),
            'average_hold_time_hours': stats['total_hold_time'] / (60 * stats['total_trades']) if stats['total_trades'] > 0 else 0,
            'total_profit': stats['total_profit'],
            'total_trades': stats['total_trades'],
            'avg_mfe': stats['max_favorable_excursion'] / stats['total_trades'] if stats['total_trades'] > 0 else 0,
            'avg_mae': stats['max_adverse_excursion'] / stats['total_trades'] if stats['total_trades'] > 0 else 0
        }

    def get_best_performing_type(self) -> TradingType:
        """Get the best performing trading type based on risk-adjusted returns."""
        best_type = None
        best_score = 0

        for trading_type, stats in self.performance_by_type.items():
            if stats['total_trades'] < 10:  # Need minimum sample size
                continue

            # Calculate risk-adjusted score
            win_rate = stats['winning_trades'] / stats['total_trades']
            profit_factor = self.calculate_profit_factor(stats)
            score = win_rate * profit_factor

            if score > best_score:
                best_score = score
                best_type = trading_type

        return best_type
```

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