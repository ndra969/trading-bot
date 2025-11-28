# CLI Reference Guide

Complete reference for all CLI commands available in the trading bot system. All commands use the Click framework and follow the pattern `uv run trading-bot <command> [options]`.

## Core System Commands

### Bot Control

```bash
# Initialize the trading bot system
uv run trading-bot init --config development
uv run trading-bot init --config production --force

# Start the trading bot
uv run trading-bot start --config production
uv run trading-bot start --dry-run                    # Simulation mode
uv run trading-bot start --ignore-market-hours        # Force trading (testing)

# Stop the trading bot
uv run trading-bot stop
uv run trading-bot stop --force                       # Force shutdown

# Get bot status and information
uv run trading-bot status
uv run trading-bot status --detailed
uv run trading-bot info --platform-check
uv run trading-bot version
```

### System Management

```bash
# Health checks
uv run trading-bot health
uv run trading-bot health --components mt5,database,strategies
uv run trading-bot ping

# Log management
uv run trading-bot logs
uv run trading-bot logs --tail 100
uv run trading-bot logs --level ERROR
uv run trading-bot logs --export --file logs_backup.zip

# Performance monitoring
uv run trading-bot monitor
uv run trading-bot monitor --cpu --memory --network
uv run trading-bot benchmark
```

## Database Management

### Database Operations

```bash
# Database initialization and migration
uv run trading-bot db init
uv run trading-bot db migrate
uv run trading-bot db migrate --version 1.2.0
uv run trading-bot db rollback --steps 1

# Database maintenance
uv run trading-bot db backup
uv run trading-bot db backup --file custom_backup.db
uv run trading-bot db restore --file backup_20241201.db
uv run trading-bot db optimize
uv run trading-bot db vacuum
uv run trading-bot db integrity-check

# Data export/import
uv run trading-bot db export --table trades --format csv
uv run trading-bot db export --all --format json
uv run trading-bot db import --file trades.csv --table trades

# Database statistics
uv run trading-bot db stats
uv run trading-bot db size
uv run trading-bot db tables --list
```

## Strategy Management

### Strategy Control

```bash
# Strategy status and control
uv run trading-bot strategy status
uv run trading-bot strategy list --available
uv run trading-bot strategy enable --name supply_demand
uv run trading-bot strategy disable --name fibonacci_confluence
uv run trading-bot strategy restart --name price_action

# Strategy weights and configuration
uv run trading-bot strategy weights --supply_demand 0.4 --breakout_retest 0.6
uv run trading-bot strategy weights --show
uv run trading-bot strategy config --name supply_demand --show
uv run trading-bot strategy config --name supply_demand --set min_strength=45.0

# Strategy testing
uv run trading-bot strategy test supply_demand
uv run trading-bot strategy test --all --symbol EURUSD
```

## Technical Indicator Analysis

### RSI Analysis Commands

```bash
# RSI analysis for specific symbol
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot technical analyze --symbol XAUUSD --indicator rsi --timeframe H4
uv run trading-bot technical analyze --symbol BTCUSD --indicator rsi --trading-type scalping

# Multi-timeframe RSI analysis
uv run trading-bot technical analyze --symbol GBPUSD --indicator rsi --multi-timeframe
uv run trading-bot technical rsi --symbol EURUSD --timeframes H1,H4,D1

# RSI divergence analysis
uv run trading-bot technical rsi-divergence --symbol EURUSD --lookback 50
uv run trading-bot technical rsi-levels --symbol XAUUSD --show-conditions

# RSI batch analysis
uv run trading-bot technical analyze --symbols EURUSD,GBPUSD,XAUUSD --indicator rsi
```

### Moving Average Analysis Commands

```bash
# Moving Average analysis
uv run trading-bot technical analyze --symbol EURUSD --indicator ma
uv run trading-bot technical analyze --symbol XAUUSD --indicator ma --timeframe H1
uv run trading-bot technical analyze --symbol GBPUSD --indicator ma --trading-type day_trading

# MA alignment and crossover analysis
uv run trading-bot technical ma-alignment --symbol EURUSD --timeframes H1,H4
uv run trading-bot technical ma-crossovers --symbol GBPUSD --period 20

# MA trend analysis
uv run trading-bot technical ma-trend --symbol XAUUSD --multi-timeframe
uv run trading-bot technical ma-levels --symbol EURUSD --dynamic

# Batch MA analysis
uv run trading-bot technical analyze --symbols EURUSD,GBPUSD --indicator ma --export
```

