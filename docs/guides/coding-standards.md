# Coding Standards & Best Practices

**Version**: 1.0.0  
**Last Updated**: 2025-11-29  
**Status**: Mandatory for all code contributions

## 📋 Table of Contents

1. [Project Structure](#project-structure)
2. [Naming Conventions](#naming-conventions)
3. [Code Style](#code-style)
4. [Documentation Standards](#documentation-standards)
5. [Testing Requirements](#testing-requirements)
6. [Import Organization](#import-organization)
7. [Error Handling](#error-handling)
8. [Configuration Management](#configuration-management)
9. [Logging Standards](#logging-standards)
10. [Examples](#examples)

---

## 1. Project Structure

### 📁 Directory Layout

```
trading-bot/
├── src/trading_bot/              # Main source code
│   ├── __init__.py               # Package initialization
│   ├── cli.py                    # CLI entry point
│   ├── config.py                 # Configuration management
│   ├── main.py                   # Main orchestrator
│   │
│   ├── connectors/               # External integrations
│   │   ├── __init__.py
│   │   ├── mt5_connector.py     # MT5 connection handler
│   │   ├── account_manager.py   # Account operations
│   │   ├── symbol_manager.py    # Symbol operations
│   │   ├── order_manager.py     # Order execution
│   │   ├── position_manager.py  # Position tracking
│   │   ├── data_manager.py      # Market data
│   │   └── dry_run_wrapper.py   # Dry-run simulation
│   │
│   ├── strategies/               # Trading strategies
│   │   ├── __init__.py
│   │   ├── base_strategy.py     # Base strategy class
│   │   └── foundation_strategy.py
│   │
│   ├── position/                 # Position management
│   │   ├── __init__.py
│   │   └── position_manager.py
│   │
│   ├── risk/                     # Risk management
│   │   ├── __init__.py
│   │   └── risk_manager.py
│   │
│   ├── market_structure/         # Market analysis
│   │   ├── __init__.py
│   │   └── structure_analyzer.py
│   │
│   ├── data/                     # Database layer
│   │   ├── __init__.py
│   │   ├── database.py          # Database manager
│   │   ├── models.py            # SQLAlchemy models
│   │   └── repositories/        # Data access layer
│   │       ├── __init__.py
│   │       └── base_repository.py
│   │
│   ├── utils/                    # Utility modules
│   │   ├── __init__.py
│   │   ├── logger.py            # Logging utilities
│   │   ├── validators.py       # Data validators
│   │   └── helpers.py           # Helper functions
│   │
│   ├── exceptions/               # Custom exceptions
│   │   ├── __init__.py
│   │   ├── mt5_exceptions.py
│   │   └── connector_exceptions.py
│   │
│   └── notifications/            # Notification system
│       ├── __init__.py
│       └── telegram_notifier.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── connectors/
│   │   │   ├── __init__.py
│   │   │   ├── test_mt5_connector.py
│   │   │   ├── test_account_manager.py
│   │   │   └── ...
│   │   └── test_config.py
│   │
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   └── test_mt5_integration.py
│   │
│   ├── properties/               # Property-based tests
│   │   ├── __init__.py
│   │   └── test_risk_properties.py
│   │
│   └── utils/                    # Test utilities
│       ├── __init__.py
│       ├── mock_helpers.py
│       └── data_generators.py
│
├── config/                       # Configuration files
│   ├── default.yaml
│   ├── development.yaml
│   ├── production.yaml
│   └── trading_types.yaml
│
├── docs/                         # Documentation
│   ├── guides/                   # Implementation guides
│   │   ├── coding-standards.md  # This file
│   │   ├── deployment-guide.md
│   │   └── troubleshooting-guide.md
│   └── ...
│
├── scripts/                      # Utility scripts
│   ├── setup_environment.py
│   └── migrate_to_postgresql.py
│
└── backup/                       # Archived code
    ├── src/
    └── tests/
```

### 📏 Directory Rules

1. **One Purpose Per Directory**: Each directory should have a single, clear responsibility
2. **Maximum 3 Levels**: Avoid deeply nested directories (max 3 levels deep)
3. **Alphabetical Order**: Files within a directory should be alphabetically organized
4. **Always Include `__init__.py`**: Every Python package directory must have `__init__.py`

---

## 2. Naming Conventions

### 📝 File Naming

#### Python Files
```python
# ✅ CORRECT - Snake case, descriptive
mt5_connector.py
account_manager.py
risk_calculator.py
supply_demand_analyzer.py

# ❌ WRONG - Camel case, abbreviations
Mt5Connector.py
AcctMgr.py
riskCalc.py
SD_analyzer.py
```

#### Test Files
```python
# ✅ CORRECT - Prefix with 'test_', mirrors source structure
test_mt5_connector.py
test_account_manager.py
test_risk_calculator.py

# ❌ WRONG - No 'test_' prefix or wrong naming
mt5_connector_test.py
test_mt5.py
connector_tests.py
```

#### Configuration Files
```yaml
# ✅ CORRECT - Lowercase, descriptive
default.yaml
development.yaml
trading_types.yaml
risk_parameters.yaml

# ❌ WRONG - Mixed case, unclear
Default.yml
dev_config.yaml
types.yaml
params.yaml
```

### 🏷️ Class Naming

```python
# ✅ CORRECT - PascalCase, noun, descriptive
class MT5Connector:
    pass

class AccountManager:
    pass

class SupplyDemandAnalyzer:
    pass

class TelegramNotifier:
    pass

# ❌ WRONG - Snake case, verb, abbreviations
class mt5_connector:
    pass

class GetAccount:
    pass

class SDAnalyzer:
    pass

class TGNotif:
    pass
```

### 🔤 Function/Method Naming

```python
# ✅ CORRECT - Snake case, verb_noun pattern, descriptive
def get_account_info():
    pass

def calculate_position_size():
    pass

def validate_trading_signal():
    pass

async def fetch_market_data():
    pass

# ❌ WRONG - Camel case, unclear, missing verb
def GetAccountInfo():
    pass

def calc():
    pass

def signal():
    pass

def marketData():
    pass
```

### 📊 Variable Naming

```python
# ✅ CORRECT - Snake case, descriptive
account_balance = 10000.0
max_position_size = 0.01
stop_loss_price = 1.0950
connection_timeout = 30

# Constants - ALL_CAPS_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_LEVERAGE = 100
API_TIMEOUT_SECONDS = 30

# Private attributes - leading underscore
_internal_state = {}
_connection_pool = None

# ❌ WRONG - Camel case, abbreviations, single letters
accountBalance = 10000.0
maxPosSz = 0.01
sl = 1.0950
to = 30

# ❌ WRONG - Constants not in caps
max_retry_attempts = 3
default_leverage = 100
```

### 📦 Module/Package Naming

```python
# ✅ CORRECT - Lowercase, short, descriptive
trading_bot
connectors
strategies
risk
utils

# ❌ WRONG - Mixed case, long names
Trading_Bot
MT5Connectors
StrategyImplementations
RiskManagementSystem
```

---

## 3. Code Style

### 🎨 Formatting Standards

**Mandatory Tool**: Black (line length: 100)

```bash
# Run before commit
uv run black src/ tests/
```

### 📐 Type Hints (Mandatory)

```python
# ✅ CORRECT - Complete type hints
from typing import Dict, List, Optional, Any
from datetime import datetime

def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    stop_loss_pips: float,
    pip_value: float
) -> float:
    """
    Calculate position size based on risk.
    
    Args:
        account_balance: Current account balance in USD
        risk_percentage: Risk as decimal (0.01 = 1%)
        stop_loss_pips: Stop loss distance in pips
        pip_value: Value per pip
        
    Returns:
        Position size in lots
    """
    risk_amount = account_balance * risk_percentage
    position_size = risk_amount / (stop_loss_pips * pip_value)
    return round(position_size, 2)

# ❌ WRONG - No type hints
def calculate_position_size(account_balance, risk_percentage, stop_loss_pips, pip_value):
    risk_amount = account_balance * risk_percentage
    position_size = risk_amount / (stop_loss_pips * pip_value)
    return round(position_size, 2)
```

### 📝 Docstring Standards

**Format**: Google Style

```python
# ✅ CORRECT - Complete docstring
class MT5Connector:
    """
    MetaTrader5 platform connector.
    
    Manages connection lifecycle, health monitoring, and basic MT5 operations.
    Supports automatic reconnection and connection pooling.
    
    Attributes:
        terminal_path: Path to MT5 terminal executable
        login: Trading account login ID
        timeout: Connection timeout in seconds
        
    Example:
        >>> connector = MT5Connector(login=12345, password="secret")
        >>> connector.initialize()
        >>> print(connector.account_info)
    """
    
    def __init__(
        self,
        terminal_path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        """
        Initialize MT5 connector.
        
        Args:
            terminal_path: Path to MT5 terminal (auto-detect if None)
            login: Trading account login
            password: Trading account password
            timeout: Connection timeout in seconds
            
        Raises:
            ImportError: If MetaTrader5 package not available
        """
        pass

# ❌ WRONG - Missing or incomplete docstring
class MT5Connector:
    """MT5 connector"""
    
    def __init__(self, terminal_path=None, login=None, password=None, timeout=30):
        pass
```

### 🔄 Async/Await Standards

```python
# ✅ CORRECT - Async functions clearly marked
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

async def get_market_data(
    symbol: str,
    timeframe: str,
    count: int = 100
) -> pd.DataFrame:
    """
    Fetch market data asynchronously.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe (H1, H4, D1)
        count: Number of bars
        
    Returns:
        DataFrame with OHLCV data
    """
    async with aiohttp.ClientSession() as session:
        data = await session.get(f"/api/data/{symbol}")
        return pd.DataFrame(data)

# ❌ WRONG - Sync function when async needed
def get_market_data(symbol, timeframe, count=100):
    response = requests.get(f"/api/data/{symbol}")
    return pd.DataFrame(response.json())
```

### 🎯 Class Structure

```python
# ✅ CORRECT - Organized class structure
class TradingStrategy:
    """Base trading strategy class."""
    
    # Class constants
    MAX_POSITIONS = 5
    DEFAULT_RISK = 0.01
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize strategy."""
        # Public attributes
        self.config = config
        self.active = True
        
        # Private attributes
        self._positions: List[Dict] = []
        self._signals: List[Dict] = []
    
    # Public methods
    def analyze_market(self) -> Dict[str, Any]:
        """Analyze market conditions."""
        pass
    
    def generate_signal(self) -> Optional[Dict]:
        """Generate trading signal."""
        pass
    
    # Private methods
    def _validate_signal(self, signal: Dict) -> bool:
        """Validate trading signal."""
        pass
    
    def _calculate_size(self, risk: float) -> float:
        """Calculate position size."""
        pass
    
    # Properties
    @property
    def is_active(self) -> bool:
        """Check if strategy is active."""
        return self.active
    
    # Magic methods
    def __repr__(self) -> str:
        return f"TradingStrategy(active={self.active})"

# ❌ WRONG - Unorganized structure
class TradingStrategy:
    def generate_signal(self):
        pass
    
    def __init__(self, config):
        self._positions = []
        self.config = config
    
    @property
    def is_active(self):
        return self.active
    
    def _validate_signal(self, signal):
        pass
```

---

## 4. Documentation Standards

### 📚 Module Documentation

```python
# ✅ CORRECT - Module-level docstring at top
"""
MetaTrader5 Connector Module

This module provides connection and interaction with MetaTrader5 trading platform.
Supports account management, order execution, and market data retrieval.

Features:
    - Automatic connection retry
    - Health monitoring
    - Connection pooling
    - Error recovery

Example:
    >>> from trading_bot.connectors import MT5Connector
    >>> connector = MT5Connector(login=12345)
    >>> connector.initialize()
    
See Also:
    - account_manager.py: Account operations
    - order_manager.py: Order execution
"""

import time
from typing import Optional, Dict, Any
...

# ❌ WRONG - No module docstring or at bottom
import time
from typing import Optional, Dict, Any

# Some comment here
class MT5Connector:
    pass
```

### 📖 Inline Comments

```python
# ✅ CORRECT - Clear, meaningful comments
def calculate_risk_amount(
    balance: float,
    risk_percent: float,
    stop_loss_pips: float
) -> float:
    """Calculate risk amount in USD."""
    # Convert risk percentage to decimal (1% = 0.01)
    risk_decimal = risk_percent / 100
    
    # Calculate maximum loss amount based on account balance
    max_loss = balance * risk_decimal
    
    # Account for pip value in final calculation
    # Note: Pip value varies by symbol (0.0001 for EUR/USD, 0.01 for USD/JPY)
    risk_per_pip = max_loss / stop_loss_pips
    
    return risk_per_pip

# ❌ WRONG - Obvious or misleading comments
def calculate_risk_amount(balance, risk_percent, stop_loss_pips):
    # Calculate risk
    risk_decimal = risk_percent / 100  # Divide by 100
    
    # Calculate loss
    max_loss = balance * risk_decimal  # Multiply
    
    # Calculate
    risk_per_pip = max_loss / stop_loss_pips  # Division
    
    return risk_per_pip  # Return value
```

---

## 5. Testing Requirements

### 🧪 Test Structure

```python
# ✅ CORRECT - Organized test class
"""
Unit tests for MT5 Connector.

Tests cover connection lifecycle, error handling, and retry logic.
"""

import pytest
from unittest.mock import Mock, patch
from trading_bot.connectors import MT5Connector

class TestMT5Connector:
    """Test MT5Connector class."""
    
    @pytest.fixture
    def connector(self):
        """Create MT5 connector instance for testing."""
        return MT5Connector(login=12345, password="test")
    
    def test_initialization_success(self, connector):
        """Test successful MT5 initialization."""
        # Arrange
        expected_login = 12345
        
        # Act
        result = connector.initialize()
        
        # Assert
        assert result is True
        assert connector.account_info["login"] == expected_login
    
    def test_initialization_failure_retry(self, connector):
        """Test initialization retry mechanism on failure."""
        # Arrange
        connector.retry_attempts = 3
        
        # Act & Assert
        with patch("MetaTrader5.initialize", return_value=False):
            with pytest.raises(MT5ConnectionError):
                connector.initialize()
    
    @pytest.mark.parametrize(
        "timeout,expected",
        [
            (10, True),
            (30, True),
            (60, True),
        ]
    )
    def test_timeout_values(self, timeout, expected):
        """Test different timeout values."""
        connector = MT5Connector(timeout=timeout)
        assert connector.timeout == timeout

# ❌ WRONG - Unorganized, unclear tests
def test_mt5():
    connector = MT5Connector()
    result = connector.initialize()
    assert result

def test_mt5_2():
    c = MT5Connector()
    c.initialize()
```

### 📊 Test Naming

```python
# ✅ CORRECT - Clear test names
def test_calculate_position_size_with_valid_inputs():
    pass

def test_calculate_position_size_returns_zero_when_risk_is_zero():
    pass

def test_validate_symbol_raises_error_for_invalid_symbol():
    pass

# ❌ WRONG - Unclear names
def test1():
    pass

def test_calc():
    pass

def test_error():
    pass
```

---

## 6. Import Organization

### 📦 Import Order (Mandatory)

```python
# ✅ CORRECT - Organized import groups
"""Module docstring."""

# 1. Standard library imports (alphabetical)
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# 2. Third-party imports (alphabetical)
import click
import pandas as pd
import yaml
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local application imports (alphabetical)
from ..config import Configuration
from ..exceptions import MT5ConnectionError
from ..utils.logger import get_logger
from .account_manager import AccountManager
from .symbol_manager import SymbolManager

# ❌ WRONG - Mixed order, unclear groups
from .account_manager import AccountManager
import os
from pydantic import BaseModel
import asyncio
from ..config import Configuration
import click
```

### 🎯 Import Style

```python
# ✅ CORRECT - Explicit imports
from trading_bot.connectors import MT5Connector, AccountManager
from trading_bot.exceptions import MT5ConnectionError, MT5OrderError

# ✅ CORRECT - Type hints only imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from trading_bot.strategies import BaseStrategy

# ❌ WRONG - Wildcard imports
from trading_bot.connectors import *
from trading_bot.exceptions import *

# ❌ WRONG - Unnecessary aliasing
import pandas as pd2
from trading_bot.connectors import MT5Connector as Conn
```

---

## 7. Error Handling

### ⚠️ Exception Handling

```python
# ✅ CORRECT - Specific exceptions with context
from trading_bot.exceptions import MT5ConnectionError, MT5OrderError
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)

def connect_to_mt5(login: int, password: str) -> bool:
    """Connect to MT5 platform."""
    try:
        result = mt5.initialize()
        if not result:
            raise MT5ConnectionError("MT5 initialization failed")
        return True
        
    except MT5ConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error during MT5 connection: {e}")
        raise MT5ConnectionError(f"Failed to connect: {e}") from e

# ❌ WRONG - Bare except, no logging
def connect_to_mt5(login, password):
    try:
        result = mt5.initialize()
        return result
    except:
        return False
```

### 🛡️ Custom Exceptions

```python
# ✅ CORRECT - Informative custom exceptions
class MT5OrderError(Exception):
    """Exception for MT5 order-related errors."""
    
    def __init__(self, message: str, error_code: int = 0):
        self.message = message
        self.error_code = error_code
        super().__init__(f"{message} (Error code: {error_code})")

class MT5SymbolError(Exception):
    """Exception for MT5 symbol-related errors."""
    
    def __init__(self, symbol: str, message: str):
        self.symbol = symbol
        self.message = message
        super().__init__(f"Symbol '{symbol}': {message}")

# ❌ WRONG - Generic exceptions
class MT5Error(Exception):
    pass

class Error(Exception):
    pass
```

---

## 8. Configuration Management

### ⚙️ Configuration Structure

```python
# ✅ CORRECT - Pydantic models for configuration
from pydantic import BaseModel, Field, validator

class MT5Config(BaseModel):
    """MT5 configuration."""
    
    terminal_path: Optional[str] = None
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    connection_timeout: int = Field(default=30, ge=5, le=120)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    
    @validator("login")
    def validate_login(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Login must be positive")
        return v

# ❌ WRONG - Plain dict without validation
mt5_config = {
    "terminal_path": None,
    "login": None,
    "password": None,
    "timeout": 30,
}
```

### 🔐 Environment Variables

```python
# ✅ CORRECT - Secure environment variable handling
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///default.db")
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")

# Never log sensitive data
logger.info(f"Database type: {'PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite'}")

# ❌ WRONG - Hardcoded credentials
DATABASE_URL = "postgresql://user:password@localhost/db"
MT5_LOGIN = 12345
MT5_PASSWORD = "my_secret_password"
logger.info(f"Database URL: {DATABASE_URL}")
```

---

## 9. Logging Standards

### 📋 Logging Best Practices

```python
# ✅ CORRECT - Structured logging with context
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)

def execute_trade(symbol: str, volume: float, order_type: str) -> Dict:
    """Execute trade order."""
    logger.info(f"Executing trade: {order_type} {volume} {symbol}")
    
    try:
        result = send_order(symbol, volume, order_type)
        logger.info(
            f"Trade executed successfully - "
            f"Ticket: {result['ticket']}, "
            f"Price: {result['price']:.5f}"
        )
        return result
        
    except Exception as e:
        logger.error(
            f"Trade execution failed - "
            f"Symbol: {symbol}, "
            f"Volume: {volume}, "
            f"Error: {e}"
        )
        raise

# ❌ WRONG - Poor logging practices
def execute_trade(symbol, volume, order_type):
    print(f"Executing {order_type}")  # Don't use print()
    result = send_order(symbol, volume, order_type)
    logger.info("Success")  # Too vague
    return result
```

### 📊 Log Levels

```python
# ✅ CORRECT - Appropriate log levels
logger.debug("Detailed diagnostic information")
logger.info("Normal operational messages")
logger.warning("Warning messages for recoverable issues")
logger.error("Error messages for failures")
logger.critical("Critical failures requiring immediate attention")

# Examples:
logger.debug(f"Validating signal: {signal_data}")  # Detailed debug info
logger.info("MT5 connection established")  # Normal operation
logger.warning("Retry attempt 2/3 for MT5 connection")  # Recoverable
logger.error("Failed to execute order: Invalid volume")  # Error
logger.critical("Database connection lost - halting operations")  # Critical

# ❌ WRONG - Misused log levels
logger.info("Critical database error occurred")  # Should be critical
logger.error("Starting application")  # Should be info
logger.debug("Trade executed")  # Should be info
```

---

## 10. Examples

### 📖 Complete Module Example

```python
"""
Account Manager Module

Handles MetaTrader5 account operations including balance, equity,
and margin monitoring.

This module provides a high-level interface for account management,
abstracting the MT5 API complexity.
"""

from typing import Dict, Any
from trading_bot.exceptions import MT5ConnectionError
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class AccountManager:
    """
    MT5 Account Manager.
    
    Provides account information, balance monitoring, and margin tracking.
    
    Attributes:
        connector: MT5Connector instance for platform communication
        
    Example:
        >>> connector = MT5Connector()
        >>> manager = AccountManager(connector)
        >>> balance = manager.get_balance()
        >>> print(f"Balance: ${balance:,.2f}")
    """
    
    def __init__(self, mt5_connector) -> None:
        """
        Initialize Account Manager.
        
        Args:
            mt5_connector: MT5Connector instance
            
        Raises:
            ImportError: If MetaTrader5 package not available
        """
        self.connector = mt5_connector
        logger.info("Account Manager initialized")
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get complete account information.
        
        Returns:
            Dictionary with account details including:
                - login: Account number
                - balance: Current balance
                - equity: Current equity
                - margin: Used margin
                - free_margin: Available margin
                
        Raises:
            MT5ConnectionError: If not connected to MT5
            
        Example:
            >>> info = manager.get_account_info()
            >>> print(f"Balance: ${info['balance']:,.2f}")
        """
        if not self.connector.is_connected():
            logger.error("Attempted to get account info without MT5 connection")
            raise MT5ConnectionError("MT5 not connected")
        
        try:
            account_info = mt5.account_info()
            
            if account_info is None:
                error_code, error_msg = mt5.last_error()
                logger.error(
                    f"Failed to get account info - "
                    f"Code: {error_code}, Message: {error_msg}"
                )
                raise MT5ConnectionError(
                    f"Failed to get account info: {error_msg} (code: {error_code})"
                )
            
            logger.debug(f"Retrieved account info for login: {account_info.login}")
            return account_info._asdict()
            
        except MT5ConnectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e}")
            raise MT5ConnectionError(f"Failed to retrieve account info: {e}")
    
    def get_balance(self) -> float:
        """
        Get current account balance.
        
        Returns:
            Account balance in account currency
            
        Example:
            >>> balance = manager.get_balance()
            >>> print(f"${balance:,.2f}")
        """
        account_info = self.get_account_info()
        balance = account_info.get("balance", 0.0)
        logger.debug(f"Current balance: ${balance:,.2f}")
        return balance
    
    def __repr__(self) -> str:
        """String representation of AccountManager."""
        return f"AccountManager(connected={self.connector.is_connected()})"
```

### 🧪 Complete Test Example

```python
"""
Unit tests for Account Manager.

Tests cover account information retrieval, error handling,
and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from trading_bot.connectors import AccountManager
from trading_bot.exceptions import MT5ConnectionError


class TestAccountManager:
    """Test AccountManager class."""
    
    @pytest.fixture
    def mock_connector(self):
        """Create mock MT5 connector."""
        connector = Mock()
        connector.is_connected.return_value = True
        return connector
    
    @pytest.fixture
    def account_manager(self, mock_connector):
        """Create AccountManager instance with mock connector."""
        return AccountManager(mock_connector)
    
    def test_initialization(self, mock_connector):
        """Test AccountManager initialization."""
        # Act
        manager = AccountManager(mock_connector)
        
        # Assert
        assert manager.connector == mock_connector
    
    def test_get_account_info_success(self, account_manager):
        """Test successful account info retrieval."""
        # Arrange
        mock_account = MagicMock()
        mock_account.login = 12345
        mock_account.balance = 10000.0
        mock_account._asdict.return_value = {
            "login": 12345,
            "balance": 10000.0,
        }
        
        with patch("mt5.account_info", return_value=mock_account):
            # Act
            result = account_manager.get_account_info()
            
            # Assert
            assert result["login"] == 12345
            assert result["balance"] == 10000.0
    
    def test_get_account_info_not_connected(self, account_manager):
        """Test account info retrieval when not connected."""
        # Arrange
        account_manager.connector.is_connected.return_value = False
        
        # Act & Assert
        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            account_manager.get_account_info()
    
    def test_get_balance(self, account_manager):
        """Test balance retrieval."""
        # Arrange
        account_manager.get_account_info = Mock(
            return_value={"balance": 5000.0}
        )
        
        # Act
        balance = account_manager.get_balance()
        
        # Assert
        assert balance == 5000.0
    
    @pytest.mark.parametrize(
        "balance,expected",
        [
            (0.0, 0.0),
            (1000.0, 1000.0),
            (9999.99, 9999.99),
        ]
    )
    def test_get_balance_various_amounts(
        self,
        account_manager,
        balance,
        expected
    ):
        """Test balance retrieval with various amounts."""
        # Arrange
        account_manager.get_account_info = Mock(
            return_value={"balance": balance}
        )
        
        # Act
        result = account_manager.get_balance()
        
        # Assert
        assert result == expected
```

---

## ✅ Checklist Before Commit

- [ ] Code formatted with Black (`uv run black src/ tests/`)
- [ ] Linting passes (`uv run ruff check src/ tests/`)
- [ ] Type checking passes (`uv run mypy src/trading_bot/`)
- [ ] All tests pass (`uv run pytest tests/`)
- [ ] Test coverage ≥ 85% for new code
- [ ] Docstrings added for all public functions/classes
- [ ] Type hints added for all function parameters
- [ ] No hardcoded credentials or sensitive data
- [ ] Logging uses appropriate levels
- [ ] Error handling is specific and informative
- [ ] Configuration uses environment variables
- [ ] Imports are organized correctly
- [ ] File and class names follow conventions
- [ ] No print() statements (use logger)
- [ ] Documentation updated if needed

---

## 🚫 Common Anti-Patterns to Avoid

### ❌ Bad Practices

```python
# DON'T: Use print() for output
print("Processing order...")
print(f"Error: {error}")

# DON'T: Bare except clauses
try:
    risky_operation()
except:
    pass

# DON'T: Hardcoded values
max_positions = 5
risk_percent = 0.01
api_key = "abc123"

# DON'T: Unclear variable names
x = calc(a, b)
tmp = get_data()
d = {"k": "v"}

# DON'T: Missing type hints
def process(data):
    return data * 2

# DON'T: No docstrings
class Strategy:
    def run(self):
        pass

# DON'T: Wildcard imports
from module import *

# DON'T: Long functions (>50 lines)
def do_everything():
    # 200 lines of code...
    pass
```

### ✅ Good Practices

```python
# DO: Use logger
logger.info("Processing order...")
logger.error(f"Error: {error}")

# DO: Specific exception handling
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise

# DO: Configuration-driven values
max_positions = config.trading.max_positions
risk_percent = config.trading.risk_per_trade
api_key = os.getenv("API_KEY")

# DO: Descriptive variable names
position_size = calculate_size(account_balance, risk_amount)
market_data = fetch_ohlcv_data()
account_info = {"login": 12345, "balance": 10000.0}

# DO: Complete type hints
def process(data: List[float]) -> List[float]:
    return [x * 2 for x in data]

# DO: Comprehensive docstrings
class Strategy:
    """Base strategy for trading."""
    
    def run(self) -> Dict[str, Any]:
        """Execute strategy logic."""
        pass

# DO: Explicit imports
from module import SpecificClass, specific_function

# DO: Small, focused functions
def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol."""
    return symbol in VALID_SYMBOLS
```

---

## 📚 Additional Resources

- **Black Formatter**: https://black.readthedocs.io/
- **Ruff Linter**: https://docs.astral.sh/ruff/
- **MyPy**: https://mypy.readthedocs.io/
- **Pytest**: https://docs.pytest.org/
- **Pydantic**: https://docs.pydantic.dev/
- **PEP 8**: https://pep8.org/
- **Google Python Style Guide**: https://google.github.io/styleguide/pyguide.html

---

**Version History**:
- v1.0.0 (2025-11-29): Initial release

