# Confluence Scoring Investigation — Task Breakdown

Investigation-first: gather data, analyse, then decide on a change.
Do NOT change scoring/thresholds until Phase 3 concludes.

## Phase 0 — Wait for sample (passive)

- [ ] Let the bot run ≥1 week under the lowered thresholds (commit
      `7259ba6`) so there are ≥100 fresh closed positions to analyse.
- [ ] Confirm `positions.meta_data.strategy_scores` is being populated
      on new positions (spot-check 5 recent rows).

## Phase 1 — Layer firing rates & distributions (~45 min)

- [ ] Write a read-only analysis script (scripts/ or ad-hoc) that pulls
      closed positions and extracts per-layer raw confidence from
      `meta_data.strategy_scores`.
- [ ] Produce a table per layer: fire-rate %, min/avg/max/p50 when fired.
- [ ] Produce per-asset-class breakdown (forex / forex_jpy / commodities
      / crypto).
- [ ] Record findings in a `findings.md` in this spec folder.

## Phase 2 — Layer → outcome correlation (~45 min)

- [ ] Join each layer's confidence with win/loss
      (`current_pnl_usd > 0`).
- [ ] Per layer per asset: avg confidence for winners vs losers.
- [ ] Flag predictive layers (winners clearly higher) vs noise layers.
- [ ] Check whether MTF confirmation (if recorded) separates win/loss
      better than single-TF confluence.
- [ ] Append to `findings.md`.

## Phase 3 — Decision (~30 min)

- [ ] Verify weights sum to 1.0 and no layer is double-counted
      (foundation_engine `_calculate_confluence_score`).
- [ ] Pick one:
      - [ ] (a) Scoring bug fix
      - [ ] (b) Layer reweight
      - [ ] (c) New gating feature (e.g. require MTF)
      - [ ] (d) Accept current behaviour, revisit later
- [ ] Document the decision + rationale in `findings.md`.

## Phase 4 — Implement (only if a/b/c chosen) (~1-2 hr)

- [ ] Make the change behind per-asset threshold config.
- [ ] Update `test_foundation_engine.py` confluence assertions.
- [ ] Add a regression test for the new behaviour.
- [ ] `uv run pytest tests/unit/` green.
- [ ] Dry-run smoke test (`uv run trading-bot --config test start`).
- [ ] Re-tune per-asset thresholds against the NEW score distribution
      (the old data-driven values assume the old scoring).
- [ ] Single commit.

## Phase 5 — Close out

- [ ] Move this spec to `specs/archive/YYYY-MM/`.
- [ ] Update `specs/README.md` index.
- [ ] If outcome was (d) "accept", note the next review date in
      `strategy-tuning.md`.

## Effort estimate

- Phase 0: passive (1 week wall-clock)
- Phases 1-3 (analysis + decision): ~2 hours
- Phase 4 (if code change): +1-2 hours
- Total active work: 2-4 hours after the sample is ready

## Tests-to-watch

- `tests/unit/strategies/foundation/test_foundation_engine.py`
- `tests/unit/strategies/test_signal_aggregator.py`
