# Plan 1 — Repository foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A valid, installable `academic-students` plugin repo with the two existing skills migrated, shared discipline packs, repo-level tests, CI, and the documentation a new contributor (human or Claude) needs.

**Architecture:** One GitHub repo is both the plugin and its marketplace. `shared/` is the single source of truth for discipline packs; `tools/sync_shared.py` copies it into each skill so every skill folder is self-contained. Repo-level pytest guards structure and portability; GitHub Actions runs it on every PR.

**Tech Stack:** Python 3.10+ (stdlib only in tools), pytest, PyYAML (tests only), GitHub Actions, Claude Code CLI (`claude plugin validate`).

**Spec:** `docs/superpowers/specs/2026-11-02-academic-students-plugin-design.md` (§3, §5, §6)

## Global Constraints

- Plugin name `academic-students`; marketplace name `noam-academic`; version `0.1.0`; license MIT.
- SKILL.md frontmatter: only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. `name` == folder name, ≤ 64 chars; `description` ≤ 1024 chars.
- SKILL.md body ≤ 300 lines. No `bin/` directory anywhere in the plugin.
- No `${CLAUDE_PLUGIN_ROOT}` inside SKILL.md bodies (not available on claude.ai); scripts referenced relative to the skill folder (`scripts/x.py`).
- Python: stdlib only for anything under `tools/` and `tests/`; tests may use `pyyaml`.
- Every Hebrew Markdown file in the repo passes `skills/hebrew-with-english/scripts/check_rtl.py` with 0 errors.
- Commit after every task; conventional-commit messages (`feat:`, `test:`, `docs:`, `chore:`).

## Review Focus

1. A skill folder zipped on its own and uploaded to claude.ai must work: every `references/` path mentioned in its SKILL.md exists inside that folder (test in Task 4).
2. `shared/disciplines/` edited but `sync_shared.py` not run → CI must fail, not silently ship stale copies (Task 3 test).
3. The two migrated SKILL.md files mention `/hebrew-with-english` style commands; under a plugin the command is `/academic-students:hebrew-with-english`. Descriptions must list both forms (Task 5).
4. Windows contributors: `sync_shared.py` must not rely on symlinks or `cp`; pure `shutil` (Task 3).
5. `check_rtl.py` applied to `README.he.md` — a Hebrew README whose lines start with badges or English headings breaks RTL; the test in Task 4 catches it, the README must be written to pass.

---

### Task 1: Plugin manifest, marketplace, root files

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `LICENSE`, `.gitignore`, `pyproject.toml`, `CHANGELOG.md`
- Test: `tests/test_plugin_structure.py`

**Interfaces:**
- Produces: `pyproject.toml` with `[tool.pytest.ini_options] testpaths = ["tests", "skills", "servers"]`, `python_files = ["test_*.py"]`, `pythonpath = ["."]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plugin_structure.py
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_plugin_manifest_fields():
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    assert m["name"] == "academic-students"
    assert m["version"] == "0.1.0"
    assert m["license"] == "MIT"
    assert m["author"]["name"]
    assert len(m["description"]) <= 1024

def test_marketplace_points_at_root():
    m = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert m["name"] == "noam-academic"
    assert m["owner"]["name"]
    [p] = m["plugins"]
    assert p["name"] == "academic-students" and p["source"] == "./"

def test_no_bin_dir():
    assert not (ROOT / "bin").exists()
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/test_plugin_structure.py -q` → FAIL (file not found)
- [ ] **Step 3: Create the files.** `plugin.json`: name, version, description (English, ≤ 1024 chars, mentions Hebrew + English, any degree, read-only Moodle, scanner), author `{"name": "Noam Marom"}`, license MIT, keywords `["students","university","hebrew","academic-writing","moodle","security"]`. `marketplace.json` per spec §5. `.gitignore`: `__pycache__/`, `*.pyc`, `.venv/`, `evals/results/`, `*-workspace/`, `.pytest_cache/`, `servers/moodle-mcp/.venv/`, `injection-scan/`, `.DS_Store`.
- [ ] **Step 4: Run tests** → PASS
- [ ] **Step 5: Commit** — `chore: plugin manifest, marketplace, pytest config`

### Task 2: Shared discipline packs and course-profile template

**Files:**
- Create: `shared/disciplines/{math-stats,physical-sciences,life-sciences,computing,engineering,medicine-clinical,social-sciences,economics-business,law,humanities,architecture-design,arts}.md`, `shared/COURSE.template.md`, `shared/ai-policy.md`
- Test: `tests/test_shared_packs.py`

