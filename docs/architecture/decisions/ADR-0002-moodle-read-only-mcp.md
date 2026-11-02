# ADR-0002. Access Moodle through a local, read-only MCP server over Moodle Web Services

- Status: accepted
- Date: 2026-11-02
- Deciders: Noam Marom
- Tags: moodle, mcp, security
- Elements: `ea:noam:academic-students:container:moodle-mcp`, `…:container:moodle-sync`, `…:external:moodle`

## Context and Problem Statement

Students want their course material, deadlines and grades available to Claude without copying files by
hand. The first idea was a skill that drives Chrome (Claude in Chrome), logs in with stored credentials,
downloads files and answers quizzes. We need a way to reach Moodle that is reliable across Moodle versions and
institutions, safe for the student, and defensible on a CV.

## Decision Drivers

- Reliability: browser automation breaks on every theme or layout change; an API does not.
- Safety: nothing the plugin does may be read as impersonation or cheating (quiz answering, submissions).
- Credentials: Claude's browser tools do not type passwords; storing one anyway would be the exact failure mode the scanner exists to prevent.
- Portability: should work in Claude Code and the desktop app; degrade gracefully in claude.ai chat.
- Scope: v0.x runs entirely on the student's machine; no hosted service, no student tokens on our servers.

## Considered Options

1. Browser automation via Claude in Chrome, using the student's existing session (no stored password).
2. Local MCP server wrapping Moodle Web Services (REST, token) — read-only tool set.
3. Remote (hosted) MCP server so claude.ai chat can use it too.
4. No integration: the student downloads the course zip / `.ics` and uploads it.

## Decision Outcome

Chosen option: **2**, with **4** as the fallback inside `moodle-sync` for surfaces without MCP, because the
Web Services API is what the official Moodle mobile app uses (so institutions that allow the app expose it),
tokens can be obtained without the plugin ever seeing a password on disk, and a tool allowlist makes
"read-only" a tested property rather than a promise. Option 1 remains documented as a last resort when a
site disables the mobile service. Option 3 is deferred: it means holding other people's tokens.

### Consequences

- Good: deterministic, testable with mocked HTTP; the same code works for any Moodle 3.x/4.x/5.x site.
- Good: the function allowlist (`ALLOWED_FUNCTIONS`) is pinned by a test; a write function cannot slip in.
- Bad: requires `uv` (or a Python environment) on the student's machine; claude.ai chat cannot load a local MCP, so `moodle-sync` must carry a zip/`.ics` fallback.
- Bad: sites that disable the mobile web service or force SSO without the launch flow are not reachable; `MANUAL_CHECKS.md` tells the student how to find out in one minute.
- Neutral: a remote MCP can be added later behind the same tool names if demand justifies the security work.

## Pros and Cons of the Options

### 1. Browser automation
- Good: works on any site a human can use.
- Bad: brittle; slow; needs Chrome + extension; every action needs confirmation; impossible to test in CI.

### 2. Local read-only MCP
- Good: reliable, fast, testable, read-only by construction, no password handling in Claude.
- Bad: one prerequisite (`uv`); not available in claude.ai chat.

### 3. Remote MCP
- Good: works everywhere including claude.ai chat.
- Bad: we would hold students' Moodle tokens; needs hosting, auth, incident handling.

### 4. Manual zip / ics
- Good: zero integration risk; works everywhere.
- Bad: no grades, no announcements, no "what's new"; the student does the clicking.

## More Information

Spec §4.8; `servers/moodle-mcp/docs/moodle-ws-facts.md` (verified protocol details); ADR-0004.
