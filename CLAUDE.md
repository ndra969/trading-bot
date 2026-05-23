# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📋 Quick Access to Project Rules & Commands

**🚀 Custom Claude Commands** (In Cursor IDE):

| Command | Description |
|---------|-------------|
| `/workflow` | **START HERE** - Complete development workflow guide |
| `/rules` / `/claude` | Display project rules and guidelines |
| `/test` | Run test suite with coverage (unit, integration, critical) |
| `/tdd` | TDD workflow guidance for new features |
| `/quality` | Run code quality checks (black, ruff, mypy) |
| `/dry-run` | Validate bot with dry-run mode (MANDATORY before commit) |
| `/coverage` | Check and display test coverage report |
| `/commit` | Pre-commit validation workflow (quick/full) |
| `/new <category>/<name>` | **Create new doc/spec** with template |
| `/analyze <symbol>` | Analyze symbol with foundation strategy |
| `/backtest <symbol>` | Run backtesting on strategies |
| `/migrate` | Database migration management |
| `/docs [topic]` | Quick access to project documentation |

**Examples:**
```bash
/workflow              # Show complete development workflow
/workflow implement     # Show TDD implementation phase
/test critical         # Run risk management tests (95% coverage)
/quality fix           # Auto-fix code quality issues
/dry-run               # Final validation before commit
/tdd new-feature       # TDD guidance for specific feature
/new guides/telegram    # Create new documentation
/analyze EURUSD        # Analyze EURUSD with foundation strategy
/backtest XAUUSD       # Backtest Gold strategy
/docs risk-management  # View risk management guide
```

**💡 Traditional CLI Commands:**
```bash
# Display project rules
uv run trading-bot rules
uv run trading-bot rules --format summary
uv run trading-bot rules --format rules-only

# Start trading bot
uv run trading-bot start --config production
uv run trading-bot start --dry-run
```

**File Reference:**
- Use `@CLAUDE.md` to reference this file directly
- Check `.cursorrules` for auto-loaded context

---

## Project Overview

This is a **New Trading Bot System** built with modern Python architecture for automated multi-asset trading (Forex, Commodities, Crypto). The system will implement sophisticated position management and market structure analysis using Test-Driven Development (TDD) methodology.

**🚀 PROJECT STATUS: Production Ready for Live Trading!**
- ✅ Foundation Strategy: 99/99 tests passing (98% coverage)
- ✅ Integration Layer: PostgreSQL + Live Trading Validation
- ✅ Ready for Position Management implementation

## Core Technologies
- **UV**: Modern Python package management
- **Click**: Command-line interface framework
- **Everett + YAML**: Configuration management
- **SQLAlchemy 2.0 + SQLite/PostgreSQL**: Async database layer with migration support
- **Pydantic**: Data validation and settings
- **Loguru**: Structured logging
- **MetaTrader5**: Windows-based trading platform integration
- **pandas-ta**: Technical indicators (RSI, Moving Averages) - Primary choice
- **TA-Lib**: High-performance technical analysis (optional)
- **Alembic**: Database migration management (SQLite ↔ PostgreSQL)

## Project Structure
```
trading-bot/
├── src/trading_bot/
│   ├── cli.py              # Click CLI entry point (with PostgreSQL commands)
│   ├── config.py           # Configuration management (env var support)
│   ├── main.py             # Main bot orchestrator
│   ├── core/               # Core components
│   ├── strategies/         # Trading strategies
│   ├── position/           # Position management
│   ├── risk/               # Risk management
│   ├── market_structure/   # Market analysis
│   ├── data/               # Database models
│   ├── connectors/         # MT5 integration
│   └── utils/              # Utilities
├── alembic/                # Database migrations
│   ├── versions/           # Migration files
│   │   └── 001_initial_migration.py # PostgreSQL schema
│   ├── env.py             # Alembic environment with async support
│   └── script.py.mako     # Migration template
├── config/                 # YAML configuration files
│   ├── postgresql.yaml    # PostgreSQL-specific configuration
│   └── ...                # Other configuration files
├── scripts/                # Utility scripts
│   └── migrate_to_postgresql.py # PostgreSQL migration helper
├── docs/                   # Documentation
│   └── postgresql-migration-guide.md # Complete migration guide
├── tests/                  # Test suite
├── .env                    # Environment variables (PostgreSQL config)
├── .env.example           # Environment variables template
└── alembic.ini           # Alembic configuration
```

## Essential Commands

