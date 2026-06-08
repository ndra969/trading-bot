# UI Dashboard — Task Breakdown

Backend first (data contract), then frontend against real endpoints.
Each phase is independently shippable.

> **Progress (2026-06-05).** Phases 0, 1.5, 1.6, and 2 are **DONE & merged**:
> monorepo skeleton, confluence-breakdown persistence, rejection telemetry
> (table + recorder + 26 instrumented sites + per-cycle flush), and the full
> read-only API (positions / analytics / rejections / account / sessions /
> config + health, 24 tests, live-DB smoke). Next up: **Phase 3-4 frontend**,
> following `reference/polyforge` conventions (see design.md → Tech stack +
> Frontend → API transport).

## Phase 0 — Prerequisite (blocking)

- [x] **[monorepo-restructure](../../archive/2026-05/monorepo-restructure/)
      DONE** (archived 2026-05). `packages/{core,worker,api}` +
      `apps/dashboard` exist; `packages/api/src/trading_api/__init__.py`
      is in place. Bot dry-run verified green.

## Phase 1.5 — Worker observability (confluence breakdown) (~30 min)

Prereq for the Tuning view + trade drill-down (requirements Goal 7).

- [ ] In the worker signal path (`foundation_engine._build_strategy_result`,
      where `meta_data` is assembled), persist
      `meta_data["confluence_breakdown"] = {foundation_share,
      enhancement_share, raw_confidences: {layer: conf}, active_layers}`.
- [ ] Snapshot/regression test the signal path: assert the returned
      signal `score` and direction are byte-identical before/after — the
      write must not touch scoring.
- [ ] Confirm a fresh dry-run / live trade writes the breakdown to a new
      `positions` row (old rows legitimately lack it).
- [ ] Commit: `feat(worker): persist confluence breakdown to meta_data`.

## Phase 1.6 — Rejection telemetry (Goal 9) (~1.5 hr)

Prereq for the Rejections view. Observability only — must not change which
setups are rejected.

- [ ] `trading_core`: add `SignalRejection` model + alembic migration
      (`signal_rejections`: id, created_at[idx], symbol[idx],
      asset_class[idx], direction, stage, confluence_score?, details JSON).
- [ ] Define a stable `RejectionStage`/reason enum in `trading_core`
      (shared by the worker writer AND the API grouping so they never
      drift): climax, pa_wrong_direction, anti_chase, confluence_too_low,
      counter_trend_gate, volume_burst, color_match, rejection_wick,
      rsi_gate, structure_gate, falling_knife, …
- [ ] `record_rejection(stage, ctx)` helper called at each existing
      `return None` rejection site in the signal path. Fire-and-forget:
      wrap so any telemetry error is swallowed (never raises into the
      loop); gate on config `telemetry.rejections_enabled` (default true).
- [ ] Retention prune: delete rows older than
      `telemetry.rejection_retention_days` (default 30), run periodically.
- [ ] Regression test: signal output (taken/rejected + score) is
      byte-identical with telemetry ON vs OFF. Unit-test the helper +
      retention prune.
- [ ] (Optional) batch INSERTs per cycle if profiling shows loop latency.
- [ ] Commit: `feat(worker): record signal rejection telemetry`.

## Phase 1 — Dashboard scaffolding (~30 min)

