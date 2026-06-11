# Enhancement-Layer Rework — Task Breakdown

Order: definite bug fixes first (measure-only), then analyzer reworks, then
weight re-derivation — each gated by backtest before touching live config.

## Phase 0 — Definite bug fixes (small, surgical)

- [ ] **Structure vocab fix**: mapping helper (BULLISH→BUY / BEARISH→SELL);
      use it in the scoring branch AND the commodities >90-confidence gate.
      Unit tests: aligned BULLISH+BUY scores (not rejected); opposed
      BEARISH+BUY at conf>90 still rejected.
- [ ] **Trendline pip_value fix**: cache `PipCalculator` on the engine; pass
      `get_pip_size(symbol)` into `analyze_trendline_signal`. Unit test per
      asset class (JPY/gold/crypto distances now scale correctly).
- [ ] Tighten the trendline substring match (`"SUPPORT" in signal_type` also
      matches `BREAK_SUPPORT`) to explicit bounce types.
- [ ] Run full suite + dry-run; commit as `fix(strategy): dead-layer bug fixes`.
- [ ] **Measure-only week**: deploy, watch `/analytics/layer-contribution` +
      `/confluence-vs-outcome` — do trendline/structure now fire, and with
      what edge? No weight/threshold changes yet.

## Phase 1 — Analyzer reworks

- [ ] **Trendline**: evaluate confluence against the zone band (projected
      line passes through/near `[lower, upper]`, tolerance ∝ zone height);
      direction filter SUPPORT↔DEMAND / RESISTANCE↔SUPPLY; confidence from
      touches + centring. Unit tests with synthetic trendlines/zones.
- [ ] **Fibonacci**: swing selection from the most recent structural leg
      (pivot-based, not global 50-bar extreme). Keep level scores in config.
- [ ] **RSI**: implement option (a) "recovering from extreme" scoring rule
      behind config; keep existing gate behaviour unchanged.

## Phase 2 — Backtest validation (the gate)

- [ ] Backtest representatives (EURUSD, USDJPY, XAUUSD, BTCUSD) over a window
      overlapping the current live winning streak.
- [ ] Per layer: `WR|fired − WR|absent` edge + firing rate. Fibonacci levels
      (0.382/0.5/0.618/0.786) ranked by measured WR — set config `levels`
      scores from data (expectation: shallow > deep at reversal zones).
- [ ] Acceptance: WR + profit factor ≥ live baseline; confluence WIN-avg >
      LOSS-avg; every retained layer has positive edge. Record before/after
      tables in this spec.

## Phase 3 — Weight re-derivation + rollout

- [ ] Recompute `confluence_weights` ∝ edge × reliability (price_action
      anchored; ≤0-edge layers → 0). Re-normalise so strong setups reach ~65.
- [ ] Re-check `quality_thresholds` against the new score distribution
      (dashboard Tuning view) — adjust only if the distribution shifted.
- [ ] Ship config; monitor layer-contribution + confluence-vs-outcome for a
      week; revert weights if live edge regresses.
- [ ] Archive spec with results.

## Effort

Phase 0 ~1-2 h · Phase 1 ~4-6 h · Phase 2 ~2-3 h (plus backtest runtime) ·
Phase 3 ~1 h. Total ~8-12 h across sessions, with a measure-only week between
Phase 0 and Phase 3.
