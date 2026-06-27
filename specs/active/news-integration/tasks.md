# News / Economic-Calendar Integration — Tasks

**Status**: 📋 Planned — do NOT start until entry/exit rework is validated live.
**Date**: 2026-06-25

Phased; every phase behind `news.enabled: false`. Strategy output must be
identical when the flag is off (golden test).

## Phase 0 — Source + parser (pure, offline)
- [ ] `NewsSource` interface + `InvestingScraper` (FF fallback). Parse against
      SAVED HTML fixtures — no live network in tests.
- [ ] Normalize to `NewsEvent` (UTC time, currency, impact, fcst/prev/actual).
- [ ] Robust to layout drift: parse failure → empty list + warning, never raise.

## Phase 1 — Persistence + fetch
- [ ] `news_events` table + Alembic migration; `NewsRepository` upsert/query.
- [ ] Daily calendar fetch job (reuse project scheduling); store upcoming week.
- [ ] Intraday refresh near high-impact events → fill `actual` + trigger a fresh
      market-data pull (download_data path).
- [ ] Bounded retry via **tenacity** (new dep): `stop_after_attempt(5)` +
      exponential backoff (~5/15/30/60 min); retry transient only, not 4xx/ToS.
- [ ] Telegram alerting via `NotificationManager`: ERROR once after retries
      exhausted; NO per-fetch / per-retry spam; `news_data_stale` flag surfaced
      in the daily report.

## Phase 2 — NewsService + symbol mapping
- [ ] Symbol→currencies map (EURUSD→EUR,USD; XAUUSD→USD; BTCUSD→USD…).
- [ ] `nearest_event`, `in_blackout`, `confidence_adjustment` — pure, unit-tested.

## Phase 3 — Blackout gate (protect-only first)
- [ ] Gate in `foundation_engine._passes_final_quality_filters`: reject inside
      `±window` of high-impact events for the symbol's currencies.
- [ ] `RejectionStage.NEWS_BLACKOUT` + `entry_tags.news` context.
- [ ] Config `news.blackout.{high,medium}.window_min`.

## Phase 4 — Confidence modifier (inform)
- [ ] Pre-event dampen + post-event surprise boost/dampen on the confluence
      score; surface in `confluence_breakdown` (no silent override).
- [ ] Config `news.confidence.*`; bounded multipliers.

## Phase 5 — Backtest + validation
- [ ] Replay stored calendar over historical candles (no lookahead: only
      actuals with `event_time <= bar_time`).
- [ ] Measure blackout-only vs blackout+modifier on EURUSD/USDJPY/XAUUSD/BTCUSD.
- [ ] Record table here; decide what (if anything) goes live.

## Phase 6 — Live (gated, staged)
- [ ] Enable blackout for one asset class; monitor via `entry_tags.news` split.
- [ ] Add the confidence modifier only if the backtest + live data support it.

## Decision log
- 2026-06-25: Source = scrape Investing.com (FF fallback), per operator — not a
  paid API. Primary purpose = feed CONFIDENCE (+ blackout protection), not a
  standalone news-scalp strategy in v1. Deferred until core strategy is stable.
