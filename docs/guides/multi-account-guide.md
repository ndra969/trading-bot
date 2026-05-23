# Multi-Account Trading Guide

## Overview

The trading bot supports **multi-account trading**, allowing you to manage multiple MT5 accounts simultaneously or switch between accounts dynamically. This is useful for:

- **Portfolio Management**: Trade across multiple accounts (e.g., demo + live, or multiple brokers)
- **Risk Distribution**: Distribute trades across different accounts
- **Account Testing**: Test strategies on demo accounts while trading live
- **Broker Diversification**: Use multiple brokers for redundancy

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Account System                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌──────────────────┐          │
│  │ AccountSelector │────────▶│ AccountRepository│          │
│  │                 │         └──────────────────┘          │
│  │ - get_active()  │                 ▲                     │
│  │ - switch()      │                 │                     │
│  │ - list_all()    │                 │                     │
│  └─────────────────┘                 │                     │
│         ▲                           │                     │
│         │                    ┌──────┴──────┐              │
│         │                    │ trading_accounts │          │
│         │                    └─────────────┘              │
│         │                                                   │
│  ┌──────┴───────┐         ┌──────────────────┐            │
│  │AccountSync    │────────▶│   MT5Connector   │            │
│  │Service        │         │                  │            │
│  │               │         │ - account_info   │            │
│  │ - sync_account│         │ - reconnect()    │            │
│  │ - ensure_exist│         └──────────────────┘            │
│  └───────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

The `trading_accounts` table stores account information:

```sql
CREATE TABLE trading_accounts (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,              -- MT5 account number
    broker_name VARCHAR(100) NOT NULL,        -- Broker name
    account_type VARCHAR(10) NOT NULL,        -- 'DEMO' or 'LIVE'
    currency VARCHAR(10) NOT NULL,            -- Account currency
    balance DECIMAL(18,2) DEFAULT 0,          -- Current balance
    equity DECIMAL(18,2) DEFAULT 0,           -- Current equity
    leverage INTEGER NOT NULL,                -- Account leverage
    margin_mode VARCHAR(20),                  -- Margin mode
    is_active BOOLEAN DEFAULT TRUE,           -- Active status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Usage

### 1. Account Selection

The `AccountSelector` service manages which account is currently active:

```python
from trading_bot.data.services.account_selector import AccountSelector

selector = AccountSelector()

# Get active account for trading
account = await selector.get_active_account()

if account:
    print(f"Trading on: {account.broker_name} - Account {account.account_id}")
    print(f"Balance: {account.balance} {account.currency}")
else:
    print("No active account found")
```

### 2. Switching Accounts

Switch to a different account during runtime:

```python
# Switch to specific MT5 account ID
success = await selector.switch_account(account_id=123456)

if success:
    print("Successfully switched accounts")
else:
    print("Failed to switch - account not found or inactive")
```

### 3. Account Synchronization

The `AccountSyncService` keeps database records in sync with MT5:

```python
from trading_bot.data.services.account_sync_service import AccountSyncService
from trading_bot.connectors.mt5_connector import MT5Connector

sync_service = AccountSyncService()
mt5 = MT5Connector()

# Ensure current MT5 account exists in database
account = await sync_service.ensure_account_exists(mt5)

if account:
    print(f"Account synced: {account.account_id}")
    print(f"Balance updated: {account.balance}")
```

---

## Configuration

### Active Account Selection Logic

1. **Cached Account**: If a current account is cached, it's used if still active
2. **First Active**: If no cached account, the first active account from DB is used
3. **No Account**: If no active accounts exist, returns `None`

### Account Type Detection

Accounts are automatically detected as DEMO or LIVE based on MT5 `trade_mode`:

| Trade Mode | Type |
|------------|------|
| 0 (DEMO) | DEMO |
| 1 (CONTEST) | DEMO |
| 2 (REAL) | LIVE |

---

## Integration with Trading Bot

### Initialization

```python
from trading_bot.main import TradingBot

bot = TradingBot(config_path="config/production.yaml")

# Account selector is initialized during bot startup
await bot.start()

# Bot uses AccountSelector internally for all trading operations
```

### Per-Account Trading

Each position is linked to an account:

```python
# When opening a position, it's automatically linked to active account
signal = TradingSignal(
    symbol="EURUSD",
    action=SignalAction.BUY,
    # ... other fields
)

# Position will be created with account_id from AccountSelector
position = await bot.execute_trade(signal)
```

---

## CLI Commands

### Check Active Account

```bash
uv run trading-bot account info
```

Output:
```
┌──────────────────────────────────────────────┐
│         Account Information                  │
├──────────────────────────────────────────────┤
│ Account ID:    159394302                     │
│ Broker:        Exness                        │
│ Type:          LIVE                          │
│ Currency:      USD                           │
│ Balance:       $10,000.00                    │
│ Equity:        $10,250.00                    │
│ Leverage:      1:2000                        │
│ Margin Mode:   NETTING                       │
│ Status:        ✅ Active                     │
└──────────────────────────────────────────────┘
```

### List All Accounts

```bash
uv run trading-bot account list
```

---

## Best Practices

### 1. Account Isolation

- **Separate Configs**: Use different config files for demo vs live accounts
- **Environment Variables**: Use `.env.demo` and `.env.live` files

### 2. Risk Management

- **Per-Account Limits**: Each account maintains its own risk limits
- **Portfolio Risk**: Total risk is calculated across all active positions

### 3. Sync Frequency

- **Startup Sync**: Accounts are synced when bot starts
- **Periodic Updates**: Balance/equity updated every trading cycle
- **Manual Sync**: Force sync with CLI command

---

## Troubleshooting

### No Active Account Found

**Problem**: `AccountSelector.get_active_account()` returns `None`

**Solutions**:
1. Ensure MT5 is connected and logged in
2. Check database has at least one account with `is_active=TRUE`
3. Manually create account in database if needed

### Account Not Syncing

**Problem**: Balance/equity not updating in database

**Solutions**:
1. Check MT5 connection status
2. Verify account_id matches MT5 login
3. Check logs for sync errors

### Wrong Account Selected

**Problem**: Bot trading on wrong account

**Solutions**:
1. Use `AccountSelector.switch_account()` to select correct account
2. Set `is_active=FALSE` on accounts you don't want to use
3. Verify only one account is active per broker

---

## Advanced Usage

### Custom Account Repository

```python
from trading_bot.data.repositories import AccountRepository

# Custom query
repo = AccountRepository()

# Get all live accounts
live_accounts = await repo.get_live_accounts()

# Get accounts by broker
exness_accounts = await repo.get_by_broker("Exness")

# Update account status
await repo.set_active_status(account_id=123, is_active=False)
```

### Multi-Broker Setup

```python
# Setup for multiple brokers
accounts = {
    "exness_demo": await selector.get_account_by_id(111111),
    "icmarkets_live": await selector.get_account_by_id(222222),
}

# Switch based on strategy
if strategy == "conservative":
    await selector.switch_account(accounts["exness_demo"].account_id)
else:
    await selector.switch_account(accounts["icmarkets_live"].account_id)
```

---

## Related Documentation

- [Database ERD](../database-erd.md) - Complete database schema
- [MT5 Connection Guide](../mt5-connection-guide.md) - MT5 integration
- [Risk Management Guide](../risk-management-guide.md) - Per-account risk limits
