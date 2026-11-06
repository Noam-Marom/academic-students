# Changelog

All notable changes to this plugin are recorded here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow SemVer.

## [Unreleased]

## [0.2.0] - 2026-11-06

### Added
- Release zips: `tools/package.py` builds the plugin zip and one zip per skill; `.github/workflows/release.yml` publishes them on a `vX.Y.Z` tag; `INSTALL.md` covers every app.
- `assignment-judge`: grade estimate by an expert-professor persona (course, year, degree) against the instructions; two blind passes, `score_rubric.py`, modes `estimate`/`compare`/`rubric`/`strict`.
- `assignment-coach`: group work — `split_work.py` splits the map among N members (parallel, serial relay, auto) with critical path and integration owner; `estimate_hours` in the map schema.
- Plugin manifest, single-repo marketplace, shared discipline packs, repo-level tests and CI.
- Skills migrated from personal use: `hebrew-with-english`, `prompt-injection-scanner`.
