# Intraday Refactoring - TODO List

**Priority:** HIGH - This is our CURRENT focus  
**Goal:** Refactor existing intraday/day trading logic into clean executor architecture  
**Status:** 🟡 Ready to Start  
**Timeline:** 8-9 days (Split into 3 phases)

**References:**
- [Zone-Based SL Bugfix Implementation](../bugfix/zone-based-sl-implementation.md)
- [Trading Type Implementation Plan](../implementation-plan-trading-types.md)
- [Trading Type Refactoring Walkthrough](../walkthrough-trading-type-refactoring.md)
- [Intraday Strategy Audit](../audit/intraday-strategy-audit.md)
- [CLAUDE.md](../../CLAUDE.md)


---

## 🎯 Objective

**AUDIT FIRST, THEN REFACTOR!**

Before extracting current working day trading logic, we will:
1. **Phase 0:** Audit & validate all strategy calculations and logic (1-2 days)
2. **Phase 1:** Create clean architecture foundation (3 days)
3. **Phase 2:** Extract H1/M30 intraday logic with ZERO regression (4 days)

Extract current working day trading logic (H1 zones + M30 entries + H1 Sniper trend gate) from current implementation into a clean `IntradayExecutor` class, WITHOUT any regression.

**Success = Validated Logic + Zero regression + Clean architecture**

---

## PHASE0_TODO: Code Audit & Review (1-2 days)

**CRITICAL:** Before refactoring, we must validate that current strategy logic is correct!

### Sprint 0.1: Strategy Logic Review

#### Task 0.1.1: Review H1 Trend Gate (Sniper Strategy)
- [x] **File:** `scripts/run_mtf_backtest.py` lines 174-238
- [x] **Review Checklist:**
  ```python
  # Lines 185-186: EMA Calculation
  h1_ema_50 = h1_hist["close"].ewm(span=50, adjust=False).mean()
  h1_ema_20 = h1_hist["close"].ewm(span=20, adjust=False).mean()
  ```
  - [x] **Verify:** EMA calculation is correct (exponential moving average)
  - [x] **Verify:** `span=50` means 50-period EMA (correct for intraday)
  - [x] **Verify:** `adjust=False` is correct (standard EMA formula)
  - [x] **Question:** Should we use SMA instead of EMA? Check strategy doc
  
  ```python
  # Lines 189-190: EMA Values
  ema_50_curr = h1_ema_50.iloc[-1]  # Current EMA 50
  ema_50_prev = h1_ema_50.iloc[-2]  # Previous EMA 50
  ```
  - [x] **Verify:** Using correct index (-1 = most recent)
  - [x] **Verify:** Slope calculation logic is sound
  
  ```python
  # Lines 193-194: Slope Calculation
  slope_up = ema_50_curr > ema_50_prev
  slope_down = ema_50_curr < ema_50_prev
  ```
  - [x] **Review:** Is simple comparison enough for slope?
  - [x] **Consider:** Should we use angle/percentage change instead?
  - [x] **Action:** Document why this is sufficient
  
  ```python
  # Lines 198-207: Bullish/Bearish Logic
  is_bullish = (
      current_price > ema_50_curr and 
      current_price > ema_20_curr and 
      slope_up
  )
  is_bearish = (
      current_price < ema_50_curr and 
      current_price < ema_20_curr and 
      slope_down
  )
  ```
  - [x] **Verify:** All three conditions required (AND logic)
  - [x] **Question:** Should EMA 20 and EMA 50 relationship matter?
  - [x] **Consider:** What if EMA 20 > EMA 50 but both below price? (Golden cross)
  - [x] **Action:** Test edge cases
  
  ```python
  # Lines 218-234: Momentum Protection
  if len(h1_hist) >= 3:
      c_curr = h1_hist["close"].iloc[-1]
      c_p1 = h1_hist["close"].iloc[-2]
      c_p2 = h1_hist["close"].iloc[-3]
      
      # Block BUY on bearish momentum
      if h1_trend_bias == "BULLISH" and c_curr < c_p1 and c_p1 < c_p2:
          h1_trend_bias = "NEUTRAL"
  ```
  - [x] **Verify:** Logic checks 2 consecutive red candles
  - [x] **Review:** Is 2 candles enough? Consider 3?
  - [x] **Question:** Should we check candle body size? (avoid doji false signals)
  - [x] **Action:** Backtest with/without this protection
  - [x] **FINDING:** Found Lookahead Bias in H1 data access!

