# Implementation Plan: Multi Trading-Type Architecture

**Created:** 2026-01-21  
**Status:** Planning Phase  
**Objective:** Refactor trading bot to support Intraday, Swing, and Scalping with clean architecture

---

## 📋 Project Context

Based on `CLAUDE.md` and existing codebase:
- ✅ **Current State:** Day trading (H1 zones, M30 entries) is mature and production-ready
- ✅ **Foundation:** Supply & Demand strategy with 99/99 tests passing (98% coverage)
- ✅ **TDD Culture:** Test-driven development is mandatory (85% min, 95% for critical)
- ✅ **Tech Stack:** Python 3.11+, SQLAlchemy 2.0, Async-first, PostgreSQL ready

**Goal:** Create architecture that allows easy switching between trading types via config, without code changes.

---

## 🎯 Success Criteria

1. **Architecture:** Abstract base class `TradingTypeExecutor` with 3 concrete implementations
2. **Intraday:** Current logic refactored into `IntradayExecutor` (no regression)
3. **Swing/Scalping:** Skeleton implementations with TODO markers
4. **Testing:** 100% test coverage for new architecture components (per CLAUDE.md)
5. **Switching:** Change one config value (`active_trading_type`) to switch modes
6. **Documentation:** Complete architecture docs + migration guide

---

## 📐 Architecture Overview

```
TradingBot (main.py)
    ↓
TradingTypeFactory
    ↓
┌──────────────┬─────────────┬──────────────┐
│ Intraday     │ Swing       │ Scalping     │
│ Executor     │ Executor    │ Executor     │
│ (ACTIVE)     │ (SKELETON)  │ (SKELETON)   │
└──────────────┴─────────────┴──────────────┘
         ↓           ↓              ↓
    ╔════════════════════════════════════╗
    ║  SHARED FOUNDATION LAYER           ║
    ║  - FoundationEngine (S&D zones)    ║
    ║  - PositionManager                 ║
    ║  - PipCalculator                   ║
    ║  - RiskManager                     ║
    ╚════════════════════════════════════╝
```

---

## 🚀 Sprint Planning

### **SPRINT 1: Architecture Foundation** (Est: 3 days)
**Goal:** Create base executor abstraction + factory pattern

#### Phase 1.1: Base Executor Class (RED → GREEN → REFACTOR)
- [ ] **RED:** Write test for `TradingTypeExecutor` abstract contract
  - Test: `test_executor_must_implement_required_methods()`
  - Test: `test_executor_cannot_be_instantiated_directly()`
  - Test: `test_executor_requires_config_and_dependencies()`
  
- [ ] **GREEN:** Implement `TradingTypeExecutor` base class
  - File: `src/trading_bot/executors/base_executor.py`
  - Abstract methods: `initialize()`, `execute_trading_loop()`, `analyze_symbol()`
  - Concrete methods: `get_risk_parameters()`, `should_close_all_positions()`
  - Follow coding standards from `docs/guides/coding-standards.md`
  
- [ ] **REFACTOR:** Add type hints, docstrings, logging

#### Phase 1.2: Factory Pattern (TDD)
- [ ] **RED:** Write factory tests
  - Test: `test_factory_creates_intraday_executor()`
  - Test: `test_factory_creates_swing_executor()`
  - Test: `test_factory_creates_scalping_executor()`
  - Test: `test_factory_raises_error_for_invalid_type()`
  
- [ ] **GREEN:** Implement `TradingTypeFactory`
  - File: `src/trading_bot/executors/factory.py`
  - Method: `create_executor(trading_type, config, foundation, position_mgr)`
  - Error handling for unknown types
  
- [ ] **REFACTOR:** Clean up, add logging

#### Phase 1.3: Test Coverage Validation
- [ ] Run: `uv run pytest tests/unit/executors/ --cov=src/trading_bot/executors --cov-fail-under=100`
- [ ] Verify: All new code has 100% test coverage (per CLAUDE.md requirement)

**Deliverables:**
- ✅ `base_executor.py` with abstract base class
- ✅ `factory.py` with factory pattern
- ✅ `tests/unit/executors/test_base_executor.py`
- ✅ `tests/unit/executors/test_factory.py`
- ✅ 100% test coverage

---

### **SPRINT 2: Intraday Refactoring** (Est: 4 days)
**Goal:** Extract current day trading logic into `IntradayExecutor` without regression

#### Phase 2.1: Create IntradayExecutor (TDD)
- [ ] **RED:** Write integration test for current intraday behavior
  - Test: `test_intraday_executor_detects_h1_zones()`
  - Test: `test_intraday_executor_confirms_m30_entries()`
  - Test: `test_intraday_executor_applies_h1_trend_gate()` (Sniper strategy)
  - Test: `test_intraday_executor_closes_positions_end_of_day()`
  - Use existing backtest data from `data/backtest/XAUUSD_H1.csv`
  
