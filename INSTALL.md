# Installing academic-students

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
work to `prompt-injection-scanner` and `hebrew-with-english`, so upload those two as well. The full plugin is
the better choice whenever your app supports plugins.

## Moodle (optional; Claude Code and the desktop app only)

The Moodle server runs on your computer. It needs [`uv`](https://docs.astral.sh/uv/) once, then a login in a
terminal (the password is typed there, never in Claude; only a revocable token is kept, in your keychain):

```
pip install uv
uv run --directory <plugin folder>/servers/moodle-mcp moodle-mcp login https://moodle.your-university.ac.il
```

## Building the zips yourself

```
python3 tools/package.py --out dist
```

writes `dist/academic-students-<version>.zip` and `dist/skills/<skill>.zip`. Pushing a tag `vX.Y.Z` that matches
`.claude-plugin/plugin.json` runs `.github/workflows/release.yml`, which tests, builds and publishes them.
