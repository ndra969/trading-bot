# Breakout-Retest Entry — Requirements

**Status**: 📋 Planned
**Priority**: 🟡 Medium (new entry archetype; current strategy is bounce-only)
**Date**: 2026-06-19

## Context

The bot currently has exactly one entry archetype: **bounce / mean-reversion**
at a Supply/Demand zone (BUY at demand expecting a bounce up, SELL at supply
expecting a bounce down). All 8 confluence layers feed that one decision.

`BreakoutAnalyzer` (`strategies/enhancement/breakout_analyzer.py`) is fully
implemented — it validates a strong-body candle closing *through* a level with
volume + momentum confirmation — but **`analyze_breakout()` is never called
anywhere**. It is instantiated in `FoundationEngine.__init__` and reserved a
0.12 confluence weight, yet contributes to 0% of trades (verified over 73 live
trades, 2026-06-12..19). The "breakout skipped at zone entry — used for
confirmation later" comment in `foundation_engine._run_enhancement_analyzers`
describes a re-entry path that was never built.

A breakout signal is the **logical opposite** of a bounce: it cannot confirm a
bounce entry (you would be buying a reversal and confirming it with a
continuation). So breakout can only be used by adding a **second, separate
entry archetype**: breakout-retest continuation.

## Goal

Add a breakout-retest entry path that uses the existing `BreakoutAnalyzer`, so
price breaking and retesting a zone becomes a tradeable continuation setup —
distinct from, and not contaminating, the bounce path.

## The setup (definition)

1. Price **breaks** an S&D zone with conviction (strong body close beyond the
   zone + volume — `BreakoutAnalyzer`).
2. Price **retests** the broken zone from the other side (old resistance →
   new support, or old support → new resistance).
3. Entry is **in the breakout direction** (continuation), with SL beyond the
   retested zone and TP at the next structure target.

## Scope

- New signal-generation path producing breakout-retest signals, kept separate
  from the bounce path (own setup type, own validation, own telemetry tag).
- Reuse `BreakoutAnalyzer`; plumb the **volume** series it requires through to
  the call site (bounce path never needed volume).
- Config-gated (`enabled: false` by default) so it ships dark and is
  backtested before going live.

## Non-goals

- Not changing the bounce path's scoring or gates.
- Not enabling it live in this spec (default off; arm after backtest).
- Not re-using the bounce confluence gates verbatim — several are
  bounce-specific (see Risks).

## Risks / conflicts to resolve in design

- **Counter-trend H1 sniper gate** and **RSI overbought/oversold gate** are
  written for bounces; for a continuation breakout they may be inverted or
  irrelevant. Must be re-evaluated, not blindly reused.
- **`max 1 trade per symbol`** still holds — breakout-retest and bounce must
  not both open on the same symbol.
- Volume quality on the broker feed (tick vs real volume) affects the
  `volume_threshold` check — validate it is meaningful per asset class.

## Acceptance criteria

- Breakout-retest signals are generated only when break + retest + direction
  align; bounce-path output is byte-for-byte unchanged when the flag is off.
- The path is observable: `entry_tags` records `setup_type=breakout_retest`
  plus the breakout confidence/volume detail.
- Backtest harness can drive it (`--setup breakout_retest` or equivalent) and
  reports its trades separately.
- Default config OFF; full test coverage on the new path; bounce regression
  suite stays green.
