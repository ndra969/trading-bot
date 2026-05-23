# Configuration Guide

Configuration system using Everett + YAML for hierarchical settings management.

## Configuration Hierarchy

1. **Environment Variables** (highest priority)
2. **Environment-specific YAML** (`config/{env}.yaml`)
3. **Strategy-specific YAML** (`config/strategy_parameters.yaml`)
4. **Trading-specific YAML** (`config/trading_parameters.yaml`)
5. **Risk-specific YAML** (`config/risk_parameters.yaml`)
6. **Default YAML** (`config/default.yaml`)

## Core Configuration Files

### Base Configuration (`config/default.yaml`)

```yaml
app:
  name: "Trading Bot"
  environment: "development"

broker:
  name: "YourBroker"
  type: "demo"
  symbols: ["EURUSD", "GBPUSD", "XAUUSD"]

trading:
  risk_per_trade: 0.005
  max_concurrent_positions: 5
  loop_interval: 60

database:
  url: "sqlite+aiosqlite:///./data/trading_bot.db"
```

### Trading Parameters (`config/trading_parameters.yaml`)

Asset-specific configurations with pip calculations:

```yaml
assets:
  forex_major:
    symbols: ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
    pip_value: 0.0001
    position_management:
      breakeven:
        trigger_pips: 15
        buffer_pips: 0.5
      trailing:
        start_pips_from_sl: 20
        distance_pips: 15

  forex_jpy:
    symbols: ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"]
    pip_value: 0.01

  commodities:
    symbols: ["XAUUSD", "XAGUSD"]
    pip_values:
      XAUUSD: 0.1
      XAGUSD: 0.001

  crypto:
    symbols: ["BTCUSD", "ETHUSD"]
    pip_value: 1.0
```

### Strategy Parameters (`config/strategy_parameters.yaml`)

```yaml
strategy_architecture:
  foundation:
    supply_demand_zones:
      enabled: true
      mandatory: true
      min_requirements:
        min_strength: 40.0
        max_age_hours: 168

  enhancement_layers:
    price_action_confirmation:
      enabled: true
      priority: 1

    fibonacci_confluence:
      enabled: true
      priority: 2

confluence_weights:
  foundation: 0.40
  price_action: 0.20
  fibonacci: 0.15
  breakout_retest: 0.15
  market_structure: 0.10

multi_timeframe:
  primary_timeframe: "H1"
  secondary_timeframe: "H4"
  tertiary_timeframe: "D1"
```

### Risk Parameters (`config/risk_parameters.yaml`)

```yaml
risk_management:
  position_level:
    max_risk_per_trade: 0.02
    min_risk_reward_ratio: 1.5

  portfolio_level:
    max_total_exposure: 0.10
    max_concurrent_positions: 5

  account_level:
    max_daily_drawdown: 0.05
    max_weekly_drawdown: 0.08
    max_monthly_drawdown: 0.15
```

### Position Coordination (`config/position_coordination.yaml`)

```yaml
position_coordination:
  execution_rules:
    max_trades_per_symbol: 1
    signal_cooldown_minutes: 15
    post_close_cooldown_minutes: 30

  signal_requirements:
    min_active_layers: 2
    min_final_confidence: 65.0
```

## Environment-Specific Configurations

```yaml
# config/development.yaml
app:
  environment: "development"
  debug: true
trading:
  dry_run: true

# config/production.yaml
app:
  environment: "production"
  debug: false
trading:
  dry_run: false
```

## CLI Commands

```bash
# View configuration
uv run trading-bot config show
uv run trading-bot config show --file trading_parameters
uv run trading-bot config diff --env development production

# Validation
uv run trading-bot config validate --all
uv run trading-bot config validate-syntax --file risk_parameters

# Environment management
uv run trading-bot config set-env --environment production
uv run trading-bot config list-environments

# Backup and restore
uv run trading-bot config backup --version "pre_optimization"
uv run trading-bot config rollback --hash "abc123"
```

## Best Practices

1. **Never hardcode** configurable values
2. **Use environment variables** for secrets
3. **Test configurations** in development first
4. **Version control** all configuration changes
5. **Validate before** applying to production

For implementation details, see [`src/trading_bot/config.py`](../../src/trading_bot/config.py).
