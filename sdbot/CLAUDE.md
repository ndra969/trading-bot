# CLAUDE.md — SDBot

SDBot: MQL5 Expert Advisor for MT5 (Supply & Demand zones + confluence score),
plus a local backoffice (FastAPI + Next.js) that shares SQLite files with the EA.
Separate from the Python bot in `../packages/`. The root rules for Python code,
YAML config, pip values and strategy weights **do not apply here**.

**Status**: planning done, no code yet. Start at EA roadmap Fase 1 (foundation).

**Decided (2026-09-28, PRD-EA "Temuan review dan keputusan")**: day trading
(H4/H1/M15) · simbol = simbol aktif bot Python (12 simbol forex/komoditas/crypto, PC-10; semula 4 pair) · entry Market (default) + Limit
option, Adaptive only if backtests prove it · Exness cent, USC, hedging
(`SymbolSuffix = c`); EA refuses netting accounts.

## Source of truth

| Doc | Content |
|-----|---------|
| [docs/PRD-EA.md](docs/PRD-EA.md) | EA behaviour, inputs, DB tables, acceptance tests, roadmap |
| [docs/RULES.md](docs/RULES.md) | Folder layout, layers, naming, safety rules, testing, git, definition of done |
| [docs/PRD-Backoffice.md](docs/PRD-Backoffice.md) | API + admin panel, SQLite contract, commands/settings |

The masters are Claude Docs on claude.ai (links at the top of each file); the
files here are read-only copies. Approved changes go to `docs/PENDING-CHANGES.md`
and are synced with the `sdbot-docs-sync` skill. Never edit the copies directly.
Numbers (risk %, R multiples, scores, timeouts) come from the PRDs. Never
invent them. Open decisions ("Keputusan terbuka") go to the user.

**Workflow**: spec-driven (Kiro method) with the `sdbot-spec` skill. Every feature or
roadmap phase gets `specs/<feature>/{requirements,design,tasks}.md`, each approved by
the user before the next; code only when executing an approved task, one task at a
time. For the EA code itself, use the `sdbot-ea` skill.

Configuration map (inputs, presets, constants, panel settings, local files) and the tuning
flow live in [README.md](README.md#konfigurasi-dan-tuning). Keep that table current when an
input, preset, or constant is added.

## Layout

```
sdbot/
  specs/       README.md (urutan spec) · fase-N-overview.md (use case) · ea-NN-<name>/{requirements,design,tasks}.md
  docs/        PRD-EA, PRD-Backoffice, RULES, flows/ (Mermaid), decisions/ (ADR)
  shared/schema/  data_db.sql (EA writes) · control_db.sql (API writes) · enums.md · fixtures/
  ea/src/      mirrors MQL5/: Experts/SDBot/SDBot.mq5 · Include/SDBot/<Layer>/ · Scripts/SDBot/ · Presets/
  ea/tests/    Scripts/SDBotTests/ (unit) · scenarios/ (Strategy Tester .ini)
  backoffice/  api/ (FastAPI, uv) · web/ (Next.js, pnpm)
  tools/       link-mt5.ps1 · start-backoffice.ps1 · gen-api-types.ps1 · queries/
  reports/     backtest output, not committed
```

`ea/src` is linked into the MT5 data folder with junctions (`tools/link-mt5.ps1`,
repo path `D:\Workspaces\trading-bot\sdbot\ea\src`). Edit in the repo, compile in MetaEditor.

## Non-negotiables

- **Single writer**: EA → `sdbot.sqlite`; API → `sdbot_control.sqlite`. EA only reads control; API opens data `?mode=ro`. Both WAL. Times are UTC epoch seconds.
- **EA stands alone**: backoffice down, missing or mismatched schema → EA keeps trading on MT5 inputs and sends one Info alert. Backoffice never sends orders.
- **Panel can only tighten**: panel settings are clamped to the MT5 input limits.
- **`shared/schema/` is the contract**. A schema change bumps `schema_version` and updates `shared/schema`, `Storage/Schema.mqh`, `Control/ControlReader.mqh`, API repositories and fixtures in one change. Enum values follow `shared/schema/enums.md` exactly.
- **No secrets in git**: Telegram token/chat ID and MetaQuotes ID only in MT5 inputs (`*.local.set` is ignored); API secret only in `backoffice/api/.env`.
- The EA order/risk/data safety rules are in `docs/RULES.md` and the `sdbot-ea` skill. Breaking one is a critical bug, even in an experiment.

## Backoffice (when built)

- API: Python 3.12+, uv, ruff, mypy strict, pytest on fixture DBs only. `routers/ → services/ → repositories/`, Pydantic in and out, parameterized SQL, every write logged to `audit_log`, config from `.env` via pydantic-settings. Listen on `127.0.0.1` only.
- Web: TypeScript strict, pnpm, ESLint + Prettier. API types generated from OpenAPI; all calls via `src/lib/api/`. Dangerous actions (`CLOSE_ALL`, `RESET_EMERGENCY`) use the shared confirm dialog.
- Build order: B1 contract → B2 read API → B3 monitoring panel → B4 auth/audit → B5 settings → B6 commands (last).

## Git

- Conventional Commits, scope = repo part: `feat(ea/position): …`, `fix(api): …`, `feat(web): …`, `chore(shared): skema v3`.
- EA version `MAJOR.MINOR` in `#property version`. MAJOR = affects open positions or DB schema.
- Releases go in `CHANGELOG.md` (EA and Backoffice sections, backtest summary for EA releases).
- Branching per RULES (`main` / `dev` / `feat/*`) is SDBot's target model. In this monorepo, follow the user's branch choice.
