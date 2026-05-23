---
description: Create new documentation file
argument-hint: <category>/<name>
---

# New Doc File

```
/new <category>/<name>
```

## Categories

**docs/**: `architecture/`, `setup/`, `trading/`, `guides/`, `diagrams/`

**specs/**: `archive/` (phases, fixes, etc.)

## Naming

Use **kebab-case**: `risk-dashboard-guide.md` ✅ | `RiskDashboard.md` ❌

## Template

```markdown
# [Title]

[1-2 sentence overview]

## [Section]
- [Content]

## Related
- [Link]
```

## Examples

```
/new guides/telegram-notifications
/new setup/postgres-tuning
/new specs/archive/fixes/sl-bug
```
