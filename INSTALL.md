# Installing academic-students

The skills follow the open Agent Skills format (`skills/<name>/SKILL.md`), so they install in Claude and in other
agents. Pick your tool below.

## Codex, Cursor, GitHub Copilot, OpenCode and other agents

```
npx skills add Noam-Marom/academic-students        # this project
npx skills add Noam-Marom/academic-students -g     # every project
```

The [`skills`](https://github.com/vercel-labs/skills) installer (Node.js 22+) detects the agents on your machine
and copies the skills where each one looks for them. Add `-a <agent>` to choose one.

## Gemini CLI

```
gemini extensions install https://github.com/Noam-Marom/academic-students
```

Installs the skills, the read-only Moodle server and `GEMINI.md` (the rules every skill keeps).

## ChatGPT and the Gemini app

Neither installs skills yet. Create a custom GPT or a Gem and paste the `SKILL.md` of the skill you want as its
instructions (its `references/` files can go in as knowledge files). Scripts do not run there.


The plugin works in Claude Code, in the Claude desktop app and on claude.ai (paid plans). Pick the
section for the app you use. Every step can also be done by Claude on your behalf where it has the means:
in Claude Code it runs the commands below in your terminal after you agree; in the desktop app or the
browser it can click through the settings with Claude in Chrome or computer use, each step approved by you.
Claude cannot change your account settings silently from inside a plain chat.

## Claude Code (terminal, or the Code tab of the desktop app)

```
claude plugin marketplace add Noam-Marom/academic-students
claude plugin install academic-students@noam-academic
```

Recent versions (2.1.292+) do both in one command:
`claude plugin install academic-students --marketplace Noam-Marom/academic-students`.
Inside a session the same works as `/plugin marketplace add …` and `/plugin install …`.
Check with `claude plugin list`; update later with `claude plugin update academic-students@noam-academic`.

Try it for one session without installing:

```
claude --plugin-dir academic-students.zip
```

with the zip from https://github.com/Noam-Marom/academic-students/releases/latest/download/academic-students.zip

## claude.ai and the Claude desktop app

1. Open **Customize** in the left sidebar → **Plugins** → **Add** → **Add marketplace** → **Add from a repository**.
2. Enter `Noam-Marom/academic-students` and confirm.
3. Find **academic-students** in the list and add it.

In claude.ai and the desktop app the skills appear in the `/` menu under their own names, without the plugin
prefix: `/assignment-coach`, `/assignment-judge`, `/rtl-writing` and so on (the menu shows "Academic
students" next to each). In Claude Code they are `/academic-students:assignment-coach` and so on. Start a new
chat after installing; a chat that was already open does not load them.

No marketplace access (for example an organisation that restricts marketplaces)? Download
https://github.com/Noam-Marom/academic-students/releases/latest/download/academic-students.zip and upload it
as a custom plugin from the same **Plugins** screen. On Team and Enterprise plans an admin may have to allow it.

## Single skills

Every release also carries one zip per skill, for uploading only the skills you want in the Skills section of
**Customize**:

```
https://github.com/Noam-Marom/academic-students/releases/latest/download/skill-<name>.zip
```

`<name>` is one of the folders under `skills/` (for example `skill-assignment-coach.zip`). Most skills hand
work to `prompt-injection-scanner` and `rtl-writing`, so upload those two as well. The full plugin is
the better choice whenever your app supports plugins.

## Moodle (optional; Claude Code and the desktop app only)

The Moodle server runs on your computer. It needs [`uv`](https://docs.astral.sh/uv/) once, then a login in a
terminal (the password is typed there, never in Claude; only a revocable token is kept, in your keychain):

```
pip install uv
uv run --frozen --directory <plugin folder>/servers/moodle-mcp moodle-mcp login https://moodle.your-university.ac.il
```

## Building the zips yourself

```
python3 tools/package.py --out dist
```

writes `dist/academic-students-<version>.zip` and `dist/skills/<skill>.zip`. Pushing a tag `vX.Y.Z` that matches
`.claude-plugin/plugin.json` runs `.github/workflows/release.yml`, which tests, builds and publishes them.
