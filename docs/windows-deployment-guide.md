# Windows Deployment Guide for Mini PC Trading Bot

Complete guide for running trading bots on Windows Mini PC with AMD 6800H and thermal monitoring.

## 🚀 Quick Start (Windows 11/10)

### Prerequisites Checklist

- ✅ Windows 10/11 installed
- ✅ Python 3.11+ installed
- ✅ MetaTrader5 installed and running
- ✅ UV package manager installed
- ✅ Telegram Bot Token & Chat ID ready

### Step 1: Install Dependencies

```powershell
# Install UV (if not already installed)
irm https://astral.sh/uv/install.ps1 | iex

# Navigate to project directory
cd C:\path\to\trading-bot

# Install dependencies
uv sync
uv sync --extra dev

# Install technical indicators
uv add pandas-ta ta numpy pandas
```

### Step 2: Setup Environment Variables

```powershell
# Set Telegram notifications
$env:TELEGRAM_BOT_TOKEN = "your_bot_token_here"
$env:TELEGRAM_CHAT_ID = "your_chat_id_here"

# Or set permanently in Windows:
# Search for "Edit the system environment variables" > Environment Variables
# Add as System Variables:
# TELEGRAM_BOT_TOKEN = your_bot_token_here
# TELEGRAM_CHAT_ID = your_chat_id_here
```

### Step 3: Start MetaTrader5

1. Launch MT5 from desktop/start menu
2. Login to your trading account
3. Enable Algorithmic Trading:
   - Tools → Options → Expert Advisors
   - ✅ Allow algorithmic trading
   - ✅ Allow DLL imports
4. Keep MT5 running in background

## 🤖 Running Trading Bots

### Option 1: Integrated Dual Bot (Recommended)

```powershell
# Start both Day Trading + Swing Trading with thermal monitoring
python scripts/start_dual_bots.py
```

**Features:**
- ✅ Auto thermal monitoring
- ✅ Telegram notifications
- ✅ Auto-stop if overheating
- ✅ Process management

### Option 2: Manual Multi-Terminal Setup

**Terminal 1 - Day Trading Bot:**
```powershell
uv run trading-bot start --config production --type day_trading --name DayTradingBot
```

**Terminal 2 - Swing Trading Bot:**
```powershell
uv run trading-bot start --config production --type swing_trading --name SwingTradingBot
```

**Terminal 3 - Thermal Monitoring:**
```powershell
uv run trading-bot monitor --thermal
```

### Option 3: Single Bot

```powershell
# Run only day trading
uv run trading-bot start --config production --type day_trading --name DayTradingBot

# Run only swing trading
uv run trading-bot start --config production --type swing_trading --name SwingTradingBot

# Run only scalping (if you want 3rd bot)
uv run trading-bot start --config production --type scalping --name ScalpingBot
```

## 🌡️ Thermal Monitoring Setup

### Configure Temperature Monitoring

Edit `config/thermal_monitoring.yaml` if needed:

```yaml
thermal_thresholds:
  normal: 70        # Normal operation
  warning: 80       # Send warning notification
  critical: 85      # Prepare to stop
  emergency: 90     # Immediate stop required
```

### Test Temperature Monitoring

```powershell
# Test thermal monitoring without starting bots
uv run trading-bot monitor --thermal --test
```

## 📱 Telegram Notifications

### Create Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow instructions to create bot
4. Copy the bot token

### Get Chat ID

1. Start conversation with your bot
2. Send any message
3. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find your chat ID in the response

### Notification Types

- 🟢 **Normal**: "Thermal Monitor started"
- ⚠️ **Warning (80°C)**: "Mini PC getting warm, monitoring closely"
- 🔥 **Critical (85°C)**: "Preparing to stop bots gracefully"
- 🚨 **Emergency (90°C)**: "EMERGENCY STOP - All bots stopped due to overheating"

## 🛠️ Windows-Specific Configuration

### Power Settings

1. Open Control Panel → Power Options
2. Set "High Performance" power plan
3. Configure "Never" sleep for both display and sleep
4. Disable "Fast startup" if running 24/7

### Windows Firewall

Allow Python and trading bot through firewall:

```powershell
# Allow Python through firewall
New-NetFirewallRule -DisplayName "Trading Bot" -Direction Inbound -Program "python.exe" -Action Allow

# Allow UV through firewall
New-NetFirewallRule -DisplayName "UV Package Manager" -Direction Inbound -Program "uv.exe" -Action Allow
```

