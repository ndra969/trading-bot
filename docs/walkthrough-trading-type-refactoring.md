# Trading Type Architecture - Planning Walkthrough

**Date:** 2026-01-21  
**Status:** Ready for Review & Implementation  
**Estimated Duration:** 13 days (~2.5 weeks)

---

## 📌 Executive Summary

Kami telah selesai menganalisis current state dan membuat complete architecture untuk mendukung 3 trading types (Intraday, Swing, Scalping) dengan clean separation dan easy switching.

### ✅ What We Analyzed

1. **Current Configuration**
   - ✅ Trading type active: `day_trading` (intraday)
   - ✅ MTF mode: H1 zones + M30 entries
   - ✅ Technical setup: EMA 50/20, RSI 14, Sniper H1 trend gate
   - ✅ Status: **Mature & Production-Ready** (99/99 tests passing)

2. **Readiness Assessment**
   - **Intraday (Current):** ✅ 100% Ready - Already working perfectly
   - **Swing Trading:** 🟡 60% Ready - Config exists, needs timeframe adjustment
   - **Scalping:** 🔴 20% Ready - Needs significant technical refactoring

3. **Key Findings**
   - Scalping requires **different indicators** (EMA 8/13 vs current 50/20)
   - Scalping requires **different timeframes** (M15/M5 vs current H1/M30)
   - Swing minimal adjustment (H4/D1 vs current H1/M30)
   - **H1 Trend Gate** hanya cocok untuk intraday, tidak untuk scalping

---

## 🏗️ Proposed Architecture

### Core Concept: "One Bot, Multiple Personalities"

```
┌──────────────────────────────────────────┐
│         Trading Bot Main                 │
│      (Orchestrator/Router)               │
└──────────────┬───────────────────────────┘
               │
               │ Reads: active_trading_type
               │
          ┌────┴────┐
          │ Factory │
          └────┬────┘
               │
      ┌────────┼────────┐
      │        │        │
┌─────▼──┐ ┌──▼────┐ ┌─▼──────┐
│Intraday│ │ Swing │ │Scalping│
│Executor│ │Exec.  │ │Exec.   │
│(ACTIVE)│ │(TODO) │ │(TODO)  │
└────────┘ └───────┘ └────────┘
     │         │          │
     └─────────┴──────────┘
               │
    ┌──────────▼──────────┐
    │ SHARED FOUNDATION   │
    │ - FoundationEngine  │
    │ - PositionManager   │
    │ - RiskManager       │
    │ - PipCalculator     │
    └─────────────────────┘
```

### Benefits

1. **Easy Switching:** Change satu config value aja
2. **No Code Duplication:** Foundation layer shared
3. **Clean Separation:** Each type isolated
4. **Extensible:** Mudah add position trading, news trading, dll
5. **Testable:** Each executor bisa di-test independently

---

## 📋 Documents Created

### 1. Architecture Documentation ✅
**File:** `docs/architecture/trading-type-architecture.md`

**Content:**
- Complete class hierarchy dengan base executor
- Full intraday executor implementation (extracted from current code)
- Swing executor skeleton with TODOs
- Scalping executor skeleton with TODOs
- Factory pattern for creating executors
- Updated main bot orchestrator

**Highlights:**
```python
class TradingTypeExecutor(ABC):
    """Base class untuk semua trading type executors"""
    
    @abstractmethod
    async def execute_trading_loop(self, symbols: List[str]):
        """Different types have different loop behaviors"""
        pass
    
    @abstractmethod
    def get_timeframes(self) -> Dict[str, str]:
        """Return zone_timeframe, entry_timeframe, trend_timeframe"""
        pass
```

### 2. Implementation Plan ✅
**File:** `docs/implementation-plan-trading-types.md`

**Content:**
- 5 detailed sprints dengan TDD approach
- Complete testing strategy (100% coverage requirement)
- Phase-by-phase breakdown
- Success criteria untuk tiap sprint
- Timeline estimate: 13 days