### Technical Indicator Testing

```bash
# Test technical indicator libraries
uv run trading-bot technical test-libraries
uv run trading-bot technical test-libraries --indicator rsi
uv run trading-bot technical test-libraries --indicator ma --fallback-only

# Performance benchmarking
uv run trading-bot technical benchmark --indicator rsi --iterations 1000
uv run trading-bot technical benchmark --indicator ma --symbol EURUSD

# Library fallback testing
uv run trading-bot technical test-fallback --force-pandas-ta
uv run trading-bot technical test-fallback --force-manual-calc
uv run trading-bot strategy validate --name price_action
uv run trading-bot strategy dry-run --name supply_demand --symbol GBPUSD

# Strategy performance
uv run trading-bot strategy performance --name supply_demand --days 30
uv run trading-bot strategy compare --strategies supply_demand,fibonacci_confluence
uv run trading-bot strategy leaderboard --period month
```

### Foundation Management

```bash
# Supply & Demand foundation control
uv run trading-bot foundation status --symbol EURUSD
uv run trading-bot foundation zones --symbol EURUSD --strength-min 40
uv run trading-bot foundation zones --all-symbols --active-only
uv run trading-bot foundation validate --zone-id 12345
uv run trading-bot foundation cleanup --expired --max-age 7d

# Zone analysis
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1
uv run trading-bot foundation detect --symbol GBPUSD --update-zones
uv run trading-bot foundation quality-check --all-zones

# Price Action analysis (Enhancement Layer #2)
uv run trading-bot foundation price-action EURUSD --timeframe H1
uv run trading-bot foundation price-action GBPUSD --trading-type scalping --min-confidence 80
uv run trading-bot foundation price-action XAUUSD --pattern engulfing,pin_bar --timeframe H4
```

### Enhancement Layers

```bash
# Layer management
uv run trading-bot layers status
uv run trading-bot layers list --enabled
uv run trading-bot layers enable --layer price_action
uv run trading-bot layers disable --layer fibonacci
uv run trading-bot layers restart --layer market_structure

# Layer configuration
uv run trading-bot layers weights --price_action 0.25 --fibonacci 0.20
uv run trading-bot layers config --layer price_action --show
uv run trading-bot layers test --layer fibonacci --symbol EURUSD

# Layer performance
uv run trading-bot layers performance --layer price_action --days 30
uv run trading-bot layers effectiveness --all --period week
uv run trading-bot layers correlation --layers price_action,fibonacci
```

## Trading Operations

### Position Management

```bash
# Active positions
uv run trading-bot positions active
uv run trading-bot positions active --symbol EURUSD
uv run trading-bot positions history --days 7
uv run trading-bot positions summary --today

# Position operations
uv run trading-bot positions close --ticket 123456
uv run trading-bot positions close-all --symbol EURUSD
uv run trading-bot positions modify --ticket 123456 --sl 1.0850
uv run trading-bot positions partial-close --ticket 123456 --percentage 50

# Position analysis
uv run trading-bot positions analyze --ticket 123456
uv run trading-bot positions performance --symbol EURUSD --days 30
uv run trading-bot positions conflicts --check
uv run trading-bot positions cooldown --symbol EURUSD --show
```

### Signal Analysis

```bash
# Signal generation and analysis
uv run trading-bot signal analyze --symbol EURUSD --show-layers
uv run trading-bot signal generate --symbol GBPUSD --strategy supply_demand
uv run trading-bot signal confluence --symbol EURUSD --min-layers 3
uv run trading-bot signal requirements --check-all

# Signal validation
uv run trading-bot signal validate --symbol EURUSD --confidence-min 70
uv run trading-bot signal test --symbol GBPUSD --dry-run
uv run trading-bot signal history --symbol EURUSD --days 7
uv run trading-bot signal performance --all-symbols --period month
```

## Market Analysis

### Market Data and Analysis

