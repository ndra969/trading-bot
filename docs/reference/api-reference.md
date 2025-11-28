# 📚 API Reference Documentation

## Overview

Dokumentasi lengkap untuk semua API, class, dan method yang tersedia dalam trading bot system. Dokumentasi ini mencakup core components, configuration options, dan usage examples.

## Core Components

### TradingBotV2

Main orchestrator class yang mengatur seluruh sistem trading.

```python
class TradingBotV2:
    """
    Main trading bot orchestrator dengan 1-minute loop architecture.
    
    Attributes:
        config (dict): Configuration dictionary
        is_running (bool): Bot running status
        strategy_engine (StrategyEngine): Strategy management
        position_manager (PositionManager): Position management
        risk_manager (RiskManager): Risk management
        mt5_connector (MT5Connector): MetaTrader5 interface
    """
    
    def __init__(self, config: dict):
        """
        Initialize trading bot dengan configuration.
        
        Args:
            config (dict): Configuration dictionary dari environment variables
            
        Raises:
            ConfigurationError: Jika configuration tidak valid
            MT5ConnectionError: Jika tidak bisa connect ke MT5
        """
    
    async def start(self) -> bool:
        """
        Start trading bot dan initialize semua components.
        
        Returns:
            bool: True jika berhasil start, False jika gagal
            
        Raises:
            SystemError: Jika critical component gagal initialize
        """
    
    async def shutdown(self) -> None:
        """
        Graceful shutdown dengan cleanup semua resources.
        
        Performs:
            - Stop trading loop
            - Close database connections
            - Save state data
            - Send shutdown notifications
        """
    
    async def trading_loop(self) -> None:
        """
        Main 1-minute trading loop execution.
        
        Loop Process:
            1. Update market data
            2. Analyze positions
            3. Generate signals
            4. Execute trades
            5. Update risk metrics
            6. Log performance data
        """
```

### StrategyEngine

Strategy management dan signal generation system.

```python
class StrategyEngine:
    """
    Strategy coordination dan signal generation engine.
    
    Manages multiple trading strategies dan coordinates signal generation
    dengan market structure analysis dan entry validation.
    """
    
    def __init__(self, config: dict, mt5_connector: MT5Connector):
        """
        Initialize strategy engine.
        
        Args:
            config (dict): Strategy configuration
            mt5_connector (MT5Connector): MT5 connection interface
        """
    
    async def generate_signals(self) -> List[TradingSignal]:
        """
        Generate trading signals dari active strategies.
        
        Returns:
            List[TradingSignal]: List of validated trading signals
            
        Process:
            1. Analyze market structure
            2. Run strategy analysis
            3. Validate entry conditions
            4. Score and rank signals
            5. Apply risk filters
        """
    
    async def analyze_market_structure(self, symbol: str, timeframe: str) -> StructureAnalysis:
        """
        Analyze market structure untuk symbol dan timeframe.
        
        Args:
            symbol (str): Trading symbol (e.g., 'EURUSD')
            timeframe (str): Analysis timeframe (e.g., 'H1')
            
        Returns:
            StructureAnalysis: Structure analysis results
            
        Analysis Includes:
            - Break of Structure (BOS) detection
            - Change of Character (CHoCH) identification
            - Order block detection
            - Fair Value Gap analysis
            - Liquidity pool identification
        """
```

### PositionManager

Comprehensive position management dengan asset-specific logic.

```python
class PositionManager:
    """
    Central position management dengan asset-aware logic.
    
    Handles breakeven, trailing stops, partial closes, dan emergency procedures
    dengan different parameters untuk different asset classes.
    """
    
    def __init__(self, config: dict, mt5_connector: MT5Connector):
        """
        Initialize position manager.
        
        Args:
            config (dict): Position management configuration
            mt5_connector (MT5Connector): MT5 connection interface
        """
    
    async def manage_positions(self) -> PositionManagementResult:
        """
        Manage semua active positions.
        
        Returns:
            PositionManagementResult: Management operation results
            
        Management Tasks:
            - Update position data
            - Check breakeven conditions
            - Update trailing stops
            - Execute partial closes
            - Monitor emergency conditions
        """
    
    async def update_position_breakeven(self, position: Position) -> bool:
        """
        Update position breakeven berdasarkan asset-specific parameters.
        
        Args:
            position (Position): Position object to update
            
        Returns:
            bool: True jika breakeven updated, False jika tidak
            
        Asset-Specific Logic:
            - Forex Major: 15 pips trigger, 0.5 pips buffer
            - Forex JPY: 18 pips trigger, 0.8 pips buffer
            - Commodities: 150 pips trigger, 5 pips buffer
            - Crypto: 300 pips trigger, 20 pips buffer
        """
    
    async def update_trailing_stop(self, position: Position) -> bool:
        """
        Update trailing stop dengan dynamic distance calculation.
        
        Args:
            position (Position): Position to update trailing stop
            
        Returns:
            bool: True jika trailing stop updated
            
        Trailing Logic:
            - Start distance dari SL (asset-specific)
            - Dynamic distance adjustment
            - Acceleration factor untuk strong trends
            - Minimum distance maintenance
        """
```

