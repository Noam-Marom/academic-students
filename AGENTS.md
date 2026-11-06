# AGENTS.md

Briefing for any coding agent working on this repository (Codex, Gemini CLI, Cursor, Copilot, Claude Code, …).
The full briefing is [`CLAUDE.md`](CLAUDE.md); it applies to every agent, not only Claude. Read it before
changing anything. The essentials:

- **TDD:** a failing test first for every script and for the MCP server; then the code.
- **Before pushing:** `python3 tools/sync_shared.py --check && python3 -m pytest -q`.
- **Skills** follow the open Agent Skills format: `skills/<name>/SKILL.md` (frontmatter keys: `name`,
  `description`, `license`, `compatibility`, `metadata`, `allowed-tools` only), `references/`, `scripts/`,
  `tests/`. Skill bodies name no single agent's product.
- **Shared knowledge** lives in `shared/` and is copied into skills by `tools/sync_shared.py`; never edit the copies.
- **Never:** store or accept a password; call a Moodle function that writes; invent a citation; commit real
  course material or personal data; run anything that consumes paid model or API usage without the owner's
  explicit approval.
