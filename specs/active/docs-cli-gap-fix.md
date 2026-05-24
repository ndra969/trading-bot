# Docs Reality Gap Fix

**Status**: Planned
**Priority**: 🔴 High (docs mislead users)
**Estimated Effort**: 1-2 hours
**Date**: 2026-05-24

Fix documentation that references features/commands that don't exist.

## Issues Found

### A. CLI Commands Gap (67 documented vs 9 actual)
### B. Trading Types Gap (4 documented vs 1 implemented)
### C. Dry-Run Wrapper Gap (documented but not integrated)
### D. ConservativeRiskManager (implemented but undocumented)
### E. PerformanceAnalyzer (implemented but undocumented)

---

## Issue A: CLI Commands Gap

## Problem

Docs reference **67 CLI commands**, but only **9 actually work**:

**Actual commands** (`uv run trading-bot --help`):
- `account info`
- `claude` / `rules`
- `config show` / `config validate`
- `mt5 connect` / `mt5 disconnect` / `mt5 status`
- `start` / `stop` / `status`
- `version`

**Documented but missing** (58 commands):
- `account list/switch/sync`
- `analytics correlation/performance/risk`
- `broker convert/discover/status/switch`
- `config backup/diff/list/restore/rollback/set`
- `db backup/restore/stats`
- `foundation analyze/price/zones`
- `health`, `info`, `init`
- `market hours/list/next/status`
- `notifications enable/status/test`
- `performance`
- `positions active/close/partial-close`
- `postgresql migrate/status/reset`
- `risk status`
- `symbol info`
- `technical analyze`
- `type switch/status/compare`
- `backtest`

## Solution

### Phase 1: Update Docs to Match Reality

Mark non-existent commands clearly in docs:

```markdown
| Command | Status |
|---------|--------|
| `account info` | ✅ Available |
| `account list` | ⏳ Planned (not implemented) |
| `account switch` | ⏳ Planned (not implemented) |
```

### Files to Update

- [ ] [cli-reference.md](../../docs/guides/cli-reference.md) - Main CLI reference
- [ ] [setup/broker-symbol-mapping-guide.md](../../docs/setup/broker-symbol-mapping-guide.md) - broker commands
- [ ] [setup/market-hours-guide.md](../../docs/setup/market-hours-guide.md) - market commands
- [ ] [setup/asset-configuration-guide.md](../../docs/setup/asset-configuration-guide.md) - symbol info
- [ ] [trading/risk-management-guide.md](../../docs/trading/risk-management-guide.md) - risk commands
- [ ] [trading/notifications-guide.md](../../docs/trading/notifications-guide.md) - notifications commands
- [ ] [trading/trading-types-guide.md](../../docs/trading/trading-types-guide.md) - type commands
- [ ] [trading/technical-indicators-guide.md](../../docs/trading/technical-indicators-guide.md) - technical commands
- [ ] [guides/multi-account-guide.md](../../docs/guides/multi-account-guide.md) - account commands
- [ ] [guides/strategy-guide.md](../../docs/guides/strategy-guide.md) - foundation commands
- [ ] [guides/multi-timeframe-guide.md](../../docs/guides/multi-timeframe-guide.md) - foundation commands
- [ ] [.claude/commands/analyze.md](../../.claude/commands/analyze.md) - foundation analyze
- [ ] [.claude/commands/backtest.md](../../.claude/commands/backtest.md) - backtest command
- [ ] [.claude/commands/migrate.md](../../.claude/commands/migrate.md) - postgresql commands

### Phase 2: Determine Strategy

Decide for each missing command:

1. **Implement** - Add to CLI (e.g., `account list`, `positions active`)
2. **Document as planned** - Mark as future feature
3. **Remove** - Not needed, just delete from docs

### Recommended Priority

**Should implement** (commonly needed):
- `account list/switch/sync` - Multi-account workflow
- `positions active/close` - Position management
- `market status` - Pre-trade check
- `symbol info` - Quick reference

**Document as planned**:
- `analytics *` - Future dashboard
- `health` - Future monitoring
- `backtest` - Standalone tool exists in scripts/

**Remove from docs**:
- `db backup/restore/stats` - Use alembic directly
- `config backup/diff/list` - Use git directly
- `notify` - Internal API, not CLI

## Acceptance Criteria

- [ ] All docs reference only existing commands OR mark non-existent as planned
- [ ] CLI reference matches `uv run trading-bot --help` output
- [ ] No misleading examples in documentation
- [ ] Updated Claude commands reflect reality

---

## Issue B: Trading Types Gap

**Documented**: 4 trading types (scalping, day_trading, swing_trading, position_trading)
**Actual**: Only `day_trading` implemented

### Evidence
`src/trading_bot/executors/factory.py`:
```python
_EXECUTORS = {
    "day_trading": IntradayExecutor,
    # "swing_trading": SwingExecutor,  # TODO Phase 3
    # "scalping": ScalpingExecutor,    # TODO Phase 4
    # "position_trading": PositionExecutor,  # TODO Future
}
```

### Files to Update

- [ ] [docs/trading/trading-types-guide.md](../../docs/trading/trading-types-guide.md) - Mark unimplemented as "Planned"
- [ ] [docs/guides/multi-timeframe-guide.md](../../docs/guides/multi-timeframe-guide.md) - Adjust timeframe sections
- [ ] [docs/guides/strategy-guide.md](../../docs/guides/strategy-guide.md) - Update trading type weights
- [ ] [CLAUDE.md](../../CLAUDE.md) - Note only day_trading working

### Recommended Format

```markdown
| Type | Status |
|------|--------|
| day_trading | ✅ Implemented |
| scalping | 📋 Planned (Phase 4) |
| swing_trading | 📋 Planned (Phase 3) |
| position_trading | 📋 Planned (Future) |
```

---

## Issue C: Dry-Run Wrapper

**Status**: `connectors/dry_run_wrapper.py` exists but not integrated

`pyproject.toml` marks it explicitly:
```toml
omit = ["*/dry_run_wrapper.py"]  # Future feature, not yet implemented
```

### Action

- [ ] Update [docs/guides/dry-run-guide.md](../../docs/guides/dry-run-guide.md) - clarify what's currently implemented vs planned

---

## Issue D & E: Undocumented Code

**Implemented but not in docs**:
- `analytics/performance_analyzer.py` (PerformanceAnalyzer)
- `risk/risk_manager_conservative.py` (ConservativeRiskManager)

### Action

- [ ] Decision: integrate, remove, or document as standalone utility
- [ ] If keep: add brief docs explaining purpose
- [ ] If remove: delete code

---

## Related

- [code-review-2026-05.md](code-review-2026-05.md) - Source review findings
- [refactor-codebase.md](refactor-codebase.md) - Code structure refactor