### RiskManager

Advanced risk management dengan correlation analysis.

```python
class RiskManager:
    """
    Advanced risk management system dengan multi-layer protection.
    
    Implements position-level, portfolio-level, dan account-level risk controls
    dengan real-time correlation analysis dan drawdown protection.
    """
    
    def __init__(self, config: dict, mt5_connector: MT5Connector):
        """
        Initialize risk manager.
        
        Args:
            config (dict): Risk management configuration
            mt5_connector (MT5Connector): MT5 connection interface
        """
    
    async def validate_trade(self, signal: TradingSignal) -> RiskValidationResult:
        """
        Comprehensive trade validation sebelum execution.
        
        Args:
            signal (TradingSignal): Trading signal to validate
            
        Returns:
            RiskValidationResult: Validation result dengan details
            
        Validation Checks:
            - Position size limits
            - Correlation exposure limits
            - Total risk exposure
            - Asset-specific limits
            - Drawdown protection status
            - Market hours validation
        """
    
    async def calculate_position_size(self, signal: TradingSignal) -> float:
        """
        Calculate optimal position size berdasarkan risk parameters.
        
        Args:
            signal (TradingSignal): Signal dengan SL dan entry price
            
        Returns:
            float: Calculated position size in lots
            
        Calculation Factors:
            - Risk per trade percentage
            - Account balance
            - SL distance
            - Volatility adjustment (ATR-based)
            - Correlation adjustment
        """
    
    async def update_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Update real-time correlation matrix untuk all trading pairs.
        
        Returns:
            Dict[str, Dict[str, float]]: Correlation matrix
            
        Features:
            - 30-day rolling correlation
            - Hourly updates
            - Correlation threshold monitoring
            - Historical trend analysis
        """
```

## Market Structure Analysis

### StructureAnalyzer

Market structure detection dan analysis engine.

```python
class StructureAnalyzer:
    """
    Comprehensive market structure analysis dengan institutional concepts.
    
    Detects Break of Structure (BOS), Change of Character (CHoCH),
    Order Blocks, Fair Value Gaps, dan Liquidity Pools.
    """
    
    async def detect_bos(self, symbol: str, timeframe: str, lookback: int = 50) -> List[BOSEvent]:
        """
        Detect Break of Structure events.
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Analysis timeframe
            lookback (int): Candles to analyze
            
        Returns:
            List[BOSEvent]: Detected BOS events
            
        Detection Criteria:
            - Swing high/low identification
            - Structure break confirmation
            - Volume validation
            - Multi-timeframe alignment
        """
    
    async def detect_order_blocks(self, symbol: str, bos_events: List[BOSEvent]) -> List[OrderBlock]:
        """
        Identify order blocks berdasarkan BOS events.
        
        Args:
            symbol (str): Trading symbol
            bos_events (List[BOSEvent]): Recent BOS events
            
        Returns:
            List[OrderBlock]: Identified order blocks
            
        Identification Process:
            - Find last opposite candle before BOS
            - Validate volume during formation
            - Calculate strength score
            - Determine validity period
        """
    
    async def detect_fair_value_gaps(self, symbol: str, timeframe: str) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps (price imbalances).
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Analysis timeframe
            
        Returns:
            List[FairValueGap]: Detected FVGs
            
        Detection Logic:
            - Three-candle gap pattern
            - Minimum gap size validation
            - Fill probability calculation
            - Gap tracking dan statistics
        """
```

### EnhancedZoneAnalyzer

Advanced supply/demand zone detection dan scoring.

