# Trading Type Architecture Design

## 🎯 Overview

This document describes the architecture for supporting multiple trading types (Intraday/Day Trading, Swing Trading, and Scalping) with clean separation of concerns and easy switching between modes.

## 🏗️ Core Principle

**"One Bot, Multiple Personalities"**

The trading bot should support different trading types through:
1. **Configuration-driven behavior** - No code changes to switch modes
2. **Type-specific strategy components** - Each type has its own technical setup
3. **Shared foundation** - Common S&D zone detection, risk management core
4. **Isolated execution loops** - Different trading loops for different time horizons

---

## 📐 Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING BOT MAIN                         │
│                  (Orchestrator/Router)                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Routes to appropriate executor based on config
                  │
      ┌───────────┴───────────┬─────────────────┬──────────────┐
      │                       │                 │              │
      ▼                       ▼                 ▼              ▼
┌─────────────┐      ┌─────────────┐   ┌─────────────┐  ┌──────────┐
│  INTRADAY   │      │    SWING    │   │  SCALPING   │  │  FUTURE  │
│  EXECUTOR   │      │  EXECUTOR   │   │  EXECUTOR   │  │  MODES   │
│  (ACTIVE)   │      │ (SKELETON)  │   │ (SKELETON)  │  │  (TODO)  │
└─────────────┘      └─────────────┘   └─────────────┘  └──────────┘
      │                       │                 │
      │                       │                 │
      └───────────────────────┴─────────────────┴──────────────┐
                                                                │
                                                                ▼
                              ┌─────────────────────────────────────┐
                              │      SHARED FOUNDATION LAYER        │
                              │                                     │
                              │  - Supply & Demand Zone Detection   │
                              │  - Position Manager                 │
                              │  - Risk Calculator                  │
                              │  - Pip Calculator                   │
                              │  - Symbol Mapper                    │
                              │  - Database Manager                 │
                              └─────────────────────────────────────┘
```

---

## 🔧 Component Design

### 1. **Trading Type Executor (Base Class)**

Abstract base class that defines the contract for all trading type executors.

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

class TradingTypeExecutor(ABC):
    """
    Base class for all trading type executors.
    
    Each trading type (Intraday, Swing, Scalping) extends this class
    and implements its own execution logic, timeframes, and parameters.
    """
    
    def __init__(self, config: Dict, foundation_engine, position_manager):
        self.config = config
        self.foundation_engine = foundation_engine
        self.position_manager = position_manager
        self.trading_type = self._get_trading_type()
        
    @abstractmethod
    def _get_trading_type(self) -> str:
        """Return the trading type name (e.g., 'day_trading', 'swing_trading')."""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Initialize type-specific components (indicators, analyzers, etc.)."""
        pass
    
    @abstractmethod
    async def execute_trading_loop(self, symbols: List[str]):
        """
        Main trading loop for this trading type.
        
        Different types have different loop behaviors:
        - Intraday: Scan every M30/H1, close all by end of day
        - Swing: Scan every H4/D1, hold for days
        - Scalping: Scan every M1/M5, rapid fire entries
        """
        pass
    
    @abstractmethod
    async def analyze_symbol(self, symbol: str, current_time: datetime) -> Optional[Dict]:
        """
        Analyze a symbol for trading opportunity.
        
        Returns signal dict if valid setup found, None otherwise.
        """
        pass
    
    @abstractmethod
    def get_timeframes(self) -> Dict[str, str]:
        """
        Return timeframes for this trading type.
        
        Returns dict with keys:
        - zone_timeframe: TF for S&D zone detection
        - entry_timeframe: TF for entry confirmation
        - trend_timeframe: TF for trend filter (if applicable)
        """
        pass
    
    @abstractmethod
    def get_technical_indicators(self) -> Dict[str, Dict]:
        """
        Return indicator configurations for this trading type.
        
        Example:
        {
            'ema': {'fast': 8, 'medium': 21, 'slow': 50},
            'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            'ma': {'trend_period': 200}
        }
        """
        pass
    
    @abstractmethod
    def validate_entry_conditions(self, signal: Dict, market_data: pd.DataFrame) -> bool:
        """
        Type-specific entry validation.
        
        Different types have different entry rules:
        - Intraday: H1 trend alignment, M30 confirmation
        - Swing: D1 structure, H4 entry
        - Scalping: M15 momentum, M5 trigger
        """
        pass
    
    async def should_close_all_positions(self, current_time: datetime) -> bool:
        """
        Check if all positions should be closed (e.g., end of day for intraday).
        
        Default: No auto-close. Override in subclasses as needed.
        """
        return False
    
    def get_risk_parameters(self) -> Dict:
        """Get risk management parameters for this trading type."""
        type_config = self.config.get('trading_types', {}).get(self.trading_type, {})
        return {
            'risk_per_trade': type_config.get('risk_per_trade', 0.01),
            'max_positions': type_config.get('max_positions', 5),
            'confluence_threshold': type_config.get('confluence_threshold', 40.0),
            'max_loss_per_day': type_config.get('max_loss_per_day', 0.02),
            'stop_loss_pips': type_config.get('stop_loss_pips', {}),
            'take_profit_pips': type_config.get('take_profit_pips', {})
        }
```

