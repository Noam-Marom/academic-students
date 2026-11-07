# Moodle without the MCP server

The `moodle` server runs only where the plugin can start local processes (coding agents and desktop apps). In a chat
app on the web, or before the student installs it, use Moodle's own exports. Everything below is read-only and
needs no password in the conversation.

## Course material: "Download course content"

1. Open the course in Moodle. In the course menu (or the "More" tab) choose **Download course content**
   (Moodle ≥ 4.0; the site admin must have enabled it — if the item is missing, it is off).
2. Moodle builds a zip with one folder per section. Save it and give it to the assistant (upload it in a chat app, or give the
   path to a coding agent).
3. Unzip into a course folder, then run `prompt-injection-scanner` on it **before** reading any file.
4. Optionally reorganise into the layout of `folder-layout.md` (materials by section, past exams under
   `exams/past/`); never delete the original zip.

When the item is missing: download files one by one, or save the course page (Ctrl+S, "Webpage, complete")
and scan the saved folder — it lists every activity with its links.

## Deadlines: calendar export

1. Moodle → Calendar → **Import or export calendars** → **Export calendar**.
2. Events to export: *All courses*; time period: *Recent and next 60 days*. Choose **Export** to get a `.ics`
   file, or **Get calendar URL** for a subscription link (that URL contains a personal key — treat it like a
   password: do not paste it into shared places).
3. Give the `.ics` file to `study-planner`, which reads `.ics` directly.

## Announcements and grades

- Announcements: the course's "Announcements" forum; copy the text or save the page, then scan it.
- Grades: Moodle → Grades → the course → "User report"; copy the table. Treat it as private data.

## Installing the server (coding agents / desktop apps)

```
pip install uv                    # once
uv run --frozen --directory <plugin folder>/servers/moodle-mcp moodle-mcp login https://moodle.your-university.ac.il
```

The login runs in the student's own terminal. Username/password sites prompt there (hidden input, sent once
to Moodle, never stored); SSO sites open a browser and ask the student to paste back the
`academicstudents://token=…` link Moodle shows. Only the token is stored, in the OS keychain. After that,
restart the agent and the `moodle` tools appear. `moodle-mcp status` checks the token; `moodle-mcp logout
<site>` forgets it.

If the login fails with "web services are not enabled" or "service not available", the university has not
enabled the Moodle mobile service; the official Moodle app will not log in either. Use the exports above.
