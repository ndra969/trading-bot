# 🛠️ Troubleshooting Guide

## Overview

Panduan lengkap untuk mendiagnosis dan mengatasi masalah yang umum terjadi pada trading bot system. Guide ini mencakup troubleshooting untuk berbagai komponen sistem dari MT5 connection hingga database performance.

## Quick Diagnostic Commands

### System Health Check

```bash
# Check bot service status
sudo systemctl status trading-bot

# Check recent logs
tail -f logs/trading_bot.log

# Check system resources
htop
df -h
free -h

# Test MT5 connection
python -c "
from src.mt5_connector import MT5Connector
connector = MT5Connector()
print('MT5 Status:', connector.test_connection())
"

# Test database connection
python -c "
from src.database.sqlite_manager import SQLiteManager
db = SQLiteManager()
print('Database Status:', db.test_connection())
"
```

## Common Issues & Solutions

### 1. MT5 Connection Issues

#### Problem: Cannot Connect to MetaTrader5

**Symptoms:**
- Bot fails to start with MT5 connection error
- "MT5 not initialized" error messages
- Trading operations fail

**Diagnostic Steps:**
```bash
# Check if MT5 is running
ps aux | grep -i metatrader

# Check MT5 terminal logs
# Windows: %APPDATA%\MetaQuotes\Terminal\<terminal_id>\Logs
# Check for connection errors

# Test MT5 Python integration
python -c "
import MetaTrader5 as mt5
print('MT5 Version:', mt5.version())
result = mt5.initialize()
print('Initialize Result:', result)
if result:
    print('Account Info:', mt5.account_info())
    mt5.shutdown()
"
```

**Common Solutions:**

1. **Restart MT5 Terminal**
```bash
# Kill MT5 processes
pkill -f metatrader
# Or on Windows: taskkill /f /im terminal64.exe

# Restart MT5 terminal
# Launch MT5 and login to account
```

2. **Check Account Credentials**
```bash
# Verify in .env file
BROKER_SERVER=YourBrokerServer
ACCOUNT_TYPE=demo  # or live
MAGIC_NUMBER=234000

# Test login manually in MT5 terminal
```

3. **Fix Python MT5 Integration**
```bash
# Reinstall MetaTrader5 package
pip uninstall MetaTrader5
pip install MetaTrader5>=5.0.45

# On Windows, ensure MT5 terminal is in PATH
# Add MT5 installation directory to system PATH
```

4. **Network/Firewall Issues**
```bash
# Check firewall settings
sudo ufw status
# Allow MT5 ports if needed
sudo ufw allow 443
sudo ufw allow 80

# Test broker server connectivity
ping your-broker-server.com
telnet your-broker-server.com 443
```

#### Problem: MT5 Connection Drops Frequently

**Symptoms:**
- Intermittent connection losses
- "Connection lost" messages
- Trading operations timeout

**Solutions:**

1. **Improve Connection Stability**
```python
# In .env file, increase timeouts
MT5_CONNECTION_TIMEOUT=60
MT5_RETRY_ATTEMPTS=5

# Enable connection monitoring
HEALTH_CHECK_MT5_CONNECTION=true
HEALTH_CHECK_INTERVAL=60
```

2. **Network Optimization**
```bash
# Use wired connection instead of WiFi
# Configure static IP if possible
# Use VPN for stable connection to broker servers
```

### 2. Database Issues

#### Problem: Database Performance Degradation

**Symptoms:**
- Slow query execution (>100ms)
- High memory usage
- Database locks/timeouts

**Diagnostic Steps:**
```bash
# Check database size
ls -lh data/trading_bot.db

# Check database integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# Analyze query performance
sqlite3 data/trading_bot.db "PRAGMA compile_options;"
sqlite3 data/trading_bot.db "EXPLAIN QUERY PLAN SELECT * FROM trades LIMIT 10;"
```

**Solutions:**

