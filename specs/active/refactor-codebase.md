# Codebase Refactoring Plan

**Status**: Planned
**Priority**: 🟠 Medium (works but unmaintainable)
**Estimated Effort**: 5-7 days
**Date**: 2026-05-24

Comprehensive refactoring plan based on [code-review-2026-05.md](code-review-2026-05.md).

## Overview

Refactoring targets organized by module. Goals:
1. Split god classes/methods (SRP)
2. Eliminate dead code
3. Fix naming conflicts
4. Reorganize misplaced files
5. Complete `__init__.py` exports

## Quick Wins (Already Applied During Review)

- ✅ Removed `src/trading_bot/core/` (dead empty directory)
- ✅ Added 5 models to `data/__init__.py`
- ✅ Added 6 Strategy exceptions to `exceptions/__init__.py`
- ✅ Fixed test_commodities_pip_size (XAGUSD pip = 0.01)

---

## 🔴 Critical Refactors

### Refactor 1: main.py (2870 lines)

**Target**: `src/trading_bot/main.py`
**Effort**: 2-3 days
**Risk**: High (core orchestrator)

#### Methods to Extract

| Method | Lines | Range |
|--------|-------|-------|
| `_execute_signal` | 482 | 611-1093 |
| `_manage_positions` | 508 | 1380-1888 |
| `_check_position_automation` | 462 | 1953-2415 |
| `_analyze_symbol` | 136 | 2734-2870 |
| `_initialize_session_management` | 126 | 375-501 |

#### Proposed Architecture

```
TradingBot (orchestrator, ~500 lines)
├── ExecutionService          → _execute_signal logic
├── PositionOrchestrator      → _manage_positions, _check_position_automation
├── AnalysisService           → _analyze_symbol
├── SessionManager            → _initialize_session_management
└── SymbolResolver (utils)    → _get_asset_class, _convert_broker_to_internal_symbol
```

#### Phases

**Phase 1: Extract Utilities (Low Risk)**
- [ ] `_get_asset_class()` → `utils/symbol_resolver.py`
- [ ] `_convert_broker_to_internal_symbol()` → `utils/symbol_resolver.py`
- [ ] `_is_market_open()` → `utils/market_hours.py`
- [ ] `_generate_mock_data()` → `utils/mock_data.py`

**Phase 2: Extract ExecutionService**
- [ ] Create `src/trading_bot/services/execution_service.py`
- [ ] Move: `_execute_signal`, `_validate_signal_risk`, `_check_exposure_limits`, `_calculate_position_size`

**Phase 3: Extract PositionOrchestrator**
- [ ] Create `src/trading_bot/services/position_orchestrator.py`
- [ ] Move: `_manage_positions`, `_check_position_automation`, `_check_position_closure`, `_get_current_price`

**Phase 4: Extract AnalysisService**
- [ ] Create `src/trading_bot/services/analysis_service.py`
- [ ] Move: `_analyze_symbol`

**Acceptance**: main.py < 800 lines, all tests pass.

---

### Refactor 2: foundation_engine.py (1363 lines)

**Target**: `src/trading_bot/strategies/foundation/foundation_engine.py`
**Effort**: 1-2 days
**Risk**: High (core strategy logic)

#### Problem

`_create_signal_from_zone` is ~1000 lines (line 354 → 1363) - 1 method orchestrating all 7 enhancement layers.

#### Proposed Split

```python
class FoundationEngine:
    async def _create_signal_from_zone(self, ...):
        # Orchestrator (max 50 lines)
        zone_info = self._evaluate_zone(...)
        scores = await self._run_enhancement_layers(...)
        confluence = self._calculate_confluence(...)
        sl_tp = self._calculate_sl_tp(...)
        return self._build_signal(...)

    def _evaluate_zone(...) -> ZoneInfo | None
    async def _run_enhancement_layers(...) -> dict
    def _calculate_confluence(...) -> ConfluenceResult
    def _calculate_sl_tp(...) -> dict
    def _build_signal(...) -> StrategyResult
```

#### Tasks

- [ ] Write TDD tests for each helper
- [ ] Extract `_evaluate_zone()`
- [ ] Extract `_run_enhancement_layers()` (parallel execution)
- [ ] Extract `_calculate_confluence()` (weighted scoring)
- [ ] Extract `_calculate_sl_tp()` (SL/TP logic)
- [ ] Extract `_build_signal()` (assembly)

