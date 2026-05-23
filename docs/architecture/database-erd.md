# Database ERD

Trading bot database schema and entity relationships.

## Schema Status

| Status | Count |
|--------|-------|
| ✅ Implemented | 5 tables |
| ⏳ In Progress (Phase 5.5) | 3 tables |
| 📋 Planned | 5 tables |
| **Target** | **14 tables** |

## Tables

### ✅ Implemented

| Table | Purpose |
|-------|---------|
| `trading_accounts` | Multi-account support (MT5 accounts) |
| `trading_sessions` | Session-level tracking |
| `positions` | Position management with pip tracking |
| `supply_demand_zones` | S&D zone detection results |
| `config_snapshots` | Configuration versioning |

### ⏳ In Progress

| Table | Purpose |
|-------|---------|
| `trading_signals` | Signal generation history |
| `position_modifications` | Breakeven/trailing audit |
| `partial_closes` | Partial close tracking |

### 📋 Planned

| Table | Purpose |
|-------|---------|
| `market_data` | OHLCV data for charting |
| `risk_metrics` | Real-time risk calculations |
| `symbol_info` | Dynamic symbol configuration |
| `risk_violations` | Risk alert history |
| `system_health` | System monitoring |

## Entity Relationships

```mermaid
erDiagram
    TRADING_ACCOUNTS ||--o{ TRADING_SESSIONS : has
    TRADING_ACCOUNTS ||--o{ POSITIONS : owns
    TRADING_SESSIONS ||--o{ POSITIONS : contains
    TRADING_SESSIONS ||--o{ TRADING_SIGNALS : generates
    POSITIONS ||--o{ POSITION_MODIFICATIONS : tracks
    POSITIONS ||--o{ PARTIAL_CLOSES : has
    TRADING_SIGNALS ||--o| POSITIONS : creates
    SUPPLY_DEMAND_ZONES ||--o{ TRADING_SIGNALS : references
    CONFIG_SNAPSHOTS ||--o{ TRADING_SESSIONS : applies_to

    TRADING_ACCOUNTS {
        int id PK
        int account_id "MT5 number"
        string broker_name
        string account_type "DEMO/LIVE"
        string currency
        decimal balance
        decimal equity
        int leverage
        bool is_active
    }

    TRADING_SESSIONS {
        int id PK
        int account_id FK
        timestamp started_at
        timestamp ended_at
        decimal total_pnl_usd
        int total_trades
        decimal win_rate
        bool is_backtest
    }

    POSITIONS {
        string position_id PK
        int session_id FK
        int account_id FK
        string symbol
        string action "BUY/SELL"
        decimal entry_price
        decimal current_price
        decimal sl
        decimal tp
        decimal volume
        decimal pip_size
        decimal current_profit_pips
        decimal current_pnl_usd
        decimal risk_amount_usd
        string status "OPEN/CLOSED"
    }

    TRADING_SIGNALS {
        int id PK
        int session_id FK
        string symbol
        string action
        decimal confidence
        json foundation_score
        json enhancement_scores
        string status
    }

    SUPPLY_DEMAND_ZONES {
        int id PK
        string symbol
        string timeframe
        string zone_type
        decimal upper_price
        decimal lower_price
        decimal strength_score
        decimal freshness_score
    }

    POSITION_MODIFICATIONS {
        int id PK
        string position_id FK
        string modification_type
        decimal old_value
        decimal new_value
        string reason
    }

    PARTIAL_CLOSES {
        int id PK
        string position_id FK
        decimal volume_closed
        decimal close_price
        decimal pnl_usd
        string level "TP1/TP2/TP3"
    }

    CONFIG_SNAPSHOTS {
        int id PK
        string config_hash
        json config_json
    }
```

## Database Engines

- **Development**: SQLite (`sqlite+aiosqlite:///trading_bot.db`)
- **Production**: PostgreSQL (`postgresql+asyncpg://...`)

## Migrations

Managed by **Alembic**:

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current
```

## Implementation Files

- **Models**: [src/trading_bot/data/models.py](../../src/trading_bot/data/models.py)
- **Repositories**: [src/trading_bot/data/repositories/](../../src/trading_bot/data/repositories/)
- **Migrations**: [alembic/versions/](../../alembic/versions/)