```python
class EnhancedZoneAnalyzer:
    """
    Enhanced zone detection dengan advanced scoring algorithm.
    
    Identifies high-quality supply dan demand zones dengan
    comprehensive quality assessment dan historical validation.
    """
    
    def detect_zones(self, data: pd.DataFrame, lookback: int = 300) -> List[Zone]:
        """
        Detect supply dan demand zones dengan quality scoring.
        
        Args:
            data (pd.DataFrame): OHLCV market data
            lookback (int): Historical data points to analyze
            
        Returns:
            List[Zone]: Detected zones dengan quality scores
            
        Detection Process:
            1. Identify potential rejection areas
            2. Analyze volume confirmation
            3. Calculate zone strength
            4. Validate historical performance
            5. Apply quality filters
        """
    
    def calculate_zone_score(self, zone: Zone, current_price: float) -> float:
        """
        Calculate comprehensive zone quality score.
        
        Args:
            zone (Zone): Zone object to score
            current_price (float): Current market price
            
        Returns:
            float: Zone score (0-100)
            
        Scoring Factors:
            - Zone strength (40%)
            - Freshness bonus (20%)
            - Historical performance (15%)
            - Volume confirmation (25%)
        """
```

## Database Operations

### SQLiteManager

Optimized SQLite database operations untuk analytics.

```python
class SQLiteManager:
    """
    High-performance SQLite database manager dengan connection pooling.
    
    Handles trade data, market structure events, performance metrics,
    dan analytics data dengan optimized queries dan backup procedures.
    """
    
    def __init__(self, db_path: str = "data/trading_bot.db"):
        """
        Initialize SQLite manager dengan connection pool.
        
        Args:
            db_path (str): Path to SQLite database file
        """
    
    async def insert_trade(self, trade_data: Dict) -> bool:
        """
        Insert trade record ke database.
        
        Args:
            trade_data (Dict): Trade information
            
        Returns:
            bool: True jika berhasil insert
            
        Trade Data Fields:
            - ticket: Trade ticket number
            - symbol: Trading symbol
            - trade_type: BUY/SELL
            - volume: Position size
            - open_price: Entry price
            - sl: Stop loss price
            - tp: Take profit price
            - strategy: Strategy name
            - confidence_score: Signal confidence
        """
    
    async def get_performance_metrics(self, period_days: int = 30) -> Dict:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            period_days (int): Analysis period in days
            
        Returns:
            Dict: Performance metrics
            
        Metrics Included:
            - Total trades
            - Win rate
            - Profit factor
            - Average RR ratio
            - Maximum drawdown
            - Sharpe ratio
            - Strategy breakdown
        """
    
    async def backup_database(self, backup_path: str) -> bool:
        """
        Create compressed database backup.
        
        Args:
            backup_path (str): Backup file path
            
        Returns:
            bool: True jika backup berhasil
            
        Backup Features:
            - Integrity verification
            - Compression
            - Incremental backups
            - Automatic cleanup
        """
```

## Configuration System

### ConfigurationManager

Hierarchical configuration management system.

```python
class ConfigurationManager:
    """
    Hierarchical configuration management dengan validation.
    
    Manages environment variables, JSON files, database settings,
    dan default values dengan priority-based resolution.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.
        
        Args:
            config_dir (str): Configuration directory path
        """
    
    def get_asset_parameters(self, symbol: str) -> Dict:
        """
        Get asset-specific parameters untuk symbol.
        
        Args:
            symbol (str): Trading symbol
            
        Returns:
            Dict: Asset-specific parameters
            
        Parameter Categories:
            - Breakeven settings
            - Trailing stop settings
            - Partial close levels
            - Risk parameters
            - Spread limits
        """
    
    def validate_configuration(self, config: Dict) -> ValidationResult:
        """
        Comprehensive configuration validation.
        
        Args:
            config (Dict): Configuration to validate
            
        Returns:
            ValidationResult: Validation result dengan error details
            
        Validation Checks:
            - Required fields presence
            - Data type validation
            - Range validation
            - Dependency validation
            - Security validation
        """
```

## Notification System

### NotificationManager

Multi-channel notification system.

