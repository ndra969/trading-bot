# Windows Setup Guide

Complete setup for running the trading bot on Windows with MetaTrader5 integration.

## Prerequisites

- **Windows 10/11** (MT5 requires Windows)
- **Python 3.12+**
- **MetaTrader5** terminal installed
- **Stable internet connection**

## Installation

### 1. Install Python

```powershell
# Download Python 3.12+ from python.org
# Check "Add Python to PATH" during installation

python --version  # Should show Python 3.12.x
```

### 2. Install MetaTrader5

1. Download MT5 from your broker
2. Install to default location: `C:\Program Files\MetaTrader 5`
3. Login with your demo/live account
4. Keep MT5 terminal running in background

### 3. Install Trading Bot

```bash
# Clone repository
git clone <repository-url>
cd trading-bot

# Install dependencies (UV package manager)
uv sync

# Or with pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
notepad .env
```

Required `.env` variables:
```bash
# MT5 Connection
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Server

# Optional: Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Mode
DRY_RUN=true  # Start with true for testing
```

## Verification

### Test MT5 Connection

```bash
uv run trading-bot mt5 connect
```

Expected output:
```
✅ Successfully connected to MT5
Account: 123456
Broker: YourBroker
Server: YourBroker-Server
```

### Test Bot in Dry-Run Mode

```bash
uv run trading-bot start --dry-run
```

Expected output:
```
🤖 Trading Bot started (DRY-RUN mode)
📊 Account: 123456 ($10,000.00)
🔍 Analyzing symbols...
```

## Troubleshooting

### MT5 Not Connecting

**Problem**: `MT5 not connected` error

**Solutions**:
1. Ensure MT5 terminal is open and logged in
2. Check account credentials in `.env`
3. Run MT5 as administrator
4. Verify firewall allows Python-MT5 connection

### Python Path Issues

**Problem**: `python` command not found

**Solution**:
```powershell
# Add Python to PATH manually
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\Scripts"
```

### Permission Errors

**Problem**: `Access denied` errors

**Solution**:
- Run terminal as Administrator
- Or disable UAC temporarily (not recommended)

## Windows-Specific Notes

### MT5 Installation Paths

Common MT5 installation locations:
- `C:\Program Files\MetaTrader 5`
- `C:\Program Files\MetaTrader 5 Terminal`
- `C:\Users\<User>\AppData\Roaming\MetaQuotes\Terminal\<ID>`

### Auto-Detection

The bot auto-detects MT5 installation:
```python
# No need to specify MT5 path in most cases
# Bot searches common locations automatically
```

### Performance Optimization

For optimal performance:
- Use SSD for database storage
- Close unnecessary applications
- Set Python process priority to High:
  ```powershell
  # Run with high priority
  Start-Process python -ArgumentList "run_trading_bot.py" -PriorityClass High
  ```

## Next Steps

1. Test with dry-run mode: `uv run trading-bot start --dry-run`
2. Review [Configuration Guide](configuration-guide.md)
3. Check [CLI Reference](cli-reference.md) for all commands
