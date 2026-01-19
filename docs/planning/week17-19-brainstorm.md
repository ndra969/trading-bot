# Week 17-19 Database Schema Enhancement - Brainstorming & Design Decisions

**Date**: January 16, 2026
**Status**: 📋 **PLANNED** - Detailed brainstorming before implementation
**Related**: PHASE5_5_TODO.md (detailed task list), DASHBOARD_BRAINSTORM.md (high-level overview)

---

## 🎯 Overview

This document captures brainstorming, design decisions, and edge cases for Week 17-19 database schema enhancements. This is the **design phase** before implementation.

**Week 17**: Signal Tracking & Audit Trail (4 tables)
**Week 18**: Market Data & Risk Metrics (4 tables)
**Week 19**: Quality Metrics & Analytics (MAE/MFE, views, indexes)

---

## 📊 Week 17: Signal Tracking & Audit Trail

### 17.1 Trading Signals Table - Design Decisions

#### **Question 1: Signal Lifecycle States**
**Decision Needed**: What are all possible signal states?

**Options**:
- **Option A (Simple)**: `GENERATED`, `EXECUTED`, `EXPIRED`, `CANCELLED`
- **Option B (Detailed)**: `GENERATED`, `VALIDATED`, `PENDING_EXECUTION`, `EXECUTED`, `REJECTED`, `EXPIRED`, `CANCELLED`

**Recommendation**: **Option A** for MVP, can extend later
- `GENERATED`: Signal created by strategy
- `EXECUTED`: Position opened from this signal
- `EXPIRED`: Signal expired (time-based or zone invalidated)
- `CANCELLED`: Manually cancelled or invalidated

**Edge Cases**:
- What if signal expires but zone is still valid? → Mark as EXPIRED, keep zone reference
- What if multiple positions from same signal? → One signal → multiple executions (tracked in SIGNAL_EXECUTIONS)
- What if signal is rejected by risk manager? → Mark as CANCELLED with reason

#### **Question 2: Enhancement Scores Storage**
**Decision Needed**: How to store multiple enhancement layer scores?

**Current Structure** (from `TradingSignal` model):
```python
strategy_scores = {
    "foundation": 30.0,
    "rsi": 8.5,
    "price_action": 12.0,
    "trendline": 15.0,
    "fibonacci": 10.0,
}
```

**Options**:
- **Option A**: JSONB field `enhancement_scores` (PostgreSQL) / JSON (SQLite)
- **Option B**: Separate table `signal_enhancement_scores` with one row per layer
- **Option C**: Denormalized columns `rsi_score`, `ma_score`, `price_action_score`, etc.

**Recommendation**: **Option A (JSONB/JSON)**
- Flexible for adding new layers without schema changes
- Easy to query with PostgreSQL JSONB operators
- SQLite JSON support is sufficient for development

**Query Examples**:
```sql
-- PostgreSQL: Find signals with high RSI score
SELECT * FROM trading_signals
WHERE (enhancement_scores->>'rsi')::float > 10.0;

-- SQLite: Find signals with price action
SELECT * FROM trading_signals
WHERE json_extract(enhancement_scores, '$.price_action') > 10.0;
```

#### **Question 3: Signal Expiration Logic**
**Decision Needed**: When does a signal expire?

**Options**:
- **Option A**: Time-based (e.g., 1 hour after generation)
- **Option B**: Zone-based (expires when zone is invalidated)
- **Option C**: Both (expires when either condition met)

**Recommendation**: **Option C (Both)**
- Time-based: Prevents stale signals (default: 1 hour for day trading)
- Zone-based: Signal invalid if zone is broken/invalidated
- Trading type specific: Scalping = 15 min, Day = 1 hour, Swing = 24 hours

**Implementation**:
```python
def is_signal_expired(signal: TradingSignal, current_time: datetime) -> bool:
    # Time-based expiration
    if signal.expires_at and current_time > signal.expires_at:
        return True

    # Zone-based expiration (if zone_id exists)
    if signal.zone_id:
        zone = get_zone(signal.zone_id)
        if not zone or not zone.is_active:
            return True

    return False
```

#### **Question 4: Signal-to-Position Relationship**
**Decision Needed**: One-to-one or one-to-many?