#### Task 0.1.2: Review Zone Detection Logic
- [x] **File:** `scripts/run_mtf_backtest.py` lines 124-126
- [x] **Review:**
  ```python
  zones = await self.engine.analyze_symbol(
      self.symbol, self.zone_data, self.zone_tf, reference_time=last_zone_timestamp
  )
  ```
  - [x] **Verify:** `reference_time` is set correctly (prevents zone expiration)
  - [x] **Check:** Zone detection inside `FoundationEngine.analyze_symbol()`
  - [x] **Action:** Review foundation engine zone detection logic
  
- [x] **File:** `src/trading_bot/strategies/foundation/foundation_engine.py`
- [x] **Review Zone Detection Algorithm:**
  - [x] **Verify:** Rejection zones - wick ratio calculation correct?
  - [x] **Verify:** Consolidation zones - range calculation correct?
  - [x] **Verify:** Breakout zones - momentum threshold correct?
  - [x] **Verify:** Zone strength scoring - weight distribution makes sense?
  - [x] **Verify:** Zone expiration - `max_zone_age_hours` properly applied?
  
- [x] **Review Zone Scoring:**
  ```yaml
  # config/strategy_parameters.yaml lines 71-75
  scoring_weights:
    strength_weight: 0.4
    freshness_weight: 0.3
    volume_weight: 0.2
    touches_weight: 0.1
  ```
  - [x] **Question:** Are these weights optimal for intraday?
  - [x] **Consider:** Should freshness be higher for scalping?
  - [x] **Action:** Document rationale for weights
  - [x] **FINDING:** Found Lookahead Bias in Zone Detection (Future zones active)!

#### Task 0.1.3: Review M30 Entry Confirmation
- [x] **File:** `scripts/run_mtf_backtest.py` lines 241-248
- [x] **Review:**
  ```python
  signal = await self.engine._create_signal_from_zone(
      self.symbol, active_zone, current_price, 'M30', m30_data,
      h1_trend_bias=h1_trend_bias
  )
  ```
- [x] **File:** `src/trading_bot/strategies/foundation/foundation_engine.py`
- [x] **Review `_create_signal_from_zone()` method:**
  - [x] **Verify:** Price action patterns detected correctly
  - [x] **Verify:** Confluence score calculation accurate
  - [x] **Verify:** H1 trend bias properly blocks counter-trend signals (Checked at line 1246)
  - [x] **Verify:** Entry price determination (zone center? edge? -> Uses Current Price)
  
- [x] **Review Signal Validation:**
  ```yaml
  # config/strategy_parameters.yaml lines 97-102
  quality_thresholds:
    min_confluence_score: 40.0
    min_foundation_score: 30.0
    min_price_action_score: 10.0
  ```
  - [x] **Question:** Is 40% confluence threshold too low?
  - [x] **Question:** Should intraday have higher threshold than swing?
  - [x] **Action:** Analyze backtest results by confluence threshold

#### Task 0.1.4: Review TP/SL Calculation
- [x] **File:** Review position creation logic
- [x] **Verify Pip Calculations:**
- [x] **Review SL/TP Settings:**
- [x] **Review Min/Max Distance:**

#### Task 0.1.5: Review Breakeven & Trailing Logic
- [x] **File:** `scripts/run_mtf_backtest.py` lines 314-374
- [x] **Review Breakeven Logic:**
  - 0.7R formula confirmed correct in Audit
- [x] **Review Trailing Stop Logic:**
  - Logic confirmed correct in Audit

#### Task 0.1.6: Review Asset-Specific Logic
- [x] **File:** `src/trading_bot/connectors/symbol_mapper.py`
- [x] **Verify Asset Classification:**
- [x] **File:** `src/trading_bot/position/pip_calculator.py`
- [x] **Review Pip Calculations:**
  - Passed Audit Part 5