**Interfaces:**
- Produces: the 8 fixed H2 headings every pack must contain, in this exact order:
  `## Degrees covered`, `## Typical deliverables`, `## Answer conventions`, `## Tools and environments`, `## What graders look for`, `## Common mistakes`, `## Default citation style`, `## Worked breakdown`.
- Produces: `COURSE.template.md` with the frontmatter keys from spec §3.1, all commented with allowed values.

- [ ] **Step 1: Write the failing test** — for each of the 12 files: exists; first line is `# <Title>`; the 8 headings appear in order; file ≥ 40 lines; `COURSE.template.md` frontmatter parses (yaml) and has keys `course, code, institution, degree, family, language, submission_language, citation_style, submission_format, environment, ai_policy, ai_policy_source, grading`.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Write the 12 packs** (English, each 60–120 lines; the worked breakdown is a realistic assignment of that family broken into an assignment map in prose). Write `ai-policy.md`: the five policy values, what each permits per skill mode (table), and the standard disclosure sentence in Hebrew and English.
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** — `feat(shared): discipline packs, course profile template, AI policy matrix`

### Task 3: `tools/sync_shared.py`

**Files:**
- Create: `tools/sync_shared.py`, `tools/__init__.py`
- Test: `tests/test_sync_shared.py`

**Interfaces:**
- Produces: `sync_shared.py [--check]`. Reads `shared/sync.json` = `{"disciplines": ["assignment-coach", "academic-writing", "exam-prep"], "course_template": ["assignment-coach", "academic-writing", "exam-prep", "study-planner"], "ai_policy": ["assignment-coach", "academic-writing", "exam-prep"]}`. For each skill under `disciplines` copies `shared/disciplines/*.md` → `skills/<skill>/references/disciplines/` (stale files there are deleted first); under `course_template` copies `shared/COURSE.template.md` → `skills/<skill>/assets/COURSE.template.md`; under `ai_policy` copies `shared/ai-policy.md` → `skills/<skill>/references/ai-policy.md`. `--check` exits 1 and lists differences without writing. Functions: `sync(root: Path, check: bool) -> list[str]` returning the repo-relative paths that differ/were written.

- [ ] **Step 1: Write the failing test** — build a temp root with `shared/disciplines/a.md`, `shared/sync.json` listing skill `x`; `sync(tmp, check=False)` creates `skills/x/references/disciplines/a.md` with identical bytes; modify the copy → `sync(tmp, check=True)` returns `["skills/x/references/disciplines/a.md"]`; a stale `b.md` in the target is removed by a non-check sync.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** with `shutil.copyfile`, `filecmp`. Add a repo-level test `test_shared_copies_in_sync()` in `tests/test_shared_packs.py` that calls `sync(ROOT, check=True) == []`.
- [ ] **Step 4: Run** → PASS (after running `python3 tools/sync_shared.py` once skills exist; until Task 5 the sync list may be empty — keep `sync.json` listing only skills that exist at each commit)
- [ ] **Step 5: Commit** — `feat(tools): sync shared discipline packs into skills`

### Task 4: Repo-level skill tests (structure, portability, RTL)

**Files:**
- Create: `tests/test_skills_portable.py`, `tests/test_hebrew_docs.py`, `tests/conftest.py`
- Modify: `tools/check_portability.py` (create)

**Interfaces:**
- Produces: `tools/check_portability.py` → `check_skill(skill_dir: Path) -> list[str]` returning problems: frontmatter has keys outside the six; `name` != folder; `description` > 1024; body > 300 lines; a relative path written as `scripts/…`, `references/…`, `assets/…`, `schemas/…` in the body that does not exist; `${CLAUDE_PLUGIN_ROOT}` present. CLI prints problems and exits 1 if any.
- Produces: `tests/conftest.py` fixture `skill_dirs` = every `skills/*/` with a `SKILL.md`.

- [ ] **Step 1: Write failing tests** — parametrised over `skill_dirs`: `check_skill(d) == []`; `tests/test_hebrew_docs.py`: every `*.md` in the repo whose text contains ≥ 20 Hebrew letters (excluding `evals/`, `tests/fixtures`) passes `check_rtl.check(text)` with 0 errors (import `check` from `skills/hebrew-with-english/scripts/check_rtl.py` via `importlib.util.spec_from_file_location`).
- [ ] **Step 2: Run** → FAIL (no skills yet / module missing)
- [ ] **Step 3: Implement `check_portability.py`** (frontmatter parsed with a minimal `---` splitter + `yaml.safe_load`; path regex `(?:scripts|references|assets|schemas)/[\w./-]+`).
- [ ] **Step 4: Run** → PASS once Task 5 lands; commit the tests now anyway.
- [ ] **Step 5: Commit** — `test: portability and RTL guards for all skills`