**Current Reality**: One signal can theoretically create multiple positions if:
- Signal is re-executed after partial close
- Signal is executed on multiple accounts
- Signal is executed with different risk levels

**Recommendation**: **One-to-Many** (via SIGNAL_EXECUTIONS table)
- `TRADING_SIGNALS`: One signal record
- `SIGNAL_EXECUTIONS`: Multiple execution attempts (successful or failed)
- `POSITIONS`: Links to `signal_execution_id` (not directly to signal)

**Schema Design**:
```sql
TRADING_SIGNALS (1) ──< (many) SIGNAL_EXECUTIONS (1) ──< (many) POSITIONS
```

**Edge Case**: What if position is opened manually (no signal)? → `signal_id = NULL` (optional FK)

---

### 17.2 Signal Executions Table - Design Decisions

#### **Question 1: Execution Types**
**Decision Needed**: What types of executions do we track?

**Options**:
- **Option A**: `ENTRY`, `EXIT` (simple)
- **Option B**: `ENTRY`, `EXIT`, `MODIFY_SL`, `MODIFY_TP`, `PARTIAL_CLOSE` (detailed)

**Recommendation**: **Option A for Week 17** (ENTRY, EXIT only)
- Position modifications tracked in `POSITION_MODIFICATIONS` table
- Keep executions focused on position creation/closing
- Can extend later if needed

#### **Question 2: Execution Failure Tracking**
**Decision Needed**: How detailed should failure tracking be?

**Options**:
- **Option A**: Simple `success` boolean + `failure_reason` text
- **Option B**: Detailed error codes + stack traces

**Recommendation**: **Option A** (simple for MVP)
- `success`: Boolean
- `failure_reason`: Text (e.g., "Insufficient margin", "Invalid price", "Risk limit exceeded")
- `error_details`: JSONB (optional, for detailed debugging)

**Failure Reasons Enum**:
```python
class ExecutionFailureReason(str, Enum):
    INSUFFICIENT_MARGIN = "insufficient_margin"
    INVALID_PRICE = "invalid_price"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    MARKET_CLOSED = "market_closed"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    SLIPPAGE_TOO_HIGH = "slippage_too_high"
    UNKNOWN_ERROR = "unknown_error"
```

#### **Question 3: Slippage Calculation**
**Decision Needed**: How to calculate and store slippage?

**Calculation**:
```python
# Entry slippage
expected_price = signal.entry_price
actual_price = execution.execution_price
slippage_pips = abs(actual_price - expected_price) / pip_size

# Store in SIGNAL_EXECUTIONS
execution.slippage_pips = slippage_pips
execution.execution_price = actual_price
```

**Edge Cases**:
- What if execution is rejected? → `slippage_pips = NULL` (no execution)
- What if market gap? → Store actual execution price, slippage can be large
- What if partial fill? → Track multiple executions (one per fill)

---

### 17.3 Position Modifications Table - Design Decisions

#### **Question 1: Modification Types**
**Decision Needed**: What modifications do we track?

**Options**:
- **Option A**: `BREAKEVEN`, `TRAILING`, `PARTIAL_CLOSE`, `MODIFY_SL`, `MODIFY_TP`
- **Option B**: More granular (e.g., `TRAILING_ACTIVATED`, `TRAILING_UPDATED`, `TRAILING_STOPPED`)

**Recommendation**: **Option A** (5 types for MVP)
- `BREAKEVEN`: Stop loss moved to breakeven
- `TRAILING`: Trailing stop activated or updated
- `PARTIAL_CLOSE`: Partial position closed (detailed in PARTIAL_CLOSES table)
- `MODIFY_SL`: Stop loss manually modified
- `MODIFY_TP`: Take profit manually modified

**Schema**:
```python
class ModificationType(str, Enum):
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"
    PARTIAL_CLOSE = "partial_close"
    MODIFY_SL = "modify_sl"
    MODIFY_TP = "modify_tp"
```

#### **Question 2: Value Change Tracking**
**Decision Needed**: How to track old vs new values?