### Auto-Start Configuration

**Option 1: Windows Task Scheduler**

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: "At system startup"
4. Action: Start a program
5. Program: `python.exe`
6. Arguments: `C:\path\to\trading-bot\scripts\start_dual_bots.py`
7. Start in: `C:\path\to\trading-bot\`

**Option 2: Windows Startup Folder**

```powershell
# Create startup script
echo @echo off > "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_trading_bots.bat"
echo cd /d C:\path\to\trading-bot >> "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_trading_bots.bat"
echo python scripts/start_dual_bots.py >> "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_trading_bots.bat"
```

## 🔧 Troubleshooting

### Common Issues

**"MT5 not found" error:**
```powershell
# Check MT5 installation path
Get-Process | Where-Object {$_.ProcessName -like "*terminal*"}

# Or set MT5 path manually in config
# Edit config/mt5.yaml:
# path: "C:\Program Files\MetaTrader 5\terminal64.exe"
```

**"Access denied" errors:**
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Temperature monitoring not working:**
```powershell
# Install OpenHardwareMonitor for temperature monitoring
# Download: https://openhardwaremonitor.org/
# Install and run with admin privileges
```

### Performance Monitoring

**Check system resources:**
```powershell
# CPU and Memory usage
Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 5 -MaxSamples 12
Get-Counter '\Memory\Available MBytes' -SampleInterval 5 -MaxSamples 12

# Temperature (if HWiNFO installed)
Get-WmiObject MSAcpi_ThermalZoneTemperature | Select-Object InstanceName, CurrentTemperature
```

### Log Files

Check logs for troubleshooting:

```powershell
# Trading bot logs
Get-Content logs\trading_bot.log -Tail 50

# Thermal monitoring logs
Get-Content logs\thermal_monitoring.log -Tail 50

# Windows Event Viewer for system issues
eventvwr.msc
```

## 📊 Performance Optimization

### SSD Optimization

```powershell
# Optimize SSD for trading
# Disable Indexing for trading folders
attrib +s "C:\path\to\trading-bot"
fsutil behavior set disablelastaccess 1

# Optimize power settings for SSD
powercfg /setactive SCHEME_MIN
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
```

### Network Optimization

```powershell
# Set DNS to Google for faster connectivity
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses "8.8.8.8","8.8.4.4"

# Disable Windows Update auto-restart
reg add "HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings" /v UxOption /t REG_DWORD /d 2 /f
```

## 🎯 Recommended Daily Routine

### Daily Startup Checklist

1. **Morning (6:00 AM GMT):**
   - Check Windows updates
   - Launch MT5 and verify connection
   - Start trading bots
   - Verify Telegram notifications working

2. **During Trading Hours:**
   - Monitor temperature occasionally
   - Check Telegram alerts
   - Review bot logs if any issues

3. **Evening (10:00 PM GMT):**
   - Review daily performance
   - Check system resources
   - Backup logs if needed

### Weekly Maintenance

```powershell
# Clean up old logs (keep last 7 days)
Get-ChildItem logs\*.log | Where-Object {$_.LastWriteTime -lt (Get-Date).AddDays(-7)} | Remove-Item

# Database maintenance
sqlite3 trading_bot.db "VACUUM;"

# Check system health
uv run trading-bot doctor
```

## 🚨 Emergency Procedures

### If Bot Stops Unexpectedly

```powershell
# Check process status
Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*trading*"}

# Restart bot system
python scripts/start_dual_bots.py

# Check MT5 connection
# Open MT5 → Tools → Options → Experts → Check "Allow live trading"
```

### Manual Emergency Stop

```powershell
# Stop all Python processes
Get-Process python | Stop-Process -Force

# Or use script
uv run trading-bot stop --all
```

### System Recovery

```powershell
# Restart MT5
Stop-Process -Name "terminal64" -Force
Start-Process "C:\Program Files\MetaTrader 5\terminal64.exe"

# Restart network
net stop "Netlogon" && net start "Netlogon"
ipconfig /flushdns
```

## 📞 Support

### Get Help

- Check logs: `logs\trading_bot.log`
- Run diagnostics: `uv run trading-bot doctor`
- Monitor temperature: `uv run trading-bot monitor --thermal`
- Test configuration: `uv run trading-bot config validate`

### Contact Support

If issues persist:
1. Collect logs from `logs/` directory
2. Run `uv run trading-bot system-info`
3. Check MT5 connection status
4. Send details to development team
