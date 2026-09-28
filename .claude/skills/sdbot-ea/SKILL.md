---
name: sdbot-ea
description: Build, modify, review or test the SDBot MQL5 Expert Advisor (Supply & Demand + confluence) in sdbot/ea/. Use for any .mq5/.mqh work, EA inputs/.set presets, Strategy Tester scenarios, shared SQLite schema changes that touch the EA, or when the user mentions SDBot, the EA, MQL5, MetaEditor or MT5 Strategy Tester. Not for the Python bot in packages/.
argument-hint: [module|task, e.g. "Risk/RiskManager" or "fase 1"]
---

# SDBot EA (MQL5)

SDBot is a standalone project inside `sdbot/`. The Python bot rules in the root
`CLAUDE.md` (pytest, black, YAML config, pip values, 8-layer weights) do **not**
apply here. `sdbot/CLAUDE.md` and the three docs below are the source of truth.

| Doc | Read it for |
|-----|-------------|
| [sdbot/docs/PRD-EA.md](../../../sdbot/docs/PRD-EA.md) | Behaviour: pipeline, scoring, execution, position mgmt, risk, notifications, DB tables, inputs, acceptance tests, roadmap |
| [sdbot/docs/RULES.md](../../../sdbot/docs/RULES.md) | Folder layout, layer/dependency rules, naming, mandatory safety rules, logging, testing, git, definition of done |
| [sdbot/docs/PRD-Backoffice.md](../../../sdbot/docs/PRD-Backoffice.md) | Only when touching Control/, Storage/ backoffice tables, or `shared/schema/` |

## Before writing code

1. Identify the module(s) from the task (`$ARGUMENTS` if given) and the roadmap
   phase in PRD-EA "Roadmap". Do not build a later phase on a missing earlier
   one (e.g. strategies before Fase 1 foundation).
2. Read the PRD-EA section for that behaviour **and** the RULES sections
   "Lapisan dan aturan dependensi" + "Aturan wajib keamanan trading". Quote
   the numbers from the PRD; never invent thresholds.
3. If the PRD leaves it open ("Keputusan terbuka"), ask the user instead of
   choosing silently.

## Layout (ea/src mirrors MQL5/)

```
sdbot/ea/src/Experts/SDBot/SDBot.mq5          event orchestration only
sdbot/ea/src/Include/SDBot/<Layer>/<Name>.mqh one class per file, file = class name without C
sdbot/ea/src/Scripts/SDBot/                   ExportCalendar, ResetState
sdbot/ea/src/Presets/                         .set files, secrets left empty
sdbot/ea/tests/Scripts/SDBotTests/            unit-test scripts (pure functions)
sdbot/ea/tests/scenarios/                     Strategy Tester .ini files
```

Layers: Core · Account · Risk · Analysis · Strategies · Signals · Filters ·
Execution · Position · Control · Notify · Storage · UI.

## Hard rules (violations = critical bug)

Ownership: only **Execution** calls `CTrade` · only **Storage** writes
`sdbot.sqlite` · only **Notify** calls `WebRequest`/`SendNotification` ·
only **Core/Inputs.mqh** declares `input`. Upper layers use lower ones, never
the reverse (see RULES table). Modules talk via structs in `Core/Types.mqh`,
not globals. Notify/Storage errors are logged and never stop trading.

Orders & positions:
- Every order carries SL **and** TP, the MagicNumber, and its `ResultRetcode()` is checked.
- Lot = balance × risk% ÷ money value of SL distance (`OrderCalcProfit()`), rounded **down** to `SYMBOL_VOLUME_STEP`; below `SYMBOL_VOLUME_MIN` → reject, never round up.
- SL/TP normalized to symbol digits and checked against stops level + freeze level.
- SL only moves in the favourable direction; modify rejects a worse SL.
- Position loops filter magic **and** symbol. State (BE done, partial done) is inferred from the position itself so restarts are safe.
- SL/TP live on the broker server; the EA detects closes via `OnTradeTransaction`, it does not close on SL/TP itself.

Risk:
- Risk pre-trade check before every entry, in PRD order: STOPPED/pause → risk per trade → total open risk → currency exposure → margin.
- Risk monitor runs in `OnTimer`, independent of signals. Peak equity, STOPPED, pause live in terminal Global Variables `SDB_<login>_<NAME>`.
- STOPPED is cleared only via `InpResetEmergencyStop` (or panel RESET_EMERGENCY using the same path), never automatically.
- No fixed money amounts; everything is percent with a `Pct` suffix (0.5 = 0.5%). `InpAllowLiveTrading` defaults to `false`.