```python
class NotificationManager:
    """
    Multi-channel notification system dengan throttling.
    
    Supports Telegram, Discord, Email notifications dengan
    intelligent throttling dan priority-based delivery.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize notification manager.
        
        Args:
            config (Dict): Notification configuration
        """
    
    async def send_trade_notification(self, trade_data: Dict) -> bool:
        """
        Send trade execution notification.
        
        Args:
            trade_data (Dict): Trade information
            
        Returns:
            bool: True jika notification berhasil sent
            
        Notification Content:
            - Trade details (symbol, type, size)
            - Entry price dan SL/TP
            - Strategy dan confidence
            - Account impact
        """
    
    async def send_risk_alert(self, alert_data: Dict) -> bool:
        """
        Send risk management alert.
        
        Args:
            alert_data (Dict): Risk alert information
            
        Returns:
            bool: True jika alert berhasil sent
            
        Alert Types:
            - High correlation exposure
            - Drawdown warnings
            - Position limit breaches
            - Emergency conditions
        """
```

## Data Models

### TradingSignal

Trading signal data structure.

```python
@dataclass
class TradingSignal:
    """
    Trading signal dengan comprehensive metadata.
    
    Contains all information needed untuk trade execution
    dan performance tracking.
    """
    
    symbol: str                    # Trading symbol
    direction: str                 # 'buy' or 'sell'
    entry_price: float            # Recommended entry price
    stop_loss: float              # Stop loss price
    take_profit: float            # Take profit price
    confidence_score: float       # Signal confidence (0-100)
    strategy: str                 # Strategy name
    zone: Optional[Zone]          # Associated zone
    structure_context: Dict       # Market structure context
    risk_reward_ratio: float      # Expected RR ratio
    timestamp: datetime           # Signal generation time
    
    def validate(self) -> bool:
        """Validate signal data integrity."""
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary format."""
```

### Position

Position data dengan state management.

```python
@dataclass
class Position:
    """
    Position object dengan comprehensive state tracking.
    
    Tracks position lifecycle dari opening hingga closing
    dengan detailed state management.
    """
    
    ticket: int                   # MT5 ticket number
    symbol: str                   # Trading symbol
    position_type: str            # 'buy' or 'sell'
    volume: float                 # Position size
    open_price: float            # Entry price
    current_price: float         # Current market price
    stop_loss: float             # Current SL
    take_profit: float           # Current TP
    profit: float                # Current profit/loss
    state: PositionState         # Position state
    breakeven_set: bool          # Breakeven status
    partial_closes: List[bool]   # Partial close status
    trailing_active: bool        # Trailing stop status
    open_time: datetime          # Position open time
    
    def calculate_profit_pips(self) -> float:
        """Calculate profit in pips."""
    
    def get_asset_class(self) -> str:
        """Determine asset class dari symbol."""
```

## Utility Functions

### Common Utilities

Frequently used utility functions.

```python
def calculate_pip_value(symbol: str, price: float) -> float:
    """
    Calculate pip value untuk symbol.
    
    Args:
        symbol (str): Trading symbol
        price (float): Current price
        
    Returns:
        float: Pip value
    """

def get_asset_class(symbol: str) -> str:
    """
    Determine asset class dari symbol.
    
    Args:
        symbol (str): Trading symbol
        
    Returns:
        str: Asset class ('forex_major', 'forex_jpy', 'commodity', 'crypto')
    """

def validate_trading_hours(symbol: str, timestamp: datetime) -> bool:
    """
    Validate if trading is allowed untuk symbol at timestamp.
    
    Args:
        symbol (str): Trading symbol
        timestamp (datetime): Time to validate
        
    Returns:
        bool: True jika trading allowed
    """

def calculate_correlation(prices1: List[float], prices2: List[float]) -> float:
    """
    Calculate correlation coefficient antara two price series.
    
    Args:
        prices1 (List[float]): First price series
        prices2 (List[float]): Second price series
        
    Returns:
        float: Correlation coefficient (-1 to 1)
    """
```

## Error Handling

### Exception Classes

Custom exception hierarchy untuk error handling.

```python
class TradingBotException(Exception):
    """Base exception untuk trading bot."""
    pass

class ConfigurationError(TradingBotException):
    """Configuration-related errors."""
    pass

class MT5ConnectionError(TradingBotException):
    """MetaTrader5 connection errors."""
    pass

class RiskValidationError(TradingBotException):
    """Risk management validation errors."""
    pass

class DatabaseError(TradingBotException):
    """Database operation errors."""
    pass

class StrategyError(TradingBotException):
    """Strategy execution errors."""
    pass
```

## Configuration Reference

### Environment Variables

Complete list of configuration options.

