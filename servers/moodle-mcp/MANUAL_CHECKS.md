# Manual checks against a live Moodle

The test suite mocks every HTTP call. Before a release, run these once against a real site with a real
student account (your own). Record the date, the Moodle release and the result of each check; never commit
tokens, screenshots with names, or downloaded course files.

1. **The official Moodle app logs in.** If the Moodle mobile app cannot log in to the site, the mobile web
   service is off and this server cannot work either; stop and use the fallback in
   `skills/moodle-sync/references/without-mcp.md`.
2. **Public config is reachable.** `moodle-mcp login <site>` prints "Connecting to …" and does not warn that it
   could not read the mobile config. Note `typeoflogin` (1 = password, 2/3 = browser).
3. **Login works with the right flow.** Password sites: the prompt hides the password; SSO sites: the browser
   opens, Moodle shows an `academicstudents://token=…` link, pasting it succeeds. A wrong password exits 1.
4. **Token is in the keychain.** `moodle-mcp status` says "token valid"; on a machine with a keychain no
   `~/.config/moodle-mcp/credentials.json` exists (only `sites.json`, which holds hosts, not secrets).
5. **`downloadfiles` is true.** `moodle_status()` in Claude reports `downloadfiles: true`; otherwise downloads
   fail by design.
6. **One course syncs.** `sync_course` on a small course creates the layout, `announcements.md`,
   `grades.md` and `.moodle-sync/manifest.json`; a second run downloads nothing.
7. **Deadlines are right.** `list_assignments` due times match the Moodle UI in local time (check one date on
   each side of a DST change if the semester spans one).
8. **Calendar export.** `export_calendar_ics` writes a `.ics` that a calendar app imports.
9. **Token not in logs.** Search the Claude Code MCP log and the terminal scrollback for the token (from
   your OS keychain app, entry `moodle-mcp` / the site host): it must not appear anywhere.
10. **Logout.** `moodle-mcp logout <site>` removes the entry; `moodle_status()` then says not logged in and
    gives the terminal command.