**Options**:
- **Option A**: `old_value`, `new_value` (generic, stored as JSON)
- **Option B**: Type-specific columns (`old_sl_price`, `new_sl_price`, `old_volume`, `new_volume`)

**Recommendation**: **Option A** (generic JSON for flexibility)
```python
# Example for breakeven
modification.old_value = {"stop_loss": 1.08200}
modification.new_value = {"stop_loss": 1.08500}  # Entry price

# Example for trailing
modification.old_value = {"stop_loss": 1.08300}
modification.new_value = {"stop_loss": 1.08400}  # Trailed up
```

**Query Example**:
```sql
-- Find all breakeven activations
SELECT * FROM position_modifications
WHERE modification_type = 'breakeven'
AND json_extract(new_value, '$.stop_loss') > json_extract(old_value, '$.stop_loss');
```

#### **Question 3: Modification Success Tracking**
**Decision Needed**: What if modification fails?

**Options**:
- **Option A**: Only track successful modifications
- **Option B**: Track both successful and failed attempts

**Recommendation**: **Option B** (track failures for debugging)
- `success`: Boolean
- `error_message`: Text (if failed)
- `retry_count`: Integer (if retried)

**Use Case**: If trailing stop update fails (MT5 error), we want to know why and retry logic.

---

### 17.4 Partial Closes Table - Design Decisions

#### **Question 1: Partial Close Tracking**
**Decision Needed**: How to track multiple partial closes?

**Options**:
- **Option A**: One record per partial close (multiple records per position)
- **Option B**: Single record with cumulative tracking

**Recommendation**: **Option A** (one record per partial close)
- Easier to query individual partial closes
- Can calculate cumulative profit by summing records
- Better audit trail

**Schema**:
```python
class PartialClose(Base):
    partial_close_id: str  # PK
    position_id: str  # FK
    close_price: float
    volume_closed: float  # Volume closed in this partial close
    remaining_volume: float  # Remaining volume after this close
    profit_pips: float
    profit_usd: float
    close_time: datetime
    reason: str  # "TP_LEVEL_1", "TP_LEVEL_2", "MANUAL", etc.
```

#### **Question 2: Partial Close Reasons**
**Decision Needed**: What reasons do we track?

**Options**:
- **Option A**: Simple text ("TP_LEVEL_1", "TP_LEVEL_2", "MANUAL")
- **Option B**: Enum with structured reasons

**Recommendation**: **Option A** (simple text for MVP)
- Can be extended to enum later
- Flexible for custom reasons

**Common Reasons**:
- `TP_LEVEL_1`: First take profit level (25% or 50%)
- `TP_LEVEL_2`: Second take profit level
- `MANUAL`: Manually closed by user
- `RISK_REDUCTION`: Closed to reduce risk exposure
- `PROFIT_LOCK`: Locked in profit before reversal

---

## 📊 Week 18: Market Data & Risk Metrics

### 18.1 Market Data Table - Design Decisions

#### **Question 1: Data Granularity**
**Decision Needed**: What timeframes to store?

**Options**:
- **Option A**: Store all timeframes (M1, M5, M15, H1, H4, D1)
- **Option B**: Store only active timeframes (based on trading type)

**Recommendation**: **Option B** (store active timeframes only)
- Reduces storage requirements
- Can add more timeframes later if needed
- Active timeframes: M15, H1, H4, D1 (for day trading)

**Configuration**:
```yaml
market_data:
  collect_timeframes: ["M15", "H1", "H4", "D1"]
  collection_interval: 60  # seconds
  retention_days: 90  # Keep 90 days of data
```

#### **Question 2: Technical Indicators Storage**
**Decision Needed**: How to store calculated indicators?

**Options**:
- **Option A**: JSONB field with all indicators
- **Option B**: Separate table `market_data_indicators`
- **Option C**: Denormalized columns (rsi_14, ma_50, etc.)

**Recommendation**: **Option A** (JSONB for flexibility)
```json
{
  "rsi_14": 65.5,
  "ma_9": 1.08500,
  "ma_21": 1.08450,
  "ma_50": 1.08300,
  "atr_14": 0.00150
}
```