---

### 2. **Intraday (Day Trading) Executor**

Implements the current mature strategy with H1 zones and M30 entries.

```python
class IntradayExecutor(TradingTypeExecutor):
    """
    Intraday/Day Trading Executor.
    
    Strategy:
    - Zone Detection: H1 (hourly supply/demand zones)
    - Entry Confirmation: M30 (30-minute price action)
    - Trend Filter: H1 EMA 50/20 for commodities (Sniper Gate)
    - Position Duration: Intraday only (close all before market close)
    - Risk: 1% per trade
    - SL/TP: Forex 15/30 pips, Gold 50/100 pips
    
    Technical Setup:
    - EMA: 20, 50, 200
    - RSI: 14 period
    - Breakeven: 0.7R trigger (Sniper)
    - Trailing: Activate at 30 pips
    """
    
    def _get_trading_type(self) -> str:
        return "day_trading"
    
    async def initialize(self):
        """Initialize intraday-specific components."""
        # Load intraday-specific analyzers
        self.h1_trend_analyzer = H1TrendAnalyzer(self.config)
        self.m30_price_action = PriceActionAnalyzer(self.config, timeframe='M30')
        
        # Cache zones on H1
        self.zone_cache = {}
        self.zone_cache_duration_minutes = 60  # Refresh H1 zones every hour
        
    async def execute_trading_loop(self, symbols: List[str]):
        """
        Intraday trading loop.
        
        Loop behavior:
        1. Scan every M30 candle close
        2. Check H1 zones (cache for 1 hour)
        3. Look for M30 entry confirmation
        4. Apply H1 trend filter (Sniper Gate) for commodities
        5. Close all positions before end of trading day
        """
        while True:
            current_time = datetime.now(timezone.utc)
            
            # Check if we should close all positions (end of day)
            if await self.should_close_all_positions(current_time):
                await self.position_manager.close_all_positions("End of trading day")
                logger.info("Closed all positions for end of day (Intraday mode)")
            
            # Scan each symbol
            for symbol in symbols:
                signal = await self.analyze_symbol(symbol, current_time)
                if signal:
                    await self.position_manager.open_position(signal)
            
            # Wait for next M30 candle
            await self._wait_for_next_candle('M30')
    
    async def analyze_symbol(self, symbol: str, current_time: datetime) -> Optional[Dict]:
        """
        Analyze symbol for intraday setup.
        
        Steps:
        1. Get/refresh H1 zones
        2. Get current M30 price data
        3. Check if price at zone
        4. Apply H1 trend filter (commodities only)
        5. Validate M30 price action
        6. Generate signal if all conditions met
        """
        # Step 1: Get H1 zones (with caching)
        zones = await self._get_or_refresh_zones(symbol, 'H1', current_time)
        if not zones:
            return None
        
        # Step 2: Get M30 data
        m30_data = await self.foundation_engine.get_market_data(symbol, 'M30', 200)
        current_price = float(m30_data.iloc[-1]['close'])
        
        # Step 3: Check if price at any zone
        active_zone = self._find_active_zone(current_price, zones)
        if not active_zone:
            return None
        
        # Step 4: Apply H1 trend filter (Sniper Gate for commodities)
        h1_trend_bias = await self._get_h1_trend_bias(symbol, current_time)
        
        # Step 5: Validate M30 price action + generate signal
        signal = await self.foundation_engine._create_signal_from_zone(
            symbol, active_zone, current_price, 'M30', m30_data,
            h1_trend_bias=h1_trend_bias
        )
        
        # Step 6: Final validation
        if signal and self.validate_entry_conditions(signal, m30_data):
            return signal
        
        return None
    
    def get_timeframes(self) -> Dict[str, str]:
        return {
            'zone_timeframe': 'H1',
            'entry_timeframe': 'M30',
            'trend_timeframe': 'H1'  # For trend filter
        }
    
    def get_technical_indicators(self) -> Dict[str, Dict]:
        return {
            'ema': {'fast': 20, 'slow': 50, 'trend': 200},
            'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            'breakeven': {'trigger_r': 0.7, 'offset_pips': 2.0},
            'trailing': {'activation_pips': 30.0, 'limit_pips': 10.0}
        }
    
    def validate_entry_conditions(self, signal: Dict, market_data: pd.DataFrame) -> bool:
        """
        Intraday-specific entry validation.
        
        Rules:
        - Price must be at S&D zone
        - M30 price action confirmation required
        - H1 trend alignment (commodities only via Sniper Gate)
        - Confluence score >= 40%
        - Market hours validation
        """
        # Confluence threshold
        if signal.get('confluence_score', 0) < 40.0:
            return False
        
        # Market hours check (avoid low liquidity periods)
        if not self._is_active_trading_session(signal['symbol']):
            return False
        
        return True
    
    async def should_close_all_positions(self, current_time: datetime) -> bool:
        """
        Close all positions at end of trading day (intraday rule).
        
        Check if we're within 30 minutes of major market close.
        """
        # TODO: Implement market hours detection
        # For now, close positions at 23:30 UTC (before NY close)
        return current_time.hour == 23 and current_time.minute >= 30
    
    async def _get_h1_trend_bias(self, symbol: str, current_time: datetime) -> Optional[str]:
        """
        Get H1 trend bias using EMA 50/20 (Sniper Gate).
        
        Only applies to commodities (Gold, Silver, Oil, etc.)
        Returns: 'BULLISH', 'BEARISH', 'NEUTRAL', or None
        """
        asset_class = self.pip_calculator.symbol_mapper.get_asset_class(symbol)
        if asset_class != 'commodities':
            return None
        
        # Get H1 data
        h1_data = await self.foundation_engine.get_market_data(symbol, 'H1', 100)
        if len(h1_data) < 50:
            return None
        
        # Calculate EMAs
        ema_50 = h1_data['close'].ewm(span=50, adjust=False).mean()
        ema_20 = h1_data['close'].ewm(span=20, adjust=False).mean()
        
        current_price = float(h1_data.iloc[-1]['close'])
        ema_50_curr = ema_50.iloc[-1]
        ema_50_prev = ema_50.iloc[-2]
        ema_20_curr = ema_20.iloc[-1]
        
        # Trend determination logic
        slope_up = ema_50_curr > ema_50_prev
        slope_down = ema_50_curr < ema_50_prev
        
        is_bullish = (current_price > ema_50_curr and current_price > ema_20_curr and slope_up)
        is_bearish = (current_price < ema_50_curr and current_price < ema_20_curr and slope_down)
        
        if is_bullish:
            return 'BULLISH'
        elif is_bearish:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
```