### 📋 View Project Rules
```bash
# Display complete project rules and guidelines
uv run trading-bot rules

# Quick summary of key rules
uv run trading-bot rules --format summary

# Critical rules only (implementation requirements)
uv run trading-bot rules --format rules-only
```

**💡 Quick Access**: In Cursor IDE, you can also use `@CLAUDE.md` to reference this file directly.

### Development Workflow
```bash
# Setup project with technical indicators
uv sync
uv sync --extra dev
uv add pandas-ta ta numpy pandas  # Technical indicators

# Start trading bot with enhanced features
uv run trading-bot start --config production
uv run trading-bot start --dry-run

# Trading type management
uv run trading-bot type switch --type scalping
uv run trading-bot type status
uv run trading-bot type compare --types scalping,day_trading

# Broker symbol management
uv run trading-bot broker switch --name exness_standard
uv run trading-bot broker convert --symbol EURUSD --to-broker

# Technical indicators testing
uv run trading-bot technical analyze --symbol EURUSD --indicator rsi
uv run trading-bot technical test-libraries

# PostgreSQL migration and management
uv run trading-bot postgresql migrate                    # Complete migration
uv run trading-bot postgresql status                     # Check migration status
uv run trading-bot postgresql migrate --command verify   # Verify migration
uv run trading-bot postgresql reset                      # Reset PostgreSQL (WARNING!)

# Foundation strategy analysis with Price Action layer
uv run trading-bot foundation analyze --symbol EURUSD --timeframe H1
uv run trading-bot foundation price-action EURUSD --timeframe H1 --trading-type day_trading

# Development with mandatory testing
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95  # Critical components
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/trading_bot/

# CRITICAL: Always validate dry-run after changes
uv run trading-bot start --dry-run

# Code quality cleanup after implementation
uv run ruff check src/ tests/ --fix
uv run black src/ tests/
```

## Key Configuration Files

### Core Configuration Structure
- `config/default.yaml`: Base configuration
- `config/postgresql.yaml`: PostgreSQL-specific configuration
- `config/trading_parameters.yaml`: Asset-specific trading rules
- `config/strategy_parameters.yaml`: Strategy settings with technical indicators
- `config/trading_types.yaml`: Trading type configurations (scalping, day, swing, position)
- `config/risk_parameters.yaml`: Advanced risk management with volume calculation
- `config/broker_symbols.yaml`: Broker-specific symbol mappings
- `config/technical_indicators.yaml`: RSI and Moving Average settings
- `config/windows.yaml`: Windows-specific settings

### Database Configuration
- `.env`: Environment variables (DATABASE_URL for PostgreSQL)
- `.env.example`: Environment variables template
- `alembic.ini`: Alembic migration configuration
- `alembic/env.py`: Migration environment with async PostgreSQL support

### Configuration Hierarchy (Priority)
1. Environment Variables
2. Environment-specific YAML
3. Strategy/Trading/Risk YAML files
4. Default YAML
5. Hardcoded defaults

## Critical Implementation Rules

### Asset-Specific Pip Values
```python
# Asset class pip calculations - CRITICAL for position sizing
PIP_VALUES = {
    "forex_major": 0.0001,    # EURUSD, GBPUSD, etc.
    "forex_jpy": 0.01,        # USDJPY, EURJPY, etc.
    "commodities": 0.1,       # XAUUSD (Gold)
    "crypto": 1.0             # BTCUSD, ETHUSD
}
```

### Position Management Rules
- **Maximum 1 trade per symbol** across all strategies
- **Asset-specific breakeven/trailing settings**
- **Multi-timeframe confluence required** (minimum 65% score)
- **Market hours validation** before execution

### Enhanced Strategy Architecture 🎯 **FOUNDATION READY**
**Foundation-First Approach**: ✅ Supply & Demand zones are COMPLETED and production-ready!

```yaml
# Strategy execution workflow - FOUNDATION & ENHANCEMENTS COMPLETED
confluence_weights:
  foundation: 0.30           # ✅ S&D zones (COMPLETED)
  trendline: 0.20            # ✅ Trendline confluence (COMPLETED)
  price_action: 0.15         # ✅ Pattern confirmation (COMPLETED)
  fibonacci: 0.12            # ✅ Level confluence (COMPLETED)
  breakout_retest: 0.12      # ✅ Structure validation (COMPLETED)
  market_structure: 0.08     # ✅ BOS/CHoCH alignment (COMPLETED)
  rsi: 0.10                  # ✅ RSI Analysis (COMPLETED)
  ma: 0.08                   # ✅ Moving Average (COMPLETED)
  volume_profile: 0.05       # Future enhancement
  multi_timeframe: 0.05      # Future enhancement
```