**Sprint Overview:**
1. **Sprint 1:** Architecture Foundation (3 days) - Base executor + factory
2. **Sprint 2:** Intraday Refactoring (4 days) - Extract current logic
3. **Sprint 3:** Swing Skeleton (2 days) - TODO implementation
4. **Sprint 4:** Scalping Skeleton (2 days) - TODO implementation
5. **Sprint 5:** Documentation & Testing (2 days) - Complete validation

---

## 🎯 Technical Comparison

### Intraday (Current - ACTIVE)
```yaml
Zone TF: H1 (hourly zones)
Entry TF: M30 (30-min confirmation)
Trend Filter: H1 EMA 50/20 (Sniper Gate for commodities)
Indicators: EMA 20/50/200, RSI 14
SL/TP: Forex 15/30 pips, Gold 50/100 pips
Risk: 1% per trade
Max Duration: 24 hours (close end of day)
Breakeven: 0.7R trigger (Sniper)
Status: ✅ Production Ready
```

### Swing Trading (SKELETON - TODO)
```yaml
Zone TF: H4 or D1 (daily zones)
Entry TF: H1 or H4 (4-hour confirmation)
Trend Filter: D1 EMA 50/100/200
Indicators: EMA 50/100/200 (slower)
SL/TP: Forex 50/100 pips, Gold 200/400 pips
Risk: 2% per trade
Max Duration: Multi-day (NO daily close)
Breakeven: 0.7R trigger
Trailing: Activate at 100 pips (wider)
Status: 🟡 Config ready, needs implementation
```

### Scalping (SKELETON - TODO)
```yaml
Zone TF: M15 (15-minute micro-zones)
Entry TF: M5 or M1 (fast triggers)
Trend Filter: M15 EMA 8/13 (FAST momentum)
Indicators: EMA 8/13 (NOT 50/20!), RSI 7 (NOT 14!)
SL/TP: Forex 5/8 pips, Gold 20/30 pips
Risk: 0.2% per trade (many trades)
Max Duration: 4 hours (auto-close)
Breakeven: 0.3R trigger (VERY fast BE)
Trailing: Activate at 10 pips (tight)
Status: 🔴 Needs major technical refactoring
```

---

## 🚀 Implementation Approach

### Phase-by-Phase Roadmap

#### **PHASE 1: Foundation (Sprint 1)** - 3 Days
**Goal:** Create architecture skeleton

**What We'll Do:**
1. Create `TradingTypeExecutor` abstract base class
2. Create `TradingTypeFactory` for executor creation
3. Write 100% test coverage for both
4. No changes to existing code yet

**TDD Steps:**
- ✅ Write failing tests first
- ✅ Implement minimal code to pass
- ✅ Refactor for quality
- ✅ Validate with dry-run

**Deliverables:**
- `src/trading_bot/executors/base_executor.py`
- `src/trading_bot/executors/factory.py`
- `tests/unit/executors/test_base_executor.py`
- `tests/unit/executors/test_factory.py`

---

#### **PHASE 2: Intraday Refactoring (Sprint 2)** - 4 Days
**Goal:** Extract current logic into IntradayExecutor (NO REGRESSION!)

**What We'll Do:**
1. Extract MTF backtest logic into `IntradayExecutor`
2. Extract H1 trend gate (Sniper) into executor method
3. Update `main.py` to use factory pattern
4. Run full regression tests

**Critical Validations:**
- ✅ Backtest results must match exactly
- ✅ All existing tests still pass
- ✅ Dry-run validation successful
- ✅ Performance: Trading loop < 55 seconds

**Deliverables:**
- `src/trading_bot/executors/intraday_executor.py`
- Updated `src/trading_bot/main.py`
- `tests/integration/test_intraday_executor.py`
- Regression validation report

---

#### **PHASE 3: Swing Skeleton (Sprint 3)** - 2 Days
**Goal:** Create skeleton for future swing implementation

**What We'll Do:**
1. Create `SwingExecutor` with all methods
2. All methods raise `NotImplementedError` with helpful messages
3. Add comprehensive TODO comments
4. Write skipped tests for future validation