```bash
# Core Trading Configuration
BROKER_NAME=string                    # Broker name
BROKER_TYPE=string                   # Broker type identifier
TRADING_SYMBOLS=string               # Comma-separated symbol list
MAX_CONCURRENT_POSITIONS=int         # Maximum open positions
RISK_PER_TRADE=float                # Risk percentage per trade

# Position Management
BREAKEVEN_ENABLED=bool              # Enable breakeven system
TRAILING_ENABLED=bool               # Enable trailing stops
PARTIAL_CLOSE_ENABLED=bool          # Enable partial closes

# Risk Management
MAX_DRAWDOWN_PERCENT=float          # Maximum account drawdown
CORRELATION_THRESHOLD=float         # Maximum correlation exposure
EMERGENCY_PROTOCOLS_ENABLED=bool    # Enable emergency procedures

# Strategy Configuration
STRATEGY_SUPPLY_DEMAND_ENABLED=bool # Enable supply/demand strategy
STRATEGY_BREAKOUT_RETEST_ENABLED=bool # Enable breakout strategy
MIN_ENTRY_SCORE=float               # Minimum entry score threshold

# Multi-Timeframe Analysis
MULTI_TIMEFRAME_ENABLED=bool        # Enable multi-timeframe analysis
PRIMARY_TIMEFRAME=string            # Main analysis timeframe (default: H1)
SECONDARY_TIMEFRAME=string          # Trend confirmation timeframe (default: H4)
TERTIARY_TIMEFRAME=string           # Major trend direction (default: D1)
ANALYSIS_TIMEFRAMES=string          # Structure detection timeframes (default: M15,H1,H4)

# Timeframe Weights for Trend Analysis
D1_TREND_WEIGHT=int                 # Daily trend weight (default: 3)
H4_TREND_WEIGHT=int                 # 4-hour trend weight (default: 2)
H1_TREND_WEIGHT=int                 # 1-hour trend weight (default: 1)
MIN_TREND_STRENGTH=int              # Minimum combined trend score (default: 4)
TREND_ALIGNMENT_WEIGHT=float        # Overall trend influence (default: 0.45)

# Database Configuration
CSV_LOGGING_ENABLED=bool            # Enable CSV logging
DATABASE_BACKUP_ENABLED=bool        # Enable database backups

# Notification Configuration
TELEGRAM_ENABLED=bool               # Enable Telegram notifications
TELEGRAM_TOKEN=string               # Telegram bot token
TELEGRAM_CHAT_ID=string            # Telegram chat ID

# Logging Configuration
LOG_LEVEL=string                    # Logging level (DEBUG, INFO, WARN, ERROR)
LOG_TO_FILE=bool                   # Enable file logging
LOG_TO_CONSOLE=bool                # Enable console logging
```

## Usage Examples

### Basic Bot Setup

```python
import asyncio
from src.trading_bot import TradingBotV2
from dotenv import load_dotenv
import os

# Load configuration
load_dotenv()
config = dict(os.environ)

# Initialize bot
bot = TradingBotV2(config)

# Start bot
async def main():
    await bot.start()
    
    # Bot will run until shutdown
    while bot.is_running:
        await asyncio.sleep(60)

# Run bot
asyncio.run(main())
```

### Custom Strategy Implementation

```python
from src.strategies.base_strategy import BaseStrategy
from src.models.trading_signal import TradingSignal

class CustomStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.name = "custom_strategy"
    
    async def analyze(self, symbol: str, data: pd.DataFrame) -> Optional[TradingSignal]:
        # Custom analysis logic
        if self.detect_entry_condition(data):
            signal = TradingSignal(
                symbol=symbol,
                direction='buy',
                entry_price=data['close'].iloc[-1],
                stop_loss=self.calculate_sl(data),
                take_profit=self.calculate_tp(data),
                confidence_score=self.calculate_confidence(data),
                strategy=self.name
            )
            return signal
        return None
```

### Database Query Examples

```python
from src.database.sqlite_manager import SQLiteManager

# Initialize database manager
db = SQLiteManager()

# Get recent trades
recent_trades = await db.execute_query("""
    SELECT * FROM trades 
    WHERE open_time >= datetime('now', '-7 days')
    ORDER BY open_time DESC
""")

# Calculate strategy performance
strategy_performance = await db.execute_query("""
    SELECT 
        strategy,
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
        AVG(profit) as avg_profit,
        SUM(profit) as total_profit
    FROM trades 
    WHERE close_time IS NOT NULL
    GROUP BY strategy
""")
```

This comprehensive API reference provides detailed information about all available classes, methods, and configuration options in the trading bot system.