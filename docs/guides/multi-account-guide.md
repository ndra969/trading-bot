# Multi-Account Guide

Manage multiple MT5 accounts with the trading bot.

## Use Cases

- **Portfolio diversification** - Trade across multiple brokers
- **Demo + Live testing** - Run strategy on both simultaneously
- **Risk distribution** - Split exposure across accounts
- **Broker redundancy** - Backup accounts

## Architecture

```
AccountSelector  ──→  Manages active account
       ↓
AccountRepository ──→  Database access
       ↓
trading_accounts table

AccountSyncService ──→ Syncs with MT5
       ↓
MT5Connector ──→ Live account data
```

## Components

### AccountSelector

Manages which account is currently active:

```python
from trading_bot.data.services.account_selector import AccountSelector

selector = AccountSelector()

# Get active account
account = await selector.get_active_account()

# Switch account
await selector.switch_account(account_id=123456)

# List all accounts
accounts = await selector.list_accounts()
```

### AccountSyncService

Syncs MT5 data to database:

```python
from trading_bot.data.services.account_sync_service import AccountSyncService

sync = AccountSyncService()

# Ensure MT5 account exists in DB
account = await sync.ensure_account_exists(mt5_connector)

# Update balance/equity
await sync.sync_account_data(account_id)
```

## Database Schema

```sql
CREATE TABLE trading_accounts (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,        -- MT5 number
    broker_name VARCHAR(100),
    account_type VARCHAR(10),           -- DEMO/LIVE
    currency VARCHAR(10),
    balance DECIMAL(18,2),
    equity DECIMAL(18,2),
    leverage INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## CLI Commands

```bash
# Show active account
uv run trading-bot account info

# List all accounts
uv run trading-bot account list

# Switch active account
uv run trading-bot account switch --account-id 123456

# Sync with MT5
uv run trading-bot account sync
```

## Configuration

```yaml
# config/production.yaml
accounts:
  enabled: true
  default_account_id: 123456
  auto_sync: true
  sync_interval_seconds: 60
```

## Account Type Detection

MT5 `trade_mode` determines account type:

| Trade Mode | Account Type |
|------------|--------------|
| 0 (DEMO) | DEMO |
| 1 (CONTEST) | DEMO |
| 2 (REAL) | LIVE |

## Active Account Logic

1. **Check cached account** - If active, use it
2. **Get first active from DB** - If no cache
3. **Return None** - If no active accounts

## Per-Account Tracking

Each position is linked to an account:

```sql
positions:
  ...
  account_id  INT  → trading_accounts.id
  session_id  INT  → trading_sessions.id
```

This enables:
- Per-account P&L
- Per-broker performance
- Risk per account

## Best Practices

### 1. Separate Configs

```bash
# Different configs per account
config/demo_account.yaml
config/live_account.yaml
```

### 2. Account Isolation

Each account maintains:
- Own risk limits
- Own position tracking
- Own performance metrics

### 3. Sync Strategy

- **Startup**: Full sync of all accounts
- **Trading cycle**: Update balance/equity
- **On-demand**: Manual sync via CLI

## Common Scenarios

### Switching Demo → Live

```bash
# Start on demo
uv run trading-bot start --config demo_config

# Stop bot (Ctrl+C)

# Switch to live account
uv run trading-bot account switch --account-id <live_id>

# Start live
uv run trading-bot start --config production
```

### Multi-Broker Setup

```python
# Define accounts in database
broker_accounts = {
    "exness_demo": 111111,
    "exness_live": 222222,
    "icmarkets_live": 333333,
}

# Switch based on strategy
if strategy == "conservative":
    await selector.switch_account(broker_accounts["exness_demo"])
else:
    await selector.switch_account(broker_accounts["icmarkets_live"])
```

## Troubleshooting

### No Active Account

**Cause**: No accounts marked active in DB

**Solution**:
```bash
# Sync from MT5
uv run trading-bot account sync

# Verify
uv run trading-bot account list
```

### Wrong Account Selected

**Solution**:
```bash
# Switch to correct account
uv run trading-bot account switch --account-id <correct_id>
```

### Sync Failures

**Causes**:
- MT5 not connected
- Account ID mismatch
- Database connection issue

Check logs:
```bash
grep "AccountSync" logs/trading_bot.log
```

## Related Documentation

- [MT5 Connection Guide](../setup/mt5-connection-guide.md) - MT5 setup
- [Database ERD](../architecture/database-erd.md) - Schema
- [Configuration Guide](../setup/configuration-guide.md) - Config setup