```bash
# Market analysis
uv run trading-bot market analyze EURUSD
uv run trading-bot market analyze GBPUSD --timeframe H4 --detailed
uv run trading-bot market structure --timeframe H1
uv run trading-bot market structure EURUSD --multi-timeframe

# Market status
uv run trading-bot market status
uv run trading-bot market status --symbol EURUSD
uv run trading-bot market hours --all-symbols
uv run trading-bot market hours --symbol XAUUSD --detailed

# Market sessions
uv run trading-bot market sessions --current
uv run trading-bot market next-session
uv run trading-bot market next-session --symbol EURUSD
uv run trading-bot market calendar --days 7

# Price data
uv run trading-bot market data EURUSD --timeframe H1 --bars 100
uv run trading-bot market data --symbols EURUSD,GBPUSD --export csv
uv run trading-bot market tick EURUSD --live --duration 60
```

## Configuration Management

### Configuration Operations

```bash
# Configuration viewing and editing
uv run trading-bot config show
uv run trading-bot config show --file trading_parameters
uv run trading-bot config show --key trading.risk_per_trade
uv run trading-bot config edit --file strategy_parameters

# Configuration comparison
uv run trading-bot config diff --env development production
uv run trading-bot config diff --file trading_parameters --version current previous
uv run trading-bot config validate --all
uv run trading-bot config validate-syntax --file risk_parameters

# Configuration management
uv run trading-bot config backup --version "pre_optimization_v1"
uv run trading-bot config backup --all --timestamp
uv run trading-bot config restore --hash "abc123def456"
uv run trading-bot config rollback --steps 1

# Environment management
uv run trading-bot config set-env --environment production
uv run trading-bot config list-environments
uv run trading-bot config create-env --name staging --base production
uv run trading-bot config delete-env --name old_test --confirm

# Configuration analysis and optimization
uv run trading-bot config analyze --strategy supply_demand --days 30
uv run trading-bot config optimize --strategy supply_demand --auto-apply
uv run trading-bot config optimize --parameter risk_per_trade --range 0.003,0.007
uv run trading-bot config suggestions --show --strategy all

# A/B testing
uv run trading-bot config ab-test --strategy supply_demand --parameter risk_per_trade --values "0.003,0.005,0.007"
uv run trading-bot config ab-test --list-active
uv run trading-bot config ab-test --results --test-id test_001
uv run trading-bot config ab-test --stop --test-id test_001
```

## Analytics and Performance

### Performance Analysis

```bash
# Performance metrics
uv run trading-bot analytics performance --strategy all --timeframe H1
uv run trading-bot analytics performance --symbol EURUSD --days 30
uv run trading-bot analytics performance --detailed --export

# Correlation analysis
uv run trading-bot analytics correlation --symbols EURUSD,GBPUSD --days 30
uv run trading-bot analytics correlation --strategies supply_demand,price_action
uv run trading-bot analytics correlation-matrix --all-symbols

# Risk analysis
uv run trading-bot analytics risk --current
uv run trading-bot analytics risk --historical --days 90
uv run trading-bot analytics drawdown --analysis --period month
uv run trading-bot analytics var --confidence 95 --holding-period 1

# Strategy analysis
uv run trading-bot analytics strategy-comparison --days 30
uv run trading-bot analytics strategy-evolution --strategy supply_demand --months 6
uv run trading-bot analytics signal-selection-effectiveness
uv run trading-bot analytics parameter-sensitivity --parameter confluence_threshold

# Layer performance
uv run trading-bot analytics layer-performance --days 30
uv run trading-bot analytics foundation-quality --symbols EURUSD,GBPUSD
uv run trading-bot analytics enhancement-effectiveness --layer fibonacci
uv run trading-bot analytics confluence-analysis --timeframe week

# Trade analysis
uv run trading-bot analytics trades --summary --period month
uv run trading-bot analytics trades --detailed --symbol EURUSD
uv run trading-bot analytics trades --winners --analysis
uv run trading-bot analytics trades --losers --lessons

# Market analysis
uv run trading-bot analytics market-conditions --current
uv run trading-bot analytics volatility --symbols EURUSD,XAUUSD --days 30
uv run trading-bot analytics spread-analysis --all-symbols
```

### Backtesting