**Skeleton Example:**
```python
async def execute_trading_loop(self, symbols: List[str]):
    """
    TODO: Swing trading loop.
    
    Required implementation:
    1. Scan every H4 or D1 candle close
    2. Check D1 zones (cache for 24 hours)
    3. Look for H4 entry confirmation
    4. Apply D1 trend filter
    5. NO auto-close (positions run for days)
    """
    raise NotImplementedError(
        "Swing trading executor not yet implemented. "
        "See docs/todos/swing-implementation-todos.md"
    )
```

**Deliverables:**
- `src/trading_bot/executors/swing_executor.py`
- `tests/unit/executors/test_swing_executor.py` (skipped)
- `docs/todos/swing-implementation-todos.md`

---

#### **PHASE 4: Scalping Skeleton (Sprint 4)** - 2 Days
**Goal:** Create skeleton for future scalping implementation

**What We'll Do:**
1. Create `ScalpingExecutor` with all methods
2. Add CRITICAL warnings about technical differences
3. Add performance requirements documentation
4. Write skipped tests for future validation

**Critical Notes:**
```python
"""
CRITICAL: Scalping requires different technical analysis!
- EMA 8/13 (NOT 50/20 like intraday)
- RSI 7 (NOT 14 like intraday)
- M15/M5 timeframes (NOT H1/M30)
- Breakeven 0.3R (NOT 0.7R)
- Spread costs matter significantly (tight SL!)
"""
```

**Deliverables:**
- `src/trading_bot/executors/scalping_executor.py`
- `tests/unit/executors/test_scalping_executor.py` (skipped)
- `docs/todos/scalping-implementation-todos.md`

---

#### **PHASE 5: Documentation & Validation (Sprint 5)** - 2 Days
**Goal:** Complete docs, testing, quality validation

**What We'll Do:**
1. Complete architecture documentation
2. Write migration guide for users
3. Run comprehensive test suite
4. Run code quality checks
5. Final dry-run validation

**Quality Checks (Per CLAUDE.md):**
```bash
# 1. Test coverage (85% minimum, 100% for executors)
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# 2. Executor coverage (100% requirement)
uv run pytest tests/unit/executors/ --cov-fail-under=100

# 3. Code quality
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/trading_bot/

# 4. MANDATORY: Dry-run
uv run trading-bot start --dry-run

# 5. Property tests
uv run pytest tests/properties/ --hypothesis-show-statistics
```

**Deliverables:**
- Migration guide
- TODO documents for swing/scalping
- 100% test coverage validation
- All quality checks passing

---

## ✅ Success Criteria

### Must Have (Definition of Done)

1. **Architecture**
   - ✅ Base executor abstract class implemented
   - ✅ Factory pattern implemented
   - ✅ Three executors created (1 active, 2 skeletons)

2. **Intraday (Current)**
   - ✅ Zero regression in backtest results
   - ✅ All existing tests pass
   - ✅ Dry-run validation successful
   - ✅ Performance maintained (< 55s loop)

3. **Swing & Scalping**
   - ✅ Skeleton implementations with TODOs
   - ✅ Configuration validated
   - ✅ Factory can create instances
   - ✅ Properly raises NotImplementedError

4. **Testing**
   - ✅ 100% coverage for executor package
   - ✅ All unit tests passing
   - ✅ Integration tests passing
   - ✅ Property tests implemented

5. **Documentation**
   - ✅ Architecture docs complete
   - ✅ Migration guide ready
   - ✅ Implementation TODOs documented
   - ✅ Code fully commented

6. **Switching**
   - ✅ Can switch types via config change only
   - ✅ No code changes needed to switch
   - ✅ Clear error messages if skeleton used

---

## 🎯 Future Work (After This Refactoring)

### Swing Trading Implementation (Est: 5-7 days)
**Prerequisites:** This architecture must be complete

**Tasks:**
- Implement D1 zone detection logic
- Implement H4 entry confirmation
- Add weekly structure analysis
- Test with historical swing data
- Optimize for multi-day holding

### Scalping Implementation (Est: 5-7 days)
**Prerequisites:** Architecture + possibly swing