**Query Example**:
```sql
-- Find candles with RSI > 70 (overbought)
SELECT * FROM market_data
WHERE json_extract(indicators, '$.rsi_14') > 70.0
AND symbol = 'EURUSD'
AND timeframe = 'H1';
```

#### **Question 3: Data Collection Strategy**
**Decision Needed**: Real-time vs batch collection?

**Options**:
- **Option A**: Real-time (collect on every candle close)
- **Option B**: Batch (collect every N minutes)
- **Option C**: Hybrid (real-time for active symbols, batch for others)

**Recommendation**: **Option C** (hybrid)
- Real-time for active trading symbols (every candle close)
- Batch for watchlist symbols (every 5 minutes)
- Reduces MT5 API calls

**Background Worker**:
```python
class MarketDataCollector:
    async def collect_active_symbols(self):
        # Real-time: Collect on candle close
        for symbol in self.active_symbols:
            await self.collect_latest_candle(symbol)

    async def collect_watchlist_symbols(self):
        # Batch: Collect every 5 minutes
        for symbol in self.watchlist_symbols:
            await self.collect_latest_candle(symbol)
```

---

### 18.2 Symbol Info Table - Design Decisions

#### **Question 1: Symbol Metadata**
**Decision Needed**: What metadata to store?

**Options**:
- **Option A**: Basic (pip_size, pip_value, digits, min/max volume)
- **Option B**: Comprehensive (spread, swap, margin, market hours, etc.)

**Recommendation**: **Option B** (comprehensive for dashboard)
- Basic trading parameters (pip_size, pip_value, digits)
- Volume constraints (min_volume, max_volume, volume_step)
- Trading costs (spread, swap_long, swap_short)
- Market hours (JSON with timezone-aware hours)
- Asset class and description

**Schema**:
```python
class SymbolInfo(Base):
    symbol: str  # PK
    asset_class: str  # "forex_major", "forex_jpy", "commodities", "crypto"
    description: str
    pip_size: float
    pip_value_per_lot: float
    digits: int
    min_volume: float
    max_volume: float
    volume_step: float
    spread: float  # Current spread
    swap_long: float  # Swap for long positions
    swap_short: float  # Swap for short positions
    market_hours: dict  # JSON: {"monday": {"open": "00:00", "close": "23:59"}, ...}
    is_active: bool
```

#### **Question 2: Symbol Sync Strategy**
**Decision Needed**: When to sync symbol info from MT5?

**Options**:
- **Option A**: On bot startup only
- **Option B**: Periodic sync (daily/weekly)
- **Option C**: On-demand when symbol is first used

**Recommendation**: **Option B** (periodic sync)
- Sync on bot startup
- Daily sync at midnight (update spreads, market hours)
- On-demand sync if symbol not found in DB

---

### 18.3 Risk Metrics Table - Design Decisions

#### **Question 1: Metrics Granularity**
**Decision Needed**: Per-session, per-position, or both?

**Options**:
- **Option A**: Per-session only (aggregated)
- **Option B**: Per-position only (detailed)
- **Option C**: Both (session-level and position-level)

**Recommendation**: **Option C** (both for flexibility)
- Session-level: Overall account risk, portfolio exposure
- Position-level: Individual position risk (optional, can be calculated on-demand)

**Schema**:
```python
class RiskMetric(Base):
    risk_id: str  # PK
    session_id: str  # FK (for session-level metrics)
    position_id: str | None  # FK (optional, for position-level)
    calculated_at: datetime

    # Account metrics
    account_balance: float
    account_equity: float
    used_margin: float
    free_margin: float

    # Exposure metrics
    total_exposure_usd: float
    total_risk_usd: float
    risk_percentage: float  # Total risk / account balance

    # Performance metrics
    daily_pnl_usd: float
    max_drawdown_usd: float
    max_drawdown_percentage: float

    # Risk limits (JSON)
    risk_limits: dict  # {"max_risk_per_trade": 0.5, "max_portfolio_risk": 2.0, ...}
```

#### **Question 2: Calculation Frequency**
**Decision Needed**: How often to calculate risk metrics?

**Options**:
- **Option A**: On every position change (real-time)
- **Option B**: Periodic (every N minutes)
- **Option C**: On-demand (when queried)

