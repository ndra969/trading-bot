# MT5 Connection Guide

Connect the trading bot to MetaTrader5 platform.

## Prerequisites

- **Windows 10/11** (MT5 requires Windows)
- **MetaTrader5 terminal** installed and logged in
- **Python MetaTrader5 package** (installed via `uv sync`)

## Quick Setup

### 1. Login to MT5 Terminal

1. Open MetaTrader5 terminal
2. Login with your account credentials
3. Keep MT5 running in background

### 2. Configure Bot Credentials

Edit `.env`:

```bash
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Server  # e.g., Exness-MT5Real20
```

### 3. Test Connection

```bash
uv run trading-bot mt5 connect
```

**Expected output**:
```
✅ SUCCESS: Connected to MT5

Account: 123456
Server: Exness-MT5Real20
Balance: $10,000.00
Equity: $10,250.00
```

## How MT5 Connection Works

### Two Modes

**1. CLI Test Commands** (one-time)
```bash
# Each command = separate process
uv run trading-bot mt5 connect       # ✅ Works, then ends
uv run trading-bot mt5 status        # New process, no connection
```

**2. Running Bot** (persistent)
```bash
# Connection maintained throughout bot lifetime
uv run trading-bot start
# Connection: persistent, real-time updates
```

## CLI Commands

```bash
# Connect to MT5
uv run trading-bot mt5 connect

# Show connection status
uv run trading-bot mt5 status

# Show account info
uv run trading-bot account info

# Disconnect
uv run trading-bot mt5 disconnect
```

## Configuration

### Auto-Detection

The bot auto-detects MT5 installation. Common paths:
- `C:\Program Files\MetaTrader 5`
- `C:\Program Files (x86)\MetaTrader 5`

### Manual Path Configuration

If auto-detection fails:

```yaml
# config/production.yaml
mt5:
  path: "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
  login: 123456
  password: ${MT5_PASSWORD}  # From .env
  server: "YourBroker-Server"
  timeout: 60000  # 60 seconds
```

## Server Configuration (CRITICAL)

**Always specify explicit server** to prevent auto-switching:

```yaml
mt5:
  server: "Exness-MT5Real20"  # ✅ Explicit
  # server: ""               # ❌ Don't leave blank
```

If MT5 server changes mid-trading, the bot **automatically stops** and sends alert.

## Connection Retry Logic

Built-in retry mechanism:

| Attempt | Wait Time |
|---------|-----------|
| 1st retry | 5 seconds |
| 2nd retry | 10 seconds |
| 3rd retry | 30 seconds |
| 4+ retries | 60 seconds |

Max retries: 5 (configurable)

## Multi-Account Support

The bot supports multiple MT5 accounts:

```bash
# List configured accounts
uv run trading-bot account list

# Switch active account
uv run trading-bot account switch --account-id 123456
```

See [Multi-Account Guide](../guides/multi-account-guide.md).

## Troubleshooting

### "MT5 not initialized"

**Causes**:
- MT5 terminal not running
- Wrong credentials
- Firewall blocking connection

**Solutions**:
1. Open MT5 terminal manually
2. Verify login in MT5 terminal
3. Check credentials in `.env`
4. Run terminal as Administrator

### Server Mismatch

**Symptoms**: Bot stops with "Server Mismatch Detected"

**Cause**: MT5 reconnected to different server

**Solutions**:
1. Set explicit `server` in config
2. Login to correct server in MT5
3. Restart bot

### Connection Drops

**Symptoms**: Frequent disconnects

**Solutions**:
1. Check internet stability
2. Increase timeout in config
3. Reduce trading symbols (less data load)

### "Authorization Failed"

**Causes**:
- Wrong password
- Account locked
- Wrong server

**Solutions**:
1. Test login in MT5 terminal first
2. Verify credentials exactly match
3. Check account is not disabled

## Security

### Credential Protection

The bot **never logs passwords**:
```
[INFO] Connecting to MT5: Account=123***, Server=Exness-MT5Real20
```

### Environment Variables

**Always use** `.env` for credentials:
```bash
# ✅ Good
MT5_PASSWORD=secret123

# ❌ Bad - don't put in config files
# config/production.yaml
# password: "secret123"
```

## Related Documentation

- [Windows Setup](windows-setup-guide.md) - Initial setup
- [Configuration Guide](configuration-guide.md) - Config options
- [Multi-Account Guide](../guides/multi-account-guide.md) - Multiple accounts
- [Troubleshooting](../guides/troubleshooting-guide.md) - Common issues
