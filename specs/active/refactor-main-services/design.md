# Refactor main.py — Design

## Architecture after refactor

```
TradingBot (~1000-1200 lines, orchestrator only)
├── execution_service        : ExecutionService          (already exists)
├── position_orchestrator    : PositionOrchestrator      (NEW — Phase 3)
├── analysis_service         : AnalysisService           (NEW — Phase 4)
├── notification_manager
├── position_manager / breakeven_manager / trailing_manager / partial_manager
├── portfolio_risk / exposure_manager / drawdown_protector
├── foundation_engine / signal_aggregator / strategy_manager / mtf_analyzer
├── session_repository / config_repository / current_session
├── account_sync_service / account_selector / current_account
├── mt5 / data_manager / symbol_mapper
└── Lifecycle: start(), stop(), _trading_loop(), _heartbeat_loop()
```

Each service class follows the **back-reference pattern** established by
`ExecutionService`:

```python
class PositionOrchestrator:
    def __init__(self, bot: "TradingBot"):
        self.bot = bot

    async def manage_positions(self):
        # was self._manage_positions(), now reads via self.bot.<dep>
        ...
```

## Phase 3 — PositionOrchestrator

### Target file: `packages/worker/src/trading_worker/services/position_orchestrator.py`

### Methods moved from `TradingBot`:

| Method (old name) | New name | Notes |
|---|---|---|
| `_manage_positions` | `manage_positions` | Main reconciliation loop with MT5 |
| `_check_position_automation` | `check_position_automation` | Dispatcher (BE/trailing/partial) |
| `_handle_breakeven_automation` | `handle_breakeven_automation` | |
| `_handle_trailing_automation` | `handle_trailing_automation` | |
| `_activate_trailing_if_needed` | `_activate_trailing_if_needed` | Internal helper |
| `_notify_trailing_update` | `_notify_trailing_update` | Internal helper |
| `_handle_partial_close_automation` | `handle_partial_close_automation` | |
| `_check_position_closure` | `check_position_closure` | Price-based SL/TP check |
| `_resolve_mt5_ticket` | `_resolve_mt5_ticket` | Internal helper |
| `_cache_ticket` | `_cache_ticket` | Internal helper |
| `_automation_preflight_passed` | `_automation_preflight_passed` | Internal helper |
| `_update_position_and_run_automation` | `_update_position_and_run_automation` | Internal helper |
| `_close_if_missing_from_mt5` | `_close_if_missing_from_mt5` | Internal helper |
| `_sync_mt5_only_positions_to_db` | `_sync_mt5_only_positions_to_db` | Internal helper |
| `_build_position_from_mt5` | `_build_position_from_mt5` | Internal helper |
| `_resolve_mt5_deal_details` | `_resolve_mt5_deal_details` | Internal helper |
| `_estimate_close_pnl` | `_estimate_close_pnl` | Internal helper |
| `_finalize_closed_position` | `_finalize_closed_position` | Internal helper |
| `_update_session_on_position_close` | `_update_session_on_position_close` | Internal helper |

### Stays on `TradingBot`:

- `_get_current_price` — also used by `AnalysisService` (next phase),
  so it stays on the bot as a shared helper.
- `_broker_to_universal_symbol`, `_convert_to_broker_symbol`,
  `_convert_to_broker_symbol_safe` — symbol conversion utilities used
  across multiple services.
- `_get_asset_class` — already a thin wrapper, used by everyone.
- `_sync_balance_from_mt5` — bot-level balance state.
- `_is_market_open`, `_generate_mock_data` — bot-level utilities.

### Call site in `TradingBot._trading_loop`:

```python
# Before
await self._manage_positions()

# After
await self.position_orchestrator.manage_positions()
```

### Initialisation:

`_initialize_position_risk_system` already initialises the existing
managers and `ExecutionService`. Append:

```python
self.position_orchestrator = PositionOrchestrator(self)
```

after all dependencies (position_manager, breakeven_manager,
trailing_manager, partial_manager, mt5, notification_manager,
exposure_manager, portfolio_risk, current_session) are set.

## Phase 4 — AnalysisService

### Target file: `packages/worker/src/trading_worker/services/analysis_service.py`

### Methods moved from `TradingBot`:

| Method (old name) | New name | Notes |
|---|---|---|
| `_analyze_symbol` | `analyze_symbol` | Main entry point per symbol |
| `_run_strategy_analysis` | `_run_strategy_analysis` | Internal helper |
| `_run_mtf_analysis` | `_run_mtf_analysis` | Internal helper |
| `_fetch_mtf_data` | `_fetch_mtf_data` | Internal helper |
| `_run_single_tf_analysis` | `_run_single_tf_analysis` | Internal helper |

### Stays on `TradingBot`:

- Same shared utilities as Phase 3 (price, asset class, symbol conv).
- `mtf_mode`, `zone_timeframe`, `entry_timeframe` config flags stay on
  bot for now (single source of truth).

### Call site in `TradingBot._trading_loop`:

```python
# Before
await self._analyze_symbol(symbol)

# After
await self.analysis_service.analyze_symbol(symbol)
```

### Dependency notes

`AnalysisService` calls `self.bot.execution_service.execute_signal(signal)`
to actually act on detected signals — the analysis service detects, the
execution service executes. This composition is intentional: each
service owns its lane.

## Service file layout (post-monorepo)

```
packages/worker/src/trading_worker/services/
├── __init__.py
├── execution_service.py        (existing, Phase 2 — moved by monorepo step)
├── position_orchestrator.py    (NEW, Phase 3)
└── analysis_service.py         (NEW, Phase 4)
```

`services/__init__.py` exports all three classes.

## Test impact

Existing tests reference `TradingBot._method` directly in some integration
tests (e.g., `tests/integration/test_position_sync.py` mocks
`bot.position_manager.close_position`, not bot methods directly). Phase 2
showed the bot back-reference pattern keeps tests working without changes.

Audit step in tasks.md greps for any test that calls
`bot._manage_positions`, `bot._check_position_automation`, or
`bot._analyze_symbol` directly so we patch fixtures before extraction.

## Rollback plan

Each phase ships as one commit. To revert a phase entirely:

```bash
git revert <commit>
```

State after revert is identical to pre-phase state (no migrations, no
data writes that survive revert).

## What "done" looks like

After both phases:

- `main.py` ≤ 1200 lines, mostly lifecycle + init methods.
- `services/` has 3 files (execution, position_orchestrator, analysis).
- `pytest tests/unit/` passes 1534+ tests unchanged.
- `uv run trading-bot --config test start` reaches the trading loop
  cleanly (mock MT5 mode).
- One live dry-run session (~30 min) shows the same signal/position
  log pattern as before the refactor.