**Recommendation**: **Option A** (real-time for critical metrics)
- Calculate on position open/close/modify
- Background worker for periodic updates (every 1 minute)
- Cache for dashboard queries

---

### 18.4 Risk Violations Table - Design Decisions

#### **Question 1: Violation Severity Levels**
**Decision Needed**: How to classify violation severity?

**Options**:
- **Option A**: Simple (LOW, MEDIUM, HIGH, CRITICAL)
- **Option B**: Numeric (1-10 scale)

**Recommendation**: **Option A** (enum for clarity)
```python
class ViolationSeverity(str, Enum):
    LOW = "low"  # Warning only
    MEDIUM = "medium"  # Alert notification
    HIGH = "high"  # Stop trading for symbol
    CRITICAL = "critical"  # Emergency stop all trading
```

#### **Question 2: Violation Resolution**
**Decision Needed**: How to track violation resolution?

**Options**:
- **Option A**: Simple `resolved` boolean + `resolved_at` timestamp
- **Option B**: Detailed resolution tracking (who resolved, how, notes)

**Recommendation**: **Option A** (simple for MVP)
- `resolved`: Boolean
- `resolved_at`: Timestamp (NULL if not resolved)
- `resolution_notes`: Text (optional, for manual resolution notes)

**Auto-Resolution**:
- Violations auto-resolve when condition no longer exists
- E.g., "Exposure limit exceeded" resolves when position closed

---

## 📊 Week 19: Quality Metrics & Analytics

### 19.1 MAE/MFE Calculator - Design Decisions

#### **Question 1: Calculation Method**
**Decision Needed**: Tick data vs M1 bars?

**Options**:
- **Option A**: M1 bars (faster, less accurate)
- **Option B**: Tick data (slower, more accurate)
- **Option C**: Hybrid (M1 for historical, tick for real-time)

**Recommendation**: **Option C** (hybrid)
- Real-time: Calculate from tick data (if available)
- Historical: Calculate from M1 bars (sufficient accuracy)
- Fallback: Use H1 bars if M1 not available

**Calculation Logic**:
```python
def calculate_mae_mfe(position: Position, price_data: list[dict]) -> tuple[float, float]:
    """
    Calculate MAE (Maximum Adverse Excursion) and MFE (Maximum Favorable Excursion)

    MAE: Maximum loss from entry before position closed (worst drawdown)
    MFE: Maximum profit from entry before position closed (best unrealized profit)
    """
    entry_price = position.entry_price
    direction = position.position_type  # BUY or SELL

    mae = 0.0  # Worst drawdown in pips
    mfe = 0.0  # Best profit in pips

    for price_point in price_data:
        if direction == "BUY":
            # For BUY: profit when price goes up
            profit_pips = (price_point["close"] - entry_price) / position.pip_size
            mfe = max(mfe, profit_pips)  # Best profit
            mae = min(mae, profit_pips)  # Worst drawdown (negative)
        else:  # SELL
            # For SELL: profit when price goes down
            profit_pips = (entry_price - price_point["close"]) / position.pip_size
            mfe = max(mfe, profit_pips)
            mae = min(mae, profit_pips)

    return abs(mae), mfe  # MAE as positive value
```

#### **Question 2: Real-time vs Historical**
**Decision Needed**: Calculate in real-time or after close?

**Options**:
- **Option A**: Real-time (update MAE/MFE as position moves)
- **Option B**: After close (calculate once when position closed)

**Recommendation**: **Option B** (after close for MVP)
- Simpler implementation
- More accurate (complete price history)
- Can add real-time tracking later if needed

**Background Worker**:
```python
async def calculate_historical_mae_mfe():
    """Calculate MAE/MFE for all closed positions without metrics"""
    closed_positions = await get_positions_without_mae_mfe()

    for position in closed_positions:
        # Get price data for position duration
        price_data = await get_price_data(
            symbol=position.symbol,
            start_time=position.open_time,
            end_time=position.close_time,
            timeframe="M1"
        )

        mae, mfe = calculate_mae_mfe(position, price_data)

        # Update position
        position.mae_pips = mae
        position.mfe_pips = mfe
        await save_position(position)
```

---

### 19.2 Quality Score Calculation - Design Decisions