**Tasks:**
- Implement M15 micro-zone detection
- Implement M5/M1 rapid entry logic
- Add fast EMA 8/13 momentum filter
- Optimize for low latency execution
- Handle spread costs carefully
- Test with high-frequency data

---

## 🚨 Risks & Mitigations

### Risk 1: Regression in Intraday Performance
**Probability:** Medium  
**Impact:** High  
**Mitigation:**
- Write regression tests before refactoring
- Run backtest comparison (before vs after)
- Keep fallback branch if needed
- Extensive dry-run testing

### Risk 2: Over-Engineering
**Probability:** Low  
**Impact:** Medium  
**Mitigation:**
- Follow YAGNI principle (You Aren't Gonna Need It)
- Only implement what's needed NOW
- Swing/Scalping are skeletons only
- Focus on clean interfaces, not perfect prediction

### Risk 3: Test Coverage Takes Too Long
**Probability:** Medium  
**Impact:** Low  
**Mitigation:**
- 100% coverage is non-negotiable (per CLAUDE.md)
- Allocate proper time in sprint planning
- Use TDD from day 1 (don't write tests after)
- Pair programming for complex tests

---

## 📊 Timeline & Resource Estimate

### Breakdown by Sprint

| Sprint | FTE Days | Deliverables | Risk |
|--------|----------|--------------|------|
| Sprint 1: Architecture | 3 | Base executor + factory | Low |
| Sprint 2: Intraday | 4 | Working refactored intraday | Medium |
| Sprint 3: Swing Skeleton | 2 | Swing skeleton + docs | Low |
| Sprint 4: Scalping Skeleton | 2 | Scalping skeleton + docs | Low |
| Sprint 5: Validation | 2 | Complete testing + docs | Low |
| **TOTAL** | **13 days** | **Complete architecture** | **Low-Medium** |

### Assumptions
- 1 developer full-time
- No major blockers or dependencies
- Existing test infrastructure works
- MT5 environment available for testing

### Buffer
- Add 20% buffer = ~3 extra days
- **Total realistic estimate: 16 days (~3 weeks)**

---

## 🎬 Next Steps

### Today (2026-01-21)
1. ✅ Review this walkthrough
2. ✅ Review architecture document
3. ✅ Review implementation plan
4. ⏳ **Get approval to proceed**

### Tomorrow (If Approved)
1. Start Sprint 1: Architecture Foundation
2. Create TDD tests for base executor
3. Implement base executor class
4. Daily progress updates

### This Week
- Complete Sprint 1 (Architecture)
- Start Sprint 2 (Intraday Refactoring)
- First regression test results

### Next Week
- Complete Sprint 2 (Intraday)
- Complete Sprint 3 (Swing Skeleton)
- Complete Sprint 4 (Scalping Skeleton)

### Week 3
- Complete Sprint 5 (Validation)
- Final documentation
- Handover & demo

---

## ❓ Questions for Review

Before we start implementation, please confirm:

1. **Approval:** Are you happy with this architecture approach?
2. **Scope:** Is Swing + Scalping skeleton (not full implementation) acceptable for now?
3. **Timeline:** Is 2-3 weeks reasonable for this refactoring?
4. **Priority:** Should we prioritize Swing or Scalping skeleton first? (Plan has Swing first)
5. **Risk:** Any concerns about regression risk for current intraday system?

**Catatan:** Intraday (current system) akan tetap berjalan sempurna. Kita HANYA refactoring structure, bukan mengubah logic.

---

## 📞 Recommendations

My professional recommendations:

1. **✅ Proceed with this architecture** - Clean, extensible, testable
2. **✅ Do skeletons first** - Don't implement swing/scalping fully yet
3. **✅ Keep TDD strict** - 100% coverage non-negotiable
4. **✅ Start with Sprint 1** - Low risk, high value
5. **⚠️ Allocate 3 weeks** - 2.5 weeks + buffer is realistic

**Next Action:** If you approve, I'll start Sprint 1 implementation right away with TDD approach. Kita mulai dari base executor tests dulu (RED phase). 🚀

---

**Prepared by:** Antigravity (Google DeepMind Agent)  
**Date:** 2026-01-21  
**Status:** Awaiting Approval 🟡
