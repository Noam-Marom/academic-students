# Changelog

All notable changes to this plugin are recorded here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.

## [Unreleased]

## [0.3.3] - 2026-11-07

### Changed
- **The student decides.** Every skill does what the student asks: a hint gets a hint, "solve" gets the full
  solution of the actual question (never a similar exercise), a draft request gets the draft, a scan shows every
  trap it finds. No course-policy check, no question about the course's rules, no reminder. `ai_policy` in
  `COURSE.md` is the student's own note; its only effect is the disclosure sentence under
  `allowed-with-disclosure`. The skills are shorter as a result. Evals and tests follow the new rule.

## [0.3.2] - 2026-11-07

### Added
- TERMS.md (terms of use), SECURITY.md (private vulnerability reporting) and a fuller PRIVACY.md, after a legal
  review of liability, academic integrity, platform terms, privacy and IP; linked from plugin.json and README.
- The directory edition ships without scripts (the directory accepts only text files from unverified
  publishers); each skill does those steps itself.

### Changed
- Public wording promises design rules, not guarantees ("grade estimate", "citations it can verify",
  "What it is designed not to do"); sponsorship is described as a voluntary gift.
- The Moodle server identifies itself as `academic-students-moodle-mcp/<version>`.
- LICENSE names both maintainers; contributions are MIT (inbound=outbound).
- lecture-notes' legal note is accurate about transcripts and no longer Israel-only.

## [0.3.1] - 2026-11-07

### Changed
- **Faster RTL replies.** `rtl-writing` is a third of its former size and carries the chat rules itself: a chat
  reply is written once, opener first, with no reference read, no checker run and no retyping. The checker
  now runs on files only. Every other skill follows the same split.
- **A fast path in every task skill**, served before the full workflow: a hint, a one-question check, a language
  edit, a reference list, a few practice questions or a deadline list skip the map files, packs, question bank
  and planning scripts they do not need. Skills assume sensible defaults and say so in one line instead of
  asking up to two questions; a file is scanned once per conversation.
- **Unknown AI policy:** the skill helps with understanding, asks once what the course allows without waiting
  for the answer, and gives a full solution or draft when the student explicitly asks for one.
- `assignment-judge` runs its second grading pass in the same context; a separate subagent only in `strict` mode
  or on request.
- The Moodle server starts from a committed `uv.lock` (`uv run --frozen`), as the Claude directory requires.

### Added
- A `directory` branch for Anthropic's plugin directory, built by `tools/build_directory.py` and published by
  `.github/workflows/directory.yml` on every release: the skills, manifest, README and license only, without the
  local Moodle server (claude.ai cannot run it) and without dev files.
- README: a scanner demo (a white-on-white trap in a sample assignment) and "What it runs and sends".
- The release workflow attaches its zips to a release published on github.com and can be re-run by hand.

## [0.3.0] - 2026-11-06

### Changed
- **Breaking:** `hebrew-with-english` is now `rtl-writing` and covers Hebrew, Arabic, Persian and Urdu
  (`check_rtl.py` and `check_docx_rtl.py` handle every RTL script; new `references/arabic-persian-urdu.md`).
  The old command still triggers it.
- README in both languages: positioned for students in any country, language, grading system and platform.

### Added
- `moodle-sync`: Canvas and Blackboard through the student's browser and their exports (`references/other-lms.md`).

## [0.2.1] - 2026-11-06

### Added
- `moodle-sync`: connects in order — the server; automatic setup (`setup_check.py`: installs uv after a yes, the student logs in in their own terminal); Moodle read-only in the student's signed-in browser; Moodle's exports.

### Fixed
- Scanner and RTL checker work in read-only folders; eval scaffolds; evals moved to `evals/<skill>/`.

## [0.2.0] - 2026-11-06

### Added
- Release zips: `tools/package.py` builds the plugin zip and one zip per skill; `.github/workflows/release.yml` publishes them on a `vX.Y.Z` tag; `INSTALL.md` covers every app.
- `assignment-judge`: grade estimate by an expert-professor persona (course, year, degree) against the instructions; two blind passes, `score_rubric.py`, modes `estimate`/`compare`/`rubric`/`strict`.
- `assignment-coach`: group work — `split_work.py` splits the map among N members (parallel, serial relay, auto) with critical path and integration owner; `estimate_hours` in the map schema.
- Plugin manifest, single-repo marketplace, shared discipline packs, repo-level tests and CI.
- Skills migrated from personal use: `hebrew-with-english`, `prompt-injection-scanner`.
