# Refactor main.py into Position & Analysis Services — Requirements

**Status**: 📋 Planned
**Priority**: 🟢 Low (cosmetic — no behavior change)
**Date**: 2026-05-27
**Predecessors**: Phase 1 (utilities) ✅, Phase 2 (ExecutionService) ✅ commit `9a98285`

## Context

`main.py` is currently 2123 lines after Phase 2's ExecutionService extraction.
Every method is small (<100 lines) and SRP-compliant after Sprint 4, but the
file still acts as the catch-all for position management and signal analysis
on top of pure orchestration. Two more service extractions (Phase 3 & 4)
would bring main.py to ~1000-1200 lines — purely an orchestrator.

This is **deferred work** done only after the live observation phase
stabilises. There is **no functional change** — this is purely an
organisation refactor.

## Goals

1. Split position-lifecycle code out of `TradingBot` into a
   `PositionOrchestrator` service.
2. Split signal-analysis code out of `TradingBot` into an
   `AnalysisService`.
3. Keep `TradingBot` as the lifecycle/orchestration coordinator: setup,
   loops, service wiring, shutdown.
4. Zero behavior change — every code path, log line, notification, and
   DB write produces the same output as before the refactor.

## Non-goals

- No new features, no bug fixes (separate from refactor).
- No change to strategy logic, risk math, or close_reason resolution.
- No restructure of the existing `services/execution_service.py`
  (Phase 2 result stays as is).
- No change to public CLI commands or test fixtures.

## Success criteria

- `main.py` ≤ 1200 lines.
- `PositionOrchestrator` and `AnalysisService` each ≤ 800 lines.
- All 1534+ unit tests pass without modification (or only mechanical
  patches like fixture imports).
- Dry-run smoke test passes: `uv run trading-bot --config test start`
  reaches the trading loop without errors.
- No regression in coverage targets (position/ 100%, risk/ 95%, total
  ≥ 85%).
- Each phase shipped as a single commit so a single revert undoes the
  whole phase.

## Constraints

- Bot is in **live observation phase** after strategy tuning round 1.
  Refactor must not introduce subtle regressions in:
  - close_reason resolution
  - slippage tracking
  - session_id attribution
  - per-symbol BE/trailing
  - per-asset confluence thresholds
  - cent-account currency labels
- Phases must be runnable in isolation — Phase 3 lands first, then
  Phase 4 (so failure in one doesn't block the other).
- Service objects hold a back-reference to `TradingBot` (same pattern
  as `ExecutionService`) to avoid threading every dependency through
  constructors.

## Risk register

| Risk | Mitigation |
|---|---|
| Async behaviour subtly changes when methods move across class boundaries | Run full integration test suite + manual dry-run + side-by-side log diff for one trading session |
| Test mocks reference `TradingBot._method_name` directly | Grep tests for `_manage_positions`, `_check_position_automation`, `_analyze_symbol` before extraction; patch fixtures pre-emptively |
| Lost state when methods stop sharing `self` accidentally | Bot back-reference (`self.bot.<state>`) keeps everything reachable; pattern proven in Phase 2 |
| Pre-commit hook stash-and-restore drops unstaged work mid-refactor | Stage in small chunks, commit per logical group; verify `git log` between each |
| Long-running bot session crashes during the refactor commit | Defer the refactor commit to a planned restart window |

## Open questions

- Should `_get_asset_class`, `_convert_to_broker_symbol_safe`, and
  `_sync_balance_from_mt5` stay on `TradingBot` (shared utilities) or
  move to the service that uses them most? → Decision in design.md.
- Where does `_get_current_price` go? It's called by both Position and
  Analysis paths. → Decision in design.md.

## Related

- [code-review-2026-05.md](../../archive/2026-05/code-review-2026-05.md) — original audit
- [refactor-codebase.md](../../archive/2026-05/refactor-codebase.md) — parent refactor plan
- Phase 2 commit: `9a98285` (ExecutionService extraction)
