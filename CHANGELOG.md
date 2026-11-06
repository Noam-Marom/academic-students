# Changelog

All notable changes to this plugin are recorded here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.

## [Unreleased]

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