**Acceptance**: No method >100 lines, foundation_engine.py <500 lines.

---

### Refactor 3: price_action_analyzer.py (489 lines)

**Target**: `src/trading_bot/strategies/enhancement/price_action_analyzer.py`
**Effort**: 1 day
**Risk**: Medium

#### Problem

Single method `analyze_pattern` is ~440 lines - violates SRP same as foundation_engine.

#### Proposed Split

```python
class PriceActionAnalyzer:
    async def analyze_pattern(...) -> PriceActionSignal:
        engulfing = self._detect_engulfing(...)
        pin_bar = self._detect_pin_bar(...)
        inside_bar = self._detect_inside_bar(...)
        doji = self._detect_doji(...)
        flag = self._detect_flag(...)
        return self._aggregate_patterns([engulfing, pin_bar, inside_bar, doji, flag])

    def _detect_engulfing(...) -> PatternResult
    def _detect_pin_bar(...) -> PatternResult
    def _detect_inside_bar(...) -> PatternResult
    def _detect_doji(...) -> PatternResult
    def _detect_flag(...) -> PatternResult
    def _aggregate_patterns(...) -> PriceActionSignal
```

#### Tasks

- [ ] Identify pattern detection logic boundaries
- [ ] Extract one pattern detector at a time (TDD)
- [ ] Aggregate results in main method

**Acceptance**: No method >80 lines, total ≤300 lines.

---

### Refactor 4: position_manager.py (872 lines)

**Target**: `src/trading_bot/position/position_manager.py`
**Effort**: 1 day
**Risk**: Medium

#### Problem

Two large methods:
- `load_positions_from_db` (211 lines)
- `save_position` (172 lines)

#### Tasks

- [ ] Extract DB row-to-Position conversion helper
- [ ] Extract Position validation logic
- [ ] Extract breakeven/trailing restoration into helper
- [ ] Add tests for restoration (lines 268-277)
- [ ] Add tests for metadata fallback (lines 311-312)
- [ ] Verify 100% coverage

**Acceptance**: All methods <100 lines, position/ 100% coverage.

---

## 🟠 Medium Refactors

### Refactor 5: Connectors Cleanup

**Target**: `src/trading_bot/connectors/`
**Effort**: 0.5 day
**Risk**: Low

#### Issues

1. **Filename conflict** - Two `position_manager.py`:
   - `position/position_manager.py` (lifecycle)
   - `connectors/position_manager.py` (MT5 queries)
2. **`dry_run_wrapper.py`** - Dead code (211 lines)
3. **`modify_position`** in mt5_connector (172 lines)

#### Tasks

- [ ] Rename `connectors/position_manager.py` → `connectors/mt5_position_query.py`
- [ ] Update imports throughout codebase
- [ ] Decision needed: implement or remove `dry_run_wrapper.py`
- [ ] Optional: split `modify_position` into smaller methods

---

### Refactor 6: Misplaced Files

**Target**: `src/trading_bot/strategies/`
**Effort**: 0.5 day
**Risk**: Low

#### Issues

1. `strategies/signal_validator_enhanced.py` (323 lines) - Should be in `strategies/enhancement/` or `strategies/validation/`
2. `strategies/mtf_analyzer.py` (308 lines) - Could be in own subfolder

#### Tasks

- [ ] Move `signal_validator_enhanced.py` to appropriate folder
- [ ] Decide if `mtf_analyzer.py` needs subfolder
- [ ] Update all imports

---

### Refactor 7: Module Decisions (Unused Code)

**Effort**: 1 day
**Risk**: Low

#### Code Without Integration

| Code | Lines | Status | Decision Needed |
|------|-------|--------|-----------------|
| `analytics/performance_analyzer.py` | 690 | Has tests, not integrated | Integrate / Remove / Document |
| `risk/risk_manager_conservative.py` | 325 | Has tests, not integrated | Integrate / Remove / Document |
| `connectors/dry_run_wrapper.py` | 211 | No tests, not integrated | Implement / Remove |

#### Tasks

