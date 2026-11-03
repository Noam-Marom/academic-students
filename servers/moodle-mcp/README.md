# moodle-mcp

A local, **read-only** MCP server over Moodle Web Services for the academic-students plugin. Claude gets
tools to list courses, read contents, assignments, deadlines, grades, announcements and notifications, and to
mirror a course into a folder. It never answers quizzes, never submits, never posts, and never sees a password.

## Install and log in

```
pip install uv                                   # once
uv run --directory servers/moodle-mcp moodle-mcp login https://moodle.your-university.ac.il
```

- Username/password sites: the password is typed in that terminal (hidden), sent once to `login/token.php`
  with service `moodle_mobile_app`, and forgotten. SSO sites (`typeoflogin` 2/3): a browser opens
  `admin/tool/mobile/launch.php`; after you log in, Moodle shows an `academicstudents://token=…` link — paste
  it back into the terminal. The link is checked against `md5(site + passport)` before it is trusted.
  `--browser` forces the browser flow.
- Only the token is stored: OS keychain (`keyring` service `moodle-mcp`, entry = site host), or
  `~/.config/moodle-mcp/credentials.json` with mode 0600 when no keychain exists (a warning says so).
- `moodle-mcp status` checks every stored token; `moodle-mcp logout <site>` forgets one.
- With several sites logged in, set `MOODLE_MCP_SITE` to the one the server should use.

The plugin's `.mcp.json` starts it with `uv run --directory ${CLAUDE_PLUGIN_ROOT}/servers/moodle-mcp moodle-mcp serve`.

## Tools

| Tool | Returns |
|---|---|
| `moodle_status()` | site, user, token validity; the login command when not logged in |
| `list_courses()` | enrolled courses with start/end dates |
| `get_course_contents(course_id)` | sections → modules → files (urls without the token), links, label text |
| `list_assignments(course_ids?)` | assignments, due dates, intro as Markdown, attachments |
| `get_upcoming_events(days=30)` | calendar action events in the window |
| `get_grades(course_id)` | the student's grade items |
| `list_forum_discussions(course_id, limit=20)` | announcements and threads, text only, newest first |
| `get_notifications(limit=20)` | popup notifications |
| `list_quizzes(course_id)` | quiz metadata only |
| `download_file(file_url, dest_dir)` | local path + sha256 |
| `sync_course(course_id, dest_dir)` | mirrors the course (see `skills/moodle-sync/references/folder-layout.md`), returns new/changed/removed |
| `export_calendar_ics(dest_path)` | writes the whole calendar as `.ics` |

Timestamps are ISO 8601 in `Asia/Jerusalem`, with the epoch kept as `*_ts`. Errors come back as
`{"error": "auth" | "not_logged_in" | "moodle" | "transport" | "forbidden", "message": …}`.

## Safety properties (each pinned by a test)

- `client.ALLOWED_FUNCTIONS` is exactly fourteen `*_get_*` functions; anything else raises `PermissionError`
  before a request is made.
- The token is sent in the POST body, appended to file urls only at download time, and stripped from every
  message, error and tool result.
- The server process has no code path that accepts a password; only the `login` CLI reads one, via `getpass`.

## Development

```
python3 -m venv servers/moodle-mcp/.venv
servers/moodle-mcp/.venv/bin/pip install -e "servers/moodle-mcp[dev]"
servers/moodle-mcp/.venv/bin/python -m pytest servers/moodle-mcp -q
```

Protocol facts with source paths: `docs/moodle-ws-facts.md`. Live-site checklist: `MANUAL_CHECKS.md`.
Fixtures in `tests/fixtures/` are hand-written and anonymised; tests never touch a real Moodle.
