# Windows Setup Guide

This guide covers the complete setup process for running the trading bot on Windows, including MetaTrader5 integration, market hours validation, and Windows-specific optimizations.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11 (required for MT5)
- **Python Version**: 3.11+ (for modern async features)
- **MT5 Installation**: MetaTrader5 platform must be installed
- **Permissions**: Administrative privileges may be required for some operations
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: 2GB free space for application and data

### Hardware Recommendations

```yaml
# Recommended system specifications
recommended_specs:
  cpu: "Intel i5/AMD Ryzen 5 or better"
  ram: "8GB DDR4"
  storage: "SSD with 10GB free space"
  network: "Stable broadband connection"
  display: "1920x1080 minimum for MT5 interface"
```

## Windows-Specific Implementation Rules

### MetaTrader5 Integration Requirements

The trading bot is designed specifically for Windows because:

- **MT5 API Limitation**: MetaTrader5 Python API only works on Windows platform
- **COM Interface**: Uses Windows COM objects for MT5 communication
- **Process Integration**: Deep integration with Windows process management
- **File System**: Windows-specific paths and file handling

### Key Implementation Constraints

```python
# Windows-only features
WINDOWS_FEATURES = {
    "mt5_api": "Windows-only MetaTrader5 Python integration",
    "process_management": "Auto-detect and start MT5 if needed",
    "path_detection": "Auto-find MT5 installation directory",
    "error_handling": "Windows-specific MT5 error codes",
    "performance": "Windows process priority optimization"
}
```

## Installation Guide

### Step 1: MetaTrader5 Installation

1. **Download MT5**:
   ```bash
   # Download from MetaQuotes official website
   # https://www.metatrader5.com/en/download
   ```

2. **Install MT5**:
   - Run installer as Administrator
   - Choose installation directory (note the path)
   - Complete broker setup and account connection
   - Verify MT5 is working and can connect to your broker

3. **Enable Algorithmic Trading**:
   - Open MT5 → Tools → Options → Expert Advisors
   - Check "Allow algorithmic trading"
   - Check "Allow DLL imports"
   - Check "Allow imports of external experts"

### Step 2: Python Environment Setup

```bash
# Install UV (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.ps1 | powershell

# Clone and setup project
git clone <repository-url> trading-bot
cd trading-bot

# Install dependencies
uv sync
uv sync --extra dev

# Windows-specific setup
scripts/setup_windows.bat
```

### Step 3: Windows-Specific Configuration

Create `config/windows.yaml`:

```yaml
# Windows-specific configuration
windows:
  # MT5 Configuration
  mt5:
    auto_detect_path: true
    installation_paths:
      - "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
      - "C:\\Program Files (x86)\\MetaTrader 5\\terminal64.exe"
      - "C:\\Users\\%USERNAME%\\AppData\\Roaming\\MetaQuotes\\Terminal\\*.exe"

    startup_timeout: 30  # seconds
    connection_timeout: 10  # seconds
    auto_start: true
    minimize_on_start: true

  # Process Management
  process:
    priority: "high"  # normal, high, realtime
    affinity_mask: null  # CPU affinity (null = all cores)
    memory_limit_mb: 2048

  # File System
  filesystem:
    data_directory: "C:\\TradingBot\\Data"
    log_directory: "C:\\TradingBot\\Logs"
    backup_directory: "C:\\TradingBot\\Backups"
    temp_directory: "%TEMP%\\TradingBot"

  # Performance
  performance:
    gc_optimization: true
    async_io_threads: 4
    database_wal_mode: true
    memory_mapping: true
```

## MT5 Integration Implementation

### MT5 Connector Class

