# 🤖 Trading Bot - Modern Python Trading System

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-400%2B%20passing-success.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-98%25-success.svg)](htmlcov/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

🚀 **Phase 3 Completed: Position Management & Risk Control System Integrated**

A sophisticated, production-ready automated trading bot built with modern Python architecture for multi-asset trading (Forex, Commodities, Crypto) with MetaTrader5 integration.

## 🌟 Current Status (Dec 6, 2025)

- ✅ **Phase 1: Core Architecture** (Completed)
- ✅ **Phase 2: Foundation Strategy** (Completed - Supply & Demand)
- ✅ **Phase 2.5: Integration Layer** (Completed - Strategy Orchestration)
- ✅ **Phase 3: Position & Risk** (Completed - Live Management)
- ✅ **Phase 4: Monitoring** (Completed - Telegram Notifications)
- ⏳ **Phase 5: Enhancement** (Future - Advanced Strategies)

## ✨ Features

### 📡 Real-Time Monitoring
- **Telegram Alerts**: Instant notifications for trades, errors, and updates
- **Heartbeat System**: Periodic health checks (Balance & Status)
- **Smart Formatting**: Clear, emoji-rich status messages
- **Non-Blocking**: Async queue architecture guarantees performance

### 🧠 Intelligent Strategy System
- **Supply & Demand**: Advanced zone detection and validation
- **Multi-Timeframe**: Adaptive analysis (M1 to W1)
- **Confluence Scoring**: Weighted signal generation
- **Dynamic Configuration**: Strategy parameters adjustable via YAML

### 🛡️ Robust Risk Management
- **Portfolio Protection**: Max 2% risk per trade, 1% daily loss limit
- **Drawdown Control**: Emergency stop at 15% drawdown
- **Exposure Limits**: Asset class and symbol-specific limits
- **Capital Preservation**: Auto-sizing based on account balance

### 💼 Advanced Position Management
- **Real-time Tracking**: Live pip and USD P&L monitoring
- **Smart Automation**: 
  - 🔄 **Breakeven**: Auto-move SL to entry + buffer
  - 📉 **Trailing Stop**: Dynamic profit locking
  - ✂️ **Partial Close**: Multi-target profit taking
- **Asset Logic**: Specific handling for Forex, Gold, Crypto

### Core Architecture
- 🏗️ **Modern Stack**: UV + Click + SQLAlchemy 2.0 + Pydantic
- 🔌 **MT5 Integration**: Complete MetaTrader5 platform integration
- 🧪 **Test-Driven Development**: 400+ tests passing (100% success rate)
- ⚡ **Async-First**: Modern async/await architecture throughout

## 📦 Installation

```bash
# Install dependencies
uv sync

# Install with development tools
uv sync --extra dev

# Install with all optional dependencies
uv sync --all-extras
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create development environment file
cat > .env.dev << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
LOG_LEVEL=DEBUG
DRY_RUN=true
EOF
```

### 2. Run the Bot

```bash
# Install dependencies
uv sync

# Start in SAFE mode (mock MT5, no risk)
uv run trading-bot start --dry-run
# → Mock MT5, simulated data, works offline, zero risk ✅

# Start with REAL MT5 data (but simulated orders)
uv run trading-bot start --dry-run --connect-mt5
# → Real MT5, real data, simulated orders, zero risk ✅

# Start in LIVE mode (REAL TRADING - use with caution!)
uv run trading-bot start
# → Real MT5, real data, REAL ORDERS, ⚠️ REAL MONEY AT RISK

# Show status
uv run trading-bot status

# Validate configuration
uv run trading-bot config validate
```

### 3. Available Commands

```bash
# Bot Control
uv run trading-bot start                    # Start bot
uv run trading-bot start --dry-run          # Start in dry-run mode
uv run trading-bot stop                     # Stop bot
uv run trading-bot status                   # Show status
uv run trading-bot version                  # Show version

# Configuration
uv run trading-bot config validate          # Validate config
uv run trading-bot config show              # Show config (safe)

# MT5 Integration
uv run trading-bot mt5 connect              # Connect to MT5
uv run trading-bot mt5 disconnect           # Disconnect from MT5
uv run trading-bot mt5 status               # MT5 connection status

# Account Management
uv run trading-bot account info             # Show account info
```

## 📋 Project Structure

```
trading-bot/
├── src/trading_bot/
│   ├── __init__.py
│   ├── cli.py              # Click CLI interface
│   ├── config.py           # Configuration management
│   ├── main.py             # Main bot orchestrator
│   ├── connectors/         # MT5 integration
│   │   ├── mt5_connector.py       # MT5 connection handler
│   │   ├── account_manager.py     # Account operations
│   │   ├── symbol_manager.py      # Symbol management
│   │   ├── order_manager.py       # Order execution
│   │   ├── position_manager.py    # Position tracking
│   │   └── data_manager.py        # Market data retrieval
│   ├── core/               # Core components
│   ├── data/               # Database layer
│   ├── utils/              # Utilities
│   └── exceptions/         # Custom exceptions
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── utils/              # Test utilities
├── config/                 # Configuration files
│   ├── default.yaml
│   └── development.yaml
├── backup/                 # Backup of old code
│   ├── src/
│   └── tests/
└── docs/                   # Documentation
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/trading_bot --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_config.py -v

# Run integration tests only
uv run pytest tests/integration/ -v
```

## 🔧 Development

```bash
# Code formatting
uv run black src/ tests/

# Linting
uv run ruff check src/ tests/ --fix

# Type checking
uv run mypy src/trading_bot/

# Run all quality checks
uv run black src/ tests/ && uv run ruff check src/ tests/ --fix && uv run mypy src/trading_bot/
```

## 📚 Implementation Status

### ✅ Phase 0: Foundation (COMPLETED)
- ✅ Modern project structure with clean architecture
- ✅ Configuration system (Pydantic + YAML + .env)
- ✅ Database layer (SQLAlchemy 2.0 async, SQLite + PostgreSQL)
- ✅ Logging system (Loguru with rotation)
- ✅ CLI interface (Click + Rich output)
- ✅ Custom exception hierarchy
- ✅ **16/16 tests passing** (100% success rate)

### ✅ Phase 1: MT5 Integration (COMPLETED)
- ✅ **MT5 Connector** - Connection management with retry logic
- ✅ **Account Manager** - Balance, equity, margin monitoring
- ✅ **Symbol Manager** - Symbol discovery and validation
- ✅ **Order Manager** - Market/pending orders with validation
- ✅ **Position Manager** - Real-time position tracking
- ✅ **Data Manager** - OHLCV and tick data retrieval
- ✅ **Test Infrastructure** - Mock helpers and data generators
- ✅ **Security** - Credential protection in logs

### 🔄 Phase 2: Trading Strategies (Next)
- ⏳ Supply & Demand zone detection
- ⏳ Multi-timeframe analysis
- ⏳ Strategy framework
- ⏳ Advanced risk management
- ⏳ Position automation (breakeven, trailing)

### 📊 Test Results
```
✅ 16/16 tests passing (100%)
📈 33% code coverage (foundation layer)
⚡ 0.61s execution time
🎯 0 failures, 0 errors
```

## 🔑 Environment Variables

### Quick Setup

Create environment-specific files:

**Development (`.env.dev`):**
```bash
# Database (SQLite for local development)
DATABASE_URL=sqlite+aiosqlite:///./trading_bot_dev.db

# MT5 Demo Account
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ENABLED=true

# Trading (Conservative for testing)
TRADING_RISK_PER_TRADE=0.001  # 0.1%
TRADING_MAX_POSITIONS=3

# Logging
LOG_LEVEL=DEBUG

# Mode
DRY_RUN=true  # No real trades
```

**Production (`.env.prd`):**
```bash
# ⚠️ WARNING: LIVE TRADING with REAL MONEY

# Database (PostgreSQL recommended)
DATABASE_URL=postgresql+asyncpg://trading_bot_user:password@localhost:5432/trading_bot_prd

# MT5 Real Account
MT5_LOGIN=your_real_login
MT5_PASSWORD=your_real_password
MT5_SERVER=YourBroker-Real

# Telegram
TELEGRAM_BOT_TOKEN=your_production_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TELEGRAM_ENABLED=true

# Trading
TRADING_RISK_PER_TRADE=0.005  # 0.5%
TRADING_MAX_POSITIONS=5

# Emergency Stop
EMERGENCY_STOP_ENABLED=true
DAILY_LOSS_LIMIT_PERCENT=5.0

# Mode
DRY_RUN=false  # ⚠️ LIVE TRADING ENABLED
```

### Usage

```bash
# Development (loads .env.dev automatically)
uv run trading-bot --config development start

# Production (loads .env.prd automatically)
uv run trading-bot --config production start
```

**📖 Full guide:** See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)