### Broker Symbol Mapping
**Universal Compatibility**: Automatic symbol conversion for different brokers.

```yaml
# Example broker configurations
exness_standard: EURUSDm    # Standard accounts
exness_cent: EURUSDc        # Cent accounts
xm: GOLD (for XAUUSD)       # Special mappings
oanda: EUR_USD              # Underscore format
```

### Real-time Pip Tracking & Automated Features
Complete position management system with comprehensive pip tracking and automated features:

```yaml
# Position Management Features
position_features:
  pip_tracking:
    real_time_calculations: true      # Live pip profit/loss tracking
    usd_amount_tracking: true         # Risk and profit in USD
    asset_specific_pip_values: true   # 0.0001 (EUR/USD), 0.01 (USD/JPY), etc.

  automation_features:
    breakeven_triggers: true          # Auto-move SL to entry + buffer
    trailing_stops: true              # Dynamic trailing stop management
    partial_closes: true              # 25% at level 1, 50% at level 2
    sl_tp_monitoring: true            # Automatic SL/TP execution

  asset_specific_settings:
    forex_major: "15 pips breakeven, 10 pips trailing"
    forex_jpy: "150 pips breakeven, 100 pips trailing"
    commodities: "500 pips breakeven for Gold"
    crypto: "50 USD breakeven, 30 USD trailing"
```

### Position Lifecycle Management
```python
# Complete position lifecycle with pip tracking
position_lifecycle:
  1_creation: "Signal → Risk validation → Position with pip data"
  2_monitoring: "Real-time price updates → Pip calculations → P&L tracking"
  3_automation: "Breakeven → Trailing → Partial closes → Final close"
  4_reporting: "Complete P&L history → Risk metrics → Performance tracking"
```

### Database Schema
```sql
-- Enhanced positions table with pip tracking
CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    -- ... standard fields ...
    pip_size REAL NOT NULL,                -- Asset-specific pip size
    pip_value_per_lot REAL NOT NULL,       -- USD value per pip
    current_profit_pips REAL DEFAULT 0.0,  -- Real-time pip profit
    risk_amount_usd REAL,                  -- USD amount at risk
    potential_profit_usd REAL,             -- USD potential profit
    current_pnl_usd REAL DEFAULT 0.0       -- Current P&L in USD
);
```

## 🧪 Test-Driven Development (TDD) Workflow

### TDD First Development Approach
**MANDATORY**: All features MUST be developed using TDD methodology with Red-Green-Refactor cycle.

#### TDD Process Requirements
1. **Red Phase**: Write failing test first
2. **Green Phase**: Write minimal code to pass test
3. **Refactor Phase**: Improve code while keeping tests green
4. **Repeat**: For every feature and component

#### Testing Infrastructure
```python
# Required testing setup (already configured in pyproject.toml)
dependencies = [
    "pytest>=7.4.0",           # Core testing framework
    "pytest-asyncio>=0.21.0",  # Async testing support
    "pytest-cov>=4.1.0",       # Coverage reporting
    "hypothesis>=6.140.3",     # Property-based testing
    "factory-boy>=3.3.0",      # Test data generation
    "freezegun>=1.2.2",        # Time mocking
    "responses>=0.23.0",       # HTTP mocking
]
```

#### Testing Standards
```yaml
coverage_requirements:
  minimum_coverage: 85%         # 85% minimum overall coverage
  critical_components: 95%      # 95% for risk management, position sizing
  new_features: 100%           # 100% coverage for all new features

testing_categories:
  unit_tests: "Individual component testing"
  integration_tests: "Component interaction testing"
  property_tests: "Mathematical invariant testing with Hypothesis"
  end_to_end_tests: "Complete workflow testing"

testing_workflow:
  - "Write failing test"
  - "Run test suite (should fail)"
  - "Write minimal implementation"
  - "Run test suite (should pass)"
  - "Refactor and optimize"
  - "Run test suite (should still pass)"
  - "Commit with tests"
```

#### Mandatory Test Commands
```bash
# Before any commit - ALL must pass
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85
uv run pytest tests/unit/test_risk_*.py --cov-fail-under=95  # Critical components
uv run pytest tests/properties/ --hypothesis-show-statistics  # Property tests
uv run black src/ tests/  # Code formatting
uv run ruff check src/ tests/  # Linting
uv run mypy src/trading_bot/  # Type checking

# Final validation
uv run trading-bot start --dry-run  # Must run without errors
```

## 🐘 Database Architecture

