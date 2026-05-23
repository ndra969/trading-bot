# Configuration Guide

This guide provides comprehensive information about the trading bot's configuration system using Everett + YAML for hierarchical settings management.

## Configuration System Overview

The trading bot uses a sophisticated configuration system that allows for flexible, environment-specific settings with clear priority hierarchies.

### Configuration Hierarchy (Priority Order)

1. **Environment Variables** (highest priority)
2. **Environment-specific YAML** (`config/{env}.yaml`)
3. **Strategy-specific YAML** (`config/strategy_parameters.yaml`)
4. **Trading-specific YAML** (`config/trading_parameters.yaml`)
5. **Risk-specific YAML** (`config/risk_parameters.yaml`)
6. **Default YAML** (`config/default.yaml`)
7. **Hardcoded defaults** (lowest priority)

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
  echo: false

position_management:
  forex_major:
    breakeven_trigger_pips: 15
    trailing_start_pips: 20
  commodities:
    breakeven_trigger_pips: 150
    trailing_start_pips: 200
```

### Trading Parameters (`config/trading_parameters.yaml`)

Asset-specific configurations with pip calculations:

```yaml
# Asset-specific configurations with pip calculations
assets:
  forex_major:
    symbols: ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
    pip_value: 0.0001
    risk_parameters:
      risk_per_trade: 0.005
      max_positions: 5
      min_sl_pips: 15
      max_sl_pips: 50
    position_management:
      breakeven:
        trigger_pips: 15
        buffer_pips: 0.5
        enabled: true
      trailing:
        start_pips_from_sl: 20
        distance_pips: 15
        acceleration_factor: 1.2
      partial_close:
        levels: [20, 40, 60]  # pips
        percentages: [0.25, 0.25, 0.5]

  forex_jpy:
    symbols: ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"]
    pip_value: 0.01  # Different pip value for JPY pairs
    position_management:
      breakeven:
        trigger_pips: 18
        buffer_pips: 0.8
      trailing:
        start_pips_from_sl: 25
        distance_pips: 18
      partial_close:
        levels: [25, 50, 75]
        percentages: [0.25, 0.25, 0.5]

  commodities:
    symbols: ["XAUUSD", "XAGUSD"]
    pip_values:
      XAUUSD: 0.1
      XAGUSD: 0.001
    position_management:
      breakeven:
        trigger_pips: 150
        buffer_pips: 5
      trailing:
        start_pips_from_sl: 200
        distance_pips: 100
      partial_close:
        levels: [100, 200, 300]
        percentages: [0.25, 0.25, 0.5]

  crypto:
    symbols: ["BTCUSD", "ETHUSD"]
    pip_value: 1.0
    position_management:
      breakeven:
        trigger_pips: 300
        buffer_pips: 20
      trailing:
        start_pips_from_sl: 400
        distance_pips: 200
      partial_close:
        levels: [200, 400, 600]
        percentages: [0.25, 0.25, 0.5]
```

### Strategy Parameters (`config/strategy_parameters.yaml`)

```yaml
# Strategy architecture configuration
strategy_architecture:
  # Foundation Layer (MANDATORY)
  foundation:
    supply_demand_zones:
      enabled: true
      mandatory: true  # Cannot be disabled
      priority: 0
      description: "Core S&D zones - primary entry point identification"
      min_requirements:
        min_strength: 40.0
        min_volume_confirmation: 1.2
        max_age_hours: 168
        max_tests: 3
        min_freshness: 0.6

  # Enhancement Layers (Optional but Additive)
  enhancement_layers:
    price_action_confirmation:
      enabled: true
      priority: 1
      requires: ["supply_demand_zones"]
      description: "PA patterns within S&D zones (engulfing, pin bars, etc.)"
      patterns: ["engulfing", "pin_bar", "inside_bar", "doji"]

    fibonacci_confluence:
      enabled: true
      priority: 2
      requires: ["supply_demand_zones"]
      description: "Fibo retracements/extensions confluence with zones"
      key_levels: [0.382, 0.5, 0.618, 0.786]

    breakout_retest_validation:
      enabled: true
      priority: 3
      requires: ["supply_demand_zones"]
      description: "Structure break confirmations from S&D levels"

    market_structure_alignment:
      enabled: true
      priority: 4
      requires: ["supply_demand_zones"]
      description: "BOS/CHoCH alignment with zone entries"

# Signal Generation Workflow
signal_workflow:
  step_1_foundation:
    name: "S&D Zone Detection"
    mandatory: true
    output: "qualified_zones"

  step_2_enhancement:
    name: "Enhancement Layer Analysis"
    input: "qualified_zones"
    layers: ["price_action", "fibonacci", "breakout_retest", "market_structure"]
    output: "enhanced_signals"

  step_3_confluence:
    name: "Multi-Layer Confluence Scoring"
    input: "enhanced_signals"
    min_confluence_layers: 2  # S&D + at least 1 enhancement
    output: "final_signal"

