---
description: Create new documentation file with template
argument-hint: <category>/<name>
---

# New Documentation

Create new doc/spec file following project standards.

## Usage

```
/new <category>/<name>
```

## Categories

**docs/**: `guides/`, `setup/`, `trading/`, `integration/`, `architecture/`

**specs/**: `dashboard/`, `database/`, `fixes/`, `phases/`

## Naming

Always **kebab-case**:
- ✅ `phase-6-todo.md`
- ✅ `risk-dashboard-guide.md`
- ❌ `PHASE6_TODO.md`
- ❌ `RiskDashboard.md`

## Template

```markdown
# [Title]

**Status**: [Draft/Ready]
**Date**: YYYY-MM-DD

## Overview
[1-2 sentences]

## Details
- [Point 1]
- [Point 2]

## Related
- [Link to related docs]
```

## Examples

```
/new guides/telegram-notifications
/new specs/phases/phase-6-dashboard
/new specs/fixes/position-sl-bug
```

## Related

- `/docs` - Browse documentation
- `/rules` - Project standards
