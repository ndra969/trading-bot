---
description: Display project rules from CLAUDE.md
argument-hint: [full|summary|rules-only]
---

# Display Project Rules

Read `CLAUDE.md` from project root and display based on format:

| Arg | Output |
|-----|--------|
| (none) or `full` | Complete CLAUDE.md |
| `summary` | Key sections only (first 500 chars each) |
| `rules-only` | "Critical Rules" section only |

## Key Sections (for summary)

- Critical Rules
- Code Standards
- Testing
- Performance Targets

## Examples

```
/rules                # Full
/rules summary        # Quick overview
/rules rules-only     # Just critical rules
```

CLI: `uv run trading-bot rules --format <fmt>`
