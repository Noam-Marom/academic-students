# ADR-0003. Keep discipline packs in `shared/` and copy them into skills instead of referencing them

- Status: accepted
- Date: 2026-11-02
- Deciders: Noam Marom
- Tags: repo-layout, portability
- Elements: `ea:noam:academic-students:container:shared`, `…:container:learning-skills`

## Context and Problem Statement

Several skills (`assignment-coach`, `academic-writing`, `exam-prep`) need the same twelve discipline packs
and the same AI-policy matrix. A skill folder must also be self-contained: claude.ai lets a user upload a
single skill, and nothing outside the folder exists there. Claude Code offers `${CLAUDE_PLUGIN_ROOT}` for
cross-folder references, but claude.ai does not document it.

## Decision Drivers

- One source of truth (editing twelve packs in three places guarantees drift).
- Each skill must work when uploaded alone to claude.ai.
- No symlinks (Windows contributors, zip uploads).
- Drift must be caught by CI, not by a user.

## Considered Options

1. Reference `${CLAUDE_PLUGIN_ROOT}/shared/…` from each SKILL.md.
2. Symlink `skills/<s>/references/disciplines → ../../../shared/disciplines`.
3. Keep `shared/` as the source of truth and **copy** into each declaring skill with `tools/sync_shared.py`; a test (`sync(ROOT, check=True) == []`) fails CI on drift.
4. Duplicate by hand.

## Decision Outcome

Chosen option: **3**, because it is the only option that is both portable to claude.ai and drift-proof.
`shared/sync.json` declares who gets what; the copy step is one command and one CI check.

### Consequences

- Good: skills are self-contained; the repo has one editable copy; CI enforces sync.
- Bad: the repo contains N copies of the packs (≈ 12 files × 3 skills); contributors must run the sync (CI tells them).
- Neutral: when claude.ai documents a plugin-root variable, option 1 can replace the copies for Claude Code without changing the skills' content.

## Pros and Cons of the Options

### 1. `${CLAUDE_PLUGIN_ROOT}`
- Good: no duplication.
- Bad: not documented on claude.ai; a skill uploaded alone breaks.

### 2. Symlinks
- Good: no duplication on disk.
- Bad: zips and Windows checkouts lose them; claude.ai upload likely breaks.

### 3. Copy with a sync tool
- Good: portable, enforceable, simple.
- Bad: duplicated bytes in git.

### 4. Hand duplication
- Bad: drift within a week.

## More Information

`tools/sync_shared.py`, `tests/test_sync_shared.py`, `tests/test_shared_packs.py::test_shared_copies_in_sync`.