1. **Database Optimization**
```sql
-- Connect to database
sqlite3 data/trading_bot.db

-- Optimize database
PRAGMA optimize;
PRAGMA wal_checkpoint(TRUNCATE);
VACUUM;

-- Check and rebuild indexes
REINDEX;

-- Update statistics
ANALYZE;
```

2. **Configuration Optimization**
```python
# In SQLiteManager initialization
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
PRAGMA mmap_size=268435456;  # 256MB
```

3. **Database Maintenance Script**
```bash
#!/bin/bash
# db_maintenance.sh

DB_FILE="data/trading_bot.db"
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
cp "$DB_FILE" "$BACKUP_DIR/trading_bot_before_maintenance_$DATE.db"

# Optimize database
sqlite3 "$DB_FILE" "
PRAGMA optimize;
PRAGMA wal_checkpoint(TRUNCATE);
VACUUM;
REINDEX;
ANALYZE;
"

echo "Database maintenance completed"
```

#### Problem: Database Corruption

**Symptoms:**
- "Database is locked" errors
- Integrity check failures
- Data inconsistencies

**Recovery Steps:**

1. **Check and Repair Database**
```bash
# Stop the bot first
sudo systemctl stop trading-bot

# Check integrity
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# If corruption detected, recover data
sqlite3 data/trading_bot.db ".recover" | sqlite3 data/trading_bot_recovered.db

# Replace corrupted database
mv data/trading_bot.db data/trading_bot_corrupted.db
mv data/trading_bot_recovered.db data/trading_bot.db

# Restart bot
sudo systemctl start trading-bot
```

2. **Prevent Future Corruption**
```bash
# Enable WAL mode for better concurrency
sqlite3 data/trading_bot.db "PRAGMA journal_mode=WAL;"

# Regular integrity checks
# Add to cron: 0 2 * * * sqlite3 /path/to/trading_bot.db "PRAGMA integrity_check;"
```

### 3. Memory Issues

#### Problem: High Memory Usage

**Symptoms:**
- Memory usage >80% of available RAM
- System becomes slow/unresponsive
- Out of memory errors

**Diagnostic Steps:**
```bash
# Monitor memory usage
free -h
htop

# Check bot memory usage
ps aux | grep python | grep trading_bot

# Monitor memory over time
while true; do
    echo "$(date): $(free -m | grep Mem | awk '{print $3"MB used of "$2"MB total"}')"
    sleep 60
done
```

**Solutions:**

1. **Memory Optimization**
```python
# In .env file
# Reduce data retention
CSV_RETENTION_DAYS=7
LOG_FILE_RETENTION=3 days

# Optimize database cache
SQLITE_CACHE_SIZE=5000  # Reduce from 10000

# Limit concurrent operations
MAX_CONCURRENT_POSITIONS=5  # Reduce if needed
```

2. **Memory Cleanup Script**
```python
# memory_cleanup.py
import gc
import psutil
import os

def cleanup_memory():
    # Force garbage collection
    gc.collect()
    
    # Get current memory usage
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    print(f"Memory usage after cleanup: {memory_mb:.2f} MB")
    
    return memory_mb

# Run cleanup every hour
```

3. **System-Level Memory Management**
```bash
# Increase swap space if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Add to /etc/fstab for permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Configure swappiness
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

### 4. Performance Issues

#### Problem: Slow Trading Loop Execution

**Symptoms:**
- Loop execution time >55 seconds
- Delayed trade execution
- Performance warnings in logs

**Diagnostic Steps:**
```bash
# Check loop timing in logs
grep "Loop execution time" logs/trading_bot.log | tail -20

# Monitor CPU usage
top -p $(pgrep -f trading_bot)

# Check I/O wait
iostat -x 1
```

**Solutions:**

1. **Performance Optimization**
```python
# In .env file
# Reduce analysis frequency
ZONE_DETECTION_INTERVAL_MINUTES=30  # Increase from 15
SIGNAL_ANALYSIS_CANDLES=200  # Reduce from 300