```python
# src/trading_bot/connectors/mt5_connector.py
import MetaTrader5 as mt5
import psutil
import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Dict, List
import yaml

class MT5Connector:
    """
    Windows-compatible MetaTrader5 integration with auto-detection and management
    """

    def __init__(self, config_path: str = "config/windows.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['windows']['mt5']

        self.mt5_path = None
        self.mt5_process = None
        self.is_connected = False

    async def initialize(self) -> bool:
        """
        Initialize MT5 connection with auto-detection and startup
        """
        try:
            # Step 1: Auto-detect MT5 installation
            if self.config['auto_detect_path']:
                self.mt5_path = await self._auto_detect_mt5_path()
                if not self.mt5_path:
                    raise MT5Error("MetaTrader5 installation not found")

            # Step 2: Check if MT5 is running
            if not self._is_mt5_running():
                if self.config['auto_start']:
                    await self._start_mt5()
                else:
                    raise MT5Error("MetaTrader5 is not running and auto_start is disabled")

            # Step 3: Initialize MT5 connection
            if not mt5.initialize():
                error_code = mt5.last_error()
                raise MT5Error(f"MT5 initialization failed: {error_code}")

            # Step 4: Verify account connection
            account_info = mt5.account_info()
            if account_info is None:
                raise MT5Error("No trading account connected")

            self.is_connected = True
            self.logger.info(f"MT5 connected successfully. Account: {account_info.login}")

            return True

        except Exception as e:
            self.logger.error(f"MT5 initialization failed: {e}")
            return False

    async def _auto_detect_mt5_path(self) -> Optional[str]:
        """
        Auto-detect MetaTrader5 installation path on Windows
        """
        search_paths = self.config['installation_paths']

        for path_pattern in search_paths:
            # Handle environment variables
            expanded_path = os.path.expandvars(path_pattern)

            # Handle wildcards
            if '*' in expanded_path:
                import glob
                matches = glob.glob(expanded_path)
                if matches:
                    # Return the first valid executable
                    for match in matches:
                        if os.path.isfile(match) and match.endswith('.exe'):
                            return match
            else:
                if os.path.isfile(expanded_path):
                    return expanded_path

        # Additional search in registry
        try:
            import winreg

            # Check HKEY_LOCAL_MACHINE
            key_path = r"SOFTWARE\MetaQuotes\Terminal"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)

            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)

                try:
                    install_path, _ = winreg.QueryValueEx(subkey, "")
                    terminal_exe = os.path.join(install_path, "terminal64.exe")
                    if os.path.isfile(terminal_exe):
                        return terminal_exe
                except FileNotFoundError:
                    continue
                finally:
                    winreg.CloseKey(subkey)

            winreg.CloseKey(key)

        except ImportError:
            pass  # winreg not available (shouldn't happen on Windows)
        except Exception as e:
            self.logger.debug(f"Registry search failed: {e}")

        return None

    def _is_mt5_running(self) -> bool:
        """
        Check if MetaTrader5 process is running
        """
        for process in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if 'terminal64.exe' in process.info['name'].lower():
                    self.mt5_process = process
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    async def _start_mt5(self) -> bool:
        """
        Start MetaTrader5 process with optimized settings
        """
        if not self.mt5_path:
            raise MT5Error("MT5 path not detected")

        try:
            # Start MT5 with specific parameters
            startup_args = [self.mt5_path]

            if self.config['minimize_on_start']:
                startup_args.append('/minimize')

            # Start process
            process = subprocess.Popen(
                startup_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            # Wait for MT5 to start
            timeout = self.config['startup_timeout']
            start_time = time.time()

            while time.time() - start_time < timeout:
                if self._is_mt5_running():
                    # Additional wait for full initialization
                    await asyncio.sleep(5)
                    return True
                await asyncio.sleep(1)

            raise MT5Error("MT5 startup timeout")

        except Exception as e:
            raise MT5Error(f"Failed to start MT5: {e}")

    async def optimize_mt5_performance(self):
        """
        Optimize MT5 process for trading bot operation
        """
        if not self.mt5_process:
            return

        try:
            # Set process priority
            priority_map = {
                'normal': psutil.NORMAL_PRIORITY_CLASS,
                'high': psutil.HIGH_PRIORITY_CLASS,
                'realtime': psutil.REALTIME_PRIORITY_CLASS
            }

            priority = self.config.get('priority', 'normal')
            if priority in priority_map:
                self.mt5_process.nice(priority_map[priority])

            # Set CPU affinity if specified
            affinity_mask = self.config.get('affinity_mask')
            if affinity_mask:
                self.mt5_process.cpu_affinity(affinity_mask)

            # Set memory limits if specified
            memory_limit = self.config.get('memory_limit_mb')
            if memory_limit:
                # Note: This is advisory on Windows
                pass

        except Exception as e:
            self.logger.warning(f"Performance optimization failed: {e}")

    async def place_order(self, signal) -> Dict:
        """
        Place trading order through MT5 with Windows-specific error handling
        """
        if not self.is_connected:
            raise MT5Error("MT5 not connected")

        try:
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": signal.volume,
                "type": mt5.ORDER_TYPE_BUY if signal.direction == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "deviation": 20,
                "magic": signal.magic_number,
                "comment": f"Bot_{signal.strategy_name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send order
            result = mt5.order_send(request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = self._get_error_description(result.retcode)
                raise MT5TradingError(f"Order failed: {error_msg}")

            return {
                "success": True,
                "ticket": result.order,
                "price": result.price,
                "volume": result.volume,
                "retcode": result.retcode
            }

        except Exception as e:
            self.logger.error(f"Order placement failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_error_description(self, retcode: int) -> str:
        """
        Get human-readable error description for MT5 return codes
        """
        error_codes = {
            10004: "Requote",
            10006: "Request rejected",
            10007: "Request canceled by trader",
            10008: "Order placed",
            10009: "Request completed",
            10010: "Only part of the request was completed",
            10011: "Request processing error",
            10012: "Request canceled by timeout",
            10013: "Invalid request",
            10014: "Invalid volume in the request",
            10015: "Invalid price in the request",
            10016: "Invalid stops in the request",
            10017: "Trade is disabled",
            10018: "Market is closed",
            10019: "There is not enough money to complete the request",
            10020: "Prices changed",
            10021: "There are no quotes to process the request",
        }

        return error_codes.get(retcode, f"Unknown error code: {retcode}")

    async def cleanup(self):
        """
        Cleanup MT5 connection and processes
        """
        try:
            if self.is_connected:
                mt5.shutdown()
                self.is_connected = False

            # Optionally terminate MT5 process if we started it
            if self.mt5_process and self.config.get('auto_terminate', False):
                self.mt5_process.terminate()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
```

