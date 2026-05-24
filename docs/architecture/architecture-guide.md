# Architecture Guide

Trading bot system architecture and design patterns.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Trading Bot                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    CLI Interface                        │ │
│  │                   (Click + Rich)                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   Main Orchestrator                     │ │
│  │                     (main.py)                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│     ┌─────────────────────┼─────────────────────┐           │
│     │                     │                     │           │
│  ┌──▼──────────┐    ┌────▼─────┐         ┌────▼─────┐      │
│  │  Strategy   │    │ Position │         │   Risk   │      │
│  │   Engine    │    │ Manager  │         │ Manager  │      │
│  └─────────────┘    └──────────┘         └──────────┘      │
│                                                    │        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  MT5 Connector                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                    │        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 Database (SQLAlchemy)                    │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Strategy Engine

**Location**: `src/trading_bot/strategies/`

- **Foundation**: Supply & Demand zone detection
- **Enhancement Layers**: 7 additional analysis layers
- **Signal Aggregator**: Combines all signals with confluence scoring

**Flow**:
```
Zone Detection → Trendline → Price Action → Fibonacci →
Breakout → Structure → RSI → MA → Signal Aggregation
```

### 2. Position Manager

**Location**: `src/trading_bot/position/`

- **Asset Managers**: Forex, JPY, Commodities, Crypto
- **Automation**: Breakeven, Trailing, Partial Close
- **Pip Tracking**: Real-time P&L calculation

**Features**:
- Asset-specific pip values
- Automated breakeven (70% of SL)
- Dynamic trailing stops
- Multi-level profit taking

### 3. Risk Manager

**Location**: `src/trading_bot/risk/`

- **Portfolio Risk**: Total exposure limits
- **Position Risk**: Per-trade risk calculation
- **Drawdown Protection**: Emergency stop at 15%
- **Correlation Monitor**: Avoid correlated overexposure

### 4. MT5 Connector

**Location**: `src/trading_bot/connectors/`

- **Connection**: Auto-reconnect with retry logic
- **Account**: Balance, equity, margin tracking
- **Orders**: Market and pending order execution
- **Data**: OHLCV and tick data retrieval

### 5. Database Layer

**Location**: `src/trading_bot/data/`

- **Models**: SQLAlchemy ORM models
- **Repositories**: Data access layer
- **Services**: Business logic (account sync, selector)

**Supports**: SQLite (dev) and PostgreSQL (production)

## Design Patterns

### Async-First Architecture

All I/O operations use async/await:

```python
async def trading_loop(self):
    while self.is_running:
        # Parallel analysis
        tasks = [self.analyze_symbol(s) for s in symbols]
        results = await asyncio.gather(*tasks)

        # Process results
        for result in results:
            if result:
                await self.execute_trade(result)

        await asyncio.sleep(60)  # Non-blocking
```

### Repository Pattern

Data access through repository classes:

```python
class AccountRepository:
    async def get_by_account_id(self, account_id: int):
        # Database access logic

    async def update_balance(self, account_id: int, balance: float):
        # Update logic
```

### Factory Pattern

Trading type executors created by factory:

```python
executor = ExecutorFactory.create_executor(
    trading_type="day_trading",
    config=config,
    foundation_engine=foundation,
    position_manager=position_manager
)
```

## Trading Loop

```
1. Initialize
   ├─ Connect to MT5
   ├─ Load configuration
   └─ Start services

2. Trading Cycle (repeats every 60 seconds)
   ├─ Scan active symbols
   ├─ Analyze each symbol (parallel)
   │  ├─ Foundation analysis (S&D zones)
   │  ├─ Enhancement layers (7 layers)
   │  └─ Aggregate signals (65%+ threshold)
   ├─ Validate risk
   │  ├─ Position sizing
   │  ├─ Portfolio exposure
   │  └─ Correlation check
   ├─ Execute trades
   │  ├─ Send order to MT5
   │  └─ Track position
   └─ Manage positions
      ├─ Update P&L
      ├─ Breakeven triggers
      ├─ Trailing stops
      └─ Partial closes

3. Shutdown
   ├─ Close all positions (optional)
   ├─ Disconnect from MT5
   └─ Save state
```

## Configuration

Located in `config/` directory:

| File | Purpose |
|------|---------|
| `default.yaml` | Base configuration |
| `development.yaml` | Development settings |
| `production.yaml` | Production settings |
| `trading_types.yaml` | Trading type configs |
| `trading_parameters.yaml` | Asset-specific params |

## Database Schema

**Key Tables**:
- `trading_accounts` - Account information
- `positions` - Open/closed positions
- `supply_demand_zones` - Detected zones
- `risk_alerts` - Risk notifications

See [Database ERD](database-erd.md) for complete schema.

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Package Manager** | UV |
| **CLI** | Click + Rich |
| **Database** | SQLAlchemy 2.0 (async) |
| **Database Engines** | SQLite, PostgreSQL |
| **Logging** | Loguru |
| **Testing** | Pytest + Hypothesis |
| **Code Quality** | Black, Ruff, MyPy |

## Directory Structure

```
src/trading_bot/
├── cli.py                  # CLI entry point
├── config.py               # Configuration management
├── main.py                 # Main orchestrator
├── connectors/             # MT5 integration
├── data/                   # Database layer
│   ├── models.py           # SQLAlchemy models
│   ├── repositories/       # Data access
│   └── services/           # Business logic (account sync, selector)
├── executors/              # Trading type executors
├── position/               # Position management
│   ├── automation/         # Breakeven, trailing, partial close
│   └── asset_managers/     # Asset-specific logic
├── risk/                   # Risk management
├── strategies/             # Trading strategies
│   ├── foundation/         # S&D zones
│   └── enhancement/        # 7 enhancement layers
├── exceptions/             # Custom exceptions (MT5, connector, strategy)
├── analytics/              # Performance analysis (standalone)
└── utils/                  # Utilities
```

## Related Documentation

- [Database ERD](database-erd.md) - Complete database schema
- [Trading Types Guide](trading/trading-types-guide.md) - Trading type details
- [Position Management Architecture](trading/position-management-architecture.md) - Position system
- [Risk Management Guide](trading/risk-management-guide.md) - Risk framework