### Database Support Options
- **SQLite** (default): Development and testing with `sqlite+aiosqlite:///trading_bot.db`
- **PostgreSQL** (production): High-performance production database with asyncpg driver

### Migration Architecture
```python
# Environment-based database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///trading_bot.db")

# PostgreSQL for production
DATABASE_URL="postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_db"

# SQLite for development
DATABASE_URL="sqlite+aiosqlite:///trading_bot.db"
```

### Migration Commands
```bash
# Complete migration process
uv run trading-bot postgresql migrate

# Step-by-step migration control
uv run trading-bot postgresql migrate --command setup     # Setup PostgreSQL
uv run trading-bot postgresql migrate --command backup    # Backup SQLite data
uv run trading-bot postgresql migrate --command migrate   # Run Alembic migration
uv run trading-bot postgresql migrate --command transfer  # Transfer data
uv run trading-bot postgresql migrate --command verify    # Verify success

# Migration status and management
uv run trading-bot postgresql status                      # Check migration status
uv run trading-bot postgresql reset                       # Reset (WARNING: deletes data)
```

### PostgreSQL Schema Features
- **ENUM Types**: Proper PostgreSQL enums for trade_status, position_update_type
- **JSONB Support**: Native JSON handling for zones and indicators
- **GIN Indexes**: Optimized indexes for JSONB columns
- **Sequences**: Auto-incrementing primary keys with proper sequences
- **Foreign Keys**: Referential integrity across related tables

### Production Considerations
- **Connection Pooling**: Advanced connection pooling with asyncpg
- **SSL Support**: Secure database connections for production
- **Performance**: Optimized queries and indexes for high-frequency trading
- **Backup Strategy**: Automated backup procedures for production data

## Multi-Timeframe Analysis (Trading Type Adaptive)
### Timeframe Selection by Trading Type
```yaml
timeframe_matrix:
  scalping: ["M1", "M5", "M15"]      # Ultra-short term
  day_trading: ["M15", "H1", "H4"]   # Intraday focus
  swing_trading: ["H4", "D1", "W1"]  # Multi-day analysis
  position_trading: ["D1", "W1", "MN1"] # Long-term trends
```
- **Adaptive Analysis**: Timeframes automatically adjust to trading type
- **Speed Optimization**: 5sec (scalping) → 60sec (position) analysis time
- **Cache Strategy**: Real-time (scalping) → Daily (position) updates
- **Technical indicators**: RSI and Moving Averages optimized per timeframe

## Technical Indicators Implementation
### Required Libraries (Windows-Compatible)
```bash
# Primary (always works)
uv add pandas-ta ta numpy pandas

# Optional high-performance (may require setup)
conda install -c conda-forge ta-lib
```

### Key Features
- **RSI Analysis**: Overbought/oversold levels, divergence detection
- **Moving Averages**: EMA 9/21/50, SMA 200, trend alignment
- **Multi-timeframe confluence**: Technical indicators across H1, H4, D1
- **Automatic fallback**: pandas-ta → TA-Lib → ta library → manual
- **Performance optimized**: Cached calculations, vectorized operations

## Trading Types System
### Available Trading Types
```yaml
# 4 complete trading styles with adaptive parameters
trading_types:
  scalping:     # 1-240 minutes, M1/M5, High frequency (20 trades/day)
  day_trading:  # 30-1440 minutes, M15/H1, Balanced (8 trades/day)
  swing_trading: # 1-7 days, H4/D1, Multi-day trends (2 trades/day)
  position_trading: # 1-4 weeks, D1/W1, Long-term trends (1 trade/day)
```

### Adaptive Features by Type
- **Dynamic Risk**: 0.2% (scalping) → 1.2% (position trading)
- **Timeframe Optimization**: M1-M15 (scalping) → D1-MN1 (position)
- **Strategy Weights**: Technical-heavy (scalping) → Fundamental-heavy (position)
- **Position Management**: Tight stops (5-15 pips) → Wide stops (150-400 pips)
- **Session Awareness**: Preferred trading sessions per type
- **Volume Calculation**: Intelligent position sizing based on risk and stop distance

## Advanced Risk Management System
Multi-layer protection system with portfolio risk control, real-time monitoring, and intelligent volume calculation. Risk configuration in `config/risk_parameters.yaml` with:
- Max 2% portfolio risk, 1% daily loss limit, 15% emergency stop
- Asset-specific pip values and trading type risk scaling
- Multi-layer protection: position → portfolio → account level

## Code Quality Standards

⚠️ **MANDATORY**: Follow coding standards defined in `docs/guides/coding-standards.md`

