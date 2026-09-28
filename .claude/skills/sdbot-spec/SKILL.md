---
name: sdbot-spec
description: Spec-driven development for SDBot using the Kiro method — requirements (user stories + EARS acceptance criteria) → design → tasks, each gated by explicit user approval, then implement one task at a time. Use when the user wants to plan, spec, or start a new SDBot feature/roadmap phase, asks for a spec, or says "lanjut task berikutnya" on an SDBot spec. Code is written only in the execute phase.
argument-hint: <feature-name> [requirements|design|tasks|execute <n>]
---

# SDBot spec workflow (Kiro method)

One spec per feature or roadmap phase, in `sdbot/specs/<feature-name>/`
(kebab-case, e.g. `ea-foundation`):

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
| 1. Requirements | `requirements.md` | "Requirements sudah sesuai? Kalau ya, saya lanjut ke design." |
| 2. Design | `design.md` | "Design sudah sesuai? Kalau ya, saya lanjut ke tasks." |
| 3. Tasks | `tasks.md` | "Tasks sudah sesuai? Kalau ya, spec siap dieksekusi." |
| 4. Execute | code + tests for **one** task | report, tick the box, stop |

Write a first draft from the PRD without a round of questions first. Put real
unknowns in "Pertanyaan terbuka" at the end of the document instead.
Spec documents are in Indonesian (like the PRDs). Identifiers, file names and
MQL5 terms stay as in the code.

## 1. requirements.md

```markdown
# Requirements — <Feature>

Status: Draft | Approved (YYYY-MM-DD)
Sumber: PRD-EA §<section>, RULES §<section>

## Pendahuluan
<2–4 kalimat: apa yang dibangun, batas lingkup, yang TIDAK termasuk.>

## Glosarium
- **R**: jarak SL awal dari entry …

## Requirements

### Requirement 1: <nama>
**User story:** Sebagai <trader/operator>, saya ingin <kemampuan>, agar <manfaat>.

#### Acceptance criteria
1. KETIKA <pemicu> MAKA EA WAJIB <respons>.
2. JIKA <kondisi tak diinginkan> MAKA EA WAJIB <respons>.
3. SELAMA <keadaan> EA WAJIB <respons>.

## Pertanyaan terbuka
- …
```

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
6. **Testing strategy**: unit tests (pure functions → `ea/tests/Scripts/`),
   Strategy Tester scenarios (`ea/tests/scenarios/*.ini`), and the PRD scenario
   each one proves.
7. **Traceability**: table requirement ID → component → test.
8. **Pertanyaan terbuka** / decisions (with reason) where options exist.

## 3. tasks.md

```markdown
# Implementation plan — <Feature>

- [ ] 1. <outcome-based title>
  - <what to write / change, files>
  - <which tests to add first>
  - _Requirements: 1.1, 1.3_
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