- [ ] User decision per module
- [ ] Execute decision (integrate/remove/document)
- [ ] Update [docs-cli-gap-fix.md](docs-cli-gap-fix.md) accordingly

---

## 🟡 Minor Refactors

### Refactor 8: Exports Cleanup

**Status**:
- ✅ `data/__init__.py` (DONE)
- ✅ `exceptions/__init__.py` (DONE)
- ⏳ `utils/__init__.py` (TODO)

#### Tasks

- [ ] Add to `utils/__init__.py`:
  - `notification_manager.NotificationManager, NotificationLevel`
  - `timeframe_manager.TimeframeManager`
  - `config_hasher.ConfigHasher` (if applicable)

---

### Refactor 9: data/models.py Split (Optional)

**Target**: `src/trading_bot/data/models.py` (694 lines)
**Effort**: 0.5 day
**Risk**: Low

#### Decision Required

Currently 5 models in 1 file. Options:
- **A.** Keep as-is (common SQLAlchemy pattern, easy circular import avoidance)
- **B.** Split per model in `data/models/` subfolder

**Recommendation**: Keep as-is unless growing further.

---

### Refactor 10: Code Smell Cleanup

#### Tasks

- [ ] Remove `confluence_weights` duplicate keys (`market_structure` alias of `structure`)
- [ ] Remove outdated comments referencing "Week 15.5.x" phases
- [ ] Update module docstrings to current state

---

## Execution Order

### Sprint 1: Quick Wins (1 day)
1. Refactor 6: Move misplaced files
2. Refactor 7: User decisions on unused code
3. Refactor 5: Rename connectors/position_manager.py
4. Refactor 8: utils/__init__.py exports
5. Refactor 10: Code smell cleanup

### Sprint 2: Medium Refactor (2 days)
1. Refactor 4: position_manager.py methods (also fills coverage gap)
2. Refactor 3: price_action_analyzer.py method
3. Refactor 5 (optional): mt5_connector.modify_position

### Sprint 3: Heavy Refactor (3-4 days)
1. Refactor 2: foundation_engine god method
2. Refactor 1: main.py god class (4 phases)

---

## Acceptance Criteria (All Refactors)

- [ ] All tests pass (1548+ unit, 8+ integration)
- [ ] Coverage maintained ≥92% (target 100% for position/, risk/)
- [ ] No method >150 lines (ideal <100)
- [ ] No single file >1000 lines (ideal <500 for non-models)
- [ ] No dead code (all modules integrated or removed)
- [ ] No misleading docs (in sync with implementation)
- [ ] Dry-run mode passes after each refactor phase

---

## Risk & Mitigation

### Risks

- Breaking integration tests
- Changing async behavior subtly
- Edge cases missed in extraction
- Production user expectations (live trading)

### Mitigation

- TDD: write tests for extracted services first
- Each phase is separate commit (easy rollback)
- Branch protection on main
- Dry-run validation after each phase
- Code review before merge

---

## Summary Table

| # | Refactor | File | Lines | Priority | Effort |
|---|----------|------|-------|----------|--------|
| 1 | main.py | main.py | 2870 | 🔴 Critical | 2-3 days |
| 2 | foundation_engine | strategies/foundation/foundation_engine.py | 1363 | 🔴 Critical | 1-2 days |
| 3 | price_action | strategies/enhancement/price_action_analyzer.py | 489 | 🔴 Critical | 1 day |
| 4 | position_manager | position/position_manager.py | 872 | 🔴 Critical | 1 day |
| 5 | connectors cleanup | connectors/ | - | 🟠 Medium | 0.5 day |
| 6 | misplaced files | strategies/ | - | 🟠 Medium | 0.5 day |
| 7 | unused code | analytics/, risk/, connectors/ | 1226 | 🟠 Medium | 1 day |
| 8 | utils exports | utils/__init__.py | - | 🟡 Minor | 0.1 day |
| 9 | models split | data/models.py | 694 | 🟡 Optional | 0.5 day |
| 10 | code smell | - | - | 🟡 Minor | 0.5 day |

**Total**: ~10-12 days of refactoring work.

---

## Related

- [code-review-2026-05.md](code-review-2026-05.md) - Source review findings
- [docs-cli-gap-fix.md](docs-cli-gap-fix.md) - Docs fix (do this first)