---

### 3. **Swing Trading Executor (SKELETON)**

```python
class SwingExecutor(TradingTypeExecutor):
    """
    Swing Trading Executor (SKELETON - TODO IMPLEMENTATION).
    
    Strategy:
    - Zone Detection: H4 or D1 (daily supply/demand zones)
    - Entry Confirmation: H1 or H4 (4-hour price action)
    - Trend Filter: D1 EMA 50/100/200
    - Position Duration: Multi-day (1-7 days typical)
    - Risk: 2% per trade
    - SL/TP: Forex 50/100 pips, Gold 200/400 pips
    
    Technical Setup:
    - EMA: 50, 100, 200 (D1 timeframe)
    - RSI: 14 period (H4/D1)
    - Breakeven: 0.7R trigger (can be more aggressive)
    - Trailing: Activate at 100 pips, limit 50 pips
    - NO end-of-day position close
    
    TODO:
    - [ ] Implement D1 zone detection logic
    - [ ] Implement H4 entry confirmation
    - [ ] Add weekly structure analysis
    - [ ] Implement position hold logic (no daily close)
    - [ ] Add swing-specific risk management
    - [ ] Test with historical swing data
    """
    
    def _get_trading_type(self) -> str:
        return "swing_trading"
    
    async def initialize(self):
        """TODO: Initialize swing-specific components."""
        raise NotImplementedError("Swing trading executor not yet implemented")
    
    async def execute_trading_loop(self, symbols: List[str]):
        """
        TODO: Swing trading loop.
        
        Loop behavior:
        1. Scan every H4 or D1 candle close
        2. Check D1 zones (cache for 24 hours)
        3. Look for H4 entry confirmation
        4. Apply D1 trend filter
        5. NO auto-close (positions can run for days)
        6. Monitor for weekly structure breaks
        """
        raise NotImplementedError("Swing trading loop not yet implemented")
    
    async def analyze_symbol(self, symbol: str, current_time: datetime) -> Optional[Dict]:
        """TODO: Analyze symbol for swing setup."""
        raise NotImplementedError("Swing analysis not yet implemented")
    
    def get_timeframes(self) -> Dict[str, str]:
        return {
            'zone_timeframe': 'H4',  # or 'D1'
            'entry_timeframe': 'H1',  # or 'H4'
            'trend_timeframe': 'D1'
        }
    
    def get_technical_indicators(self) -> Dict[str, Dict]:
        return {
            'ema': {'fast': 50, 'medium': 100, 'slow': 200},
            'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
            'breakeven': {'trigger_r': 0.7, 'offset_pips': 5.0},
            'trailing': {'activation_pips': 100.0, 'limit_pips': 50.0}
        }
    
    def validate_entry_conditions(self, signal: Dict, market_data: pd.DataFrame) -> bool:
        """TODO: Swing-specific entry validation."""
        raise NotImplementedError("Swing validation not yet implemented")
    
    async def should_close_all_positions(self, current_time: datetime) -> bool:
        """Swing trading: NO auto-close at end of day."""
        return False
```

