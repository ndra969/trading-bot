# News / Economic-Calendar Integration — Tasks

**Status**: 📋 Planned — do NOT start until entry/exit rework is validated live.
**Date**: 2026-06-25

Phased; every phase behind `news.enabled: false`. Strategy output must be
identical when the flag is off (golden test).

## Phase 0 — Source + parser (pure, offline) ✅ DONE 2026-06-27
- [x] `NewsSource` interface (`source.py`) + `InvestingScraper`
      (`investing_scraper.py`). Parse against SAVED fixture
      (`tests/fixtures/news/investing_calendar.html`) — no live network in tests.
- [x] Normalize to `NewsEvent`/`NewsImpact` (`models.py`): UTC-aware time
      (naive rejected), currency, impact tier, fcst/prev/actual as raw strings,
      `source_id` (Investing `occurrenceId`) for Phase-1 upsert.
- [x] Robust to schema drift: missing/invalid `__NEXT_DATA__` or store path →
      `NewsParseError` caught → empty list + warning; bad event skipped, rest
      survive. 24 unit tests, mypy/ruff clean.
- [x] **VERIFIED LIVE** 2026-06-27: end-to-end `fetch()` returns real events.
      Diagnostic/refresh tool: `scripts/fetch_investing_calendar.py [--save]`.
- New deps added to worker: `beautifulsoup4`, `tenacity`.

> ⚠️ DESIGN CHANGE (supersedes design.md "scrape HTML table"). Two surfaces on
> investing.com, verified live 2026-06-27:
> - Public page = Next.js; calendar is `__NEXT_DATA__` JSON, CURRENT DAY ONLY,
>   presentation classes hashed per build. Not used.
> - XHR filter endpoint `…/Service/getCalendarFilteredData` returns a DATE RANGE
>   for ALL countries as the classic, long-stable `tr.js-event-item` rows
>   (`data-event-datetime`, `td.flagCur|sentiment|event|act|fore|prev`). **This
>   is what the parser uses.** `source_id` = `eventRowId_<n>` (== homepage
>   `occurrenceId`). `timeZone=0` ⇒ times are GMT, stored as UTC.
> Requires realistic browser headers (Referer + Sec-Fetch-*) or it 403s.

## Phase 1 — persistence + fetch ✅ (scheduler wiring still pending)
- [x] `InvestingScraper.fetch()` pulls the upcoming 7 days day-by-day (stays
      under the endpoint's ~200-row cap, no pagination), dedups by `source_id`,
      returns sorted events. Live run: 498 events / 7 days, 17 high-impact.
- [x] `news_events` table (`NewsEventRecord` in core models) + Alembic migration
      `f3c8a1e6b9d2`. Naive-UTC storage (schema convention); unique `source_id`.
- [x] `NewsRepository` (worker side — maps domain↔ORM): idempotent
      `upsert_events` (key=source_id, fills `actual` on re-fetch),
      `get_in_window` (currencies × ±window × min_impact), `get_between`
      (backtest replay). 10 DB tests.
- [x] `NewsFetchService`: tenacity bounded retry (transient only: network/5xx/429,
      NOT hard 4xx), one Telegram ERROR after retries exhausted (no per-retry
      spam), success quiet; `from_config` builder; `is_stale` surfaced. 9 tests.
- [x] Config `news` block in default.yaml (enabled:false), loads cleanly.
- [x] Daily fetch job wired into the worker: `_news_fetch_loop` (mirrors
      `_heartbeat_loop`) — initial pull at startup + every
      `news.fetch_interval_hours` (default 24). Built by `_initialize_news_service`
      ONLY when `news.enabled` (else None, never scheduled). Dry-run verified:
      with the flag off the bot logs "News integration disabled" and starts
      clean — default path unchanged.
- [ ] STILL TODO (deferred to Phase 3-adjacent): intraday refresh near
      high-impact events (fill `actual` + force a fresh market-data pull). Left
      out here because the market-data-pull coupling belongs with the gate, not
      the data layer.
- Total news suite: 42 unit tests; ruff/black clean; mypy clean except the
  pre-existing `get_session` context-manager annotation shared with all repos.

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

## Phase 2 — NewsService + symbol mapping ✅ DONE 2026-07-01
- [x] `symbol_currencies` map (EURUSD→EUR,USD; USDJPY→USD,JPY; XAUUSD→USD;
      BTCUSD→USD; broker suffixes tolerated) — non-fiat legs drop out.
- [x] `NewsService` (`news_service.py`): `nearest_event` (closest high-impact in
      lookahead), `in_blackout` (tier-aware — high vs medium window, returns the
      triggering event + signed minutes), `confidence_adjustment` (pre-event
      dampen implemented; post-event surprise deferred to Phase 4 → neutral).
      Config-driven windows/dampen. 22 unit tests.
- Total news suite now: 64 tests; ruff/black/mypy clean. NOT wired into the
  strategy yet — Phase 3 is the first change that touches `foundation_engine`.

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
