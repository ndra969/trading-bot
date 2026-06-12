# Exit / Payoff Tuning — Task Breakdown

## Phase 0 — Baseline (done 2026-06-11, keep for comparison)

- [x] 14-day live baseline recorded in requirements.md: payoff 0.47, WR ~75%,
      TP reached 1/129, BE bucket reached 0.51R kept 0.14R, trailing kept
      0.71R of 1.12R.

## Phase 1 — Backtest sweep

- [ ] Confirm the backtester reproduces the automation ladder (BE/trailing/
      partial) — if it only simulates SL/TP, extend it first (blocking).
- [ ] Grid: trailing activation {current, 0.5R, 0.6R} × TP {1.2R, 1.5R, 2R}
      × partial {off, size-gated on} over EURUSD/USDJPY/XAUUSD/BTCUSD on the
      live-streak window.
- [ ] Score by expectancy + payoff (tie-break drawdown); record the table in
      this spec.

## Phase 2 — Partial close size-guard (small code change)

- [x] `PartialCloseManager`: add `partial_close.min_position_volume` guard
      (skip cleanly when `volume × close% < 0.01`); unit tests for 0.01 /
      0.03 / 0.04 lot cases. *(2026-06-12: position-level gate, logged once;
      `min_volume` also made config-driven, default 0.01)*
- [x] First-partial level moved to a reachable tier (config) per design L3.
      *(2026-06-12: `partial_close.level_ratios` — flat list or per-asset
      dict with `default`; values still come from the Phase 1 sweep, this is
      the knob)*

> Note (out of scope, for Phase 3 wiring): `position_orchestrator
> ._handle_partial_close_automation` reads `result["closed_volume"]` but
> `execute_partial_close` returns `close_volume` — the MT5 sync block is
> skipped on the key-mismatch. Fix when enabling partial close live.

## Phase 3 — Ship + monitor

- [ ] Apply the winning YAML combo (automation tiers + TP ratio + partial
      flag). `/dry-run`, commit, restart bot.
- [ ] Monitor 2 weeks via dashboard by-close-reason / by-exit-type:
      BREAKEVEN_STOP avg-kept > 0.3R, payoff trending ≥ 0.8, WR ≥ 65%.
- [ ] Revert config commit if expectancy regresses; archive spec with
      results either way.

## Effort

Phase 1: 2-4 h (more if the backtester lacks automation simulation) ·
Phase 2: ~1 h · Phase 3: config + monitoring. Ship separately from
enhancement-layer-rework so effects stay attributable.
