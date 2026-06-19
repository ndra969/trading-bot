# Breakout-Retest Entry — Design

**Status**: 📋 Planned
**Date**: 2026-06-19

## Where it plugs in

The bounce path runs in `FoundationEngine.analyze_symbol` →
`generate_signals` → zone detection → `_run_enhancement_analyzers` →
`_passes_final_quality_filters`. Breakout-retest is a **parallel branch off the
same detected zones**, not a layer inside the bounce confluence:

```
detect zones ─┬─ bounce branch     (price INSIDE zone, expecting reversal)
              └─ breakout branch    (price BROKE zone, now retesting)   ← new
```

Both branches honour `max 1 trade per symbol` (a symbol with a live breakout-
retest candidate skips the bounce branch and vice-versa).

## Detection state machine (per symbol+zone)

A zone progresses through states; only `RETEST_CONFIRMED` emits a signal:

1. `INTACT` — price has not broken the zone. (bounce branch owns this.)
2. `BROKEN` — `BreakoutAnalyzer.analyze_breakout(level=zone_edge, dir)` returns
   a signal (strong body close beyond the zone + volume). Record break price,
   direction, bar index.
3. `RETESTING` — price returns to the broken zone band (within tolerance) from
   the breakout side, within N bars of the break.
4. `RETEST_CONFIRMED` — a rejection candle forms at the retest (reuse
   `PriceActionAnalyzer` for the rejection pattern, in the **continuation**
   direction) → emit signal.
5. `EXPIRED` — retest not seen within N bars, or price closed back inside the
   zone (break failed) → drop candidate.

State is held in a small per-symbol tracker (mirror how zones are already
tracked). No new persistence required for v1 (in-memory, rebuilt on restart).

## Signal construction

- **Direction**: breakout direction (BULLISH→BUY, BEARISH→SELL). NOT the
  bounce direction.
- **Entry**: at/near the retest of the broken zone edge.
- **SL**: beyond the retested zone (break-failure invalidation), asset-aware
  via existing pip logic.
- **TP**: next structure level / R-multiple from existing risk_reward config.
- **Confidence**: `BreakoutAnalyzer.confidence` blended with the retest
  rejection (price action) confidence. Reuse the normalised-score machinery;
  do **not** reuse the bounce's foundation-share formula (no S&D bounce here).

## Validation gates (re-evaluated, not inherited)

| Bounce gate | Breakout-retest treatment |
|---|---|
| `require_price_action` | Keep — the retest rejection candle IS the price action. |
| `require_trendline` | Optional/off — trendline confluence is a bounce concept. |
| Counter-trend H1 sniper | **Invert intent**: a breakout *with* H1 trend is good; only block breakouts hard against H1 trend. |
| RSI overbought/oversold gate | Relax — continuation can run into "overbought" legitimately. Use as soft signal, not hard block. |
| Climax / anti-chase | Keep — still don't chase an overextended retest. |
| Commodities ≥1 enhancement layer | Keep. |

## Data plumbing

`analyze_breakout` needs `volumes`. The bounce path passes opens/highs/lows/
closes; volume must be threaded from the data loader → engine → breakout call.
Confirm the connector + backtest CSV both carry a volume column (tick volume is
acceptable; validate `volume_threshold` against it per asset class).

## Config (`signal_generation.breakout_retest`)

```yaml
breakout_retest:
  enabled: false              # ships dark
  retest_window_bars: 10      # break → retest must occur within N bars
  retest_tolerance: 0.5       # fraction of zone height for "back at the zone"
  min_breakout_confidence: 50 # from BreakoutAnalyzer
  weight_breakout: 0.6        # blend vs retest price-action
  weight_retest_pa: 0.4
breakout:                     # already read by BreakoutAnalyzer
  volume_threshold: 1.5
  min_body_ratio: 0.6
```

## Telemetry

- `entry_tags.setup_type = "breakout_retest"` (vs implicit `bounce`), plus
  break confidence, volume ratio, retest bar gap. Lets analytics separate the
  two archetypes from day one (the bounce path now also fills `entry_tags`).
- New `RejectionStage` values: `BREAKOUT_NOT_CONFIRMED`, `RETEST_EXPIRED`.

## Backtest

Extend `scripts/run_backtest.py` with a `--setup {bounce,breakout_retest,both}`
selector so the harness can drive and report the new path in isolation, reusing
the now-quiet logging + real-manager wiring.

## Open questions

- One zone tracker per symbol or per (symbol, zone)? Start per-zone, capped.
- Should a confirmed breakout-retest *suppress* a simultaneous bounce signal on
  the opposite side, or just lose the `max 1 per symbol` race? (Lean: explicit
  suppression once `BROKEN`, since the zone has flipped polarity.)
