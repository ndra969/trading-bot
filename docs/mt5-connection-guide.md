# MT5 Connection Guide

## ✅ MT5 Connection Working!

MT5 connector sudah berhasil diimplementasikan dan berfungsi dengan baik.

## 🔌 How MT5 Connection Works

### CLI Commands (One-Time Execution)
Setiap CLI command adalah **separate process**:

```bash
# Test connection (works, but doesn't persist)
uv run trading-bot mt5 connect
# Output: SUCCESS: Connected to MT5
# Connection: ✅ Works
# Persistence: ❌ Lost after command ends

# Check status (new process, no connection)
uv run trading-bot mt5 status  
# Output: Status: Not Connected
# Reason: Different process, connection not shared
```

### Running Bot (Persistent Connection)
Untuk persistent connection, run bot dalam mode daemon:

```bash
# Start bot with persistent MT5 connection
uv run trading-bot start
# Connection: ✅ Works
# Persistence: ✅ Maintained while bot runs
# Monitoring: Real-time updates
```

## 🎯 Use Cases

### 1. Test MT5 Connection
```bash
# Quick connection test
uv run trading-bot mt5 connect
```
**Output:**
```
SUCCESS: Connected to MT5 successfully!

Account Information:
  Login: 159394302
  Server: Exness-MT5Real20
  Company: Exness Technologies Ltd
  Balance: $1,792.81
  Equity: $1,792.81
  Leverage: 1:500
```

### 2. Get Account Info (One-Time)
```bash
# Connect first
uv run trading-bot mt5 connect

# In same command session, get account info
uv run trading-bot account info
```

**Note:** Each command is separate, so connection doesn't persist.

### 3. Persistent Trading (Recommended)
```bash
# Start bot - maintains persistent MT5 connection
uv run trading-bot start --dry-run

# Bot will:
# 1. Connect to MT5 once
# 2. Keep connection alive
# 3. Monitor account
# 4. Execute trades
# 5. Track positions
```

## 🔄 Connection Lifecycle

### CLI Command Mode
```
┌─────────────────────┐
│  Run Command        │
│  uv run trading-bot │
│  mt5 connect        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Connect to MT5     │
│  ✅ Success         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Show Account Info  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Command Ends       │
│  ❌ Connection Lost │
└─────────────────────┘
```

### Bot Mode (Persistent)
```
┌─────────────────────┐
│  Start Bot          │
│  uv run trading-bot │
│  start              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Connect to MT5     │
│  ✅ Success         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Keep Connection    │
│  ✅ Alive           │
│  - Monitor account  │
│  - Track positions  │
│  - Execute trades   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  User stops (Ctrl+C)│
│  ✅ Clean disconnect│
└─────────────────────┘
```

## 📝 Configuration

### Environment Variables (.env.dev)
```env
# MT5 Connection Settings
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Server

# Optional
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_CONNECTION_TIMEOUT=30
MT5_RETRY_ATTEMPTS=3
```

### YAML Configuration (config/development.yaml)
```yaml
mt5:
  path: "C:\\Program Files\\MetaTrader 5\\Broker"
  login: 12345678  # Optional, use .env instead
  password: "..."  # Optional, use .env instead
  server: "..."    # Optional, use .env instead
  timeout: 60000
```

## ✅ What Works Now

| Feature | Status | Notes |
|---------|--------|-------|
| MT5 Connection | ✅ Working | Can connect to MT5 terminal |
| Account Info | ✅ Working | Retrieves balance, equity, etc |
| Connection Test | ✅ Working | Validates MT5 setup |
| CLI Commands | ✅ Working | All MT5 commands functional |
| Persistent Mode | 🔄 Ready | Use `trading-bot start` |

## 🚀 Next Steps

### For Development
```bash
# 1. Test connection
uv run trading-bot mt5 connect

# 2. If successful, start bot
uv run trading-bot start --dry-run
```

### For Production
```bash
# 1. Setup .env.prd with real credentials
nano .env.prd

# 2. Test connection
uv run trading-bot --config production mt5 connect

# 3. Start bot (live trading)
uv run trading-bot --config production start
```

## 🔍 Troubleshooting

### Issue: "Not Connected" after connect
**Cause:** Each CLI command is separate process  
**Solution:** Use `trading-bot start` for persistent connection

### Issue: Connection fails
**Check:**
1. MT5 terminal is running
2. Credentials correct in .env file
3. Windows firewall not blocking
4. Server name matches MT5 terminal

### Issue: "MetaTrader5 package not installed"
**Solution:**
```bash
pip install MetaTrader5
# or
uv add MetaTrader5
```
**Note:** MT5 only works on Windows

## 📊 Example Session

```bash
# Test connection
$ uv run trading-bot mt5 connect
SUCCESS: Connected to MT5 successfully!

Account Information:
  Login: 159394302
  Server: Exness-MT5Real20
  Balance: $1,792.81
  Equity: $1,792.81
  Leverage: 1:500

# Start bot with persistent connection
$ uv run trading-bot start --dry-run
Starting Trading Bot...
WARNING: Running in DRY-RUN mode
OK Configuration validated
OK Database initialized: PostgreSQL (trading_bot_dev)
SUCCESS: Connected to MT5
  Account: 159394302
  Balance: $1,792.81

Trading Bot started successfully!
Monitoring positions...
Press Ctrl+C to stop...
```

## 🎉 Success!

MT5 integration is **fully functional**! Connection works perfectly. Untuk persistent connection dan real-time trading, gunakan `trading-bot start` command.