## Market Hours Validation System

### Comprehensive Market Hours Implementation

```python
# src/trading_bot/utils/market_hours.py
from datetime import datetime, timezone, timedelta
import pytz
from typing import Dict, List, Optional
import yaml

class MarketHoursValidator:
    """
    Comprehensive market hours validation for different asset classes
    """

    def __init__(self, config_path: str = "config/market_hours.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Server timezone (usually GMT/UTC for MT5)
        self.server_tz = pytz.UTC

        # Trading holidays (extend as needed)
        self.holidays = {
            2025: [
                datetime(2025, 1, 1),   # New Year
                datetime(2025, 4, 18),  # Good Friday
                datetime(2025, 4, 21),  # Easter Monday
                datetime(2025, 5, 26),  # Spring Bank Holiday
                datetime(2025, 8, 25),  # Summer Bank Holiday
                datetime(2025, 12, 25), # Christmas
                datetime(2025, 12, 26), # Boxing Day
            ]
        }

    def is_trading_allowed(self, symbol: str, current_time: Optional[datetime] = None) -> bool:
        """
        Check if trading is allowed for symbol at current time
        """
        if current_time is None:
            current_time = datetime.now(self.server_tz)

        # Get asset class for symbol
        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            return False

        # Get market hours config
        market_config = self.config['market_hours'][asset_class]

        # Check all validation criteria
        checks = [
            self.is_trading_day(current_time, market_config),
            self.is_within_trading_hours(current_time, market_config),
            not self.is_holiday(current_time),
            self.is_outside_buffer_periods(current_time, market_config)
        ]

        return all(checks)

    def get_asset_class(self, symbol: str) -> Optional[str]:
        """
        Get asset class for a trading symbol
        """
        mapping = self.config.get('asset_class_mapping', {})
        return mapping.get(symbol)

    def is_trading_day(self, dt: datetime, market_config: Dict) -> bool:
        """
        Check if current day is a valid trading day
        """
        weekday_name = dt.strftime('%A').lower()

        # Check if day is in trading days
        if weekday_name not in market_config['trading_days']:
            return False

        # Check if day is excluded
        if weekday_name in market_config.get('excluded_days', []):
            return False

        return True

    def is_within_trading_hours(self, dt: datetime, market_config: Dict) -> bool:
        """
        Check if current time is within trading hours
        """
        start_time = market_config['start_time']
        end_time = market_config['end_time']

        current_time = dt.strftime('%H:%M')

        # Handle overnight sessions (like forex Sunday-Friday)
        if start_time <= end_time:
            # Normal day session
            return start_time <= current_time <= end_time
        else:
            # Overnight session (crosses midnight)
            return current_time >= start_time or current_time <= end_time

    def is_holiday(self, dt: datetime) -> bool:
        """
        Check if current date is a trading holiday
        """
        year = dt.year
        if year not in self.holidays:
            return False

        date_only = dt.date()
        holiday_dates = [h.date() for h in self.holidays[year]]
        return date_only in holiday_dates

    def is_outside_buffer_periods(self, dt: datetime, market_config: Dict) -> bool:
        """
        Check if current time is outside buffer periods
        """
        buffer_before_close = market_config.get('buffer_before_close', 0)
        buffer_after_open = market_config.get('buffer_after_open', 0)

        if buffer_before_close == 0 and buffer_after_open == 0:
            return True

        # Calculate buffer times
        start_time = datetime.strptime(market_config['start_time'], '%H:%M').time()
        end_time = datetime.strptime(market_config['end_time'], '%H:%M').time()

        # Combine with current date
        current_date = dt.date()
        market_open = datetime.combine(current_date, start_time).replace(tzinfo=self.server_tz)
        market_close = datetime.combine(current_date, end_time).replace(tzinfo=self.server_tz)

        # Handle overnight sessions
        if start_time > end_time:
            if dt.time() >= start_time:
                # We're in today's session that started yesterday
                market_close += timedelta(days=1)
            else:
                # We're in yesterday's session that continues today
                market_open -= timedelta(days=1)

        # Check buffers
        buffer_start = market_open + timedelta(minutes=buffer_after_open)
        buffer_end = market_close - timedelta(minutes=buffer_before_close)

        return buffer_start <= dt <= buffer_end

    def get_next_trading_session(self, symbol: str) -> Optional[datetime]:
        """
        Get the next trading session start time for a symbol
        """
        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            return None

        market_config = self.config['market_hours'][asset_class]
        current_time = datetime.now(self.server_tz)

        # Start checking from tomorrow
        check_date = current_time.date() + timedelta(days=1)

        # Check up to 7 days ahead
        for i in range(7):
            check_datetime = datetime.combine(check_date, datetime.min.time()).replace(tzinfo=self.server_tz)

            if self.is_trading_day(check_datetime, market_config) and not self.is_holiday(check_datetime):
                # Calculate session start with buffer
                start_time = datetime.strptime(market_config['start_time'], '%H:%M').time()
                session_start = datetime.combine(check_date, start_time).replace(tzinfo=self.server_tz)
                buffer_minutes = market_config.get('buffer_after_open', 0)

                return session_start + timedelta(minutes=buffer_minutes)

            check_date += timedelta(days=1)

        return None

    def get_trading_status_message(self, symbol: str) -> str:
        """
        Get human-readable trading status for a symbol
        """
        asset_class = self.get_asset_class(symbol)
        if not asset_class:
            return f"❌ {symbol}: Unknown asset class"

        if self.is_trading_allowed(symbol):
            return f"✅ {symbol}: Trading allowed ({asset_class})"

        next_session = self.get_next_trading_session(symbol)
        if next_session:
            return f"🕐 {symbol}: Market closed. Next session: {next_session.strftime('%Y-%m-%d %H:%M %Z')} ({asset_class})"
        else:
            return f"❌ {symbol}: Market closed ({asset_class})"

    def get_market_hours_summary(self) -> Dict:
        """
        Get comprehensive market hours summary for all asset classes
        """
        summary = {}
        current_time = datetime.now(self.server_tz)

        for asset_class, config in self.config['market_hours'].items():
            symbols = [symbol for symbol, cls in self.config['asset_class_mapping'].items()
                      if cls == asset_class]

            summary[asset_class] = {
                'trading_now': self.is_trading_day(current_time, config) and
                              self.is_within_trading_hours(current_time, config) and
                              not self.is_holiday(current_time) and
                              self.is_outside_buffer_periods(current_time, config),
                'trading_days': config['trading_days'],
                'trading_hours': f"{config['start_time']} - {config['end_time']}",
                'symbols': symbols,
                'next_session': None
            }

            if not summary[asset_class]['trading_now']:
                # Find next session for this asset class
                next_session = self.get_next_trading_session(symbols[0] if symbols else None)
                summary[asset_class]['next_session'] = next_session.isoformat() if next_session else None

        return summary
```