- [ ] **GREEN:** Implement `IntradayExecutor`
  - File: `src/trading_bot/executors/intraday_executor.py`
  - Extract logic from `run_mtf_backtest.py` lines 113-255 (current MTF logic)
  - Extract H1 trend gate from lines 174-238
  - Implement `get_timeframes()` → {'zone': 'H1', 'entry': 'M30', 'trend': 'H1'}
  - Implement `get_technical_indicators()` → EMA 20/50/200, RSI 14
  - Implement `should_close_all_positions()` → End of day logic
  
- [ ] **REFACTOR:** 
  - Extract `_get_h1_trend_bias()` into separate method
  - Extract `_get_or_refresh_zones()` with caching logic
  - Add comprehensive docstrings per coding standards
  
#### Phase 2.2: Update Main Bot (TDD)
- [ ] **RED:** Write tests for main bot orchestration
  - Test: `test_main_bot_loads_intraday_executor_from_config()`
  - Test: `test_main_bot_routes_to_correct_executor()`
  - Test: `test_main_bot_passes_dependencies_correctly()`
  
- [ ] **GREEN:** Update `main.py`
  - Import `TradingTypeFactory`
  - Read `active_trading_type` from config
  - Create executor via factory
  - Call `executor.initialize()` and `executor.execute_trading_loop()`
  
- [ ] **REFACTOR:** Clean up old code, add error handling

#### Phase 2.3: Regression Testing
- [ ] Run full test suite: `uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85`
- [ ] Run MTF backtest: `python scripts/run_mtf_backtest.py --symbol XAUUSD --zone-tf H1 --entry-tf M30`
- [ ] Verify: Same results as before refactoring (no regression)
- [ ] Run: `uv run trading-bot start --dry-run` (MANDATORY per CLAUDE.md)

#### Phase 2.4: Update Configuration
- [ ] Update `config/trading_config.yaml`:
  ```yaml
  trading:
    mode: mtf  # Keep existing
    active_trading_type: day_trading  # NEW: Explicit type
  ```
- [ ] Ensure backwards compatibility with existing configs

**Deliverables:**
- ✅ `intraday_executor.py` with full implementation
- ✅ Updated `main.py` using factory pattern
- ✅ `tests/integration/test_intraday_executor.py`
- ✅ No regression in backtest results
- ✅ Dry-run passes without errors

---

### **SPRINT 3: Swing Skeleton** (Est: 2 days)
**Goal:** Create SwingExecutor skeleton with TODO markers and tests

#### Phase 3.1: Swing Executor Skeleton (TDD)
- [ ] **RED:** Write skeleton tests (all should be skipped initially)
  - Test: `test_swing_executor_raises_not_implemented()` (should pass)
  - Test: `@pytest.mark.skip test_swing_d1_zone_detection()`
  - Test: `@pytest.mark.skip test_swing_h4_entry_confirmation()`
  - Test: `@pytest.mark.skip test_swing_no_end_of_day_close()`
  
- [ ] **GREEN:** Implement `SwingExecutor` skeleton
  - File: `src/trading_bot/executors/swing_executor.py`
  - All methods raise `NotImplementedError` with helpful messages
  - Include comprehensive TODO comments with implementation hints
  - Implement `get_timeframes()` → {'zone': 'H4', 'entry': 'H1', 'trend': 'D1'}
  - Implement `get_technical_indicators()` → EMA 50/100/200
  
- [ ] **REFACTOR:** Add detailed docstrings explaining swing logic

#### Phase 3.2: Factory Integration
- [ ] Update factory to support `swing_trading` type
- [ ] Add test: `test_factory_creates_swing_executor_skeleton()`
- [ ] Verify it raises NotImplementedError when called

#### Phase 3.3: Configuration
- [ ] Verify `config/trading_types.yaml` has `swing_trading` config
- [ ] Update if needed: SL 50/200 pips, TP 100/400 pips, risk 2%

**Deliverables:**
- ✅ `swing_executor.py` with skeleton + TODOs
- ✅ `tests/unit/executors/test_swing_executor.py` (skipped tests)
- ✅ Factory supports swing type
- ✅ Config validation

---

### **SPRINT 4: Scalping Skeleton** (Est: 2 days)
**Goal:** Create ScalpingExecutor skeleton with TODO markers and tests

#### Phase 4.1: Scalping Executor Skeleton (TDD)
- [ ] **RED:** Write skeleton tests (all should be skipped)
  - Test: `test_scalping_executor_raises_not_implemented()` (should pass)
  - Test: `@pytest.mark.skip test_scalping_m15_zone_detection()`
  - Test: `@pytest.mark.skip test_scalping_m5_entry_confirmation()`
  - Test: `@pytest.mark.skip test_scalping_fast_ema_filter()`
  - Test: `@pytest.mark.skip test_scalping_4hour_auto_close()`
  