# Layer Weights for Confluence Scoring
confluence_weights:
  foundation: 0.40      # S&D zones - 40%
  price_action: 0.20    # PA confirmation - 20%
  fibonacci: 0.15       # Fibo confluence - 15%
  breakout_retest: 0.15 # Breakout validation - 15%
  market_structure: 0.10 # Structure alignment - 10%

# Multi-timeframe configuration
multi_timeframe:
  enabled: true
  primary_timeframe: "H1"      # Main analysis timeframe
  secondary_timeframe: "H4"    # Trend confirmation
  tertiary_timeframe: "D1"     # Major trend direction
  analysis_timeframes: ["M15", "H1", "H4"]  # Structure detection

# Trend analysis weights
trend_weights:
  D1: 3    # Daily trend - Highest priority (30% influence)
  H4: 2    # 4-hour trend - Medium priority (40% influence)
  H1: 1    # 1-hour trend - Lower priority (30% influence)
  minimum_trend_strength: 4    # Combined score threshold
  trend_alignment_weight: 0.45 # Overall trend influence in signal scoring
```

### Risk Parameters (`config/risk_parameters.yaml`)

```yaml
# Risk management configuration
risk_management:
  # Position-level risk
  position_level:
    max_risk_per_trade: 0.02  # 2% account risk per trade
    min_risk_reward_ratio: 1.5
    max_drawdown_per_position: 0.05  # 5%

  # Portfolio-level risk
  portfolio_level:
    max_total_exposure: 0.10  # 10% total account exposure
    max_correlation_threshold: 0.70
    max_concurrent_positions: 5
    max_positions_per_asset_class: 3

  # Account-level risk
  account_level:
    max_daily_drawdown: 0.05      # 5% daily drawdown limit
    max_weekly_drawdown: 0.08     # 8% weekly drawdown limit
    max_monthly_drawdown: 0.15    # 15% monthly drawdown limit

  # Real-time monitoring
  monitoring:
    drawdown_warning_threshold: 0.04  # 4% warning
    correlation_check_interval: 300   # 5 minutes
    risk_update_frequency: 60         # 1 minute
```

### Analytics Parameters (`config/analytics_parameters.yaml`)

Performance tracking and optimization settings:

```yaml
analytics:
  performance_tracking:
    metrics_calculation:
      min_trades_for_stats: 10
      rolling_window_days: 30
      confidence_intervals: [0.90, 0.95, 0.99]

    optimization_tracking:
      parameter_sensitivity: true
      correlation_analysis: true
      drawdown_analysis: true
      risk_adjusted_returns: true

  real_time_monitoring:
    update_frequency_seconds: 60
    alert_thresholds:
      drawdown_warning: 0.04
      win_rate_decline: 0.10
      profit_factor_decline: 0.20
      correlation_spike: 0.80

  backtesting:
    default_lookback_days: 90
    min_sample_size: 30
    statistical_significance_level: 0.95
    walk_forward_analysis: true
```

### Position Coordination (`config/position_coordination.yaml`)

```yaml
position_coordination:
  # Core execution rules
  execution_rules:
    max_trades_per_symbol: 1  # CRITICAL: Only 1 active trade per symbol
    signal_cooldown_minutes: 15
    post_close_cooldown_minutes: 30

  # Signal requirements
  signal_requirements:
    min_active_layers: 2  # Foundation + minimum 1 enhancement
    min_final_confidence: 65.0
    require_volume_confirmation: true

  # Confluence bonuses
  confluence_bonuses:
    multi_layer_bonus: 5.0
    perfect_alignment_bonus: 10.0  # All layers agree
    fibonacci_zone_confluence: 8.0  # S&D zone + Fibo level
```

## Configuration Management Framework

### Automated Parameter Optimization

The system includes a sophisticated configuration tuning framework:

```python
# Strategy optimization workflow
class ConfigurationTuner:
    async def analyze_parameter_effectiveness(self,
                                            strategy_name: str,
                                            lookback_days: int = 30) -> Dict:
        """
        Analyze effectiveness of current strategy parameters.

        Returns:
            Dict containing:
            - parameter_effectiveness: Score for each parameter
            - optimization_recommendations: Suggested changes
            - performance_impact: Expected improvement
        """

    async def suggest_optimizations(self, strategy_name: str) -> List[ConfigurationChange]:
        """Generate data-driven optimization suggestions"""

    async def create_ab_test(self,
                           strategy_name: str,
                           parameter_variations: Dict[str, List[Any]],
                           test_duration_days: int = 30) -> str:
        """Create A/B test for parameter optimization"""
