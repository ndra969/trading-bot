# News / Economic-Calendar Integration — Requirements

**Status**: 📋 Planned (do NOT start until the core strategy is stable)
**Priority**: 🟢 Later (after entry/exit fixes prove out in live monitoring)
**Date**: 2026-06-25

## Context

The bot is blind to scheduled news. High-impact releases (NFP, CPI, FOMC, BoJ,
etc.) drive sharp moves that blow straight through S&D zones — exactly the
"entry immediately wrong, full-SL" pattern seen on USDJPY/XAU. The strategy
currently has no awareness of *when* a release is due or *what* it printed, so
it can open a mean-reversion bounce seconds before a news spike runs it over.

The operator wants news woven in two ways:
1. **Schedule awareness** — a daily fetch of the economic calendar so the bot
   knows which symbols have high-impact events and when.
2. **Per-event reaction** — when a release drops, refresh ("scrape again") the
   market data and let the news outcome feed the **confidence/confluence**
   score (and/or block trading around the event).

> Explicitly deferred: build this only AFTER the entry/exit rework is validated
> live. This spec exists so the design is ready, not to start now.

## Goal

Make the bot news-aware: avoid trading into high-impact events by default, and
(optionally) use the release outcome as a confluence input, without
contaminating the existing strategy when the feature is off.

## Scope

- A **news data source** (economic calendar) with a normalized `NewsEvent`
  model (time, currency, impact, forecast/previous/actual).
- A **daily scheduled fetch** of upcoming events (+ intraday refresh as actuals
  print).
- A **news-blackout gate**: suppress (or widen SL / shrink size for) entries
  within a configurable window around high-impact events for the affected
  currencies.
- A **confidence modifier** (later phase): once an actual prints, factor the
  surprise (actual vs forecast) into confidence for trades in the news
  direction; "scrape data again" = force a fresh data pull post-release so
  signals use post-news candles, not stale ones.
- Config-gated (`enabled: false`); telemetry via `entry_tags` (which event,
  window, surprise) so impact is measurable.

## Non-goals (v1)

- Not a standalone news-trading/scalping strategy — first just *awareness* +
  *protection*. The "scalp the release" idea is a later phase.
- Not real-time tick news feeds / paid low-latency wires — calendar + periodic
  refresh is enough for H1/M30 day-trading.
- No NLP/sentiment on free-text headlines initially — structured calendar only.

## Open questions (resolve in design)

- Source: scrape (ForexFactory/Investing) vs API (e.g. a calendar API). Cost,
  reliability, ToS, timezone handling.
- Currency→symbol mapping (USD event affects EURUSD, USDJPY, XAUUSD, …).
- Blackout window per impact tier (e.g. high = ±30 min, medium = ±10 min).
- Does a release ENABLE a directional scalp, or only PROTECT (blackout)? Start
  protect-only; revisit after data.

## Acceptance criteria

- With the flag off, strategy output is byte-for-byte unchanged.
- With it on: entries inside a high-impact window for the affected currency are
  blocked (recorded as a `NEWS_BLACKOUT` rejection), and `entry_tags` carries
  the nearest-event context for trades that pass.
- Calendar fetch runs on schedule, persists events, survives source downtime
  (degrades to "no news data → no blackout", logged).
- Full test coverage on the gate + parser; backtestable (calendar replayable
  over historical windows).