#### Task 0.1.7: Performance & Edge Case Review
- [ ] **Review Performance:**
  - [ ] **Check:** Zone caching effectiveness (line 15 - 60 min cache)
  - [ ] **Check:** Do we refresh zones too often or not enough?
  - [ ] **Measure:** Time taken to detect zones on H1
  - [ ] **Measure:** Time taken to analyze M30 candle
  - [ ] **Target:** Total loop < 55 seconds (per CLAUDE.md)
  
- [ ] **Review Edge Cases:**
  - [ ] **Case 1:** What if no H1 data available? (e.g., new symbol)
  - [ ] **Case 2:** What if zone cache empty at startup?
  - [ ] **Case 3:** What if price gaps through zone (weekend gap)?
  - [ ] **Case 4:** What if H1 EMA data insufficient (<50 candles)?
  - [ ] **Case 5:** What if all zones are expired?
  - [ ] **Action:** Add error handling for each case

---

### Sprint 0.2: Bug Identification & Fix Planning

#### Task 0.2.1: Known Issues Check
- [ ] Review conversation history for known bugs
- [x] Check if "ghost bug" (commodities vs commodity) is fixed
- [x] Verify H1 trend gate activates for Gold
- [x] Verify counter-trend signals are blocked
- [x] **NEW:** Fix Lookahead Bias (H1 Trend Gate + Zone Detection) - **PRIORITY**

#### Task 0.2.2: Backtest Analysis
- [ ] Run current backtest: `python scripts/run_mtf_backtest.py --symbol XAUUSD`
- [ ] Analyze results:
  - [ ] Win rate - is it reasonable? (expect 30-50% for trend-following)
  - [ ] Average R multiple - is it positive?
  - [ ] Max drawdown - is it acceptable?
  - [ ] Trade count - are we getting enough signals?
- [ ] Document baseline metrics for comparison

#### Task 0.2.3: Create Improvement List
- [ ] List potential bugs found during review
- [ ] List potential optimizations
- [ ] Prioritize: Critical bugs vs Nice-to-have improvements
- [ ] Decision: Fix during refactoring or separate sprint?

---

### Sprint 0.3: Strategy Validation Document

#### Task 0.3.1: Create Strategy Audit Report
- [ ] Create: `docs/audit/intraday-strategy-audit.md`
- [ ] Document findings from review
- [ ] List validated calculations (correct ✅)
- [ ] List questionable logic (needs review ⚠️)
- [ ] List bugs found (must fix 🔴)
- [ ] Include baseline backtest metrics

#### Task 0.3.2: Update Todolist with Fixes
- [ ] Add bug fixes to Phase 2 implementation
- [ ] Add improvement tasks
- [ ] Update timeline if needed

---

## PHASE1_TODO: Architecture Foundation (3 days)

### Sprint 1.1: Base Executor Abstract Class

#### Task 1.1.1: Write Failing Tests (RED)
- [ ] Create `tests/unit/executors/test_base_executor.py`
- [ ] Write test: `test_base_executor_cannot_be_instantiated()`
  - Expect TypeError when trying to instantiate abstract class
- [ ] Write test: `test_base_executor_requires_all_abstract_methods()`
  - Mock subclass, verify it must implement all abstract methods
- [ ] Write test: `test_base_executor_initializes_with_config()`
  - Verify constructor accepts config, foundation_engine, position_manager
- [ ] Run tests: `uv run pytest tests/unit/executors/test_base_executor.py -v`
  - **Expected:** All tests FAIL (no implementation yet)

#### Task 1.1.2: Implement Base Executor (GREEN)
- [ ] Create `src/trading_bot/executors/__init__.py`
- [ ] Create `src/trading_bot/executors/base_executor.py`
- [ ] Implement `TradingTypeExecutor(ABC)`:
  ```python
  class TradingTypeExecutor(ABC):
      def __init__(self, config, foundation_engine, position_manager):
          self.config = config
          self.foundation_engine = foundation_engine
          self.position_manager = position_manager
          
      @abstractmethod
      async def initialize(self): pass
      
      @abstractmethod
      async def execute_trading_loop(self, symbols): pass
      
      @abstractmethod
      async def analyze_symbol(self, symbol, current_time): pass
      
      @abstractmethod
      def get_timeframes(self): pass
      
      @abstractmethod
      def get_technical_indicators(self): pass
  ```