```

### Database Schema for Configuration Tracking

Critical tables for strategy analysis and parameter tracking:

```sql
-- Strategy performance tracking with configuration hash
CREATE TABLE strategy_performance_detailed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    -- Performance metrics
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    average_rr_ratio REAL DEFAULT 0.0,
    sharpe_ratio REAL DEFAULT 0.0,

    -- Strategy-specific metrics
    average_confluence_score REAL DEFAULT 0.0,
    average_entry_score REAL DEFAULT 0.0,

    -- Configuration tracking
    config_hash TEXT,  -- MD5 hash for configuration tracking
    config_version TEXT,

    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL
);

-- Parameter effectiveness tracking
CREATE TABLE parameter_effectiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    parameter_value TEXT NOT NULL,

    -- Performance impact
    trades_with_parameter INTEGER DEFAULT 0,
    win_rate_with_parameter REAL DEFAULT 0.0,
    avg_profit_with_parameter REAL DEFAULT 0.0,
    performance_vs_baseline REAL DEFAULT 0.0,

    analysis_period_days INTEGER DEFAULT 30,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- A/B testing results
CREATE TABLE ab_test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    variant_name TEXT NOT NULL,

    -- Test performance
    trades_count INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    statistical_significance REAL DEFAULT 0.0,

    test_start_date TIMESTAMP,
    test_end_date TIMESTAMP,
    test_status TEXT DEFAULT 'running'
);
```

## CLI Commands for Configuration Management

### Configuration Analysis and Tuning

```bash
# Configuration analysis and tuning
uv run trading-bot config analyze --strategy supply_demand --days 30
uv run trading-bot config optimize --strategy supply_demand --auto-apply
uv run trading-bot config ab-test --strategy supply_demand --parameter risk_per_trade --values "0.003,0.005,0.007"

# Performance monitoring
uv run trading-bot analytics performance --strategy all --timeframe H1
uv run trading-bot analytics correlation --symbols EURUSD,GBPUSD --days 30
uv run trading-bot analytics parameter-sensitivity --parameter confluence_threshold

# Configuration management
uv run trading-bot config backup --version "pre_optimization_v1"
uv run trading-bot config rollback --hash "abc123def456"
uv run trading-bot config validate --environment production

# Configuration inspection
uv run trading-bot config show --file trading_parameters
uv run trading-bot config diff --env development production
uv run trading-bot config validate-syntax --all

# Environment management
uv run trading-bot config set-env --environment production
uv run trading-bot config list-environments
uv run trading-bot config create-env --name staging --base production
```

## Configuration Management Rules

### Key Principles

1. **All Tunable Parameters in YAML**: Never hardcode configurable values
2. **Configuration Versioning**: Track all config changes with MD5 hashes
3. **Performance Impact Tracking**: Monitor performance before/after config changes
4. **Statistical Validation**: Require minimum sample size for optimization decisions
5. **Rollback Capability**: Always maintain ability to revert configurations
6. **A/B Testing**: Test parameter changes with statistical significance
7. **Real-time Monitoring**: Alert on performance degradation after config changes

### Environment-Specific Configurations

```yaml
# config/development.yaml
app:
  environment: "development"
  debug: true

database:
  echo: true  # SQL logging for debugging

trading:
  dry_run: true
  loop_interval: 30  # Faster for testing

# config/production.yaml
app:
  environment: "production"
  debug: false

database:
  echo: false

trading:
  dry_run: false
  loop_interval: 60

# config/testing.yaml
app:
  environment: "testing"

database:
  url: "sqlite+aiosqlite:///:memory:"

trading:
  symbols: ["EURUSD"]  # Limited for testing
```

### Configuration Validation

The system automatically validates configurations on startup:

```python
# Configuration validation rules
VALIDATION_RULES = {
    "trading.risk_per_trade": {
        "type": float,
        "min": 0.001,
        "max": 0.05,
        "description": "Risk per trade must be between 0.1% and 5%"
    },
    "trading.max_concurrent_positions": {
        "type": int,
        "min": 1,
        "max": 20,
        "description": "Max positions must be between 1 and 20"
    },
    "confluence_weights.foundation": {
        "type": float,
        "min": 0.1,
        "max": 1.0,
        "description": "Foundation weight must be between 10% and 100%"
    }
}
```

## Best Practices

### 1. Configuration Organization
- Keep related settings in the same file
- Use descriptive names for configuration keys
- Include comments explaining complex configurations
- Maintain consistent naming conventions

### 2. Environment Management
- Always use environment-specific configurations for production
- Test configurations in development environment first
- Use version control for all configuration changes
- Implement configuration backup and rollback procedures

### 3. Performance Optimization
- Monitor the impact of configuration changes on performance
- Use A/B testing for parameter optimization
- Implement gradual rollouts for significant changes
- Maintain performance baselines for comparison

### 4. Security Considerations
- Never commit sensitive data (API keys, passwords) to configuration files
- Use environment variables for secrets
- Implement access controls for production configurations
- Audit configuration changes regularly

This comprehensive configuration guide provides all the necessary information for managing the trading bot's complex configuration system effectively.
