# Enhancement-Layer Rework — Requirements

**Status**: 📋 Planned
**Priority**: 🟠 Medium (confluence is non-predictive; safe to defer while profitable)
**Date**: 2026-06-11

## Context

Dashboard-driven analysis of the live confluence breakdown + outcomes
(2026-06-11, n=82 taken trades with persisted breakdown, overall WR 73%)
showed the enhancement layers are mostly dead or unhelpful:

| Layer | weight | fired% | WR fired vs absent | Verdict |
|-------|--------|--------|--------------------|---------|
| price_action | 0.15 | 85% | **75.7%** vs 58.3% | ✅ the one positive predictor |
| ma | 0.08 | 11% | 66.7% vs 74.0% | ➖ weak / noise |
| fibonacci | 0.12 | 17% | **57.1%** vs 76.5% | ❌ counter-predictive |
| trendline | **0.20** | **0%** | — | 💀 never fires |
| rsi | 0.10 | 1% | — | 💀 effectively dead |
| structure | 0.08 | 0% | — | 💀 never fires |

`enhancement_share` is *higher* on losers (13.1) than winners (10.1), and
WIN-avg confluence (65.1) ≈ LOSS-avg (67.4) → **confluence does not predict
outcome.** The bot is profitable anyway because the `require_price_action`
gate + risk management (trailing/breakeven cutting stops) do the work — not
the score. This spec fixes the two highest-value layers so the score
becomes meaningful, *without* destabilising a profitable system.

## Why not just zero the bad layers

The operator's intent is to **fix** the layers, not delete them. Zeroing
fibonacci/trendline is a band-aid; the goal is a confluence score that
actually separates winners from losers. But the live sample is small
(fibonacci n=14), so changes MUST be backtest-validated before shipping —
not tuned to 14 live trades.

## Goals

1. **Trendline — revive it.** Two confirmed defects keep it at 0% across all
   assets:
   - **pip_value bug**: `analyze_trendline_signal(..., pip_value=0.0001)`
     default is never overridden by the caller, so for forex_jpy /
     commodities / crypto the 20-pip bounce window is 100–10000× too small —
     it can never fire.
   - **model mismatch**: even forex_major fires 0% — the "price within 20
     pips of a trendline on the entry candle" test rarely coincides with an
     S&D-zone entry (entries are computed independently of trendlines).
   Rework so trendline confluence is evaluated against the *zone* (does a
   trendline reinforce this S&D level?) rather than a bounce at the entry bar.
2. **Fibonacci — make it predictive (or prove it can't be).** Today it draws
   fib from the global 50-bar high/low and scores the deepest retracement
   highest (0.5 = 20 pts). Hypothesis from the data: deep retracements into a
   reversal zone carry more momentum → more likely to break the zone → the
   highest-scored level dominates losers. Rework swing selection (recent
   structural leg) + re-rank level scores by *measured* win-rate, validated
   by backtest.
3. **Structure — fix the vocabulary bug (definite).** The analyzer returns
   `direction = "BULLISH"/"BEARISH"` but the engine compares it against
   `SignalDirection.name` (`"BUY"/"SELL"`):
   - scoring: `struct_res.direction == direction.name` is **never** true →
     structure can never contribute (explains 0% firing);
   - commodities gate: `struct_res.direction != direction.name and
     confidence > 90` is **always** "misaligned" — a BULLISH structure on a
     BUY can erroneously REJECT an aligned trade.
   Fix the mapping (BULLISH↔BUY, BEARISH↔SELL) in both places.
4. **RSI — decide its role.** No vocab bug; it fires ~1% by design (needs an
   RSI extreme exactly at the zone-entry candle, then further neutralising
   blocks). In practice it acts as a hard rejection gate (2.6k `rsi_gate`
   rejections), not a scorer. Either give it a scoring rule that can
   actually fire at reversal zones (e.g. "RSI recovering from the extreme in
   trade direction") or formally reclassify it as gate-only and remove its
   weight — decided by backtest, not by hand.
5. **Re-derive confluence weights from measured predictiveness.** Once layers
   fire correctly, set each weight from its backtested edge (e.g. drop or
   down-weight any layer whose presence doesn't lift WR). price_action stays.
6. **Keep the live system safe.** No change ships to live config until the
   backtest shows a non-worse (ideally better) WR / profit factor on the
   same period the live system is currently winning on.

## Non-goals

- Not touching `require_price_action`, the thresholds, the climax/commodity
  gates, or risk management — those are working.
- Not adding new layers; this is about making the existing ones honest.
- No live A/B; validation is via the existing backtester on historical data.

## Success criteria

- Trendline fires a meaningful fraction of the time across all asset classes
  (no pip_value scale bug; participation visible in `/analytics/layer-contribution`).
- Each retained layer's `WR|fired > WR|absent` on the backtest (positive edge);
  counter-predictive behaviour removed (fibonacci no longer WR-negative).
- Confluence WIN-avg > LOSS-avg on the backtest (the score finally separates).
- Backtest WR + profit factor ≥ current live baseline over a comparable window.
- New unit tests for both analyzers; dashboard layer-contribution used to
  monitor post-ship.

## Related

- [confluence-scoring-investigation](../confluence-scoring-investigation/requirements.md)
  — the original "confluence is a weak predictor" finding; this operationalises its fix.
- [strategy-tuning](../strategy-tuning.md)
- Dashboard `/analytics/layer-contribution` + `/analytics/confluence-vs-outcome`
  — the evidence source and the post-ship monitor.
- Code: `strategies/enhancement/trendline_analyzer.py`,
  `strategies/enhancement/fibonacci_analyzer.py`,
  `foundation_engine._run_enhancement_analyzers` (call sites + weights).
