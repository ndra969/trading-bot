# Confluence Scoring Investigation — Requirements

**Status**: 📋 Planned
**Priority**: 🟠 Medium (blocks meaningful strategy tuning)
**Date**: 2026-05-28

## Context

DB analysis of closed positions (2026-05-28) revealed two problems with
the confluence scoring system:

1. **Confluence ceiling is unexpectedly low.** Observed max confluence
   per asset class:
   - forex: 57.4% (p50 35.4)
   - forex_jpy: 57.9% (p50 41.9)
   - crypto: 42.8% (p50 34.3)
   - commodities: 45.5% (p50 34.2)

   The strategy docs target "min 65% confluence" but the system rarely
   produces scores above 45%. This forced us to lower thresholds to
   ~p50 (commit `7259ba6`) just to get signals through at all.

2. **Confluence does NOT predict outcome.** Win vs loss average
   confluence is nearly identical per asset:
   - forex:       WIN 36.6 vs LOSS 37.0  (confluence higher on losers!)
   - crypto:      WIN 35.1 vs LOSS 34.4
   - commodities: WIN 34.6 vs LOSS 32.3  (only commodities shows signal)

   If confluence were a good quality filter, winners should score
   noticeably higher than losers. They don't.

The likely culprit: weighted layer scoring caps the foundation
contribution at 30% (weight 0.30 × max 100% confidence) and the 7
enhancement layers rarely fire together, so total confluence saturates
in the low-to-mid 30s.

## Goals

1. Determine **why** confluence saturates so low (scoring math vs layer
   firing rates vs config weights).
2. Determine **whether** confluence (raw or reweighted) can be made
   predictive of win/loss, or whether a different feature should gate
   signals.
3. Produce a concrete recommendation: fix the scoring, reweight layers,
   replace the metric, or keep-as-is-with-lower-thresholds.

## Non-goals

- Not changing live thresholds again until the investigation concludes
  (current data-driven values from `7259ba6` stay for the observation
  window).
- Not rewriting the foundation strategy logic — only the scoring /
  aggregation layer.
- Not a general strategy redesign.

## Success criteria

- A written analysis (in design.md or a results note) answering: per
  layer, how often does it fire, what's its score distribution, and how
  does each layer correlate with win/loss?
- A decision: one of
  (a) scoring bug fix, (b) layer reweight, (c) new gating feature,
  (d) accept current behaviour.
- If a code change is recommended, it ships behind the existing
  per-asset threshold config so it's tunable without redeploy.

## Constraints

- Bot is in live observation phase — investigation is read-only
  (DB queries + log analysis) until a fix is decided and reviewed.
- Need a larger sample first: target ≥1 week of trades under the new
  lowered thresholds before drawing conclusions.
- Any scoring change must keep `confluence_score` on a 0-100 scale
  (DB column + downstream display assume this).

## Risk register

| Risk | Mitigation |
|------|------------|
| Small sample biases the analysis | Wait for ≥1 week / ≥100 trades post-`7259ba6` before concluding |
| "Fixing" scoring silently changes signal volume | Gate any change behind per-asset thresholds; dry-run before live |
| Correlation ≠ causation on layer→outcome | Treat findings as hypotheses; validate on held-out window |
| Reweighting overfits to past noise | Prefer simple, explainable weight changes over fitted ones |

## Open questions

- Is the low ceiling a bug (weights don't sum to 1.0 / double-counting)
  or by design (layers genuinely rarely agree)? → design.md analysis.
- Should `confluence_score` stay a weighted sum, or move to a
  count-of-agreeing-layers model? → design.md.
- Does MTF (multi-timeframe) confirmation add predictive power that the
  single-TF confluence misses? → design.md.

## Related

- Threshold tuning commit: `7259ba6`
- Per-asset thresholds: `2b2a08e`
- [strategy-tuning.md](../strategy-tuning.md) — parent tuning spec
- Confluence weights config: `config/strategy_parameters.yaml`
  (`confluence_weights`)
- Scoring code: `src/trading_bot/strategies/foundation/foundation_engine.py`
  (`_calculate_confluence_score`, `_run_enhancement_analyzers`)
