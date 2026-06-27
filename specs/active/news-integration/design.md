# News / Economic-Calendar Integration — Design

**Status**: 📋 Planned
**Date**: 2026-06-25

## Source: scrape (Investing.com / ForexFactory calendar)

Per operator: scrape a public economic calendar (Investing.com preferred,
ForexFactory as fallback) rather than a paid API. Both expose a weekly/daily
calendar with: datetime, currency, impact (low/med/high), event name,
actual / forecast / previous.

- Respect ToS / robots; cache aggressively; one fetch/day + light intraday
  refresh (not a hammer). A scrape is brittle — isolate it behind a
  `NewsSource` interface so the parser can be swapped without touching
  consumers, and degrade safely when the page layout changes (log + "no news
  data" → no blackout, no confidence change).
- Timezone: store all event times in UTC; the calendar's local TZ must be
  normalized on parse (a frequent scrape bug).

## Data model

`NewsEvent` (persisted, e.g. `news_events` table):
`id, event_time_utc, currency, impact, name, forecast, previous, actual,
fetched_at`. `actual` is null until the release prints (filled by the intraday
refresh). Surprise = `actual - forecast` (normalized per event where possible).

## Components

```
NewsScraper (Investing/FF) ──parse──► NewsEvent[] ──► NewsRepository (DB)
                                                         │
            daily fetch + intraday refresh (scheduler)   │
                                                         ▼
                                                   NewsService
                                         ┌───────────┴────────────┐
                              (1) blackout gate          (2) confidence modifier
                              in foundation_engine        on the confluence score
```

- **NewsScraper / NewsSource**: fetch + parse → `NewsEvent[]`. Pure, testable
  against saved HTML fixtures.
- **NewsRepository**: upsert events; query "high-impact events for currency C
  within ±W minutes of time T".
- **NewsService**: the only thing the strategy talks to. Maps a symbol to its
  currencies (EURUSD → EUR, USD; XAUUSD → USD) and answers:
  `nearest_event(symbol, now)`, `in_blackout(symbol, now)`,
  `confidence_adjustment(symbol, direction, now)`.

## Scheduling

- **Daily fetch**: pull the upcoming week's calendar (cron/daily job — reuse the
  project's scheduling approach; a worker startup task + interval, mirroring the
  existing analysis loop).
- **Intraday refresh** ("scrape data again on each news"): around each known
  high-impact event time, re-scrape to capture the `actual`, and force a fresh
  **market-data** pull (download_data path) so the next signal evaluates
  post-release candles, not stale pre-news data.

## How it feeds confidence (the operator's main ask)

Two integration points in `foundation_engine`, both config-gated:

1. **Blackout gate (protect)** — within `±window` of a high-impact event for an
   affected currency, reject entries (new `RejectionStage.NEWS_BLACKOUT`). This
   alone removes the "open a bounce seconds before the spike" losses.

2. **Confidence modifier (inform)** — feed news into the confluence score as a
   first-class signal, e.g.:
   - Pre-event, high-impact pending → **dampen** confidence (uncertainty).
   - Post-event, actual printed → **boost** confidence for trades aligned with
     the surprise direction (e.g. USD-positive surprise supports USD-long
     setups), **dampen** for trades against it.
   Implement as a bounded multiplier/additive term on the final confluence,
   surfaced in `confluence_breakdown` like the other layers — never a silent
   override.

Default behavior with flag off: neither gate nor modifier runs; confluence is
identical to today.

## Config (`signal_generation.news` + `news`)

```yaml
news:
  enabled: false
  source: investing            # investing | forexfactory
  fetch_cron: "0 6 * * *"      # daily calendar pull
  refresh_around_events: true  # intraday re-scrape near high-impact events
  blackout:
    high:   {window_min: 30}
    medium: {window_min: 10}
  confidence:
    pre_event_dampen: 0.85     # multiplier when high-impact pending in window
    surprise_boost:   1.15     # aligned with a printed surprise
    surprise_dampen:  0.80     # against a printed surprise
```

## Telemetry

- `entry_tags.news`: nearest high-impact event (name, currency, minutes-to/from,
  surprise) + the applied adjustment. Makes "did news help?" measurable from
  day one, same as the new `h1_trend_bias` / layer attribution.
- `RejectionStage.NEWS_BLACKOUT` for suppressed entries.

## Backtest

`NewsRepository` is replayable: given a historical calendar, the harness can
apply the same blackout/confidence logic over past candles. Scrape once, store,
replay — so the news effect can be measured in-sample before going live.

## Risks

- Scrape fragility (layout changes, rate limits, ToS) — isolate + degrade safe.
- Lookahead bias in backtest: only use events whose `event_time_utc <= bar_time`
  (actuals) when replaying; never peek at a release before its candle.
- Over-fitting confidence multipliers on a few events — keep them coarse and
  backtest-validated; start protect-only (blackout) before the modifier.