# Optimize database operations
CSV_LOGGING_ENABLED=false  # Use SQLite only
DATABASE_BATCH_SIZE=100

# Reduce monitoring frequency
POSITION_UPDATE_INTERVAL=120  # Increase from 60
```

2. **Code-Level Optimizations**
```python
# Use async operations where possible
# Implement caching for expensive calculations
# Optimize database queries with proper indexing
# Use connection pooling
```

3. **System-Level Optimizations**
```bash
# Set higher process priority
sudo renice -10 $(pgrep -f trading_bot)

# Use SSD for database storage
# Ensure adequate CPU resources
# Optimize network settings for low latency
```

### 5. Telegram Notification Issues

#### Problem: Telegram Notifications Not Working

**Symptoms:**
- No Telegram messages received
- Telegram connection errors
- SSL/TLS errors

**Diagnostic Steps:**
```bash
# Test Telegram bot token
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Test sending message
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
     -d "chat_id=<YOUR_CHAT_ID>&text=Test message"

# Check bot logs for Telegram errors
grep -i telegram logs/trading_bot.log
```

**Solutions:**

1. **Fix Telegram Configuration**
```bash
# Verify token and chat ID in .env
TELEGRAM_TOKEN=your_actual_bot_token
TELEGRAM_CHAT_ID=your_actual_chat_id

# Test configuration
python -c "
from src.notifications.notification_manager import NotificationManager
import os
from dotenv import load_dotenv

load_dotenv()
config = dict(os.environ)
notifier = NotificationManager(config)
result = notifier.test_all_notifiers()
print('Telegram test result:', result)
"
```

2. **SSL/TLS Issues**
```bash
# For SSL issues, use lenient SSL
TELEGRAM_USE_LENIENT_SSL=true
TELEGRAM_SSL_VERIFY=false

# Or fix SSL certificates
sudo apt update && sudo apt install ca-certificates
```

3. **Network/Proxy Issues**
```bash
# If behind proxy, configure proxy settings
export https_proxy=http://proxy.company.com:8080
export http_proxy=http://proxy.company.com:8080

# Or use VPN for Telegram access
```

### 6. Strategy Issues

#### Problem: No Trading Signals Generated

**Symptoms:**
- Bot runs but no trades executed
- "No signals generated" in logs
- Strategy analysis returns empty results

**Diagnostic Steps:**
```bash
# Check strategy configuration
grep -i strategy .env

# Check zone detection
python -c "
from src.strategies.supply_demand_strategy import SupplyDemandStrategy
strategy = SupplyDemandStrategy({})
# Test zone detection manually
"

# Check market data availability
python -c "
from src.mt5_connector import MT5Connector
connector = MT5Connector()
data = connector.get_rates('EURUSD', 'H1', 100)
print('Data points:', len(data) if data is not None else 'None')
"
```

**Solutions:**

1. **Adjust Strategy Parameters**
```bash
# Relax zone detection criteria
ZONE_MIN_STRENGTH=25.0  # Reduce from 35.0
MIN_ENTRY_SCORE=40      # Reduce from 50
ZONE_ENTRY_TOLERANCE_PIPS_FOREX=15  # Increase from 12

# Enable more strategies
STRATEGY_BREAKOUT_RETEST_ENABLED=true
STRATEGY_PRICE_ACTION_ENABLED=true
```

2. **Check Market Conditions**
```bash
# Verify trading hours
MARKET_HOURS_VALIDATION_ENABLED=true

# Check spread conditions
MAX_SPREAD_FOREX=6.0  # Increase if spreads are high

# Verify symbol availability
TRADING_SYMBOLS=EURUSD,GBPUSD  # Test with major pairs first
```

#### Problem: Poor Strategy Performance

**Symptoms:**
- Low win rate (<40%)
- High drawdown
- Frequent stop-outs

**Analysis Steps:**
```bash
# Analyze recent performance
python -c "
from src.analytics.performance_analyzer import PerformanceAnalyzer
analyzer = PerformanceAnalyzer()
metrics = analyzer.get_strategy_performance('supply_demand', 30)
print('Strategy metrics:', metrics)
"

