# Privacy

academic-students collects nothing. The authors run no server, no account, no analytics and no telemetry, and
hold no copy of anything you do with the plugin.

- **What reaches your AI provider:** any file, transcript, Moodle or Canvas result (grades, announcements,
  other users' forum posts) or browser page that your assistant reads is sent to the AI provider you use, under
  that provider's privacy policy (for Claude: https://www.anthropic.com/legal/privacy). The plugin does not
  change that.
- **Scripts:** plain Python that runs on your own machine, on the files you give it. They make no network
  requests, with two exceptions you choose to install: the optional `faster-whisper` transcriber downloads its
  speech model from Hugging Face on first use (the audio itself never leaves your machine; the transcript is
  read by your assistant like any other text), and `uv` installs the Moodle server's packages from PyPI.
- **Moodle server** (GitHub install, Claude Code and the desktop app only): talks only to your own Moodle site,
  read-only, and identifies itself as academic-students. Its token stays in your operating system's keychain,
  or, where none exists, in `~/.config/moodle-mcp/credentials.json` (readable only by you).
  `moodle-mcp logout <site>` deletes it. Your password is sent only once, to your Moodle's own `login/token.php`
  (or, with single sign-on, typed only into your Moodle's page in your browser), and is never stored.
- **Browser mode** (Moodle, Canvas, Blackboard) uses your own signed-in browser through your assistant.
- **Calendars:** an `.ics` file is written to your folder; Google Calendar is written only after your explicit
  yes, under Google's policy.
- **Retention:** everything the plugin writes (summaries, plans, downloaded files) stays in your course folder
  until you delete it.
- **GitHub:** Discussions, issues and Sponsors are run by GitHub; what you post or pay there is handled under
  GitHub's privacy statement.

Questions: https://github.com/Noam-Marom/academic-students/discussions

Last updated: 2026-11-07