---

### 4. **Scalping Executor (SKELETON)**

```python
class ScalpingExecutor(TradingTypeExecutor):
    """
    Scalping Executor (SKELETON - TODO IMPLEMENTATION).
    
    Strategy:
    - Zone Detection: M15 (15-minute micro zones)
    - Entry Confirmation: M5 or M1 (1-5 minute triggers)
    - Trend Filter: M15 EMA 8/13 (fast momentum)
    - Position Duration: Ultra-short (minutes to hours, max 4 hours)
    - Risk: 0.2% per trade (many trades, small risk)
    - SL/TP: Forex 5/8 pips, Gold 20/30 pips
    
    Technical Setup:
    - EMA: 8, 13 (M15 for momentum)
    - RSI: 5-9 period (faster than day trading)
    - Breakeven: 0.3R trigger (very fast breakeven)
    - Trailing: Activate at 10 pips, limit 5 pips
    - Max position time: 4 hours (auto-close)
    
    TODO:
    - [ ] Implement M15 micro-zone detection
    - [ ] Implement M5/M1 rapid entry logic
    - [ ] Add tick-level spread monitoring
    - [ ] Implement fast EMA momentum filter
    - [ ] Add position time-based auto-close (4 hours max)
    - [ ] Optimize for low latency execution
    - [ ] Test with high-frequency data
    
    IMPORTANT:
    - Scalping requires different technical analysis (faster indicators)
    - Need to handle spread costs more carefully (tight SL = spread matters!)
    - Consider broker execution speed
    """
    
    def _get_trading_type(self) -> str:
        return "scalping"
    
    async def initialize(self):
        """TODO: Initialize scalping-specific components."""
        raise NotImplementedError("Scalping executor not yet implemented")
    
    async def execute_trading_loop(self, symbols: List[str]):
        """
        TODO: Scalping loop.
        
        Loop behavior:
        1. Scan every M5 or M1 candle close (high frequency!)
        2. Check M15 micro-zones (cache for 15 minutes)
        3. Look for M5/M1 momentum trigger
        4. Apply M15 EMA 8/13 fast trend filter
        5. Auto-close positions after 4 hours max
        6. Monitor spread costs aggressively
        """
        raise NotImplementedError("Scalping loop not yet implemented")
    
    async def analyze_symbol(self, symbol: str, current_time: datetime) -> Optional[Dict]:
        """TODO: Analyze symbol for scalping setup."""
        raise NotImplementedError("Scalping analysis not yet implemented")
    
    def get_timeframes(self) -> Dict[str, str]:
        return {
            'zone_timeframe': 'M15',
            'entry_timeframe': 'M5',  # or 'M1'
            'trend_timeframe': 'M15'
        }
    
    def get_technical_indicators(self) -> Dict[str, Dict]:
        return {
            'ema': {'fast': 8, 'medium': 13},  # Fast EMAs for scalping
            'rsi': {'period': 7, 'overbought': 70, 'oversold': 30},  # Faster RSI
            'breakeven': {'trigger_r': 0.3, 'offset_pips': 1.0},  # Fast BE
            'trailing': {'activation_pips': 10.0, 'limit_pips': 5.0}
        }
    
    def validate_entry_conditions(self, signal: Dict, market_data: pd.DataFrame) -> bool:
        """TODO: Scalping-specific entry validation."""
        raise NotImplementedError("Scalping validation not yet implemented")
    
    async def should_close_all_positions(self, current_time: datetime) -> bool:
        """Scalping: Check if positions exceeded 4-hour max hold time."""
        # TODO: Check each position's age
        return False
```