### Task 5: Migrate the two existing skills

**Files:**
- Create: `skills/hebrew-with-english/{SKILL.md, scripts/check_rtl.py}`, `skills/prompt-injection-scanner/{SKILL.md, scripts/scan.py, references/techniques.md}` — copied from `/root/.claude/skills/synced/*/{hebrew-with-english,prompt-injection-scanner}/`
- Modify: both `SKILL.md` frontmatter and the command names in their bodies

- [ ] **Step 1: Copy** the folders byte-for-byte, then `pytest tests/ -q` → expect portability failures only if frontmatter/paths violate constraints.
- [ ] **Step 2: Edit frontmatter**: add `license: MIT`; `hebrew-with-english` description mentions `/hebrew-with-english`, `/academic-students:hebrew-with-english`, complaints about flipped lines, and "another skill writing Hebrew to a file"; scanner description unchanged except adding "or another skill in this plugin is about to read a course file". Add to `shared/sync.json`: `hebrew-with-english` (glossary comes in Plan 2; keep the list minimal now).
- [ ] **Step 3: Run** `pytest -q` → PASS; `claude plugin validate . --strict` → exit 0 (if the CLI is unavailable, record that in the commit message and run it in CI).
- [ ] **Step 4: Commit** — `feat(skills): migrate hebrew-with-english and prompt-injection-scanner`

### Task 6: CI workflows

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/evals.yml`

- [ ] **Step 1: `ci.yml`** — on push/PR: `actions/setup-python@v5` (3.10 and 3.12 matrix), `pip install pytest pyyaml`, `python tools/sync_shared.py --check`, `pytest -q`, then `npm install -g @anthropic-ai/claude-code && claude plugin validate . --strict` in a step with `continue-on-error: false`.
- [ ] **Step 2: `evals.yml`** — `workflow_dispatch` + weekly cron; runs `claude plugin eval . --trust-plugin --threshold 0.8 --max-cost-usd 20 --no-publish --json results.json` with `ANTHROPIC_API_KEY` secret; installs `bubblewrap socat`; uploads `results.json`.
- [ ] **Step 3: Validate YAML** — `python3 -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml`
- [ ] **Step 4: Commit** — `ci: tests, validate and scheduled evals`

### Task 7: Documentation for humans and for Claude

**Files:**
- Create: `CLAUDE.md`, `README.md`, `README.he.md`, `CONTRIBUTING.md`, `docs/skill-conventions.md`, `docs/architecture/c4.md`, `docs/architecture/decisions/ADR-0001-merge-helper-and-solver.md`, `ADR-0002-moodle-read-only-mcp.md`, `ADR-0003-shared-packs-copied-not-linked.md`, `ADR-0004-no-password-storage.md`

- [ ] **Step 1: `CLAUDE.md`** — for a contributor's Claude: what the plugin is; the invariants (spec §3.3) verbatim; repo map; how to run tests/validate/sync; the skill-conventions in short; where the spec and plans live and that **plans are executed task-by-task with superpowers:executing-plans**; commit style; what never to do (store passwords, answer quizzes, invent sources, add Claude-Code-only frontmatter, commit real course material or personal data); current status table (which plan is done).
- [ ] **Step 2: `docs/skill-conventions.md`** — the "design system" of the plugin: SKILL.md section order (`Purpose · When this triggers · Workflow · Modes · Files in this skill · Verify before sending`), description style (pushy, lists trigger phrases in Hebrew and English), script CLI contract (`--json`, exit codes 0/1/2, never modify inputs, `--out`), test layout (`tests/test_<script>.py`, fixtures generated in code), eval case layout, naming (kebab-case skills, snake_case scripts, unique module names across skills).
- [ ] **Step 3: `docs/architecture/c4.md`** — Mermaid `C4Context` (student, plugin, Moodle, Claude) and `C4Container` (8 skills as one container "Skills", `moodle-mcp` server, keychain, course folder, scanner output); IDs `ea:noam:academic-students:…`.
- [ ] **Step 4: Four ADRs** in MADR format (template: enterprise-architecture skill), status `accepted`, with options considered and consequences.
- [ ] **Step 5: `README.md`** — badges (CI), one-paragraph pitch, 60-second install (Claude Code two commands; claude.ai marketplace add / zip upload), the skills table, "what it will never do", status/roadmap, contributing, license. `README.he.md`: Hebrew version, every line opening in Hebrew (badges go after a Hebrew heading line), passes `check_rtl.py`.
- [ ] **Step 6: Run** `pytest -q` (Hebrew README passes RTL test) → PASS
- [ ] **Step 7: Commit** — `docs: CLAUDE.md, README (en/he), conventions, C4 and ADRs`
