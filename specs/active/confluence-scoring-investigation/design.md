# Confluence Scoring Investigation — Design

This is an **investigation** spec — the "design" is the analysis plan and
the decision framework, not a predetermined code change. Code changes (if
any) are chosen at the end based on findings.

## How confluence is computed today

`foundation_engine` builds a weighted sum of layer scores:

```
confluence_score = Σ (layer_confidence × layer_weight)
```

Weights (`config/strategy_parameters.yaml → confluence_weights`):

| Layer | Weight |
|-------|--------|
| foundation (S&D) | 0.30 |
| trendline | 0.20 |
| price_action | 0.15 |
| fibonacci | 0.12 |
| breakout_retest | 0.12 |
| rsi | 0.10 |
| structure | 0.08 |
| ma | 0.08 |
| volume_profile | 0.05 (optional) |
| multi_timeframe | 0.05 (optional) |

Each `layer_confidence` is 0-100. In `_run_enhancement_analyzers` the
score is stored already weighted, e.g. `layer_scores["rsi"] = conf × 0.10`.

### Hypothesis for the low ceiling

If foundation is the only consistently-firing layer (weight 0.30) and it
maxes at 100% confidence, its contribution caps at 30 points. Enhancement
layers each add single-digit points and rarely all fire, so total
saturates in the 30s-40s. That matches the observed max ~45-57%.

This needs **verification with data**, not assumption.

## Analysis plan

### Step 1 — Layer firing rates & distributions

For each closed position, we need the per-layer raw confidence. Two
sources:
- `positions.meta_data.strategy_scores` (JSON) — captured at signal time
  via `create_position_from_signal`.
- Bot logs (`_run_enhancement_analyzers` debug lines).

Query / parse to produce, per layer:
- fire rate (% of signals where layer_confidence > 0)
- score distribution (min/avg/max/p50) when fired
- weighted contribution distribution

### Step 2 — Layer → outcome correlation

Join each layer's raw confidence with the position outcome
(`current_pnl_usd > 0`). Compute, per layer per asset class:
- avg layer confidence for winners vs losers
- point-biserial-ish signal: does a higher layer score track wins?

Layers where winners clearly score higher are the predictive ones and
deserve more weight. Layers with no separation are noise.

### Step 3 — Decision

Pick one based on the data:

| Finding | Recommendation |
|---------|----------------|
| Weights don't sum to 1.0 or layers double-counted | (a) Bug fix — normalise, dedupe |
| Some layers predictive, others noise | (b) Reweight — boost predictive, drop noise |
| No single-TF layer predictive, but MTF is | (c) New gate — require MTF confirmation |
| Nothing predictive at current data size | (d) Accept — keep low thresholds, gather more |

## Data capture check

`strategy_scores` is stored in `positions.meta_data`. Confirm it's
populated for recent positions (post per-asset threshold change). If
sparse, may need to add structured per-layer columns first (separate
small task) before meaningful analysis.

## Test impact

- Investigation phase: none (read-only DB/log analysis).
- If a scoring change ships: update
  `tests/unit/strategies/foundation/test_foundation_engine.py`
  confluence assertions + add regression test for the new weighting.

## Rollback plan

Any scoring change ships as one commit behind the existing per-asset
threshold config. Revert = `git revert <commit>`; thresholds already
absorb the difference so no data migration needed.

## What "done" looks like

- A results section (appended here or a sibling `findings.md`) with the
  layer fire-rate + correlation tables.
- A chosen option (a/b/c/d) with rationale.
- If code change: committed + dry-run validated; otherwise a documented
  "accept current behaviour, revisit after N more weeks" note.