### Market Hours Configuration

Create `config/market_hours.yaml`:

```yaml
# Asset-specific trading hours configuration
market_hours:
  forex:
    trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    excluded_days: ["saturday", "sunday"]
    start_time: "00:00"  # Sunday 17:00 EST (Monday 00:00 GMT)
    end_time: "22:00"    # Friday 17:00 EST (Friday 22:00 GMT)
    buffer_before_close: 60  # Stop trading 60 minutes before market close
    buffer_after_open: 30    # Wait 30 minutes after market open

  commodities:
    trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    excluded_days: ["saturday", "sunday"]
    start_time: "01:00"  # Monday 01:00 GMT (Sunday 18:00 EST)
    end_time: "21:00"    # Friday 21:00 GMT (Friday 16:00 EST)
    buffer_before_close: 120 # Stop trading 2 hours before close (spread widening)
    buffer_after_open: 60    # Wait 1 hour after open

  crypto:
    trading_days: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    excluded_days: []    # 24/7 trading
    start_time: "00:00"
    end_time: "23:59"
    buffer_before_close: 0
    buffer_after_open: 0

# Symbol to asset class mapping
asset_class_mapping:
  # Forex Major Pairs
  "EURUSD": "forex"
  "GBPUSD": "forex"
  "USDCHF": "forex"
  "USDJPY": "forex"
  "AUDUSD": "forex"
  "USDCAD": "forex"
  "NZDUSD": "forex"
  "EURGBP": "forex"
  "EURJPY": "forex"
  "GBPJPY": "forex"

  # Commodities
  "XAUUSD": "commodities"  # Gold
  "XAGUSD": "commodities"  # Silver
  "XBRUSD": "commodities"  # Brent Oil
  "XTIUSD": "commodities"  # WTI Oil

  # Cryptocurrencies
  "BTCUSD": "crypto"
  "ETHUSD": "crypto"
  "ADAUSD": "crypto"
  "DOTUSD": "crypto"
```

