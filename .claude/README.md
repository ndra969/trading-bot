# Claude Code Skills

Project skills live in `.claude/skills/<name>/SKILL.md` and are invoked as
`/<name>`. Claude can also load a skill on its own when the task matches its
`description`. (These were `.claude/commands/*.md` slash commands before.)

## Skills

| Skill | Scope | Purpose |
|-------|-------|---------|
| `sdbot-spec` | SDBot (`sdbot/specs/`) | Kiro-style spec workflow: requirements → design → tasks → execute |
| `sdbot-ea` | SDBot (`sdbot/`) | MQL5 EA work: PRD, layer & safety rules, compile, definition of done |
| `workflow` | Python bot | Dev workflow (start here) |
| `rules` / `claude` | Repo | Show `CLAUDE.md` |
| `docs` | Python bot | Browse `docs/` by topic |
| `tdd` | Python bot | Red-Green-Refactor guidance |
| `test` / `coverage` | Python bot | Test suite and coverage |
| `quality` | Python bot | black / ruff / mypy |
| `dry-run` | Python bot | Validate the bot (mandatory pre-commit) |
| `commit` | Python bot | Pre-commit validation |
| `new` / `spec` | Repo | New doc / 3-file spec |
| `status` / `logs` | Python bot | Runtime status and logs |
| `analyze` / `backtest` | Python bot | Strategy analysis and backtests |
| `migrate` | Python bot | Alembic migrations |

## Adding a skill

1. Create `.claude/skills/<name>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <name>
   description: <what it does and when to use it — this drives auto-loading>
   argument-hint: [optional args]
   ---
   ```
2. Put supporting files (templates, references) next to `SKILL.md` and link them.
3. Add a row to the table above and to `CLAUDE.md`.