```bash
# Strategy backtesting
uv run trading-bot backtest --strategy supply_demand --symbol EURUSD --days 90
uv run trading-bot backtest --all-strategies --symbol GBPUSD --from 2024-01-01 --to 2024-12-01
uv run trading-bot backtest --config custom_backtest.yaml --export-results

# Backtest analysis
uv run trading-bot backtest results --test-id bt_001 --detailed
uv run trading-bot backtest compare --test-ids bt_001,bt_002
uv run trading-bot backtest optimize --strategy supply_demand --parameter-range risk_per_trade:0.003-0.007

# Walk-forward analysis
uv run trading-bot backtest walk-forward --strategy supply_demand --window 30 --step 7
uv run trading-bot backtest rolling --strategy price_action --window-days 60
```

## Windows-Specific Commands

### Windows System Management

```bash
# Windows system status
uv run trading-bot windows status
uv run trading-bot windows performance
uv run trading-bot windows optimize
uv run trading-bot windows diagnostics

# MT5 management
uv run trading-bot mt5 status
uv run trading-bot mt5 start
uv run trading-bot mt5 stop
uv run trading-bot mt5 restart
uv run trading-bot mt5 optimize
uv run trading-bot mt5 check-connection
uv run trading-bot mt5 path --detect
uv run trading-bot mt5 version

# Windows service management
uv run trading-bot service install
uv run trading-bot service uninstall
uv run trading-bot service start
uv run trading-bot service stop
uv run trading-bot service status
uv run trading-bot service logs

# Windows-specific testing
uv run trading-bot test mt5-connection
uv run trading-bot test market-hours
uv run trading-bot test windows-performance
uv run trading-bot test system-compatibility
```

## Notification Management

### Telegram Notifications

```bash
# Notification status and control
uv run trading-bot notifications status
uv run trading-bot notifications test
uv run trading-bot notifications test --type trade_opened
uv run trading-bot notifications setup --interactive

# Notification configuration
uv run trading-bot notifications enable --type trade_opened
uv run trading-bot notifications disable --type trailing_updated
uv run trading-bot notifications list --enabled
uv run trading-bot notifications config --show

# Manual notifications
uv run trading-bot notifications send --message "Manual test message"
uv run trading-bot notifications send --type system_alert --message "System maintenance"
uv run trading-bot notifications summary --send
uv run trading-bot notifications daily-summary --send-now

# Notification history
uv run trading-bot notifications history --days 7
uv run trading-bot notifications stats --period month
uv run trading-bot notifications failed --retry
```

## Development and Testing

### Development Tools

```bash
# Development workflow
uv sync
uv sync --extra dev
uv sync --upgrade

# Code quality
uv run black src/ tests/
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/
uv run mypy src/trading_bot/
uv run mypy --strict src/trading_bot/

# Testing
uv run pytest tests/
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ --mt5
uv run pytest tests/unit/test_strategies.py::TestSupplyDemand
uv run pytest --cov=src/trading_bot tests/
uv run pytest --cov-report=html tests/

# Database testing
uv run pytest tests/database/ --create-db
uv run pytest tests/database/ --reset-db

# Performance testing
uv run pytest tests/performance/ --benchmark
uv run trading-bot test performance --component strategies
uv run trading-bot test load --concurrent-symbols 10
```

### Debug Commands

```bash
# Debug information
uv run trading-bot debug info
uv run trading-bot debug config --show-all
uv run trading-bot debug strategies --verbose
uv run trading-bot debug database --connections

# Debug analysis
uv run trading-bot debug signal --symbol EURUSD --verbose
uv run trading-bot debug zones --symbol EURUSD --show-calculations
uv run trading-bot debug confluence --symbol GBPUSD --detailed

# Debug trading
uv run trading-bot debug dry-run --symbol EURUSD --steps
uv run trading-bot debug simulate --scenario high-volatility
uv run trading-bot debug market-hours --check-all

# Debug logs
uv run trading-bot debug logs --level DEBUG --tail 200
uv run trading-bot debug logs --component strategy_engine
uv run trading-bot debug export --logs --config --performance
```

## Utility Commands

### Data Management

```bash
# Data export
uv run trading-bot export trades --format csv --period month
uv run trading-bot export performance --format json --all-strategies
uv run trading-bot export config --all --format yaml
uv run trading-bot export logs --level ERROR --days 7

# Data import
uv run trading-bot import trades --file trades_backup.csv
uv run trading-bot import config --file strategy_config.yaml --validate
uv run trading-bot import zones --file zones_backup.json --symbol EURUSD

# Data cleanup
uv run trading-bot cleanup logs --older-than 30d
uv run trading-bot cleanup database --optimize
uv run trading-bot cleanup temp --all
uv run trading-bot cleanup backups --keep-latest 10
```

