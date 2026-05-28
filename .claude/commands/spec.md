---
description: Create a new 3-file spec (requirements, design, tasks)
argument-hint: <spec-name>
---

# New Spec

Scaffold a new spec under `specs/active/<spec-name>/` using the standard
3-file format. Use kebab-case for `<spec-name>`.

```
/spec <spec-name>
```

## Structure

```
specs/active/<spec-name>/
├── requirements.md   # WHAT + WHY: goals, non-goals, success criteria, risks
├── design.md         # HOW: architecture, interfaces, method tables, rollback
└── tasks.md          # STEPS: ordered checklist (pre-flight, impl, verify, commit)
```

Reference example: [refactor-main-services](../../specs/active/refactor-main-services/).

## File templates

### requirements.md
```markdown
# <Title> — Requirements

**Status**: 📋 Planned | 🟡 In Progress | ✅ Resolved
**Priority**: 🔴 High | 🟠 Medium | 🟢 Low
**Date**: YYYY-MM-DD

## Context
[Why this work exists — the problem or trigger]

## Goals
1. [Concrete outcome]

## Non-goals
- [Explicitly out of scope]

## Success criteria
- [Measurable / verifiable]

## Constraints
- [Hard limits — live bot, perf, compat]

## Risk register
| Risk | Mitigation |
|------|------------|

## Open questions
- [Decisions deferred to design.md]

## Related
- [Links]
```

### design.md
```markdown
# <Title> — Design

## Architecture
[Diagram / structure after the change]

## Approach
[How it works — interfaces, data flow, examples]

## Detailed changes
[Method/file tables: what moves, what stays, what's new]

## Test impact
[Which tests are affected + how]

## Rollback plan
[How to undo if it goes wrong]

## What "done" looks like
[Concrete end state]
```

### tasks.md
```markdown
# <Title> — Task Breakdown

## Phase 1: <name>
### Pre-flight (~Xmin)
- [ ] [audit / snapshot / clean tree]
### Implementation (~Xmin)
- [ ] [discrete steps]
### Verification (~Xmin)
- [ ] [tests, coverage, smoke test]
### Commit
- [ ] [single commit, message format]

## Effort estimate
- Phase 1: X hours
```

## Conventions

- **Status / Priority** use the emoji legend above.
- Convert relative dates to absolute (`2026-05-28`, not "today").
- Each implementation phase = one revertable commit.
- Move spec to `specs/archive/YYYY-MM/` once resolved; update
  `specs/README.md` index.

## Related

- [/new](new.md) — create a single doc file
- [specs/README.md](../../specs/README.md) — spec index