## Integration with Main Trading Bot

### Windows-Optimized Trading Loop

```python
# Integration with main trading bot
class WindowsTradingBot:
    """
    Windows-optimized trading bot with MT5 integration
    """

    def __init__(self, config):
        self.config = config
        self.mt5_connector = MT5Connector()
        self.market_validator = MarketHoursValidator()
        self.is_running = False

    async def initialize(self):
        """
        Initialize all Windows-specific components
        """
        # Initialize MT5 connection
        mt5_success = await self.mt5_connector.initialize()
        if not mt5_success:
            raise RuntimeError("Failed to initialize MT5 connection")

        # Optimize MT5 performance
        await self.mt5_connector.optimize_mt5_performance()

        # Setup Windows-specific logging
        await self._setup_windows_logging()

        # Initialize database with Windows paths
        await self._initialize_database()

        self.logger.info("Windows trading bot initialized successfully")

    async def trading_loop(self):
        """
        Main trading loop with Windows optimizations and market hours validation
        """
        self.is_running = True

        while self.is_running:
            loop_start_time = time.time()
            current_time = datetime.now(pytz.UTC)

            try:
                for symbol in self.trading_symbols:
                    # ✅ FIRST CHECK: Market hours validation
                    if not self.market_validator.is_trading_allowed(symbol, current_time):
                        self.logger.debug(f"⏰ Market closed for {symbol}")
                        continue

                    # ✅ SECOND CHECK: Existing position limit (max 1 per symbol)
                    if await self.has_active_position(symbol):
                        self.logger.debug(f"📊 Position already exists for {symbol}")
                        continue

                    # ✅ THIRD CHECK: MT5 connection status
                    if not self.mt5_connector.is_connected:
                        self.logger.warning("MT5 connection lost, attempting reconnection")
                        await self.mt5_connector.initialize()
                        continue

                    # ✅ PROCEED: Run strategy analysis
                    await self.analyze_and_trade(symbol)

                # Windows-specific performance monitoring
                await self._monitor_system_performance()

            except Exception as e:
                self.logger.error(f"Trading loop error: {e}")
                await self._handle_loop_error(e)

            # Ensure 60-second loop timing
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, 60 - loop_duration)
            await asyncio.sleep(sleep_time)

    async def execute_trade(self, signal):
        """
        Execute trade with final Windows/MT5 validations
        """
        symbol = signal.symbol

        # Final market hours check
        if not self.market_validator.is_trading_allowed(symbol):
            self.logger.warning(f"⏰ Trade cancelled - market closed for {symbol}")
            return False

        # Execute through MT5
        result = await self.mt5_connector.place_order(signal)

        if result['success']:
            self.logger.info(f"✅ Trade executed: {symbol} - Ticket: {result['ticket']}")

            # Windows-specific trade logging
            await self._log_trade_windows(signal, result)

            return True
        else:
            self.logger.error(f"❌ Trade failed: {symbol} - Error: {result['error']}")
            return False

    async def _setup_windows_logging(self):
        """
        Setup Windows-specific logging with proper file paths
        """
        log_config = self.config['windows']['filesystem']
        log_dir = Path(log_config['log_directory'])
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure loguru for Windows
        from loguru import logger

        logger.add(
            log_dir / "trading_bot_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
        )

    async def _monitor_system_performance(self):
        """
        Monitor Windows system performance and MT5 health
        """
        # Check MT5 process health
        if self.mt5_connector.mt5_process:
            try:
                cpu_percent = self.mt5_connector.mt5_process.cpu_percent()
                memory_mb = self.mt5_connector.mt5_process.memory_info().rss / 1024 / 1024

                if cpu_percent > 80:
                    self.logger.warning(f"High MT5 CPU usage: {cpu_percent}%")

                if memory_mb > 1024:  # 1GB
                    self.logger.warning(f"High MT5 memory usage: {memory_mb:.1f}MB")

            except psutil.NoSuchProcess:
                self.logger.error("MT5 process not found")
                await self.mt5_connector.initialize()

        # Check system resources
        system_memory = psutil.virtual_memory()
        if system_memory.percent > 90:
            self.logger.warning(f"High system memory usage: {system_memory.percent}%")

    async def cleanup(self):
        """
        Cleanup Windows-specific resources
        """
        self.is_running = False

        try:
            # Cleanup MT5 connection
            await self.mt5_connector.cleanup()

            # Close database connections
            await self.database.close()

            # Windows-specific cleanup
            await self._cleanup_windows_resources()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
```