### Maintenance Commands

```bash
# System maintenance
uv run trading-bot maintenance start --mode safe
uv run trading-bot maintenance stop
uv run trading-bot maintenance status
uv run trading-bot maintenance schedule --task backup --cron "0 2 * * *"

# Cache management
uv run trading-bot cache clear --all
uv run trading-bot cache clear --type market_data
uv run trading-bot cache stats
uv run trading-bot cache optimize

# Resource management
uv run trading-bot resources check
uv run trading-bot resources optimize
uv run trading-bot resources monitor --duration 300
```

## Command Patterns and Options

### Global Options

Most commands support these global options:

```bash
# Configuration options
--config CONFIG_NAME           # Specify configuration environment
--config-file PATH             # Use custom config file
--verbose, -v                  # Verbose output
--quiet, -q                    # Quiet mode
--debug                        # Debug mode

# Output options
--format FORMAT                # Output format: json, csv, yaml, table
--output FILE                  # Output to file
--no-color                     # Disable colored output
--no-header                    # Disable table headers

# Filter options
--symbol SYMBOL                # Filter by symbol
--strategy STRATEGY            # Filter by strategy
--timeframe TIMEFRAME          # Filter by timeframe
--days DAYS                    # Filter by days
--from DATE                    # Start date filter
--to DATE                      # End date filter

# Execution options
--dry-run                      # Simulation mode
--force                        # Force execution
--confirm                      # Require confirmation
--async                        # Asynchronous execution
```

### Common Patterns

```bash
# Pattern: Command with symbol filter
uv run trading-bot <command> --symbol EURUSD [options]

# Pattern: Command with time filter
uv run trading-bot <command> --days 30 [options]
uv run trading-bot <command> --from 2024-01-01 --to 2024-12-31

# Pattern: Command with output format
uv run trading-bot <command> --format json --output results.json

# Pattern: Command with multiple filters
uv run trading-bot <command> --symbol EURUSD --strategy supply_demand --days 7

# Pattern: Command with confirmation
uv run trading-bot <command> --force --confirm

# Pattern: Dry run mode
uv run trading-bot <command> --dry-run --verbose
```

### Help System

```bash
# Get help for any command
uv run trading-bot --help
uv run trading-bot <command> --help
uv run trading-bot <command> <subcommand> --help

# Examples:
uv run trading-bot strategy --help
uv run trading-bot config optimize --help
uv run trading-bot analytics performance --help
```

## Exit Codes

The CLI uses standard exit codes:

- `0`: Success
- `1`: General error
- `2`: Invalid command/arguments
- `3`: Configuration error
- `4`: Database error
- `5`: MT5 connection error
- `6`: Market data error
- `7`: Strategy error
- `8`: Permission error
- `9`: Network error
- `10`: Validation error

## Environment Variables

Key environment variables that affect CLI behavior:

```bash
# Configuration
export TRADING_BOT_CONFIG=production
export TRADING_BOT_CONFIG_PATH="/custom/config/path"

# Database
export TRADING_BOT_DB_URL="sqlite:///custom/path/trading_bot.db"

# MT5
export TRADING_BOT_MT5_PATH="/custom/mt5/path"

# Logging
export TRADING_BOT_LOG_LEVEL=DEBUG
export TRADING_BOT_LOG_PATH="/custom/log/path"

# Development
export TRADING_BOT_ENV=development
export TRADING_BOT_DEBUG=true
```

## Quick Reference

### Most Common Commands

```bash
# Start/stop bot
uv run trading-bot start --config production
uv run trading-bot stop

# Check status
uv run trading-bot status
uv run trading-bot positions active
uv run trading-bot market status

# Configuration
uv run trading-bot config show
uv run trading-bot config backup

# Performance
uv run trading-bot analytics performance --days 30
uv run trading-bot strategy performance --name supply_demand

# Testing
uv run trading-bot test mt5-connection
uv run trading-bot strategy test supply_demand
```

This comprehensive CLI reference provides complete documentation for all available commands and their usage patterns.