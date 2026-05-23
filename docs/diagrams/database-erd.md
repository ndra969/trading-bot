# Database ERD

Entity relationship diagram for the trading bot database schema.

## Current State

| Status | Tables | Completion |
|--------|--------|------------|
| **Implemented** | 8 | ~50% |
| **Target** | 14 | 100% |

### Implemented Tables
- `supply_demand_zones` - S&D zone tracking
- `positions` - Position management
- `trading_accounts` - Multi-account support
- `trading_sessions` - Session grouping
- `trading_signals` - Signal tracking
- `config_snapshots` - Config versioning
- `position_modifications` - Modification audit
- `partial_closes` - Profit-taking tracking

### In Progress
- `market_data` - OHLCV storage
- `risk_metrics` - Risk tracking

### Planned
- `symbol_info` - Dynamic symbol config
- `risk_violations` - Risk alerts
- `system_health` - Monitoring

## Entity Relationship Diagram

```mermaid
erDiagram
    TRADING_SESSIONS {
        string session_id PK
        string trading_type
        boolean dry_run
        datetime start_time
        datetime end_time
        string status
    }

    POSITIONS {
        string position_id PK
        string session_id FK
        string symbol
        string direction
        float entry_price
        float volume
        float current_profit_pips
        float current_pnl_usd
        datetime entry_time
        string status
    }

    TRADING_SIGNALS {
        string signal_id PK
        string session_id FK
        string zone_id FK
        string symbol
        string direction
        float final_confidence
        string signal_status
    }

    SUPPLY_DEMAND_ZONES {
        string zone_id PK
        string session_id FK
        string symbol
        string zone_type
        float strength_score
        boolean is_valid
    }

    TRADING_ACCOUNTS {
        string account_id PK
        string broker_name
        string account_type
        float balance
        float equity
    }

    RISK_METRICS {
        string risk_id PK
        string session_id FK
        float account_balance
        float total_exposure
        float daily_pnl
    }

    MARKET_DATA {
        string data_id PK
        string symbol
        datetime timestamp
        float open_price
        float high_price
        float low_price
        float close_price
    }

    TRADING_SESSIONS ||--o{ POSITIONS : "manages"
    TRADING_SESSIONS ||--o{ TRADING_SIGNALS : "generates"
    TRADING_SESSIONS ||--o{ SUPPLY_DEMAND_ZONES : "analyzes"
    TRADING_SESSIONS ||--o{ RISK_METRICS : "tracks"
    SUPPLY_DEMAND_ZONES ||--o{ TRADING_SIGNALS : "triggers"
    TRADING_SIGNALS ||--o{ POSITIONS : "creates"
    TRADING_ACCOUNTS ||--o{ POSITIONS : "holds"
```

## Missing Tables (Priority)

| Phase | Table | Purpose |
|-------|-------|---------|
| 3 | `MARKET_DATA` | OHLCV + indicators |
| 3 | `RISK_METRICS` | Risk dashboard |
| 3 | `SYMBOL_INFO` | Dynamic symbol config |
| 4 | `RISK_VIOLATIONS` | Risk alerts history |
| 4 | `SYSTEM_HEALTH` | Monitoring |

## Migration Checklist

- [x] Phase 1: Core tables (sessions, accounts, configs)
- [x] Phase 2: Signal tracking & execution
- [ ] Phase 3: Market data & risk metrics
- [ ] Phase 4: System health & monitoring

## Dashboard Feasibility

| Feature | Ready? |
|---------|--------|
| Position Dashboard | ✅ Yes |
| Strategy Analysis | ✅ Yes |
| Risk Dashboard | ⚠️ Partial |
| Analytics | ⚠️ Partial |

**For database implementation details, see [`src/trading_bot/data/models.py`](../../src/trading_bot/data/models.py).**