## Windows Setup Scripts

### Automated Setup Script (`scripts/setup_windows.bat`)

```batch
@echo off
echo Setting up Trading Bot for Windows...

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - Good!
) else (
    echo Please run this script as Administrator
    pause
    exit /b 1
)

REM Create directories
echo Creating directory structure...
mkdir "C:\TradingBot\Data" 2>nul
mkdir "C:\TradingBot\Logs" 2>nul
mkdir "C:\TradingBot\Backups" 2>nul
mkdir "C:\TradingBot\Config" 2>nul

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo Python found
) else (
    echo Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check UV installation
echo Checking UV installation...
uv --version >nul 2>&1
if %errorLevel% == 0 (
    echo UV found
) else (
    echo Installing UV...
    powershell -Command "& {Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression}"
)

REM Install dependencies
echo Installing Python dependencies...
uv sync
uv sync --extra dev

REM Check MetaTrader5 installation
echo Checking MetaTrader5 installation...
if exist "C:\Program Files\MetaTrader 5\terminal64.exe" (
    echo MetaTrader5 found in standard location
) else if exist "C:\Program Files (x86)\MetaTrader 5\terminal64.exe" (
    echo MetaTrader5 found in x86 location
) else (
    echo MetaTrader5 not found in standard locations
    echo Please install MetaTrader5 from https://www.metatrader5.com/en/download
    pause
)

REM Set environment variables
echo Setting environment variables...
setx TRADING_BOT_HOME "C:\TradingBot" /M
setx TRADING_BOT_ENV "development" /M

REM Copy configuration templates
echo Copying configuration templates...
copy "config\default.yaml" "C:\TradingBot\Config\default.yaml"
copy "config\windows.yaml" "C:\TradingBot\Config\windows.yaml"

REM Create Windows service (optional)
echo Would you like to install as Windows service? (Y/N)
set /p service_choice=
if /i "%service_choice%"=="Y" (
    echo Installing Windows service...
    REM Service installation code here
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Configure your broker settings in C:\TradingBot\Config\default.yaml
echo 2. Ensure MetaTrader5 is connected to your broker account
echo 3. Run: uv run trading-bot start --config production
echo.
pause
```

