# Enhancement-Layer Rework — Design

## Trendline

### Defect 1 — pip_value scale bug (definite)
`TrendlineAnalyzer.analyze_trendline_signal(self, symbol, prices, timeframe,
pip_value: float = 0.0001)` converts the price-to-line distance to pips via
`dist_pips = abs(current_price - line_price) / pip_value`, then requires
`dist_pips <= 20`. The caller
(`foundation_engine._run_enhancement_analyzers`) never passes `pip_value`, so
0.0001 is used for every symbol:

| asset | real pip | computed scale error | result |
|-------|----------|----------------------|--------|
| forex_major | 0.0001 | 1× | OK (but see Defect 2) |
| forex_jpy | 0.01 | 100× | never within 20 |
| commodities | 0.1 | 1000× | never |
| crypto | 1.0 | 10000× | never |

**Fix**: pass the symbol's pip size
(`PipCalculator().get_pip_size(symbol)`) as `pip_value`. Cache a
`PipCalculator` on the engine (`self.pip_calculator`) instead of re-creating
it per call.

### Defect 2 — model mismatch (forex_major also 0%)
The analyzer asks "is price within 20 pips of a trendline *on the entry
candle*". The strategy enters at an **S&D zone**, located independently of
trendlines, so the two rarely coincide — forex_major fires 0% even with the
correct pip size.

**Rework**: evaluate trendline confluence against the **zone**, not the entry
bar. For a candidate zone at `[lower, upper]`:
- Project each top trendline to the zone's time/price and test whether the
  line passes **through or adjacent to the zone band** (tolerance = a
  fraction of zone height, not a fixed 20 pips).
- Direction filter: a SUPPORT line reinforcing a DEMAND zone (BUY), a
  RESISTANCE line reinforcing a SUPPLY zone (SELL). (Today's substring match
  `"SUPPORT" in signal_type` also matches `BREAK_SUPPORT`; tighten to bounce
  types only.)
- Confidence from touches + how centred the line is in the zone.

This makes trendline a *zone-quality* signal (does structure agree this level
matters?) which is what the foundation-first strategy actually wants.

## Fibonacci

### Observations
- Swings come from the **global** 50-bar `max(high)` / `min(low)` with an
  ordering check — can be stale and ignores intermediate structure.
- Config `levels: {0.382: 10, 0.5: 20, 0.618: 15}` → the **0.5** level scores
  highest. Normalised, that's confidence 100 — and confidence 100 dominates
  **losers** (LOSS-avg 100 vs WIN-avg 75). I.e. the highest-scored level is
  the worst outcome.

### Rework
1. **Swing selection**: use the most recent *significant* swing leg (pivot
   high/low, like `TrendlineAnalyzer._find_swing_highs/lows`) instead of the
   global extreme, so the retracement is measured off current structure.
2. **Level scores from measured edge**: do NOT hand-pick. Backtest each fib
   level's WR (0.382 / 0.5 / 0.618 / 0.786) and set the config `levels`
   scores proportional to (WR − baseline). Expectation to test: shallow
   retracements (0.382) into a reversal zone are higher quality than deep
   (0.618); if so the ranking inverts from today.
3. If no level shows positive edge after rework → fibonacci weight goes to
   0 *with backtest justification* (the spec's escape hatch — "fix it OR
   prove it can't be fixed", not a blind zero).

## Structure (vocabulary bug — definite, two sites)

`StructureSignal.direction ∈ {"BULLISH","BEARISH","NEUTRAL"}` vs
`SignalDirection.name ∈ {"BUY","SELL"}` in `foundation_engine`:

```python
# scoring — never true:
if struct_res.direction == direction.name: ...
# commodities gate — always "misaligned", can reject ALIGNED trades (conf>90):
if struct_res.direction != direction.name and struct_res.confidence > 90.0: ...
```

**Fix**: a single mapping helper (`BULLISH→BUY`, `BEARISH→SELL`) used by both
the scoring branch and the gate. The gate fix is a pure correctness fix
(stops wrongly rejecting aligned commodity trades) and is a candidate to
ship early; the scoring fix activates a new layer → goes through the same
measure-first rollout as trendline/fibonacci.

## RSI (rarely fires by design)

Vocab is fine (BUY/SELL/NEUTRAL). It only signals on an RSI extreme at the
entry candle, then lines ~123-133 re-neutralise marginal cases → fires ~1%.
Its real, observable role is the hard gate (`rsi_gate` rejections). Options
to evaluate in the backtest:
- (a) score "RSI recovering from extreme toward trade direction" (RSI rising
  from <35 for BUY at demand; falling from >65 for SELL at supply) — fits
  the mean-reversion entry;
- (b) keep gate-only, weight → 0, re-allocate.
Pick whichever shows edge; don't keep a dead weight.

## Weight re-derivation

After both analyzers fire correctly, recompute `confluence_weights` from the
backtest:
- For each layer, measure `WR|fired − WR|absent` (edge) and its firing rate.
- Weight ∝ edge × reliability; layers with ≤0 edge are dropped to 0.
- price_action is the anchor (proven positive). Re-normalise so a strong,
  broadly-confirmed setup still reaches the documented ~65 target.

## Validation methodology (the safety gate)

Nothing ships to `config/` until the backtester shows, on a window
overlapping the current live winning streak:
- WR and profit factor **≥ current live baseline**, and
- confluence WIN-avg **>** LOSS-avg (the score now separates), and
- each retained layer has positive edge.

Use `uv run trading-bot backtest <symbols>` across forex_major / forex_jpy /
commodities / crypto representatives. Record before/after in the spec.

## Rollout

1. Land analyzer fixes behind their current weights but **measure only** first
   (the breakdown + rejection telemetry already capture firing/edge live).
2. Flip the re-derived weights once the backtest gate passes.
3. Watch `/analytics/layer-contribution` + `/confluence-vs-outcome` for a week
   post-ship; revert weights if live edge regresses.