- [ ] **GREEN:** Implement `ScalpingExecutor` skeleton
  - File: `src/trading_bot/executors/scalping_executor.py`
  - All methods raise `NotImplementedError`
  - Include CRITICAL notes about scalping differences (spread costs, speed, etc.)
  - Implement `get_timeframes()` → {'zone': 'M15', 'entry': 'M5', 'trend': 'M15'}
  - Implement `get_technical_indicators()` → EMA 8/13, RSI 7, BE 0.3R
  
- [ ] **REFACTOR:** Add implementation warnings about latency requirements

#### Phase 4.2: Factory Integration
- [ ] Update factory to support `scalping` type
- [ ] Add test: `test_factory_creates_scalping_executor_skeleton()`
- [ ] Verify NotImplementedError behavior

#### Phase 4.3: Configuration
- [ ] Verify `config/trading_types.yaml` has `scalping` config
- [ ] Critical check: confluence_threshold 75% (too high, document for future fix)

**Deliverables:**
- ✅ `scalping_executor.py` with skeleton + TODOs + warnings
- ✅ `tests/unit/executors/test_scalping_executor.py` (skipped tests)
- ✅ Factory supports scalping type
- ✅ Config validation + improvement notes

---

### **SPRINT 5: Documentation & Testing** (Est: 2 days)
**Goal:** Complete documentation and comprehensive testing

#### Phase 5.1: Architecture Documentation
- [ ] **Already created:** `docs/architecture/trading-type-architecture.md` ✅
- [ ] Update with final implementation details
- [ ] Add sequence diagrams for each executor type

#### Phase 5.2: Migration Guide
- [ ] Create: `docs/guides/trading-type-migration-guide.md`
  - How to switch between trading types
  - Configuration changes needed
  - What to expect from each mode
  - Troubleshooting guide
  
#### Phase 5.3: Implementation TODOs
- [ ] Create: `docs/todos/swing-implementation-todos.md`
  - Detailed checklist for swing implementation
  - Technical requirements per CLAUDE.md
  - Test coverage requirements
  
- [ ] Create: `docs/todos/scalping-implementation-todos.md`
  - Detailed checklist for scalping implementation
  - Performance considerations
  - Spread cost analysis requirements

#### Phase 5.4: Comprehensive Testing
- [ ] **Unit Tests:**
  - `uv run pytest tests/unit/executors/ -v --cov=src/trading_bot/executors --cov-fail-under=100`
  
- [ ] **Integration Tests:**
  - Test intraday executor with real historical data
  - Test factory pattern with all types
  - Test main bot orchestration
  
- [ ] **Property Tests (Hypothesis):**
  - Property: All executors must return same interface types
  - Property: Risk parameters must be within valid ranges
  - `uv run pytest tests/properties/test_executor_properties.py --hypothesis-show-statistics`
  
- [ ] **Performance Tests:**
  - Intraday loop execution time < 55 seconds (per CLAUDE.md)
  - Zone caching effectiveness
  - Memory usage under load

#### Phase 5.5: Code Quality Validation
- [ ] Run formatter: `uv run black src/trading_bot/executors/ tests/unit/executors/`
- [ ] Run linter: `uv run ruff check src/trading_bot/executors/ tests/unit/executors/ --fix`
- [ ] Run type checker: `uv run mypy src/trading_bot/executors/`
- [ ] Final validation: `uv run trading-bot start --dry-run`

#### Phase 5.6: Update Master Documentation
- [ ] Update `CLAUDE.md` with executor architecture
- [ ] Update `README.md` with trading type switching instructions
- [ ] Update `docs/cli-reference.md` with new commands

**Deliverables:**
- ✅ Complete architecture documentation
- ✅ Migration guide for switching types
- ✅ TODO documents for future sprints
- ✅ 100% test coverage for executors
- ✅ All quality checks passing
- ✅ Dry-run validation successful

---

## 📊 Testing Strategy (Per CLAUDE.md)

### Coverage Requirements
```yaml
Overall Coverage: 85% minimum
Executor Components: 100% (new feature requirement)
Critical Paths: 100% (TDD requirement)
Integration Tests: All trading loops tested
Property Tests: Interface contracts validated
```

### Test Organization
```
tests/
├── unit/
│   └── executors/
│       ├── test_base_executor.py          # Abstract base tests
│       ├── test_factory.py                # Factory pattern tests
│       ├── test_intraday_executor.py      # Intraday logic tests
│       ├── test_swing_executor.py         # Swing skeleton tests
│       └── test_scalping_executor.py      # Scalping skeleton tests
├── integration/
│   ├── test_intraday_mtf_workflow.py      # E2E intraday flow
│   ├── test_executor_factory_integration.py
│   └── test_main_bot_orchestration.py
└── properties/
    └── test_executor_properties.py        # Hypothesis property tests
```