### PowerShell Installation Script (`scripts/install_mt5.ps1`)

```powershell
# PowerShell script for MT5 installation and configuration

Write-Host "MetaTrader5 Installation and Configuration Script" -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Please run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Download MT5 installer
$mt5Url = "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
$mt5Installer = "$env:TEMP\mt5setup.exe"

Write-Host "Downloading MetaTrader5 installer..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $mt5Url -OutFile $mt5Installer
    Write-Host "Download completed" -ForegroundColor Green
} catch {
    Write-Host "Download failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Install MT5 silently
Write-Host "Installing MetaTrader5..." -ForegroundColor Yellow
try {
    Start-Process -FilePath $mt5Installer -ArgumentList "/S" -Wait
    Write-Host "Installation completed" -ForegroundColor Green
} catch {
    Write-Host "Installation failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Clean up installer
Remove-Item $mt5Installer -Force

# Verify installation
$mt5Paths = @(
    "C:\Program Files\MetaTrader 5\terminal64.exe",
    "C:\Program Files (x86)\MetaTrader 5\terminal64.exe"
)

$mt5Found = $false
foreach ($path in $mt5Paths) {
    if (Test-Path $path) {
        Write-Host "MetaTrader5 found at: $path" -ForegroundColor Green
        $mt5Found = $true
        break
    }
}

if (-not $mt5Found) {
    Write-Host "MetaTrader5 installation verification failed" -ForegroundColor Red
    exit 1
}

# Configure Windows firewall
Write-Host "Configuring Windows Firewall..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "MetaTrader5" -Direction Inbound -Program "C:\Program Files\MetaTrader 5\terminal64.exe" -Action Allow
    Write-Host "Firewall configured" -ForegroundColor Green
} catch {
    Write-Host "Firewall configuration failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "Please manually:" -ForegroundColor Yellow
Write-Host "1. Open MetaTrader5" -ForegroundColor White
Write-Host "2. Connect to your broker" -ForegroundColor White
Write-Host "3. Enable algorithmic trading in Tools -> Options -> Expert Advisors" -ForegroundColor White
```

