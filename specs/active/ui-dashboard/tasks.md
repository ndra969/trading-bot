# UI Dashboard — Task Breakdown

Backend first (data contract), then frontend against real endpoints.
Each phase is independently shippable.

## Phase 0 — Prerequisite (blocking)

- [ ] **[monorepo-restructure](../monorepo-restructure/tasks.md) must be
      DONE first.** It creates `packages/api/` and `apps/dashboard/`
      skeletons + the `trading_core` package this API imports. Do not
      start Phase 1 until the monorepo restructure has landed and the
      bot dry-run is verified green.

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
- [ ] `api/schemas.py`: Pydantic response models (PositionOut,
      AccountSummary, SessionOut, AnalyticsRow, EquityPoint, etc.) with
      `currency_unit` field.
- [ ] `api/app.py`: app factory, CORS for `localhost:3000`, mount
      routers, `/api/v1/health`.
- [ ] Shared cent-detection helper (factor out from TradingBot or
      duplicate the small "cent in broker name" check).

### Routers
- [ ] `routers/positions.py`: `/open`, `/closed`.
- [ ] `routers/account.py`: `/summary`.
- [ ] `routers/sessions.py`: `/sessions`.
- [ ] `routers/signals.py`: `/recent`.
- [ ] `routers/analytics.py`: `/by-asset`, `/by-session`,
      `/by-close-reason`, `/equity-curve`.

### Tests (mandatory — API gates like the bot does)
- [ ] Add `syrupy` to dev deps.
- [ ] `packages/api/tests/` (or `tests/api/`) with FastAPI TestClient +
      mocked repositories/DB session (never hit a real DB).
- [ ] Per endpoint: happy path + empty-data + error + currency-unit.
- [ ] syrupy snapshot assertions on each endpoint's JSON shape; explicit
      assertions for P&L math + currency unit (don't let snapshots mask
      business-critical fields).
- [ ] `uv run pytest tests/api/ --cov=trading_api` → ≥85%.

### Verify
- [ ] `uv run uvicorn trading_api.app:app --port 8000`, hit each
      endpoint + open `/docs` (Swagger) + `/redoc`, confirm live shape.
- [ ] Commit: `feat(api): read-only dashboard endpoints + tests`.

## Phase 3 — Frontend scaffold (~1-2 hr)

- [ ] `npx create-next-app@latest frontend --ts --app --no-tailwind`
      (or with tailwind if preferred).
- [ ] `lib/api.ts`: typed fetch client + `usePoll(endpoint, ms)` hook.
- [ ] `.env.local`: `NEXT_PUBLIC_API_BASE=http://localhost:8000`.
- [ ] Base layout + nav (Overview / Positions / History / Analytics).
- [ ] Health-check banner (API reachable?).
- [ ] Commit: `feat(frontend): Next.js scaffold + API client`.

## Phase 4 — Dashboard pages (~3-4 hr)

- [ ] **Overview**: account summary cards (balance/equity/open count
      with currency unit), open positions table, today P&L.
- [ ] **Positions**: open + closed tables with symbol/reason filters.
- [ ] **History**: closed trades + close_reason breakdown chart.
- [ ] **Analytics**: WR by asset / session / close_reason; equity curve
      (lightweight-charts); confluence distribution.
- [ ] Currency unit labels everywhere (USC/USD from API).
- [ ] Loading / empty / error states per page.
- [ ] Commit: `feat(frontend): dashboard pages`.

## Phase 5 — Polish & docs (~1 hr)

- [ ] Auth stub: `X-Dashboard-Token` middleware (disabled for localhost,
      documented as required-before-remote).
- [ ] `docs/guides/dashboard-guide.md`: how to run backend + frontend.
- [ ] README/CLAUDE.md note on the dashboard.
- [ ] Move this spec to `specs/archive/YYYY-MM/`; update specs/README.md.

## Effort estimate

- Phase 1: 0.5 hr
- Phase 2 (API + tests): 2-3 hr
- Phase 3 (frontend scaffold): 1-2 hr
- Phase 4 (pages): 3-4 hr
- Phase 5 (polish): 1 hr
- **Total: ~8-11 hr** across multiple sessions (backend can land
  independently of frontend).

## Sequencing notes

- Phase 2 (API) is the critical dependency — ship + verify it before
  building frontend so the data contract is stable.
- Frontend phases (3-4) can be done in a separate session.
- Keep each commit green (`pytest` for backend, `npm run build` for
  frontend) so a revert is always clean.

## Tests-to-watch

- Full existing `tests/unit/` must stay green after Phase 1-2 (monorepo
  restructure should not touch bot imports).