### Mandatory Pre-Commit Checks
```bash
# 1. All tests pass
uv run pytest tests/ --cov=src/trading_bot --cov-fail-under=85

# 2. Critical component coverage
uv run pytest tests/unit/executors/ --cov=src/trading_bot/executors --cov-fail-under=100

# 3. Code quality
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/trading_bot/

# 4. MANDATORY: Dry-run validation
uv run trading-bot start --dry-run

# 5. Property tests
uv run pytest tests/properties/ --hypothesis-show-statistics
```

---

## 🔧 Implementation Guidelines (From CLAUDE.md)

### Code Standards
- ✅ **Type hints:** All functions must have type annotations
- ✅ **Async-first:** All I/O operations must be async
- ✅ **No hardcoded values:** Use YAML configuration
- ✅ **Docstrings:** Google-style docstrings for all public methods
- ✅ **Single Responsibility:** Each class/method does one thing
- ✅ **Dependency Injection:** For testability

### File Naming Conventions
```
src/trading_bot/executors/
├── __init__.py                 # Export public interfaces
├── base_executor.py            # Abstract base (lowercase, underscore)
├── factory.py                  # Factory pattern
├── intraday_executor.py        # Concrete intraday
├── swing_executor.py           # Skeleton swing
└── scalping_executor.py        # Skeleton scalping
```

### Import Organization
```python
# Standard library
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

# Third-party
import pandas as pd

# Local application
from trading_bot.strategies.foundation.foundation_engine import FoundationEngine
from trading_bot.position.position_manager import PositionManager
from trading_bot.utils.logger import get_logger
```

---

## 🎯 Success Metrics

### Sprint 1 (Architecture)
- [ ] Base executor tests: 100% coverage
- [ ] Factory tests: 100% coverage
- [ ] No regression in existing tests

### Sprint 2 (Intraday)
- [ ] Intraday executor: 100% coverage
- [ ] Backtest results match pre-refactoring
- [ ] Dry-run passes
- [ ] Performance: Trading loop < 55s

### Sprint 3 (Swing Skeleton)
- [ ] Swing executor skeleton complete
- [ ] All methods documented with TODOs
- [ ] Factory creates swing executor

### Sprint 4 (Scalping Skeleton)
- [ ] Scalping executor skeleton complete
- [ ] Performance requirements documented
- [ ] Factory creates scalping executor

### Sprint 5 (Documentation)
- [ ] Architecture docs complete
- [ ] Migration guide ready
- [ ] TODO lists for future sprints
- [ ] All tests passing (85%+ coverage)

---

## 🚨 Critical Notes

### From CLAUDE.md
1. **TDD MANDATORY:** Write failing tests first, then implementation
2. **No Regression:** Existing backtest results must not change
3. **Dry-run Required:** Must pass before any commit
4. **100% Coverage:** New features require 100% test coverage
5. **Async-First:** All I/O must be async
6. **Type Hints:** mypy validation required

### Known Constraints
1. **Scalping Threshold:** `confluence_threshold: 75%` is too high (document for future fix)
2. **H1 Trend Gate:** Only applies to commodities (keep for intraday, remove for swing/scalping)
3. **Pip Values:** Asset-specific pip values critical for position sizing
4. **MT5 Dependency:** Windows 10/11 required

---

## 📅 Timeline Estimate

| Sprint | Duration | Dependencies |
|--------|----------|--------------|
| Sprint 1: Architecture | 3 days | None |
| Sprint 2: Intraday | 4 days | Sprint 1 complete |
| Sprint 3: Swing Skeleton | 2 days | Sprint 2 complete |
| Sprint 4: Scalping Skeleton | 2 days | Sprint 3 complete |
| Sprint 5: Docs & Testing | 2 days | All sprints complete |
| **TOTAL** | **13 days** | **~2.5 weeks** |

**Note:** Future implementation of swing and scalping executors will be separate sprints (estimated 5-7 days each).

---

## 🔄 Next Steps

1. **Review this plan** with stakeholders
2. **Start Sprint 1** with base executor TDD
3. **Daily stand-ups** to track progress
4. **Continuous validation** with dry-run after each phase
5. **Documentation updates** as we learn

---

## ✅ Definition of Done

**This refactoring is complete when:**
- ✅ All 5 sprints delivered
- ✅ Intraday executor works identically to current system
- ✅ Swing and scalping skeletons ready for future implementation
- ✅ 100% test coverage for executor components
- ✅ All quality checks passing
- ✅ Dry-run validation successful
- ✅ Documentation complete and accurate
- ✅ Can switch trading types via config change only
- ✅ No code changes needed to add new trading types

---

**Last Updated:** 2026-01-21  
**Next Review:** After Sprint 1 completion
