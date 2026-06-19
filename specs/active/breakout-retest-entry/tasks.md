# Breakout-Retest Entry — Tasks

**Status**: 📋 Planned
**Date**: 2026-06-19

Phased so each step is shippable behind the `breakout_retest.enabled` flag
(default off). Bounce path must stay byte-for-byte unchanged when the flag is off.

## Phase 0 — Plumbing & data (no behaviour change)
- [ ] Confirm volume series is available end-to-end (connector + backtest CSV);
      add a volume column to the backtest loader if missing.
- [ ] Validate broker volume is meaningful (tick vs real) per asset class;
      sanity-check `volume_threshold=1.5` against real distributions.
- [ ] Thread `volumes` through `analyze_symbol` → enhancement call site.

## Phase 1 — Detection state machine (pure, unit-tested)
- [ ] Add a per-zone breakout-retest tracker (INTACT→BROKEN→RETESTING→
      RETEST_CONFIRMED/EXPIRED) — pure functions over bars, no I/O.
- [ ] Wire `BreakoutAnalyzer.analyze_breakout` for the BROKEN transition.
- [ ] Reuse `PriceActionAnalyzer` for the retest rejection (continuation dir).
- [ ] Unit tests for every transition + expiry + failed-break-back-inside.

## Phase 2 — Signal construction
- [ ] Build a breakout-retest `TradingSignal` (direction=breakout dir, SL beyond
      retest, TP from risk_reward config, blended confidence).
- [ ] `entry_tags.setup_type="breakout_retest"` + break/volume/retest detail.
- [ ] New `RejectionStage`: `BREAKOUT_NOT_CONFIRMED`, `RETEST_EXPIRED`.

## Phase 3 — Validation gates (re-evaluated for continuation)
- [ ] Keep require_price_action (retest rejection); make require_trendline n/a.
- [ ] Invert counter-trend gate intent (block only breakouts hard against H1).
- [ ] Soften RSI ob/os gate to non-blocking for continuation.
- [ ] Keep climax/anti-chase + commodities ≥1-layer.
- [ ] Enforce `max 1 trade per symbol` across both archetypes; decide bounce
      suppression once a zone is BROKEN.

## Phase 4 — Config & wiring
- [ ] Add `signal_generation.breakout_retest` block (default `enabled: false`).
- [ ] Branch in the engine: zones route to bounce or breakout-retest.
- [ ] Off-flag regression: bounce output identical (golden test).

## Phase 5 — Backtest & validation
- [ ] `scripts/run_backtest.py --setup {bounce,breakout_retest,both}`.
- [ ] Report breakout-retest trades separately (count, WR, payoff).
- [ ] Backtest across EURUSDc/USDJPYc/XAUUSDc/BTCUSDc H1+M30; record table here.
- [ ] Decide whether the edge justifies arming live.

## Phase 6 — Live (gated)
- [ ] Enable for one symbol/asset class first; monitor ~1-2 weeks via dashboard
      (entry_tags.setup_type split) before broadening.

## Decision log
- 2026-06-19: Chosen over removing the orphaned BreakoutAnalyzer (option a),
  per operator: build the second entry archetype rather than delete the code.
