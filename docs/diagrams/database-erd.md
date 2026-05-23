# Database ERD

Entity relationship diagram for the trading bot database schema.

## Current State

| Status | Tables | Completion |
|--------|--------|------------|
| **Implemented** | 5 | ~36% |
| **Target** | 14 | 100% |

### Implemented Tables
- `supply_demand_zones` - S&D zone tracking
- `positions` - Position management
- `trading_accounts` - Multi-account support
- `trading_sessions` - Session grouping
- `config_snapshots` - Config versioning

### In Progress
- `trading_signals` - Signal tracking
- `position_modifications` - Modification audit
- `partial_closes` - Profit-taking tracking

### Planned
- `market_data` - OHLCV storage
- `risk_metrics` - Risk tracking
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

    CONFIG_SNAPSHOTS {
        string config_hash PK
        json config_json
        datetime created_at
    }

    TRADING_SESSIONS ||--o{ POSITIONS : "manages"
    TRADING_SESSIONS ||--o{ SUPPLY_DEMAND_ZONES : "analyzes"
    TRADING_SESSIONS ||--o{ TRADING_SIGNALS : "generates"
    TRADING_ACCOUNTS ||--o{ POSITIONS : "holds"
    SUPPLY_DEMAND_ZONES ||--o{ TRADING_SIGNALS : "triggers"
    TRADING_SIGNALS ||--o{ POSITIONS : "creates"
```

## Missing Tables (Priority)

| Phase | Table | Purpose |
|-------|-------|---------|
| 2 | `TRADING_SIGNALS` | Signal quality analysis |
| 2 | `SIGNAL_EXECUTIONS` | Execution tracking |
| 2 | `POSITION_MODIFICATIONS` | Breakeven/trailing audit |
| 2 | `PARTIAL_CLOSES` | Profit-taking tracking |
| 3 | `MARKET_DATA` | OHLCV + indicators |
| 3 | `RISK_METRICS` | Risk dashboard |
| 3 | `SYMBOL_INFO` | Dynamic symbol config |
| 4 | `RISK_VIOLATIONS` | Risk alerts history |
| 4 | `SYSTEM_HEALTH` | Monitoring |

## Migration Checklist

- [x] Phase 1: Core tables (sessions, accounts, configs)
- [ ] Phase 2: Signal tracking & execution
- [ ] Phase 3: Market data & risk metrics
- [ ] Phase 4: System health & monitoring

## Dashboard Feasibility

| Feature | Ready? |
|---------|--------|
| Position Dashboard | ⚠️ Partial (no signal tracking) |
| Strategy Analysis | ⚠️ Partial (no execution tracking) |
| Risk Dashboard | ❌ No risk metrics table |
| Analytics | ⚠️ Partial (basic aggregations) |

**For database implementation details, see [`src/trading_bot/data/models.py`](../../src/trading_bot/data/models.py).**
