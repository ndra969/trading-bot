---
description: Display project rules and guidelines from CLAUDE.md file
argument-hint: [full|summary|rules-only]
---

# Display Project Rules

When this command is invoked, you must:

1. **Read the CLAUDE.md file** from the project root directory
2. **Parse the format argument** (if provided):
   - `full` (default): Display complete CLAUDE.md content
   - `summary`: Extract and display key sections only
   - `rules-only`: Display only "Critical Implementation Rules" section
3. **Display the content** based on the format

## Format Handling

### Full Format (default)
Display the complete `CLAUDE.md` file content as-is.

### Summary Format
Extract and display these key sections from CLAUDE.md:
- Critical Implementation Rules
- Code Quality Standards
- Testing Requirements
- Test-Driven Development (TDD) Workflow

Show the first 500 characters of each section with a preview indicator.

### Rules-Only Format
Extract and display ONLY the "Critical Implementation Rules" section, including:
- Asset-Specific Pip Values
- Position Management Rules
- Enhanced Strategy Architecture
- Broker Symbol Mapping
- Real-time Pip Tracking & Automated Features
- Position Lifecycle Management
- Database Schema

## Implementation Steps

1. Locate `CLAUDE.md` in the project root
2. Read the file content
3. If format is `summary`:
   - Find each key section by searching for `## Section Name`
   - Extract content until next `##` section
   - Display first 500 chars of each with section headers
4. If format is `rules-only`:
   - Find `## Critical Implementation Rules` section
   - Extract until next major section
   - Display complete section
5. If format is `full` or no format specified:
   - Display entire CLAUDE.md content

## Examples

- `/rules` → Display complete CLAUDE.md
- `/rules full` → Display complete CLAUDE.md
- `/rules summary` → Display key sections summary
- `/rules rules-only` → Display only critical implementation rules

## Related

- CLI: `uv run trading-bot rules --format [format]`
- File reference: `@CLAUDE.md`
