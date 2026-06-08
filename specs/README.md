# Internal Specifications

Development tracking and historical documentation.

> **Note**: This directory contains internal project files. For user-facing documentation, see [docs/](../docs/).

---

## Structure

```
specs/
├── active/              # 🔥 Current ongoing work
└── archive/             # 📦 Completed/historical work
```

---

## Active Work

| Spec | Status | Priority |
|------|--------|----------|
| [strategy-tuning.md](active/strategy-tuning.md) | 🟢 Round 1 applied, observation phase | 🟠 Medium |
| [confluence-scoring-investigation/](active/confluence-scoring-investigation/) | 📋 Planned — investigate weak confluence predictor (wait 1wk sample) | 🟠 Medium |

## Recently Archived (2026-06)

- [ui-dashboard/](archive/2026-06/ui-dashboard/) — read-only dashboard:
  worker observability + FastAPI read-only API + Next.js frontend
  (✅ Shipped 2026-06, Phases 1.5–4)

## Recently Archived (2026-05)

- [code-review-2026-05.md](archive/2026-05/code-review-2026-05.md) — module-by-module audit (✅ Completed 2026-05-24)
- [docs-cli-gap-fix.md](archive/2026-05/docs-cli-gap-fix.md) — fake CLI references resolved (✅ Completed 2026-05-26)
- [refactor-codebase.md](archive/2026-05/refactor-codebase.md) — god-method splits done, service extraction (Phase 3-4) explicitly deferred (✅ Resolved 2026-05-26)

---

## Archive

Historical records of completed work (Phase 0-5):

```
archive/
├── phases/              # Phase 0-5 implementation tracking
├── fixes/               # Historical bug fixes
├── implementation-logs/ # Implementation notes
├── dashboard/           # Phase 6 planning
└── database/            # Database analysis (completed)
```

---

## Status Summary

| Phase | Status |
|-------|--------|
| 0-5 | ✅ Complete (see archive/) |
| 5.5 | ⏳ Database enhancement |
| 6 | 📋 Web dashboard (planned) |

For current roadmap, see [docs/planning/roadmap.md](../docs/planning/roadmap.md).

---

## Purpose

- **active/** - Current work items, ongoing reviews, planned refactors
- **archive/** - Historical record, decision trails, completed work

When work is done in `active/`, move it to `archive/`.
