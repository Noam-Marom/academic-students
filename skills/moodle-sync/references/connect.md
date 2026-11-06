# Connecting to Moodle: the order to try

Try each way in order and stop at the first one that works. Never ask for the Moodle password, at any step.

## 1. The `moodle` server is already connected

The `moodle_status` tool exists → call it and continue with the SKILL.md workflow. `logged_in: false` →
the login step below, then reconnect.

## 2. Set the server up (Claude Code, or the desktop app linked to the student's computer)

Needs a shell on the student's own computer (the Claude Code terminal, or the desktop app's link to the
computer). Run, from this skill folder:

```
python3 scripts/setup_check.py --url <the student's Moodle URL> --json
```

`mcp_possible: false` → the server is not bundled here; go to 3. Otherwise do the `steps` in order:

- **install-uv** (`run_by: assistant`, `needs_consent: true`): ask once, in one sentence, naming what is
  installed and from where ("install uv, the Python runner the Moodle server needs, from astral.sh?"). Run
  the command only after a clear yes. No → go to 3.
- **login** (`run_by: student`): give the command exactly as printed for the student to run in **their own
  terminal**. Never run it yourself and never type into it: it asks for the password (or opens the
  university's SSO page) and keeps only a token in the keychain.
- **reconnect** (`run_by: student`): `/mcp` in Claude Code, or restarting the desktop app; then back to 1.

The login fails with "web services are not enabled" or "service not available" → the university has not
enabled Moodle's mobile service; go to 3.

## 3. Moodle in the student's browser

When the server cannot run (claude.ai on the web, a skill uploaded alone, uv declined, mobile service off)
and a browser tool is available (Claude in Chrome, or the desktop app's built-in browser) → follow
`via-browser.md`.

## 4. Moodle's own exports

No browser tool either → `without-mcp.md`: the student downloads the course zip and the calendar `.ics`
themselves and hands them over.
