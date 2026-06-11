# Exit / Payoff Tuning — Design

## The exit ladder today (and where it leaks)

```
entry ──0.4R──▶ BE trigger (SL→entry+offset)
        │            │
        │            ▼  ← THE LEAK: between BE and trailing activation,
        │               nothing locks profit. 44 trades reached ~0.51R
        │               here and scratched at +0.14R.
        └──~0.8-1R──▶ trailing activates (keeps ~63% of peak → 0.71R avg)
                 ~2R ▶ TP (reached by 1/129 — decorative)
```

All thresholds already live in YAML (`config/default.yaml` automation tiers,
per asset class; `signal_generation.risk_reward` for the TP ratio) — this
spec changes values + adds at most one knob, no new mechanisms.

## Levers (evaluated independently in backtest)

### L1 — Close the BE-gap (highest expected value)
Lower the trailing **activation** threshold into the gap (e.g. activate at
~0.5R instead of ~0.8–1R), keeping the trailing **distance** as-is. Effect:
the 44-trade BE bucket converts partially into small trailing wins
(0.3–0.5R) instead of 0.14R scratches. Risk: earlier trailing can clip a few
eventual big runners — measure net expectancy, not just the bucket.

### L2 — Honest TP
Evaluate TP ratio at 1.2R / 1.5R / 2R (current) in backtest. Note the
signal-gate coupling: `min_risk_reward_ratio: 2.0` requires 2R *potential*
at entry — lowering the **placed TP** does not require lowering the gate
(keep requiring 2R room; place TP nearer). If trailing outperforms any fixed
TP, keep TP as a far cap and document trailing as the real exit.

### L3 — Partial close, size-aware
Policy for a cent account:
- Gate per position: enable partial only when `volume ≥ min_volume /
  close_percentage` (e.g. 25% ladder ⇒ ≥ 0.04 lots) — computed, not assumed.
- Config: `partial_close.enabled: true` + per-asset ladders already exist;
  add `partial_close.min_position_volume` guard so sub-floor positions skip
  cleanly (no log noise, visible in dashboard as a non-firing automation).
- First partial at a **reachable** level (~0.8–1R, where 19% of trades get),
  not at the 2R fantasy tiers.

### L4 — (defensive) keep BE as-is
BE at 0.4R is why losers don't multiply; do not weaken it. SL distance is
also out of scope (entry-side).

## Validation

Backtester sweep over the same window as the live winning streak:
- grid: trailing activation {current, 0.5R, 0.6R} × TP {1.2R, 1.5R, 2R} ×
  partial {off, on-where-size-allows};
- score by **expectancy per trade** and payoff ratio, tie-break on drawdown;
- acceptance: payoff ≥ 0.8, WR ≥ 65%, expectancy ≥ current baseline.

Ship the winning combo as YAML-only changes; monitor 2 weeks via
`/analytics/by-close-reason` (watch: BREAKEVEN_STOP avg-kept rises,
TRAILING share rises, SL bucket unchanged).

## Rollback

All changes are YAML values — revert the config commit. No code paths change
except the optional `min_position_volume` guard in PartialCloseManager.
