# Claude Slash Commands

This directory contains custom slash commands for Claude Code in Cursor IDE.

## Available Commands

### `/rules` - Display Project Rules
Display project rules and guidelines from CLAUDE.md file.

**Usage:**
- `/rules` - Display complete rules
- `/rules summary` - Display quick summary
- `/rules rules-only` - Display only critical rules

**File:** `.claude/commands/rules.md`

### `/claude` - Display Project Rules (Alias)
Same functionality as `/rules`, provides an alternative command name.

**Usage:**
- `/claude` - Display complete rules
- `/claude summary` - Display quick summary
- `/claude rules-only` - Display only critical rules

**File:** `.claude/commands/claude.md`

## How Slash Commands Work

Slash commands in Claude Code allow you to:
1. Define reusable commands in markdown files
2. Invoke commands with `/command-name` syntax
3. Pass arguments to commands
4. Have Claude automatically execute the command based on context

## Command Structure

Each command file (`.md`) in `.claude/commands/` should contain:
- Command name and description
- Usage syntax
- Arguments (if any)
- Examples
- Expected behavior
- Related commands or references

## Adding New Commands

To add a new slash command:
1. Create a new `.md` file in `.claude/commands/`
2. Follow the structure of existing commands
3. Document the command behavior clearly
4. Update this README with the new command

## Related Documentation

- `CLAUDE.md` - Main project rules and guidelines
- `.cursorrules` - Auto-loaded context for Claude
- CLI commands: `uv run trading-bot rules` or `uv run trading-bot claude`