## 📖 Documentation

For detailed documentation, see the `docs/` directory:

- `CLAUDE.md` - AI assistant guidance
- `PHASE0_TODO.md` - Phase 0 implementation
- `PHASE1_TODO.md` - Phase 1 implementation
- `docs/planning/roadmap.md` - Complete roadmap

## ⚠️ Windows Requirements

- Windows 10/11 (for MT5 integration)
- Python 3.12+
- MetaTrader5 terminal installed

## 🤝 Contributing

This is a rebuild project following TDD methodology. All contributions should:
- Include comprehensive tests
- Follow Black code formatting
- Pass Ruff linting
- Pass MyPy type checking
- Maintain 85%+ test coverage

## 📝 License

MIT License - See LICENSE file for details

## 🎯 Getting Started

### Prerequisites
- **Windows 10/11** (for MT5 integration)
- **Python 3.12+**
- **MetaTrader5** terminal installed and running
- Demo/Real trading account with credentials

### ✅ MT5 Connection Status
**Status**: ✅ **WORKING** - Fully functional MT5 integration!

```bash
# Test MT5 connection
uv run trading-bot mt5 connect
# Output: SUCCESS: Connected to MT5 successfully!
```

**Note**: CLI commands are one-time tests. For persistent connection, use:
```bash
uv run trading-bot start --dry-run
```

### Step-by-Step Setup

1. **Clone and Install**
   ```bash
   git clone <repository>
   cd trading-bot
   uv sync
   ```

2. **Create Environment File**
   ```bash
   # Copy template and edit with your credentials
   cp .env.example .env.dev
   nano .env.dev
   ```

3. **Test the System**
   ```bash
   # Run tests
   uv run pytest tests/ -v
   
   # Validate configuration
   uv run trading-bot config validate
   
   # Check status
   uv run trading-bot status
   ```

4. **Start Trading (Dry-Run)**
   ```bash
   uv run trading-bot --config development start --dry-run
   ```

5. **Connect to MT5** (Windows only)
   ```bash
   uv run trading-bot mt5 connect
   uv run trading-bot account info
   ```

---

**Built with ❤️ using modern Python best practices**
