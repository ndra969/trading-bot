# Exit / Payoff Tuning — Requirements

**Status**: 📋 Planned
**Priority**: 🟠 Medium-High (profit quality; system is net-positive but fragile)
**Date**: 2026-06-11

## Context

14-day live data (129 closed trades, WR ~75%, net positive) shows the profit
profile the operator explicitly does NOT want: high win-rate with tiny
winners, carried by frequency instead of payoff.

| exit | n | reached (MFE) | kept | TP target |
|------|---|---------------|------|-----------|
| TRAILING_STOP | 47 | 1.12R | **0.71R** | ~2.0R |
| BREAKEVEN_STOP | 44 | **0.51R** | **0.14R** | ~1.9R |
| STOP_LOSS | 34 | 0.16R | −0.91R | ~1.9R |
| TAKE_PROFIT | 4 | 1.81R | 1.88R | 1.88R |

- **Payoff ratio 0.47** — avg win 8.52 vs avg loss −18.11. Losers are ~2×
  winners; the edge is 100% carried by the 75% WR.
- **TP at ~2R is structurally unreachable**: 1/129 trades ever reached 2R;
  only 25/129 (19%) ever reached 1R; median path = 0.29× of the TP distance.
- **Biggest leak = the breakeven bucket**: 44 trades reached avg 0.51R and
  were scratched at 0.14R — the gap between the BE trigger (~0.4R) and the
  trailing activation threshold gives back nearly everything.
- Trailing itself is decent (keeps 63% of peak).

## Partial close: actual status (clears up "belum diimplement")

`PartialCloseManager` is fully implemented AND wired
(`position_orchestrator._handle_partial_close_automation`, called every
update loop, with real MT5 partial closes). It never fires because:
1. `partial_close.enabled: false` in `config/default.yaml` (explicit default), and
2. **lot-size floor**: close volume must be ≥ 0.01 lot. At the account's
   typical 0.01–0.03 lots, 25% of the position is below the MT5 minimum →
   skipped even if enabled. Only positions ≥ 0.04 lots can partial-close.

So "enable the flag" alone fixes almost nothing — the ladder percentages /
minimums must respect the account's lot sizes, or sizing must grow first.

## Goals

1. **Raise the payoff ratio** (avg win / avg loss) without destroying the
   75% WR — target ≥ 0.8 as first milestone (expectancy headroom), measured
   on backtest + 2 live weeks.
2. **Close the BE-gap leak**: trades that reach ~0.5R should not round-trip
   to +0.14R. Candidate: activate trailing earlier (between BE trigger and
   current activation), or a tighter "lock" step at 0.5R.
3. **Make the TP honest**: either bring TP into reachable range (data: 1.2R
   is reached by ~19% — evaluate 1.2–1.5R), or formally treat trailing as
   the exit and TP as a far cap — decided by backtest expectancy, not vibes.
4. **Decide partial close policy for a cent account**: enable only where
   volume supports it (≥ 0.04 lots), with level percentages that respect the
   0.01 floor; otherwise document it as size-gated and revisit when sizing
   grows. No silent "should fire but skipped" states.

## Non-goals

- No entry/signal changes (that's `enhancement-layer-rework`).
- No risk-per-trade increase to "make partial close possible" — sizing is a
  risk decision, not an exit-tuning lever.
- No removal of breakeven protection (it's why losers don't multiply).

## Success criteria

- Backtest: payoff ratio ≥ 0.8 with WR ≥ 65% and net expectancy ≥ current,
  on a window overlapping the live winning streak.
- BE bucket: avg kept of trades reaching ≥0.5R improves materially (>0.3R).
- Live (2 weeks post-ship): same direction of movement, monitored via the
  dashboard by-close-reason + by-exit-type views.
- Every change is a YAML knob (breakeven/trailing/partial/TP ratio) — no
  hardcoded values.

## Related

- [enhancement-layer-rework](../enhancement-layer-rework/requirements.md) —
  entry-side counterpart; ship separately so effects are attributable.
- [strategy-tuning](../strategy-tuning.md) — earlier per-asset BE/trailing rounds.
- Code: `position/automation/{breakeven_manager,trailing_stop_manager,partial_close_manager}.py`,
  `config/default.yaml` (automation tiers + `partial_close`),
  `signal_generation.risk_reward` (TP ratio).
- Dashboard: `/analytics/by-close-reason`, `/by-exit-type` — monitoring.
