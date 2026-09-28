---
name: sdbot-spec
description: Spec-driven development for SDBot using the Kiro method — requirements (user stories + EARS acceptance criteria) → design → tasks, each gated by explicit user approval, then implement one task at a time. Use when the user wants to plan, spec, or start a new SDBot feature/roadmap phase, asks for a spec, or says "lanjut task berikutnya" on an SDBot spec. Code is written only in the execute phase.
argument-hint: <feature-name> [requirements|design|tasks|execute <n>]
---

# SDBot spec workflow (Kiro method)

A roadmap phase is split into several small specs that are built **in order**,
each one testable on its own. The index with order, dependencies and status is
`sdbot/specs/README.md`; the phase's use cases and shared architecture are in
`sdbot/specs/fase-<n>-overview.md`. Spec folders are numbered in build order,
`sdbot/specs/ea-NN-<name>/` (e.g. `ea-05-risk`):

```
sdbot/specs/<feature-name>/
  requirements.md   WHAT — user stories + EARS acceptance criteria
  design.md         HOW  — architecture, components, interfaces, data, errors, tests
  tasks.md          STEPS — checklist of coding tasks traced to requirements
```

**Steering** (Kiro's always-on context) is already in the repo. Read it before
any phase, and never contradict it in a spec:
- product → `sdbot/docs/PRD-EA.md`, `sdbot/docs/PRD-Backoffice.md`
- tech + structure → `sdbot/docs/RULES.md`, `sdbot/CLAUDE.md`, the `sdbot-ea` skill

Also read `sdbot/specs/python-bot-lessons.md`: bugs and findings from the
Python bot that a spec in the same area must prevent or measure.

A spec narrows the PRD to one deliverable. It does not change product
decisions. If the spec needs a PRD change, say so and ask; update the PRD
(Claude Docs master + `sdbot/docs/` copy) only after the user agrees.

## Phases and gates

Work strictly in order. **After writing each document, stop and ask the user to
review it.** Move to the next phase only after an explicit approval ("ok",
"lanjut", "approve"). A requested change → revise the same document and ask
again. Never write the next document in the same turn as the previous one.
Never write EA code before `tasks.md` is approved.

| Phase | Output | Ends with |
|---|---|---|
| 0. Use cases + split (once per roadmap phase) | `fase-<n>-overview.md` (actors, use cases with main/alternative flows, use case → spec table, shared architecture, test strategy) + rows in `README.md` | "Use case dan pembagian spec sudah sesuai?" |
| 1. Requirements | `requirements.md` | "Requirements sudah sesuai? Kalau ya, saya lanjut ke design." |
| 2. Design | `design.md` | "Design sudah sesuai? Kalau ya, saya lanjut ke tasks." |
| 3. Tasks | `tasks.md` | "Tasks sudah sesuai? Kalau ya, spec siap dieksekusi." |
| 4. Execute | code + tests for **one** task | report, tick the box, stop |

Break down use cases **before** splitting into specs: the split follows layers
that can be built and tested alone, in dependency order (tooling → core →
storage → execution → risk → position → integration for Fase 1).

The user may ask to draft requirements and design of several specs at once
(as for Fase 1). Then each spec still gets its own approval, in build order,
and `tasks.md` of a spec is written only after its requirements and design
are approved.

Write a first draft from the PRD without a round of questions first. Put real
unknowns in "Pertanyaan terbuka" at the end of the document instead.
Spec documents are in Indonesian (like the PRDs). Identifiers, file names and
MQL5 terms stay as in the code.

## 1. requirements.md

```markdown
# Requirements — <Feature>

Status: Draft | Approved (YYYY-MM-DD)
Use case: UC-xx, UC-yy (link ke overview)
Asal: PRD-EA §<section>, RULES §<section>, python-bot-lessons §<n>
Butuh: spec <nomor> (yang harus selesai dulu)

## Pendahuluan
<2–4 kalimat: apa yang dibangun, batas lingkup, yang TIDAK termasuk,
dan bukti selesai (suite/skenario yang harus PASS).>

## Glosarium
- **R**: jarak SL awal dari entry …

## Requirements

### Requirement 1: <nama>
**User story:** Sebagai <trader/operator>, saya ingin <kemampuan>, agar <manfaat>.

#### Acceptance criteria
1. KETIKA <pemicu> MAKA EA WAJIB <respons>.
2. JIKA <kondisi tak diinginkan> MAKA EA WAJIB <respons>.
3. SELAMA <keadaan> EA WAJIB <respons>.

## Edge case

| ID | Kondisi | Perilaku | Kriteria |
|---|---|---|---|
| EC-01 | <kondisi tepi yang realistis> | <perilaku yang diharapkan> | 1.2 |

## Pertanyaan terbuka
- …
```

Edge cases are mandatory. Think through, for the area in scope: restart and
crash mid-operation, several instances on one account at the same moment,
terminal start before login, disconnect, weekend/market closed, broker
rejects and ambiguous replies, gaps and spread spikes, minimum lot on the
cent account, JPY pairs (3 digits), manual actions by the trader, Strategy
Tester and optimization mode, missing history, DB locked/deleted. Every edge
case points to the criterion that covers it; add a criterion if none does.

EARS patterns (Indonesian keywords):

| Pattern | Form |
|---|---|
| Ubiquitous | EA WAJIB <respons>. |
| Event (WHEN) | KETIKA <pemicu> MAKA EA WAJIB <respons>. |
| State (WHILE) | SELAMA <keadaan> EA WAJIB <respons>. |
| Unwanted (IF) | JIKA <kondisi> MAKA EA WAJIB <respons>. |
| Optional (WHERE) | BILA <fitur/input aktif> EA WAJIB <respons>. |

Rules: one testable behaviour per criterion, with the PRD number in it
(`≥ 1R`, `3%`, `3x`, `5 detik`). No implementation detail (class names are for
design). Cover the unwanted paths (disconnect, broker reject, restart, tester
mode). Number criteria `<req>.<n>` so tasks can reference them.

## 2. design.md

Sections, in order:
1. **Overview**: approach in a few sentences; how it satisfies the requirements.
2. **Architecture**: Mermaid diagram of the modules in scope and their calls,
   consistent with the RULES layer table.
3. **Components and interfaces**: per `.mqh` class, its layer, public methods
   with MQL5 signatures, and which requirement IDs it covers. Mark pure
   functions (unit-testable without a market).
4. **Data models**: structs/enums for `Core/Types.mqh`, input list for
   `Core/Inputs.mqh`, Global Variables, SQL tables/columns (`shared/schema/`).
5. **Error handling**: per failure (retcode, handle, DB lock, disconnect):
   detection, retry policy, log level, alert.
6. **Test case catalogue** with concrete inputs and expected values, one row
   per case, each pointing to a criterion:
   - `TC-<SUITE>-nn`: MQL5 unit test of a pure function (suite `.mqh` in
     `ea/tests/Include/SDBotTests/Suites/`, run by `tools/run-ea-tests.ps1`).
   - `TS-nn`: pytest for Python tooling (`sdbot/tools/tests/`).
   - `SC-nn`: Strategy Tester scenario (harness + `ea/tests/scenarios/`) in
     Given / When / Then form, asserted automatically by the harness.
   - `MC-nn`: manual check, only for what the tester cannot simulate.
   Include the edge cases (JPY digits, floating-point rounding, boundaries
   exactly at the threshold).
7. **Traceability**: table requirement ID → component → test IDs.
8. **Keputusan yang perlu disetujui**: every choice not dictated by the PRD,
   with the reason and the alternative.

## 3. tasks.md

```markdown
# Implementation plan — <Feature>

- [ ] 1. <outcome-based title>
  - Red: tulis TC-XX-01..05 di <suite>, stub fungsi, jalankan runner → FAIL
  - Green: implementasi di <files> sampai ALL PASS, compile 0/0
  - Refactor: <apa yang dirapikan>
  - _Requirements: 1.1, 1.3_ · _Tests: TC-XX-01..05_
- [ ] 2. <title>
  - [ ] 2.1 <sub-task>
    - …
    - _Requirements: 2.2_
```

Rules (Kiro): only coding tasks (write/modify/test code, `.ini`, `.set`,
schema); no "deploy", "run backtest for 3 months" or manual-only steps (list
those under a final "Validasi manual (di luar tasks)" note). Max two levels.
Each task is small enough to finish and verify in one sitting, builds on the
previous ones, and leaves nothing orphaned. Tests come first inside a task
(TDD). Every task references requirement IDs, and every criterion is covered by
at least one task.

## 4. Execute

`/sdbot-spec <feature> execute [n]`: without `n`, pick the first unchecked task.
1. Read requirements, design and tasks of the spec; load the `sdbot-ea` skill.
2. Do **only that task** (and its sub-tasks). Test first where applicable.
3. Verify per `sdbot-ea` (compile 0/0; say plainly what could not be run).
4. Tick the checkbox in `tasks.md`, then report: what changed, verification
   result, anything that deviated from design (and update design.md if so).
5. Stop. Wait for the user before the next task. Commit only when asked,
   `feat(ea/<layer>): … (spec <feature> task <n>)`.

When all tasks are done, set Status to Done in all three files and list the
manual validations still owed (PRD acceptance stages).
