# Refactor main.py — Task Breakdown

Sequenced so each task is a discrete unit of work. Phase 3 must land
before Phase 4 (Phase 4 depends on Phase 3's pattern being established).

## Phase 3 — PositionOrchestrator

### Pre-flight audit (~15 min)

- [ ] Grep tests for direct bot method references that will move:
      `grep -rn "_manage_positions\|_check_position_automation\|_handle_breakeven_automation\|_handle_trailing_automation\|_handle_partial_close_automation\|_check_position_closure\|_finalize_closed_position\|_resolve_mt5_deal_details" tests/`
- [ ] List affected test files in a scratch note; patch order matters.
- [ ] Snapshot current behaviour: run `uv run trading-bot --config test start`
      for ~5 min, save log to `/tmp/refactor_before.log` for later diff.
- [ ] Confirm `git status` is clean (no in-flight work).

### Implementation (~60-90 min)

- [ ] Create `src/trading_bot/services/position_orchestrator.py`.
- [ ] Skeleton class:
      ```python
      class PositionOrchestrator:
          def __init__(self, bot: "TradingBot"):
              self.bot = bot
      ```
- [ ] Move methods listed in design.md "Methods moved" table.
      Replace every `self.<dep>` with `self.bot.<dep>` for state
      access. Internal helpers (those prefixed `_`) stay private.
- [ ] Move the class-level `_SILENT_MT5_ERROR_CODES` constant if any
      method needs it (it lives on ExecutionService already, so likely
      a re-export or import).
- [ ] Update `TradingBot._initialize_position_risk_system`:
      ```python
      self.position_orchestrator = PositionOrchestrator(self)
      ```
      after all dependency managers are constructed.
- [ ] Delete the moved method definitions from `main.py` (use the
      python line-range delete pattern Phase 2 used).
- [ ] Update the two call sites in `TradingBot._trading_loop`:
      ```python
      await self.position_orchestrator.manage_positions()
      ```
- [ ] Update `services/__init__.py` to export `PositionOrchestrator`.

### Verification (~15 min)

- [ ] `uv run pytest tests/unit/ --no-cov -q` → all green.
- [ ] `uv run pytest tests/integration/ --no-cov -q` → all green
      (skip the pre-existing `test_sync_position_no_ticket_symbol_exists_in_mt5`
      and `test_data_manager_integration` flakes).
- [ ] `uv run pytest --cov` → coverage targets met
      (overall ≥85%, position/ 100%, risk/ ≥95%).
- [ ] `uv run trading-bot --config test start` for ~5 min, save log
      to `/tmp/refactor_after_phase3.log`; diff against
      `/tmp/refactor_before.log` — only timestamps should differ.
- [ ] `wc -l src/trading_bot/main.py` → expect ~1300-1500 lines.

### Commit

- [ ] Single commit, message format:
      ```
      refactor: extract PositionOrchestrator from TradingBot (Phase 3)
      ```
      Body includes method list, before/after line counts, "All tests
      pass" note.

## Phase 4 — AnalysisService

### Pre-flight audit (~10 min)

- [ ] Grep tests for direct bot method references:
      `grep -rn "_analyze_symbol\|_run_strategy_analysis\|_run_mtf_analysis\|_fetch_mtf_data\|_run_single_tf_analysis" tests/`
- [ ] Snapshot behaviour again (Phase 3 already landed, fresh baseline).

### Implementation (~30-45 min)

- [ ] Create `src/trading_bot/services/analysis_service.py`.
- [ ] Skeleton class with `__init__(self, bot)`.
- [ ] Move 5 methods listed in design.md.
- [ ] Inside `analyze_symbol`, replace
      `await self._execute_signal(signal)` with
      `await self.bot.execution_service.execute_signal(signal)` (already
      done in Phase 2 — confirm it's still right after the move).
- [ ] Update `TradingBot._initialize_position_risk_system` to add:
      ```python
      self.analysis_service = AnalysisService(self)
      ```
- [ ] Delete the moved method definitions from `main.py`.
- [ ] Update call site in `TradingBot._trading_loop`:
      ```python
      await self.analysis_service.analyze_symbol(symbol)
      ```
- [ ] Update `services/__init__.py` to export `AnalysisService`.

### Verification (~15 min)

- [ ] Full unit + integration suite → green.
- [ ] Coverage targets unchanged.
- [ ] Dry-run smoke test (~5 min) → log diff shows behaviour parity.
- [ ] `wc -l src/trading_bot/main.py` → expect ≤1200 lines.

### Commit

- [ ] Single commit:
      ```
      refactor: extract AnalysisService from TradingBot (Phase 4)
      ```

## Post-refactor cleanup

- [ ] Move this spec to `specs/archive/2026-XX/` once both phases land.
- [ ] Update `refactor-codebase.md` in the archive: mark Phase 3 and
      Phase 4 as ✅ Done (or just leave the deferred note, since
      they're now in this dedicated spec).

## Tests-to-watch list

These are the tests historically broken by similar refactors. Watch
them closely:

- `tests/integration/test_position_sync.py` — patches bot methods
- `tests/unit/test_main.py` — bot-level tests
- `tests/unit/position/test_position_manager.py` — position lifecycle
- `tests/unit/strategies/foundation/test_foundation_engine.py` —
  signal generation
- `tests/unit/connectors/test_dry_run_wrapper.py` — dry-run path

## Effort estimate

- Phase 3: 1.5-2 hours (audit + impl + verify + commit)
- Phase 4: 1 hour
- Total: ~2.5-3 hours focused work

Do NOT split across multiple sessions — async behaviour bugs are
hardest to spot when context is fresh; partial work risks introducing
inconsistent state.