- **Type hints** required (mypy validation)
- **Async-first** architecture throughout
- **No hardcoded values** (use YAML configuration)
- **SQLAlchemy 2.0** modern async syntax
- **Comprehensive testing** with pytest
- **TDD-First Development** - Write failing tests before implementation
- **ORM + Repository Pattern** - Use SQLAlchemy ORM with clean data access layer
- **Maintainable Code Principles**:
  - Single Responsibility Principle (SRP)
  - Dependency Injection for testability
  - Clean Architecture with clear separation of concerns
  - Configuration management through environment variables
  - Modular design with proper abstractions
- **Code Documentation**:
  - Docstrings for all public functions and classes
  - Type hints for all function parameters and returns
  - Clear variable and function naming
  - Consistent code style with Black formatting

### 📋 Coding Standards Reference
See **`docs/guides/coding-standards.md`** for complete guidelines:
- Project structure and directory layout
- Naming conventions (files, classes, functions, variables)
- Code style and formatting rules
- Documentation standards
- Testing requirements
- Import organization
- Error handling patterns
- Configuration management
- Logging standards
- Complete code examples

**Before any code changes**: Review coding standards document to ensure compliance.

## Testing Requirements (MANDATORY)
### Test Coverage Requirements
```bash
# Minimum test coverage for all new features
minimum_coverage: 85%              # 85% minimum code coverage
critical_components: 95%           # 95% for risk management, volume calculation
new_features: 100%                 # 100% coverage for all new features
```

### Test Execution Requirements
```bash
# All tests must pass before any commit
uv run pytest tests/ --cov=src/trading_bot --cov-report=term-missing
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ --mt5  # MT5 integration tests
uv run pytest tests/properties/ --hypothesis-show-statistics

# CRITICAL: Final validation - dry-run must work without errors
uv run trading-bot start --dry-run

# Final code quality cleanup
uv run ruff check src/ tests/ --fix
uv run black src/ tests/
```

### New Feature Testing Protocol
**MANDATORY**: For every new feature - 100% unit test coverage, integration tests, property tests with Hypothesis, and performance validation. One test file per module, no redundant files.

### Continuous Integration Requirements
**MANDATORY**: Pre-commit hooks (black, ruff, mypy, tests, dry-run), automated testing on PR/main, 85%+ coverage (95% for critical), performance benchmarks (volume calc <1ms, trading loop <55s), manual approval for production.

## Performance Targets
- Trading loop: <55 seconds execution time
- Database queries: <100ms response time
- Memory usage: <2GB under normal load
- MT5 operations: <1 second for execution

## Windows/MT5 Requirements
- **Windows 10/11 required** (MT5 limitation)
- **Python 3.11+** for modern async features
- **Administrative privileges** may be required
- **Auto-detection** of MT5 installation

## Documentation Reference
For detailed implementation guides, see `docs/` directory:

**Core Implementation:**
- `setup/configuration-guide.md`: Complete config management
- `architecture/architecture-guide.md`: System architecture details
- `guides/strategy-guide.md`: Strategy development
- `trading/trading-types-guide.md`: Trading types (scalping, day, swing, position)
- `trading/risk-management-guide.md`: **Complete Risk Management System** ✅ **UPDATED with Architecture Diagrams**
- `guides/multi-timeframe-guide.md`: Adaptive timeframe analysis
- `trading/position-management-architecture.md`: **Position Management System** with pip tracking ✅ **NEW**

**Technical Components:**
- `trading/technical-indicators-guide.md`: RSI & Moving Average implementation
- `setup/broker-symbol-mapping-guide.md`: Multi-broker compatibility
- `setup/asset-configuration-guide.md`: Asset-specific settings
- `guides/multi-timeframe-guide.md`: Multi-timeframe analysis

**Operations & Integration:**
- `setup/windows-setup-guide.md`: Windows/MT5 setup
- `guides/cli-reference.md`: Complete CLI commands
- `trading/notifications-guide.md`: Telegram notification system

**Database & Architecture:**
- `diagrams/database-erd.md`: **Database ERD** with entity relationships ✅ **NEW**
- `diagrams/position-management-flow.mermaid`: **Position Management Flow** diagram ✅ **NEW**
- `diagrams/risk-management-architecture.mermaid`: **Risk Management System Architecture** diagrams ✅ **NEW**

**Quality Assurance (CRITICAL):**
- `testing-guide.md`: Comprehensive testing strategy and requirements
- `volume-calculation-testing.md`: Critical volume calculation test cases
- `risk-management-testing.md`: Risk management validation protocols