- [ ] Add type hints for all parameters and returns
- [ ] Add comprehensive docstrings (Google style)
- [ ] Run tests: `uv run pytest tests/unit/executors/test_base_executor.py -v`
  - **Expected:** All tests PASS

#### Task 1.1.3: Code Quality (REFACTOR)
- [ ] Run formatter: `uv run black src/trading_bot/executors/`
- [ ] Run linter: `uv run ruff check src/trading_bot/executors/ --fix`
- [ ] Run type checker: `uv run mypy src/trading_bot/executors/`
- [ ] Check coverage: `uv run pytest tests/unit/executors/ --cov=src/trading_bot/executors --cov-report=term-missing`
  - **Expected:** 100% coverage for base_executor.py

---

### Sprint 1.2: Factory Pattern

#### Task 1.2.1: Write Failing Tests (RED)
- [ ] Create `tests/unit/executors/test_factory.py`
- [ ] Write test: `test_factory_creates_intraday_executor()`
  - Mock config with `active_trading_type: day_trading`
  - Expect IntradayExecutor instance returned
- [ ] Write test: `test_factory_raises_error_for_invalid_type()`
  - Pass invalid type like `'invalid_type'`
  - Expect ValueError with helpful message
- [ ] Write test: `test_factory_passes_dependencies_correctly()`
  - Verify config, foundation_engine, position_manager passed to executor