# Check entry quality
grep "Entry score" logs/trading_bot.log | tail -20
```

**Optimization Solutions:**

1. **Improve Entry Criteria**
```bash
# Increase minimum entry score
MIN_ENTRY_SCORE=60  # Increase from 50

# Require structure alignment
REQUIRE_TREND_ALIGNMENT=true
STRUCTURE_ALIGNMENT_BONUS=15

# Add volume confirmation
VOLUME_CONFIRMATION_ENABLED=true
MIN_PATTERN_VOLUME_RATIO=1.5
```

2. **Optimize Risk Management**
```bash
# Reduce risk per trade
RISK_PER_TRADE=0.003  # Reduce from 0.005

# Improve SL placement
PRIORITIZE_ZONE_BASED_SL=true
SL_ADJUSTMENT_PENALTY=-0.20

# Enhance position management
BREAKEVEN_THRESHOLD_PIPS=10  # Reduce for quicker breakeven
TRAILING_START_PIPS=15       # Start trailing sooner
```

### 7. Configuration Issues

#### Problem: Configuration Validation Errors

**Symptoms:**
- Bot fails to start with config errors
- "Missing required configuration" messages
- Invalid parameter value errors

**Solutions:**

1. **Validate Configuration**
```python
# config_validator.py
from src.config.configuration_manager import ConfigurationManager

def validate_config():
    config_manager = ConfigurationManager()
    
    # Load and validate configuration
    config = config_manager.load_configuration()
    result = config_manager.validate_configuration(config)
    
    if not result.is_valid:
        print("Configuration errors:")
        for error in result.errors:
            print(f"- {error}")
    else:
        print("Configuration is valid")
    
    return result.is_valid

if __name__ == "__main__":
    validate_config()
```

2. **Fix Common Configuration Issues**
```bash
# Ensure required fields are set
BROKER_NAME=YourBroker          # Must not be empty
TRADING_SYMBOLS=EURUSD,GBPUSD   # Must have at least one symbol
RISK_PER_TRADE=0.005            # Must be between 0.001 and 0.05

# Fix numeric format issues
MAX_CONCURRENT_POSITIONS=5      # Must be integer
BREAKEVEN_THRESHOLD_PIPS=15     # Must be positive number

# Fix boolean values
TELEGRAM_ENABLED=true           # Use lowercase true/false
CSV_LOGGING_ENABLED=false
```

### 8. System Resource Issues

#### Problem: High CPU Usage

**Symptoms:**
- CPU usage consistently >80%
- System becomes unresponsive
- Trading loop timeouts

**Solutions:**

1. **CPU Optimization**
```bash
# Reduce analysis frequency
ZONE_DETECTION_INTERVAL_MINUTES=30
POSITION_UPDATE_INTERVAL=120
HEALTH_CHECK_INTERVAL=300

# Limit concurrent operations
MAX_CONCURRENT_ANALYSIS=2
ASYNC_TIMEOUT_SECONDS=15

# Use process priority
sudo renice -5 $(pgrep -f trading_bot)
```

2. **Code Optimization**
```python
# Implement caching for expensive operations
# Use vectorized operations with pandas/numpy
# Optimize database queries
# Reduce unnecessary calculations
```

#### Problem: Disk Space Issues

**Symptoms:**
- "No space left on device" errors
- Log files growing too large
- Database backup failures

**Solutions:**

1. **Disk Space Management**
```bash
# Check disk usage
df -h
du -sh logs/
du -sh data/
du -sh backups/

# Clean up old files
find logs/ -name "*.log" -mtime +7 -delete
find backups/ -name "*.db.gz" -mtime +30 -delete