---

### 5. **Trading Type Factory**

Factory pattern to instantiate the correct executor based on configuration.

```python
class TradingTypeFactory:
    """Factory for creating trading type executors."""
    
    @staticmethod
    def create_executor(trading_type: str, config: Dict, foundation_engine, position_manager) -> TradingTypeExecutor:
        """
        Create appropriate executor based on trading type.
        
        Args:
            trading_type: 'day_trading', 'swing_trading', 'scalping', etc.
            config: Full configuration dict
            foundation_engine: Shared foundation engine instance
            position_manager: Shared position manager instance
            
        Returns:
            Appropriate TradingTypeExecutor subclass instance
            
        Raises:
            ValueError: If trading type not supported
        """
        executors = {
            'day_trading': IntradayExecutor,
            'swing_trading': SwingExecutor,
            'scalping': ScalpingExecutor
        }
        
        executor_class = executors.get(trading_type)
        if not executor_class:
            raise ValueError(
                f"Unsupported trading type: {trading_type}. "
                f"Supported types: {list(executors.keys())}"
            )
        
        return executor_class(config, foundation_engine, position_manager)
```

---

### 6. **Main Bot Orchestrator (Updated)**

```python
class TradingBot:
    """
    Main trading bot orchestrator.
    
    Routes to appropriate trading type executor based on configuration.
    """
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        
        # Get active trading type from config
        self.active_trading_type = self.config.get('trading_types', {}).get('active_trading_type', 'day_trading')
        
        # Initialize shared components (used by all trading types)
        self.db_manager = DatabaseManager(self.config)
        self.position_manager = PositionManager(self.config, self.db_manager)
        self.foundation_engine = FoundationEngine(self.config, use_database=True)
        
        # Create appropriate executor
        self.executor = TradingTypeFactory.create_executor(
            self.active_trading_type,
            self.config,
            self.foundation_engine,
            self.position_manager
        )
        
        logger.info(f"Trading Bot initialized with trading type: {self.active_trading_type}")
    
    async def start(self):
        """Start the trading bot with active trading type."""
        await self.executor.initialize()
        
        symbols = self._get_active_symbols()
        logger.info(f"Starting {self.active_trading_type} executor for symbols: {symbols}")
        
        await self.executor.execute_trading_loop(symbols)
    
    def _get_active_symbols(self) -> List[str]:
        """Get enabled symbols from watchlist."""
        watchlist = self.config.get('trading', {}).get('watchlist', [])
        return [s['symbol'] for s in watchlist if s.get('enabled', False)]
```

---

## 📊 Configuration Structure

Each trading type has its own config section in `trading_types.yaml`:

```yaml
# Active trading type (change this to switch modes)
active_trading_type: day_trading  # Options: day_trading, swing_trading, scalping

trading_types:
  day_trading:
    # Intraday parameters...
    
  swing_trading:
    # Swing parameters...
    
  scalping:
    # Scalping parameters...
```

---

## 🔄 Migration Path

### Phase 1: Refactor Intraday (Current Sprint) ✅
1. Extract current logic into `IntradayExecutor`
2. Update `main.py` to use factory pattern
3. Test thoroughly to ensure no regression

### Phase 2: Implement Swing (Next Sprint) 📋
1. Implement `SwingExecutor` based on skeleton
2. Add D1/H4 timeframe logic
3. Test with historical swing data

### Phase 3: Implement Scalping (Future) 🔮
1. Implement `ScalpingExecutor` based on skeleton
2. Add M15/M5 micro-zone logic
3. Optimize for low latency

---

## ✅ Benefits of This Architecture

1. **Clean Separation** - Each trading type is isolated
2. **Easy Switching** - Change one config value to switch modes
3. **No Code Duplication** - Shared foundation components
4. **Type Safety** - Abstract base class enforces contracts
5. **Testable** - Each executor can be tested independently
6. **Scalable** - Easy to add new trading types (position trading, etc.)

---

## 📝 Next Steps

See `implementation-plan-trading-types.md` for detailed todolist and sprint planning.