- [ ] Add `apps/dashboard/.next/`, `node_modules/`, `out/` to
      `.gitignore` (if monorepo spec didn't already).
- [ ] Confirm `packages/api/src/trading_api/__init__.py` exists (from
      monorepo spec) and `uv run python -c "import trading_api"` works.
- [ ] Confirm `trading_api` can import `trading_core.data.repositories`.
- [ ] Commit: `chore(api): confirm dashboard api scaffold`.

## Phase 2 — Read-only API (~2-3 hr)

### Backend foundation
- [ ] `api/deps.py`: read-only async DB session dependency (separate
      engine, never writes).
- [ ] Shared query helpers: `parse_time_range(since, until)` and a
      `Page`/pagination envelope (`{items,total,limit,offset}`) used by all
      list endpoints. `limit` default 50 / max 500; `offset` default 0.
- [ ] `api/schemas.py`: Pydantic response models (PositionOut,
      PositionDetail, AccountSummary, SessionOut, AnalyticsRow,
      SymbolStatRow, EquityPoint, ConfluenceBucket, LayerContribRow,
      RejectionRow, Page[T], etc.) with `currency_unit` where money appears.
- [ ] `api/app.py`: app factory, CORS for `localhost:3000`, mount
      routers, `/api/v1/health`.
- [ ] Shared cent-detection helper (factor out from TradingBot or
      duplicate the small "cent in broker name" check).
- [ ] Push aggregation (GROUP BY asset/symbol/bucket/reason) to SQL via
      thin read repos; no full-table scans in Python.

### Routers (all historical endpoints honour `since`/`until`/`symbol`)
- [ ] `routers/positions.py`: `/open`; `/closed` (paginated envelope;
      filters symbol, exit_type, close_reason, since/until);
      `/{position_id}` drill-down (quality metrics + confluence_breakdown;
      `404` if unknown).
- [ ] `routers/account.py`: `/summary` (exposure = Σ open `risk_amount_usd`).
- [ ] `routers/sessions.py`: `/sessions` (paginated envelope).
- [ ] `routers/analytics.py`: `/by-asset`, `/by-symbol`, `/by-session`,
      `/by-close-reason`, `/by-exit-type`, `/equity-curve`,
      `/confluence-distribution`, `/confluence-vs-outcome`,
      `/layer-contribution` (report `coverage` = fraction of rows carrying
      a breakdown).
- [ ] `routers/rejections.py`: `/by-reason`, `/by-symbol`,
      `/recent` (paginated). Reuses the shared `RejectionStage` enum.
- [ ] `routers/config.py`: `/config/thresholds` — read the loaded
      `signal_generation` config (quality_thresholds + confluence_weights
      + volatility_filter + commodity_gates), read-only, loaded once at
      startup.
- [ ] (Removed) no `signals.py` — signals are not a persisted entity
      (see requirements Non-goals); "what's happening now" = open positions
      + rejection feed.

### Tests (mandatory — API gates like the bot does)
- [ ] Add `syrupy` to dev deps.
- [ ] `packages/api/tests/` (or `tests/api/`) with FastAPI TestClient +
      mocked repositories/DB session (never hit a real DB).
- [ ] Per endpoint: happy path + empty-data (200 + `[]`/empty page, not
      404) + error + currency-unit.
- [ ] Pagination: envelope shape, `total` correctness, limit/offset
      clamping (max 500). Time-range: `since`/`until` filtering applied.
- [ ] `/positions/{id}`: 404 on unknown id; breakdown present vs
      "unavailable" (old row) both covered.
- [ ] `layer-contribution`/tuning: `coverage` field reflects rows lacking
      the breakdown.
- [ ] syrupy snapshot assertions on each endpoint's JSON shape; explicit
      assertions for P&L math + currency unit (don't let snapshots mask
      business-critical fields).
- [ ] `uv run pytest tests/api/ --cov=trading_api` → ≥85%.

### Verify
- [ ] `uv run uvicorn trading_api.app:app --port 8000`, hit each
      endpoint + open `/docs` (Swagger) + `/redoc`, confirm live shape.
- [ ] Commit: `feat(api): read-only dashboard endpoints + tests`.

## Phase 3 — Frontend scaffold (~2 hr)

Mirror `reference/polyforge/frontend/nextjs` conventions (cloned locally,
gitignored). Port its patterns; skip its auth/Firebase/i18n.

- [ ] `create-next-app` into `apps/dashboard` (`--ts --app --tailwind`,
      `src/` dir, import alias `@/*`). Tailwind v4.
- [ ] shadcn/ui init; add the primitives we use (button, card, table,
      dialog/drawer, select, badge, skeleton, toast). `lib/utils.ts` → `cn()`.
- [ ] **Proxy route** `src/app/api/proxy/[...path]/route.ts` forwarding
      `/api/proxy/*` → `${API_URL}/*` (server-side). `.env.local`:
      `API_URL=http://localhost:8000` (NOT `NEXT_PUBLIC_*`).
- [ ] `lib/api.ts`: `apiFetch<T>()` + `ApiError` (same-origin `/api/proxy`),
      and `lib/usePoll.ts` (tiered: live 3 s, history 15 s, analytics/tuning/
      rejections 60 s + manual refresh).
- [ ] `types/api.ts`: TS types mirroring the Pydantic schemas
      (OpenPosition, ClosedPosition, PositionDetail, Page<T>, StatRow,
      Confluence*, Rejection*, AccountSummary, SessionOut, ThresholdsOut).
- [ ] Port `features/theme` + `features/toast`; `(dashboard)/layout.tsx`
      with `Sidebar` (Overview/Positions/History/Analytics/Tuning/Rejections)
      + `Topbar`; shared `TimeRangePicker` (24h/7d/30d/since/all → since/until),
      `Pagination`, `StatusDot`, skeletons.
- [ ] Health banner (poll `/api/v1/health` via proxy).
- [ ] `npm run build` green. Commit: `feat(frontend): Next.js scaffold + API client (polyforge conventions)`.

## Phase 4 — Dashboard pages (~3-4 hr)

- [ ] **Overview**: account summary cards (balance/equity/open count/
      exposure with currency unit), open positions table, today P&L.
- [ ] **Positions**: open positions table; row → drill-down drawer.
- [ ] **History**: paginated closed trades (envelope + pager) +
      close_reason/exit_type breakdown charts; filters (symbol, exit_type,
      close_reason) + time-range picker.
- [ ] **Trade drill-down** (shared drawer, used by Positions + History):
      full quality metrics + confluence/per-layer breakdown from
      `/positions/{id}`. Show "breakdown unavailable" for old rows.
- [ ] **Analytics**: sortable **per-symbol** P&L/WR table (headline) +
      by asset / session / close_reason / exit_type; equity curve
      (lightweight-charts); time-range picker.
- [ ] **Tuning**: asset-class selector → confluence histogram with the
      current threshold line (`/config/thresholds`), WR-by-confluence-
      bucket + WIN-avg vs LOSS-avg, per-layer contribution bars (+ coverage
      note), and a read-only active-gates panel (climax multipliers +
      per-direction commodity_gates). Read-only banner.
- [ ] **Rejections**: by-reason bar chart + per-symbol×reason matrix +
      paginated recent-rejections table; symbol filter + time-range picker;
      "data since <date>" note.
- [ ] Currency unit labels everywhere (USC/USD from API).
- [ ] Loading / empty / error states per page.
- [ ] Commit: `feat(frontend): dashboard pages, tuning + rejections views`.

## Phase 5 — Polish & docs (~1 hr)

- [ ] Auth stub: `X-Dashboard-Token` middleware (disabled for localhost,
      documented as required-before-remote).
- [ ] `docs/guides/dashboard-guide.md`: how to run backend + frontend.
- [ ] README/CLAUDE.md note on the dashboard.
- [ ] Move this spec to `specs/archive/YYYY-MM/`; update specs/README.md.

## Effort estimate

- Phase 1: 0.5 hr
- Phase 1.5 (worker breakdown persistence + test): 0.5 hr
- Phase 1.6 (rejection telemetry: model + migration + writer + test): 1.5 hr
- Phase 2 (API: ~15 endpoints + pagination/time-range + tests): 4-5 hr
- Phase 3 (frontend scaffold + time-range picker + tiered poll): 1.5-2 hr
- Phase 4 (pages incl. Tuning + Rejections + drill-down): 5-6 hr
- Phase 5 (polish): 1 hr
- **Total: ~14-17 hr** across multiple sessions. Land Phase 1.5 + 1.6
  EARLY so live trades start accumulating breakdown + rejection data —
  the Tuning/Rejections views are empty until then and cannot be
  backfilled.

## Sequencing notes

- Phases 1.5 + 1.6 (worker observability) should ship first and quietly —
  they only start collecting forward, so every day of delay is a day of
  missing tuning data.
- Phase 2 (API) is the critical dependency — ship + verify it before
  building frontend so the data contract is stable.
- Frontend phases (3-4) can be done in a separate session.
- Keep each commit green (`pytest` for backend, `npm run build` for
  frontend) so a revert is always clean.

## Tests-to-watch

- Full existing `tests/unit/` must stay green after every worker-touching
  phase (1.5, 1.6).
- Signal-path snapshot/regression: identical taken/rejected + score with
  observability writes (breakdown + rejection telemetry) ON vs OFF.