# Configure log rotation
LOG_FILE_RETENTION=3 days
CSV_RETENTION_DAYS=7
```

2. **Automated Cleanup Script**
```bash
#!/bin/bash
# cleanup.sh

# Remove old log files
find /home/trading/bot-trading-2/logs -name "*.log.*" -mtime +7 -delete

# Remove old CSV files
find /home/trading/bot-trading-2/logs/csv -name "*.csv" -mtime +14 -delete

# Remove old backups
find /home/trading/bot-trading-2/backups -name "*.db.gz" -mtime +30 -delete

# Compress current logs
gzip /home/trading/bot-trading-2/logs/*.log.1

echo "Cleanup completed at $(date)"
```

## Emergency Procedures

### Emergency Shutdown

```bash
# Immediate shutdown
sudo systemctl stop trading-bot

# Force kill if needed
sudo pkill -f trading_bot

# Check for remaining processes
ps aux | grep trading_bot
```

### Emergency Position Closure

```python
# emergency_close.py
from src.mt5_connector import MT5Connector
from src.position_manager import PositionManager

def emergency_close_all():
    connector = MT5Connector()
    position_manager = PositionManager({}, connector)
    
    # Get all open positions
    positions = connector.positions_get()
    
    for position in positions:
        # Close position immediately
        result = position_manager.close_position_immediately(position.ticket)
        print(f"Closed position {position.ticket}: {result}")

if __name__ == "__main__":
    emergency_close_all()
```

### System Recovery

```bash
#!/bin/bash
# recovery.sh

echo "Starting system recovery..."

# Stop bot
sudo systemctl stop trading-bot

# Backup current state
cp data/trading_bot.db backups/emergency_backup_$(date +%Y%m%d_%H%M%S).db

# Check and repair database
sqlite3 data/trading_bot.db "PRAGMA integrity_check;"

# Clear temporary files
rm -f logs/*.tmp
rm -f data/*.tmp

# Restart services
sudo systemctl start trading-bot

# Monitor startup
sleep 10
sudo systemctl status trading-bot

echo "Recovery completed"
```

## Monitoring & Alerting

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

# Check service status
if ! systemctl is-active --quiet trading-bot; then
    echo "CRITICAL: Trading bot service is down"
    # Send alert notification
    curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
         -d "chat_id=$TELEGRAM_CHAT_ID&text=🚨 CRITICAL: Trading bot service is down"
    exit 1
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
if [ $MEMORY_USAGE -gt 85 ]; then
    echo "WARNING: High memory usage: $MEMORY_USAGE%"
fi

# Check disk space
DISK_USAGE=$(df /home/trading | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "WARNING: High disk usage: $DISK_USAGE%"
fi

# Check log errors
ERROR_COUNT=$(grep -c "ERROR" logs/trading_bot.log | tail -1)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "WARNING: High error count: $ERROR_COUNT errors in log"
fi

echo "Health check completed successfully"
```

### Performance Monitoring

```python
# performance_monitor.py
import psutil
import time
from src.database.sqlite_manager import SQLiteManager

def monitor_performance():
    db = SQLiteManager()
    
    while True:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Database performance
        start_time = time.time()
        db.execute_query("SELECT COUNT(*) FROM trades")
        db_response_time = (time.time() - start_time) * 1000
        
        # Log metrics
        print(f"CPU: {cpu_percent}%, Memory: {memory_percent}%, "
              f"Disk: {disk_percent:.1f}%, DB: {db_response_time:.2f}ms")
        
        # Alert if thresholds exceeded
        if cpu_percent > 80 or memory_percent > 80 or db_response_time > 100:
            print("⚠️ Performance threshold exceeded!")
        
        time.sleep(60)

if __name__ == "__main__":
    monitor_performance()
```

This comprehensive troubleshooting guide should help resolve most common issues encountered with the trading bot system. For issues not covered here, check the logs for specific error messages and consult the technical documentation.