#### **Question 1: Quality Score Formula**
**Decision Needed**: How to calculate quality score (0-100)?

**Options**:
- **Option A**: Simple (P&L based only)
- **Option B**: Multi-factor (P&L, R:R, signal quality, automation effectiveness)

**Recommendation**: **Option B** (multi-factor for comprehensive analysis)

**Formula**:
```python
def calculate_quality_score(position: Position) -> float:
    """
    Calculate position quality score (0-100)

    Factors:
    - P&L contribution (40%): How much profit/loss
    - Risk/Reward achievement (20%): Did we hit target R:R?
    - Signal quality (20%): Was signal high confidence?
    - Automation effectiveness (20%): Did automation work well?
    """

    # 1. P&L Contribution (40%)
    pnl_score = min(100, max(0, (position.realized_pnl_usd / position.risk_amount_usd) * 50))
    # Normalize: 2:1 R:R = 100 points, 1:1 = 50 points, loss = 0 points

    # 2. Risk/Reward Achievement (20%)
    target_rr = position.entry_to_tp_pips / position.entry_to_sl_pips
    actual_rr = abs(position.realized_profit_pips / position.entry_to_sl_pips) if position.entry_to_sl_pips > 0 else 0
    rr_score = min(100, (actual_rr / target_rr) * 100) if target_rr > 0 else 0

    # 3. Signal Quality (20%)
    signal_score = position.signal_confidence or 0  # Use signal confidence directly

    # 4. Automation Effectiveness (20%)
    automation_score = 0
    if position.breakeven_activated:
        automation_score += 10
    if position.trailing_activated:
        automation_score += 10
    # Add more automation factors (partial closes, etc.)

    # Weighted average
    quality_score = (
        pnl_score * 0.40 +
        rr_score * 0.20 +
        signal_score * 0.20 +
        automation_score * 0.20
    )

    return round(quality_score, 2)
```

#### **Question 2: Quality Classification**
**Decision Needed**: How to classify position quality?

**Options**:
- **Option A**: Simple (WINNER, LOSER)
- **Option B**: Detailed (EXCELLENT, GOOD, AVERAGE, POOR, TERRIBLE)

**Recommendation**: **Option A** (simple for MVP)
- `is_winner`: Boolean (realized_pnl_usd > 0)
- `quality_score`: Float (0-100, for detailed analysis)

Can add classification later:
- EXCELLENT: quality_score >= 80
- GOOD: 60-79
- AVERAGE: 40-59
- POOR: 20-39
- TERRIBLE: < 20

---

### 19.3 Materialized Views - Design Decisions

#### **Question 1: View Refresh Strategy**
**Decision Needed**: When to refresh materialized views?

**Options**:
- **Option A**: Manual refresh (on-demand)
- **Option B**: Scheduled refresh (every N minutes)
- **Option C**: Auto-refresh on data change (triggers)

**Recommendation**: **Option B** (scheduled refresh)
- Refresh every 5 minutes for real-time dashboard
- Manual refresh available for immediate updates
- Can optimize with incremental refresh later

**Views to Create**:
1. `session_performance` - Session-level aggregations
2. `strategy_effectiveness` - Strategy performance metrics
3. `position_quality_metrics` - Quality score distribution

**Example View**:
```sql
CREATE MATERIALIZED VIEW session_performance AS
SELECT
    s.session_id,
    s.account_id,
    s.start_time,
    s.end_time,
    COUNT(p.position_id) as total_trades,
    SUM(CASE WHEN p.is_winner THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN NOT p.is_winner THEN 1 ELSE 0 END) as losing_trades,
    ROUND(
        (SUM(CASE WHEN p.is_winner THEN 1 ELSE 0 END)::float /
         NULLIF(COUNT(p.position_id), 0)) * 100,
        2
    ) as win_rate,
    SUM(p.realized_pnl_usd) as total_pnl_usd,
    AVG(p.quality_score) as avg_quality_score,
    AVG(p.holding_time_seconds) as avg_holding_time_seconds
FROM trading_sessions s
LEFT JOIN positions p ON p.session_id = s.session_id
WHERE p.status = 'CLOSED'
GROUP BY s.session_id, s.account_id, s.start_time, s.end_time;
```

