# Database ERD

## Current State

| Status | Tables | Completion |
|--------|--------|------------|
| **Implemented** | 2 | 14% |
| **Target** | 14 | 100% |

### Existing Tables
- `supply_demand_zones` - S&D zone tracking
- `positions` - Basic position management

## Target Schema

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

    ZONES {
        string zone_id PK
        string session_id FK
        string symbol
        string zone_type
        float strength_score
        boolean is_valid
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
    TRADING_SESSIONS ||--o{ ZONES : "analyzes"
    TRADING_SESSIONS ||--o{ RISK_METRICS : "tracks"
    ZONES ||--o{ TRADING_SIGNALS : "triggers"
    TRADING_SIGNALS ||--o{ POSITIONS : "creates"
```

## Missing Tables (Priority Order)

| Phase | Table | Purpose |
|-------|-------|---------|
| 1 | `TRADING_ACCOUNTS` | Multi-account support |
| 1 | `TRADING_SESSIONS` | Session grouping & P&L |
| 1 | `CONFIG_SNAPSHOTS` | Config versioning |
| 2 | `TRADING_SIGNALS` | Signal quality analysis |
| 2 | `SIGNAL_EXECUTIONS` | Execution tracking |
| 2 | `POSITION_MODIFICATIONS` | Breakeven/trailing audit |
| 2 | `PARTIAL_CLOSES` | Profit-taking tracking |
| 3 | `MARKET_DATA` | OHLCV + indicators |
| 3 | `SYMBOL_INFO` | Dynamic symbol config |
| 3 | `RISK_METRICS` | Risk dashboard |
| 3 | `RISK_VIOLATIONS` | Risk alerts history |
| 4 | `SYSTEM_HEALTH` | Monitoring |

## Migration Checklist

- [ ] Phase 1: Core tables (sessions, accounts, configs)
- [ ] Phase 2: Signal tracking & execution
- [ ] Phase 3: Market data & risk metrics
- [ ] Phase 4: System health & monitoring

## Dashboard Feasibility

| Feature | Ready? |
|---------|--------|
| Position Dashboard | ⚠️ Partial (no session context) |
| Strategy Analysis | ❌ No signal data |
| Risk Dashboard | ❌ No risk metrics |
| Analytics | ❌ Missing aggregations |

**Conclusion**: Complete Phase 1-3 for full dashboard functionality.
