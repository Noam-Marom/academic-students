# ADR-0004. The plugin never stores, logs, echoes or accepts a password; Moodle login is a terminal command

- Status: accepted
- Date: 2026-11-02
- Deciders: Noam Marom
- Tags: security, credentials
- Elements: `ea:noam:academic-students:container:moodle-mcp`, `…:external:keychain`

## Context and Problem Statement

The original Moodle idea included "remember username and password so it can log in by itself". A plugin
whose own flagship skill scans for prompt injection cannot also keep a university password where a model
reads it: any hidden instruction that gets past the scanner would then have a secret to exfiltrate, and the
password would also sit in conversation logs. Moodle's own mobile app solves this with tokens.

## Decision Drivers

- Blast radius of a successful injection must exclude the student's credentials.
- Conversation transcripts (Claude Code, claude.ai) must never contain a password.
- The student should log in once per semester, not per session.
- Must work for both password sites and SSO sites.

## Considered Options

1. Store username + password (encrypted) and log in automatically.
2. Pass the password once through a tool call; store only the token.
3. Login happens **outside Claude** in a terminal command (`moodle-mcp login <site>`): `getpass` for password sites, the Moodle mobile launch flow (paste-back) for SSO sites; only the token is stored in the OS keychain via `keyring` (file fallback `0600` with a warning). The MCP server has no code path that accepts a password.
4. Browser session reuse (Claude in Chrome) with no credentials at all.

## Decision Outcome

Chosen option: **3**. Option 2 still puts the password in the model's context once, which is once too many.
Option 1 is the failure mode we are designing against. Option 4 is ADR-0002's fallback and carries no
credentials, but cannot be the primary path for reliability reasons.

### Consequences

- Good: no password ever exists in Claude's context, in logs, or on disk; a leaked token is revocable and expires (default 12 weeks).
- Good: every tool result passes through `strip_token()`; a test greps results and logs for the token.
- Bad: one extra step for the student (a terminal command); SSO sites require copying a link back into the terminal.
- Neutral: when the token expires, tools return a calm "run `moodle-mcp login`" message instead of an error dump.

## Pros and Cons of the Options

### 1. Stored password
- Good: zero friction after setup.
- Bad: unacceptable blast radius; against most universities' account policies.

### 2. Password through a tool call
- Good: one-time.
- Bad: password in the transcript and model context once; server needs a password-accepting tool.

### 3. Terminal login, token in keychain
- Good: password never near the model; standard mobile-app pattern; revocable.
- Bad: one terminal step.

### 4. Browser session only
- Good: no credentials at all.
- Bad: brittle (ADR-0002).

## More Information

Spec §4.8; `servers/moodle-mcp/docs/moodle-ws-facts.md` §1–3; ADR-0002.