#### **Question 2: View Indexing**
**Decision Needed**: What indexes to create on views?

**Recommendation**: Index on commonly queried columns
- `session_performance`: Index on `account_id`, `start_time`
- `strategy_effectiveness`: Index on `strategy_id`, `symbol`
- `position_quality_metrics`: Index on `quality_score`, `is_winner`

---

### 19.4 Performance Indexes - Design Decisions

#### **Question 1: Index Strategy**
**Decision Needed**: What indexes to create?

**Recommendation**: Create indexes for common dashboard queries

**Positions Table Indexes**:
```sql
-- Session + Symbol (common filter)
CREATE INDEX idx_positions_session_symbol ON positions(session_id, symbol);

-- Account + Status (active positions)
CREATE INDEX idx_positions_account_status ON positions(account_id, status);

-- Created time (recent positions)
CREATE INDEX idx_positions_created_at ON positions(created_at DESC);

-- Quality score (top performers)
CREATE INDEX idx_positions_quality_score ON positions(quality_score DESC);

-- Signal relationship
CREATE INDEX idx_positions_signal_id ON positions(signal_id) WHERE signal_id IS NOT NULL;
```

**Trading Signals Indexes**:
```sql
-- Session + Confidence (signal quality)
CREATE INDEX idx_signals_session_confidence ON trading_signals(session_id, final_confidence DESC);

-- Generated time (recent signals)
CREATE INDEX idx_signals_generated_at ON trading_signals(generated_at DESC);

-- Status (active signals)
CREATE INDEX idx_signals_status ON trading_signals(signal_status) WHERE signal_status = 'GENERATED';
```

**Market Data Indexes**:
```sql
-- Symbol + Timeframe + Timestamp (time-series queries)
CREATE INDEX idx_market_data_symbol_timeframe ON market_data(symbol, timeframe, timestamp DESC);

-- Timestamp only (recent data)
CREATE INDEX idx_market_data_timestamp ON market_data(timestamp DESC);
```

---

## 🎯 Implementation Priority

### Week 17 Priority Order:
1. **17.1 Trading Signals** - CRITICAL (needed for signal analysis)
2. **17.2 Signal Executions** - HIGH (needed for execution quality)
3. **17.3 Position Modifications** - HIGH (needed for automation tracking)
4. **17.4 Partial Closes** - MEDIUM (nice to have for profit analysis)

### Week 18 Priority Order:
1. **18.3 Risk Metrics** - CRITICAL (needed for risk dashboard)
2. **18.1 Market Data** - HIGH (needed for charts)
3. **18.2 Symbol Info** - MEDIUM (nice to have for symbol management)
4. **18.4 Risk Violations** - MEDIUM (nice to have for alert history)

### Week 19 Priority Order:
1. **19.2 Quality Score** - CRITICAL (needed for position analysis)
2. **19.1 MAE/MFE** - HIGH (needed for quality metrics)
3. **19.3 Materialized Views** - HIGH (needed for dashboard performance)
4. **19.4 Performance Indexes** - MEDIUM (optimization)

---

## ❓ Open Questions

1. **Signal Expiration**: Should expired signals be automatically cleaned up or kept for analysis?
   - **Recommendation**: Keep for analysis, add `is_expired` flag, cleanup old signals (>30 days) in background job

2. **Market Data Retention**: How long to keep market data?
   - **Recommendation**: 90 days for active symbols, 30 days for inactive symbols

3. **Risk Metrics History**: How long to keep risk metric snapshots?
   - **Recommendation**: Keep all (for trend analysis), archive old data (>1 year) to separate table

4. **MAE/MFE for Open Positions**: Calculate in real-time or only for closed?
   - **Recommendation**: Only for closed positions (MVP), add real-time later if needed

---

## 📝 Next Steps

1. **Review this brainstorming** with team/stakeholders
2. **Finalize design decisions** for open questions
3. **Create detailed task breakdown** (already in PHASE5_5_TODO.md)
4. **Start Week 17 implementation** with TDD approach

---

**Last Updated**: January 16, 2026
**Status**: 📋 Ready for review and implementation
