# Privacy

academic-students collects nothing. It has no server, no account, no analytics and no telemetry.

- **The skills** run inside your AI assistant. Their scripts are plain Python that run on your own machine,
  on the files you give them, and make no network requests. What the assistant itself does with your
  conversation is governed by that assistant's own privacy policy (for Claude: https://www.anthropic.com/legal/privacy).
- **The optional Moodle server** (GitHub install, Claude Code and the desktop app only) talks only to your own
  Moodle site, read-only. Its login token stays in your operating system's keychain; downloaded course files go
  to the folder you choose. Your password is never stored or sent anywhere except to your Moodle's own login page.
- **Optional transcription** runs locally with `faster-whisper`; the audio never leaves your machine.

Nothing is sent to the authors of this project. Questions: https://github.com/Noam-Marom/academic-students/discussions