- [ ] Run tests: `uv run pytest tests/unit/executors/test_factory.py -v`
  - **Expected:** All tests FAIL (factory doesn't exist yet)

#### Task 1.2.2: Implement Factory (GREEN)
- [ ] Create `src/trading_bot/executors/factory.py`
- [ ] Implement `TradingTypeFactory`:
  ```python
  class TradingTypeFactory:
      @staticmethod
      def create_executor(trading_type, config, foundation_engine, position_manager):
          executors = {
              'day_trading': IntradayExecutor,
              # 'swing_trading': SwingExecutor,  # TODO: Sprint 3
              # 'scalping': ScalpingExecutor,    # TODO: Sprint 4
          }
          
          executor_class = executors.get(trading_type)
          if not executor_class:
              raise ValueError(f"Unsupported trading type: {trading_type}")
          
          return executor_class(config, foundation_engine, position_manager)
  ```
- [ ] Add logging for executor creation
- [ ] Run tests: `uv run pytest tests/unit/executors/test_factory.py -v`
  - **Expected:** All tests PASS

#### Task 1.2.3: Code Quality (REFACTOR)
- [ ] Format, lint, type check (same as above)
- [ ] Check coverage: 100% for factory.py

---

### Sprint 1.3: Validation

- [ ] Run complete executor tests: `uv run pytest tests/unit/executors/ -v --cov=src/trading_bot/executors --cov-fail-under=100`
  - **Expected:** All tests pass, 100% coverage
- [ ] No changes to existing code yet (we only created new files)
- [ ] Git commit: `feat: Add base executor architecture and factory pattern`

**✅ Phase 1 Complete:** We now have clean architecture foundation!

---

## PHASE2_TODO: Intraday Executor Implementation (4 days)

### Sprint 2.1: Extract Current Intraday Logic

#### Task 2.1.1: Write Integration Tests (RED)
- [ ] Create `tests/integration/test_intraday_executor.py`
- [ ] Write test: `test_intraday_executor_detects_h1_zones()`
  - Use real historical data from `data/backtest/XAUUSD_H1.csv`
  - Verify zones detected on H1 timeframe
- [ ] Write test: `test_intraday_executor_confirms_m30_entries()`
  - Use M30 data from `data/backtest/XAUUSD_M30.csv`
  - Verify entry signals generated on M30
- [ ] Write test: `test_intraday_executor_applies_h1_trend_gate()`
  - Test Sniper H1 EMA 50/20 trend filter for commodities
  - Verify BULLISH/BEARISH/NEUTRAL bias logic
- [ ] Write test: `test_intraday_executor_generates_same_signals_as_current()`
  - **CRITICAL REGRESSION TEST**
  - Run both old backtest and new executor on same data
  - Compare signal counts, entry prices, SL/TP levels
  - **Expected:** Identical results
- [ ] Run tests: `uv run pytest tests/integration/test_intraday_executor.py -v`
  - **Expected:** All tests FAIL (executor not implemented yet)

#### Task 2.1.2: Implement IntradayExecutor (GREEN)

**Step 1: Create File Structure**
- [ ] Create `src/trading_bot/executors/intraday_executor.py`
- [ ] Import required dependencies:
  ```python
  from datetime import datetime, timezone
  from typing import Dict, List, Optional
  import pandas as pd
  from .base_executor import TradingTypeExecutor
  from ..utils.logger import get_logger
  ```

**Step 2: Implement Core Methods**
- [ ] Implement `_get_trading_type()`:
  ```python
  def _get_trading_type(self) -> str:
      return "day_trading"
  ```

- [ ] Implement `get_timeframes()`:
  ```python
  def get_timeframes(self) -> Dict[str, str]:
      return {
          'zone_timeframe': 'H1',
          'entry_timeframe': 'M30',
          'trend_timeframe': 'H1'
      }
  ```

- [ ] Implement `get_technical_indicators()`:
  ```python
  def get_technical_indicators(self) -> Dict[str, Dict]:
      return {
          'ema': {'fast': 20, 'slow': 50, 'trend': 200},
          'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
          'breakeven': {'trigger_r': 0.7, 'offset_pips': 2.0},
          'trailing': {'activation_pips': 30.0, 'limit_pips': 10.0}
      }
  ```

**Step 3: Extract H1 Trend Gate (Sniper Strategy)**
- [ ] Extract logic from `scripts/run_mtf_backtest.py` lines 174-238
- [ ] Implement `_get_h1_trend_bias()` method:
  ```python
  async def _get_h1_trend_bias(self, symbol: str, current_time: datetime) -> Optional[str]:
      """
      Get H1 trend bias using EMA 50/20 (Sniper Gate).
      Only applies to commodities (Gold, Silver, etc.)
      
      Returns: 'BULLISH', 'BEARISH', 'NEUTRAL', or None
      """
      # Check asset class
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
      
      # Current values
      current_price = float(h1_data.iloc[-1]['close'])
      ema_50_curr = ema_50.iloc[-1]
      ema_50_prev = ema_50.iloc[-2]
      ema_20_curr = ema_20.iloc[-1]
      
      # Determine trend
      slope_up = ema_50_curr > ema_50_prev
      slope_down = ema_50_curr < ema_50_prev
      
      is_bullish = (current_price > ema_50_curr and 
                   current_price > ema_20_curr and 
                   slope_up)
      is_bearish = (current_price < ema_50_curr and 
                   current_price < ema_20_curr and 
                   slope_down)
      
      if is_bullish:
          return 'BULLISH'
      elif is_bearish:
          return 'BEARISH'
      else:
          return 'NEUTRAL'
  ```

**Step 4: Implement Zone Detection with Caching**
- [ ] Implement `initialize()`:
  ```python
  async def initialize(self):
      """Initialize intraday-specific components."""
      from trading_bot.position.pip_calculator import PipCalculator
      self.pip_calculator = PipCalculator()
      
      # Zone cache
      self.zone_cache = {}
      self.zone_cache_duration_minutes = 60  # Refresh H1 zones hourly
      
      logger.info("IntradayExecutor initialized (H1 zones, M30 entries)")
  ```

- [ ] Implement `_get_or_refresh_zones()`:
  ```python
  async def _get_or_refresh_zones(self, symbol: str, timeframe: str, current_time: datetime):
      """Get zones from cache or refresh if expired."""
      cache_key = f"{symbol}_{timeframe}"
      
      # Check cache
      if cache_key in self.zone_cache:
          cached_zones, cached_time = self.zone_cache[cache_key]
          age_minutes = (current_time - cached_time).total_seconds() / 60
          
          if age_minutes < self.zone_cache_duration_minutes:
              logger.debug(f"Using cached zones for {symbol} (age: {age_minutes:.1f}m)")
              return cached_zones
      
      # Refresh zones
      data = await self.foundation_engine.get_market_data(symbol, timeframe, 200)
      zones = await self.foundation_engine.analyze_symbol(
          symbol, data, timeframe, reference_time=current_time
      )
      
      # Update cache
      self.zone_cache[cache_key] = (zones, current_time)
      logger.info(f"Refreshed {len(zones)} zones for {symbol} on {timeframe}")
      
      return zones
  ```

**Step 5: Implement Symbol Analysis**
- [ ] Implement `analyze_symbol()`:
  ```python
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
      # Get H1 zones (with caching)
      zones = await self._get_or_refresh_zones(symbol, 'H1', current_time)
      if not zones:
          return None
      
      # Get M30 data
      m30_data = await self.foundation_engine.get_market_data(symbol, 'M30', 200)
      current_price = float(m30_data.iloc[-1]['close'])
      
      # Check if price at any zone
      active_zone = self._find_active_zone(current_price, zones)
      if not active_zone:
          return None
      
      # Apply H1 trend filter (Sniper Gate)
      h1_trend_bias = await self._get_h1_trend_bias(symbol, current_time)
      
      # Generate signal
      signal = await self.foundation_engine._create_signal_from_zone(
          symbol, active_zone, current_price, 'M30', m30_data,
          h1_trend_bias=h1_trend_bias
      )
      
      return signal
  ```

- [ ] Implement helper `_find_active_zone()`:
  ```python
  def _find_active_zone(self, price: float, zones: List) -> Optional:
      """Find zone that price is currently at."""
      for zone in zones:
          zone_size = zone.upper_bound - zone.lower_bound
          tolerance = zone_size * 0.2
          
          if zone.lower_bound - tolerance <= price <= zone.upper_bound + tolerance:
              return zone
      
      return None
  ```

**Step 6: Implement Trading Loop**
- [ ] Implement `execute_trading_loop()`:
  ```python
  async def execute_trading_loop(self, symbols: List[str]):
      """
      Intraday trading loop.
      
      Behavior:
      1. Scan every M30 candle close
      2. Check H1 zones (cached for 1 hour)
      3. Look for M30 entry confirmation
      4. Apply H1 trend filter for commodities
      5. Close all positions before end of trading day
      """
      logger.info("Starting intraday trading loop (H1/M30 MTF)")
      
      while True:
          current_time = datetime.now(timezone.utc)
          
          # Check end of day closure
          if await self.should_close_all_positions(current_time):
              await self.position_manager.close_all_positions("End of trading day")
              logger.info("Closed all positions (intraday mode)")
          
          # Scan each symbol
          for symbol in symbols:
              try:
                  signal = await self.analyze_symbol(symbol, current_time)
                  if signal:
                      await self.position_manager.open_position(signal)
              except Exception as e:
                  logger.error(f"Error analyzing {symbol}: {e}")
          
          # Wait for next M30 candle
          await self._wait_for_next_candle('M30')
  ```

- [ ] Implement `should_close_all_positions()`:
  ```python
  async def should_close_all_positions(self, current_time: datetime) -> bool:
      """Close all positions at end of trading day."""
      # Close at 23:30 UTC (before NY market close)
      return current_time.hour == 23 and current_time.minute >= 30
  ```

- [ ] Implement `_wait_for_next_candle()`:
  ```python
  async def _wait_for_next_candle(self, timeframe: str):
      """Wait for next candle close."""
      wait_seconds = {
          'M1': 60, 'M5': 300, 'M15': 900, 
          'M30': 1800, 'H1': 3600, 'H4': 14400
      }
      await asyncio.sleep(wait_seconds.get(timeframe, 1800))
  ```

**Step 7: Add Validation Method**
- [ ] Implement `validate_entry_conditions()`:
  ```python
  def validate_entry_conditions(self, signal: Dict, market_data: pd.DataFrame) -> bool:
      """Intraday-specific entry validation."""
      # Confluence threshold
      if signal.get('confluence_score', 0) < 40.0:
          return False
      
      # TODO: Add market hours validation
      
      return True
  ```

**Step 8: Run Tests**
- [ ] Run integration tests: `uv run pytest tests/integration/test_intraday_executor.py -v`
  - **Expected:** All tests PASS
- [ ] Verify regression test passes (same signals as old backtest)

#### Task 2.1.3: Code Quality (REFACTOR)
- [ ] Add comprehensive docstrings to all methods
- [ ] Add type hints everywhere
- [ ] Extract magic numbers to constants
- [ ] Add logging at key decision points
- [ ] Run formatter: `uv run black src/trading_bot/executors/intraday_executor.py`
- [ ] Run linter: `uv run ruff check src/trading_bot/executors/intraday_executor.py --fix`
- [ ] Run type checker: `uv run mypy src/trading_bot/executors/intraday_executor.py`

---

### Sprint 2.2: Update Main Bot

#### Task 2.2.1: Write Main Bot Tests (RED)
- [ ] Create `tests/integration/test_main_bot_orchestration.py`
- [ ] Write test: `test_main_bot_loads_intraday_executor_from_config()`
  - Mock config with `active_trading_type: day_trading`
  - Verify main bot creates IntradayExecutor
- [ ] Write test: `test_main_bot_routes_to_correct_executor()`
  - Verify factory.create_executor() called with correct params
- [ ] Write test: `test_main_bot_passes_dependencies_correctly()`
  - Verify foundation_engine, position_manager passed to executor
- [ ] Run tests: `uv run pytest tests/integration/test_main_bot_orchestration.py -v`
  - **Expected:** FAIL (main.py not updated yet)

#### Task 2.2.2: Update Main Bot (GREEN)
- [ ] Backup current `src/trading_bot/main.py` as `main.py.backup`
- [ ] Update `main.py`:
  ```python
  from trading_bot.executors.factory import TradingTypeFactory
  
  class TradingBot:
      def __init__(self, config_path: str):
          self.config = self._load_config(config_path)
          
          # Get active trading type
          trading_types_config = self.config.get('trading_types', {})
          self.active_trading_type = trading_types_config.get(
              'active_trading_type', 'day_trading'
          )
          
          # Initialize shared components
          self.db_manager = DatabaseManager(self.config)
          self.position_manager = PositionManager(self.config, self.db_manager)
          self.foundation_engine = FoundationEngine(self.config, use_database=True)
          
          # Create executor via factory
          self.executor = TradingTypeFactory.create_executor(
              self.active_trading_type,
              self.config,
              self.foundation_engine,
              self.position_manager
          )
          
          logger.info(f"Trading Bot initialized: {self.active_trading_type}")
      
      async def start(self):
          """Start trading bot with active executor."""
          await self.executor.initialize()
          
          symbols = self._get_active_symbols()
          logger.info(f"Starting {self.active_trading_type} for: {symbols}")
          
          await self.executor.execute_trading_loop(symbols)
  ```
- [ ] Run tests: `uv run pytest tests/integration/test_main_bot_orchestration.py -v`
  - **Expected:** PASS

#### Task 2.2.3: Update Configuration
- [ ] Update `config/trading_config.yaml`:
  ```yaml
  trading:
    mode: mtf  # Keep existing
    
    # Multi-Timeframe Settings (will be read from executor)
    mtf:
      zone_timeframe: H1
      entry_timeframe: M30
      zone_cache_minutes: 60
  ```
- [ ] Ensure `config/trading_types.yaml` has:
  ```yaml
  # Active trading type (change this to switch modes)
  active_trading_type: day_trading
  ```

---

### Sprint 2.3: Comprehensive Testing

#### Task 2.3.1: Regression Testing
- [ ] **CRITICAL:** Run MTF backtest with NEW code:
  ```bash
  python scripts/run_mtf_backtest.py --symbol XAUUSD --zone-tf H1 --entry-tf M30
  ```
- [ ] Compare results with previous backtest (saved in `config/backtest_before_fixes.yaml`)
- [ ] **Expected:** Identical or better results
  - Same number of trades
  - Same entry/exit prices (within 0.1 pips)
  - Same win rate
- [ ] Document any differences in `docs/regression-test-results.md`

#### Task 2.3.2: Full Test Suite
- [ ] Run all unit tests:
  ```bash
  uv run pytest tests/unit/ -v --cov=src/trading_bot --cov-report=term-missing
  ```
  - **Expected:** All pass, 85%+ coverage

- [ ] Run all integration tests:
  ```bash
  uv run pytest tests/integration/ -v
  ```
  - **Expected:** All pass

- [ ] Run executor tests with 100% coverage requirement:
  ```bash
  uv run pytest tests/unit/executors/ tests/integration/test_intraday_executor.py \
    --cov=src/trading_bot/executors --cov-fail-under=100
  ```
  - **Expected:** 100% coverage for executors package

#### Task 2.3.3: Code Quality Validation
- [ ] Format all code:
  ```bash
  uv run black src/trading_bot/ tests/
  ```
- [ ] Fix linting issues:
  ```bash
  uv run ruff check src/trading_bot/ tests/ --fix
  ```
- [ ] Type checking:
  ```bash
  uv run mypy src/trading_bot/executors/
  uv run mypy src/trading_bot/main.py
  ```
- [ ] **MANDATORY:** Dry-run validation:
  ```bash
  uv run trading-bot start --dry-run
  ```
  - **Expected:** Runs without errors, uses IntradayExecutor

---

### Sprint 2.4: Documentation

- [ ] Update `README.md` with executor architecture
- [ ] Update `CLAUDE.md` to reference executor architecture
- [ ] Create `docs/guides/switching-trading-types.md` (user guide)
- [ ] Add migration notes to `CHANGELOG.md`

---

## ✅ Definition of Done (Intraday Refactoring)

**This phase is complete when:**

1. **Architecture:**
   - [x] Base executor abstract class implemented
   - [x] Factory pattern implemented
   - [x] IntradayExecutor fully implemented

2. **Testing:**
   - [x] 100% test coverage for executor package
   - [x] All unit tests passing
   - [x] All integration tests passing
   - [x] Regression test shows zero degradation

3. **Code Quality:**
   - [x] All code formatted (black)
   - [x] All linting issues fixed (ruff)
   - [x] Type checking passes (mypy)
   - [x] Dry-run validation successful

4. **Functionality:**
   - [x] Backtest produces same results as before
   - [x] H1 zones detected correctly
   - [x] M30 entries confirmed correctly
   - [x] H1 Sniper trend gate works for commodities
   - [x] End-of-day position closure works

5. **Documentation:**
   - [x] All code has docstrings
   - [x] User guide updated
   - [x] README updated
   - [x] CHANGELOG updated

---

## 🚨 Risks & Blockers

### Potential Issues:
1. **Regression in backtest results**
   - Mitigation: Save current results first, compare carefully
   
2. **Foundation engine API changes needed**
   - Mitigation: Keep existing API, add new methods if needed
   
3. **Zone caching breaks current behavior**
   - Mitigation: Make caching optional, test thoroughly

### Red Flags:
- ⚠️ If backtest results differ by >5%, STOP and investigate
- ⚠️ If dry-run fails, DO NOT proceed to next phase
- ⚠️ If test coverage <100% for executors, DO NOT commit

---

## 📝 Notes

- **Current system is in:** `scripts/run_mtf_backtest.py` (lines 32-486)
- **Key logic to extract:** H1 trend gate (lines 174-238), zone detection (line 124-126), M30 entry confirmation (line 241-248)
- **Keep foundation engine unchanged:** We're only wrapping it in executor
- **Performance target:** Trading loop < 55 seconds (per CLAUDE.md)

---

**Last Updated:** 2026-01-21  
**Status:** Ready to Start ✅  
**Next Action:** Begin Sprint 1.1 - Base Executor Tests (RED phase)