## Trading Hours Validation Examples

### Real-World Examples

```bash
# Weekend check (Saturday)
🕐 EURUSD: Market closed. Next session: 2025-01-06 00:30 UTC (forex)
🕐 XAUUSD: Market closed. Next session: 2025-01-06 01:00 UTC (commodities)
✅ BTCUSD: Trading allowed (crypto)

# Friday near close
🕐 EURUSD: Market closed. Buffer period active (forex)
🕐 XAUUSD: Market closed. Buffer period active (commodities)
✅ BTCUSD: Trading allowed (crypto)

# Holiday check (Christmas)
🕐 EURUSD: Market closed. Holiday: Christmas Day (forex)
🕐 XAUUSD: Market closed. Holiday: Christmas Day (commodities)
✅ BTCUSD: Trading allowed (crypto)

# Normal trading hours
✅ EURUSD: Trading allowed (forex)
✅ XAUUSD: Trading allowed (commodities)
✅ BTCUSD: Trading allowed (crypto)
```

## CLI Commands for Windows Management

### Windows-Specific Commands

```bash
# System status and diagnostics
uv run trading-bot windows status
uv run trading-bot windows mt5-check
uv run trading-bot windows performance

# Market status checking
uv run trading-bot market-status
uv run trading-bot market-status --symbol EURUSD
uv run trading-bot next-session

# MT5 management
uv run trading-bot mt5 start
uv run trading-bot mt5 stop
uv run trading-bot mt5 restart
uv run trading-bot mt5 optimize

# Windows service management
uv run trading-bot service install
uv run trading-bot service uninstall
uv run trading-bot service start
uv run trading-bot service stop

# Force trading during closed hours (for testing)
uv run trading-bot start --ignore-market-hours

# Windows-specific testing
uv run trading-bot test mt5-connection
uv run trading-bot test market-hours
uv run trading-bot test windows-performance
```

## Troubleshooting Guide

### Common Windows Issues

#### 1. MT5 Connection Issues
```
Error: MT5 initialization failed
Solutions:
- Ensure MT5 is installed and running
- Check if algorithmic trading is enabled
- Verify broker connection in MT5
- Run as Administrator
```

#### 2. Permission Issues
```
Error: Access denied to create directories
Solutions:
- Run script as Administrator
- Check Windows UAC settings
- Verify folder permissions
```

#### 3. Performance Issues
```
Problem: High CPU/Memory usage
Solutions:
- Adjust process priority in config
- Set CPU affinity
- Increase memory limits
- Close unnecessary MT5 charts
```

#### 4. Market Hours Validation
```
Problem: Trades not executing during valid hours
Solutions:
- Check system timezone settings
- Verify market hours configuration
- Check holiday calendar
- Test with --ignore-market-hours flag
```

### Performance Optimization

```yaml
# Windows performance optimization settings
windows_optimization:
  process_priority: "high"
  memory_optimization:
    enable_gc_optimization: true
    memory_limit_mb: 2048

  mt5_optimization:
    minimize_charts: true
    disable_news: true
    limit_history_bars: 10000

  system_optimization:
    disable_windows_defender_scanning: false  # Manual configuration required
    set_power_plan: "high_performance"
    disable_sleep_mode: true
```

This comprehensive Windows setup guide provides everything needed to successfully deploy and run the trading bot on Windows with MetaTrader5 integration and proper market hours validation.