Data & analysis:
- Analyse closed bars only (shift ≥ 1); recompute a TF only on its new bar. No repainting indicators (no ZigZag) — swings from Fractals with bar delay.
- Indicator handles created in `OnInit`, checked for `INVALID_HANDLE`, released in `OnDeinit`; never in `OnTick`. Check `CopyRates`/`CopyBuffer` counts.
- Zones are rebuilt from history in `OnInit`, never loaded from DB (no backtest leakage).
- `MQL_TESTER`: no WebRequest, no calendar calls (news filter uses CSV). `MQL_OPTIMIZATION`: no DB logging.
- Prices in **points**, not pips. The Python `PIP_VALUES` table does not apply.

## Style

| Element | Format | Example |
|---|---|---|
| Class | `C` + PascalCase | `CRiskManager` |
| Struct | PascalCase | `TradingSignal` |
| Enum / value | `ENUM_SDB_` / `SDB_` + UPPER_SNAKE | `ENUM_SDB_ZONE_STATUS` / `SDB_ZONE_FRESH` |
| Method | PascalCase verb-first | `CalcLotSize()` |
| Member / local | `m_camelCase` / `camelCase` | `m_peakEquity` / `stopDistance` |
| Input | `Inp` + PRD name | `InpRiskPerTradePct` |
| Constant | `SDB_` + UPPER_SNAKE in `Core/Constants.mqh` | `SDB_MAX_RETRY` |
| Include guard | `SDB_<FOLDER>_<FILE>_MQH` | `SDB_RISK_RISKMANAGER_MQH` |

Every `.mqh` starts with its include guard and a one-line purpose comment.
Functions ≲ 50 lines. No magic numbers: inputs or `Core/Constants.mqh`. Every
`new` has a matching `delete`. Comments explain *why*. All logging through
`Core/Utils.mqh` (`LogInfo`, `LogWarn`, …), never raw `Print`, in the format
`[SDB][LEVEL][Module][Symbol] message | key=value`, with the error code.
Retry only transient errors (requote, price changed, busy), max 3× with delay.

Template for a new module: [templates/Module.mqh](templates/Module.mqh).
Template for a unit-test script: [templates/UnitTest.mq5](templates/UnitTest.mq5).

## Verify

1. **Compile, 0 errors and 0 warnings.** Compiling needs MetaEditor on this
   Windows machine and the junctions from `sdbot/tools/link-mt5.ps1`. Find
   `metaeditor64.exe` (usually beside `terminal64.exe` of the MT5 install),
   then compile through the MQL5 data folder so `#include <SDBot/...>` resolves:
   ```powershell
   & "<MT5 dir>\metaeditor64.exe" /compile:"<MQL5>\Experts\SDBot\SDBot.mq5" /log:"$env:TEMP\sdbot_compile.log"
   Get-Content "$env:TEMP\sdbot_compile.log" -Encoding Unicode | Select-String "error|warning|result"
   ```
   If MetaEditor or the junctions aren't found, say so and ask the user to
   press F7. Never claim it compiles without a compile log showing 0/0.
2. **Unit tests**: every new pure function gets test cases (IDs from the
   spec's design catalogue) in a suite under
   `ea/tests/Include/SDBotTests/Suites/`, written **before** the function
   (Red → Green). Run them with `sdbot/tools/run-ea-tests.ps1 -Unit` (built in
   spec `ea-01-tooling`; exit 0 = all pass). Until that runner exists, or if it
   reports the environment is not ready, ask the user to run the
   `RunUnitTests` script on a chart and paste the result.
3. **Scenario**: behaviour that needs real positions is proven by a harness
   scenario `SC-nn` with automatic asserts, run by
   `run-ea-tests.ps1 -Scenario SC-nn`. Only what the tester cannot simulate goes
   to `ea/tests/manual-checklist.md` (`MC-nn`).
4. Every bug fix starts with a test that reproduces it.

## Definition of done (EA side)

- [ ] Compile 0 errors / 0 warnings; unit tests ALL PASS
- [ ] No dependency, ownership or safety-rule violation (re-read the list above against the diff)
- [ ] New input added in `Core/Inputs.mqh`, the PRD input table, and the example `.set`
- [ ] Schema change: `shared/schema/*.sql` + `schema_version` + `Storage/Schema.mqh` + `Control/ControlReader.mqh` + API repo + fixtures in one change
- [ ] Logic change: `sdbot/docs/flows/` diagram, PRD and `sdbot/CHANGELOG.md` updated; `#property version` bumped (MAJOR.MINOR)
- [ ] No token, chat ID or MetaQuotes ID in any committed file (`.set` included; private presets use `*.local.set`)

Commit format: Conventional Commits with the repo part as scope, e.g.
`feat(ea/position): trailing berbasis ATR`, `fix(ea/risk): ...`, `chore(shared): skema v3`.
The Python test hooks in `.pre-commit-config.yaml` are scoped with `files:` to
`packages/`, `tests/unit/`, `config/`, `alembic/`, so SDBot-only commits skip
them; the generic hooks (whitespace, EOF, JSON/YAML) still run. No `--no-verify`.
