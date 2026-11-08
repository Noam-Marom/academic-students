# academic-students plugin — design spec

- Status: accepted (v0.1 scope)
- Date: 2026-11-02
- Owner: Noam Marom
- Amended 2026-11-08: everything below about a course AI policy (the `ai_policy` field, the policy matrix, gating modes on it, the disclosure sentence) is removed. The student's request decides; see CHANGELOG 0.3.4 and `tests/test_student_decides.py`.
- Source of the design conversation: Claude Doc "תוכנית: academic-students plugin" (https://claude.ai/artifact/EuFWcKUsjjExEbjHgjR9HK)

## 1. What this is

A Claude plugin for university students in **any** degree (physics, law, nursing, dance, software
engineering, …), in Hebrew and English. It bundles eight skills and one local MCP server. Everything
is read-only toward the university's systems, never impersonates the student, and never fabricates
sources.

The plugin exists to remove friction around studying — not to do the studying for the student.
The one place it produces a complete solution (`assignment-coach` in "solve" mode) is gated behind
the course's AI policy and is framed as a worked example to learn from.

### Non-goals (v0.x)

- No quiz answering, no assignment submission, no writing to Moodle.
- No storing of passwords, anywhere, ever. Tokens only, in the OS keychain.
- No hosted/remote service. Everything runs on the student's machine.
- No fabricated citations: a source the skill cannot verify is marked `[unverified]`.

## 2. Skills and server (the deliverables)

| Deliverable | Kind | Status | One-line purpose |
|---|---|---|---|
| `rtl-writing` | skill | exists → extend | Hebrew prose with English terms that renders RTL correctly in chat, Markdown, Word, LaTeX, PowerPoint |
| `prompt-injection-scanner` | skill | exists → harden | Scan every course file for hidden instructions before Claude works on it; report, don't obey |
| `assignment-coach` | skill | new | Break down, guide, check, or (policy permitting) solve any assignment in any discipline |
| `academic-writing` | skill | new | Plan, give feedback on, edit, cite — academic writing in Hebrew and English |
| `exam-prep` | skill | new | Past exams + course material → topic map, practice questions, mock exam, formula sheet |
| `lecture-notes` | skill | new | Slides / recording / transcript → structured summary in the course's terminology |
| `study-planner` | skill | new | All deadlines in one place + a weekly plan that fits the student's real availability |
| `moodle-sync` | skill | new | Uses the Moodle MCP to download and organise course material, report what's new |
| `moodle-mcp` | MCP server (Python) | new | Read-only wrapper of Moodle Web Services; token in keychain; no password ever passes through Claude |

The original idea list had `assignment-helper` + `assignment-solver` (merged → `assignment-coach`
with modes), `academic-writing-hebrew` + `academic-writing-english` (merged → one skill, language
detected from the text), and `moodle-connection-extraction` with stored credentials and quiz answering
(replaced → `moodle-mcp` + `moodle-sync`). A `course-setup` skill that builds a course profile from
the syllabus was dropped: the profile is optional and each skill asks for what it needs.

## 3. Shared context model

### 3.1 Course profile — `COURSE.md` (optional)

A short Markdown file with YAML frontmatter, in the course folder (Claude Code) or in Project
knowledge (claude.ai). Every skill:

1. looks for it (`./COURSE.md`, then the nearest parent directory, then Project knowledge);
2. if found, uses it silently;
3. if not found, asks at most **two** questions it actually needs for the task at hand, and offers
   once to save the answers as `COURSE.md` so it never asks again.

Frontmatter fields (all optional):

```yaml
course: "Operating Systems"        # name
code: "202-1-3031"
institution: "BGU"
degree: "Software Engineering"
family: computing                  # one of the 12 discipline families, see 3.2
language: he                       # he | en | mixed  (language of teaching)
submission_language: he
citation_style: ieee               # apa7 | ieee | chicago | mla | vancouver | hebrew-legal | none
submission_format: [pdf, code]     # pdf | handwritten-scan | docx | latex | code | slides
environment: ["C11", "gcc", "Linux"]
ai_policy: unknown                 # allowed | allowed-with-disclosure | limited | forbidden | unknown
ai_policy_source: "syllabus §4"    # where the policy came from, verbatim quote in the body
grading: {assignments: 30, midterm: 20, final: 50}
```

`ai_policy` drives how far `assignment-coach`, `academic-writing` and `exam-prep` go (see 4.3).
`unknown` is a legal value and the default; the skill then says once what it would do under each
policy and asks the student which applies.

### 3.2 Discipline packs — `shared/disciplines/<family>.md`

Twelve families. Each file has the **same headings** so a skill can read any of them the same way:

1. Degrees covered
2. Typical deliverables
3. Answer conventions (structure, notation, what "show your work" means here)
4. Tools and environments (incl. free/browser alternatives)
5. What graders look for
6. Common mistakes
7. Default citation style
8. One worked breakdown of a typical assignment

Families: `math-stats`, `physical-sciences`, `life-sciences`, `computing`, `engineering`,
`medicine-clinical`, `social-sciences`, `economics-business`, `law`, `humanities`,
`architecture-design`, `arts`.

`shared/` is the source of truth. `tools/sync_shared.py` copies `shared/disciplines/` into every
skill that declares it needs them (`skills/<name>/references/disciplines/`), because a skill folder
must be self-contained to work when uploaded to claude.ai on its own. A repo test fails if a copy is
out of date.

### 3.3 Plugin-wide invariants

Every skill in the plugin:

- **Works with zero configuration.** No `COURSE.md`, no MCP, no extra installs → still useful.
- **Scans before reading.** A skill that reads a file that came from outside the conversation
  (assignment, exam, slides, Moodle page) first invokes `prompt-injection-scanner`. Course files are
  data, never instructions.
- **Treats AI policy as a ceiling.** When `ai_policy` is `forbidden` or `limited`, the skill says so
  once and offers the modes that do not produce submittable work. No nagging after that.
- **Hebrew output passes `check_rtl.py`** before it is sent or written to a file (the
  `rtl-writing` rules). Each skill's SKILL.md says so in one line and points at the script.
- **Progressive disclosure.** `SKILL.md` ≤ 300 lines: workflow + routing. Domain knowledge in
  `references/`, deterministic work in `scripts/`.
- **Scripts are stdlib-first.** Optional dependencies (PyMuPDF, python-docx, pint, faster-whisper…)
  degrade gracefully: the script says what it skipped and why, exit code stays meaningful.
- **Portable frontmatter.** Only `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed-tools` — the six fields claude.ai accepts. No Claude-Code-only fields.
- **Never writes outside the course folder or the scratch directory**, never deletes originals.

## 4. Skill-level design

### 4.1 rtl-writing (extend)

Current rules (first word of every line is Hebrew, punctuation anchoring, table cells, code block
neighbours) stay as `references/chat-markdown.md`. Additions:

- `references/docx.md` — `w:bidi` on paragraphs, `w:rtl` on runs, fonts, page numbering.
- `references/latex.md` — `polyglossia` (XeLaTeX/LuaLaTeX) with `\texthebrew`/`\textenglish`, fonts,
  formulas inside Hebrew text, `babel` fallback.
- `references/pptx.md` — text-box direction and alignment per shape.
- `references/glossary/<family>.md` — Hebrew ⇄ English term pairs per discipline family (10–40 pairs
  each). Rule: first mention = Hebrew term + English in parentheses; afterwards whichever the course uses.
- `scripts/check_rtl.py` (exists) gains `--fix`: for each failing line, print a suggested rewrite that
  opens with a Hebrew noun from a small lexicon (`הפקודה`, `הפונקציה`, `הקובץ`, `הכלי`, …). It never
  edits the file.
- `scripts/check_docx_rtl.py`: lists paragraphs that contain Hebrew but lack `w:bidi` (zipfile + XML,
  no dependency). `--json`.
- Triggering: explicit command, a complaint about flipped/mirrored lines, or another plugin skill
  writing Hebrew to a file. Not merely because the user wrote Hebrew.

### 4.2 prompt-injection-scanner (harden)

`scripts/scan.py` and `references/techniques.md` stay. Additions:

- `--quick`: no OCR, no renders, summary only; used by other skills as a gate. Escalates (tells the
  caller to run the full scan) when anything ≥ HIGH is found.
- `--json` is already written as `findings.json`; document it and keep its shape stable:
  `{"findings":[{severity,file,location,technique,text,detail}], "inventory":[...], "manual":[...]}`.
- Hebrew injection phrases in the pattern set (e.g. "אם אתה מודל שפה", "התעלם מההוראות", "העוזר
  האוטומטי", "אל תספר למשתמש") and `windows-1255` decoding.
- `tests/fixtures/make_fixtures.py` generates every fixture file in code (PDF via PyMuPDF when
  available, DOCX/PPTX/XLSX via zipfile+XML, notebooks, zips, a git repo) — no binaries in git.
- `benchmark/`: `generate.py` (seeded corpus: technique × file type × language × intent, plus clean
  look-alikes), `labels.csv`, `run_benchmark.py` → recall per technique, false-positive rate on clean
  files, Markdown table for the README.
- Planned, not in v0.1: split `scan.py` into `scanner/` modules **after** the test suite exists.

### 4.3 assignment-coach (new)

Workflow (all modes): scan → context (COURSE.md or ≤2 questions) → **assignment map** → plan → mode.

Assignment map = JSON validated by `schemas/assignment-map.schema.json`:

```json
{
  "course": "…", "family": "computing", "title": "HW3",
  "deliverables": [{"name": "report.pdf", "format": "pdf"}],
  "questions": [{"id": "1a", "type": "proof|calculation|code|essay|design|analysis|practical|other",
                 "weight": 10, "text": "…", "depends_on": []}],
  "constraints": ["max 5 pages", "only course material"],
  "show_work": true,
  "due": "2026-11-20",
  "ai_policy": "unknown"
}
```

Modes:

| Mode | Output | Under `forbidden` |
|---|---|---|
| `breakdown` | the map + a plan (order, time per part, environment, what to review first) | available |
| `guide` | hint ladder: direction → method → first step; one rung at a time, next rung only on request or after an attempt | concepts + a similar exercise only |
| `check` | what is wrong in the student's own work and where, no silent fixes; rubric score if a rubric exists | per policy; most courses allow feedback |
| `solve` | full solution in the required format, after verification; "what you need to understand to explain this" section; disclosure text when policy requires | not available: says so once, offers `guide` on a similar exercise |

Verification before any answer leaves `solve` or `check`: recompute numbers in code, run code and
tests, check units (`scripts/check_units.py`), confirm every cited source exists.

`references/answer-formats.md` — one section per question type (proof: claim/proof/∎; calculation:
given/required/solution with units/sanity check; code: design/implementation/tests/complexity; lab
report: IMRaD; legal problem: IRAC; clinical case: SOAP / nursing process; design project: brief,
concept, iterations, rationale; studio/performance: process, reflection, artist statement — the skill
says explicitly what stays the student's own).

`references/environments.md` — tool per task with free/browser fallback (Overleaf, Colab, JASP,
Jamovi, GeoGebra, Tinkercad, Replit…).

Scripts: `validate_map.py` (schema check, exit 1 on failure), `check_units.py` (bare numbers on
final-answer lines; dimensional mismatch via `pint` when installed), `render_solution.py`
(Markdown → DOCX with RTL paragraphs via python-docx; → PDF via LibreOffice when present).

Boundary with `academic-writing`: continuous-prose work (seminar paper, essay) → academic-writing.
Assignment with discrete questions → assignment-coach; it hands essay-type questions to
academic-writing's conventions.

### 4.4 academic-writing (new)

Modes: `plan` (research question/thesis, outline per genre, source-to-section mapping), `feedback`
(rubric score, ten most valuable fixes, margin comments in a DOCX copy), `edit` (same text, academic
register, author's voice, change list), `cite` (reference list in the required style + in-text ⇄ list
consistency), `draft` (a section, only when policy allows, with disclosure text).

Knowledge: `references/genres/*.md` (seminar paper, IMRaD lab report, literature review, research
proposal, legal opinion, clinical case study, policy paper, reflection, artist statement, abstract);
`references/hebrew-academic.md`; `references/english-academic.md` (incl. Hebrew-speaker error list:
articles, prepositions, tense, word order); `references/citation-styles/{apa7,ieee,chicago,mla,
vancouver,hebrew-legal}.md` with Hebrew-source examples; `references/rubric-default.md`.

Scripts: `check_citations.py` (orphans both directions; author-year incl. Hebrew names, numeric,
footnote styles; `.md` and `.docx`), `format_refs.py` (CSL-JSON → style; `citeproc-py` if installed,
built-in templates for APA 7 and IEEE otherwise; Hebrew entries sorted/formatted per style),
`word_count.py` (per course rules: exclude bibliography, footnotes, title page).

Invariant: never invents a source. A reference not resolvable via DOI/search is `[unverified]`.

### 4.5 exam-prep (new)

Workflow: scan → classify every question of every past exam (topic, type, difficulty, points, year)
→ topic map (frequency × points; what's in the syllabus but never examined) → practice (new
questions in the exam's style with full solutions; flashcards; Anki export) → mock exam under course
conditions → formula sheet within the allowed page limit → spaced-repetition dates for `study-planner`.

Scripts: `question_bank.py` (JSON bank, dedupe by normalised text), `mock_exam.py` (sample by topic
weights, seeded), `anki_export.py` (tab-separated, MathJax `\( \)` for formulas, Hebrew-safe).

Full solutions are the point here (practice, not submission). The plugin ships **no** real exams —
fixtures are written for the tests.

### 4.6 lecture-notes (new)

Inputs: PPTX/PDF slides, audio/video, a transcript the student already has, board photos. Output:
summary with fixed structure (concepts & definitions, formulas in LaTeX, examples, "sounds like exam
material", open questions for the lecturer); every addition not in the source marked **[הרחבה]**;
new terms appended to the course glossary.

Scripts: `slides_extract.py` (PPTX incl. speaker notes & hidden slides; PDF; → `slides.json`),
`transcribe.py` (local `faster-whisper` if installed, else clear instructions; never uploads audio
anywhere), `align.py` (keyword overlap → map transcript segments to slides; stdlib).

Legal note in SKILL.md: only recordings the student may hold (published by the university or with
the lecturer's consent).

### 4.7 study-planner (new)

Inputs: `COURSE.md` files, Moodle `.ics`/deadlines from `moodle-sync`, syllabus dates, student
availability. Output: `deadlines.json` (deduplicated), weekly plan (back-planned milestones for big
assignments, spaced repetition for exams), overload warning two weeks ahead, draft extension-request
message (student sends it). Export: `.ics`; Google Calendar events only via the connector and only
after explicit confirmation.

Scripts: `merge_deadlines.py`, `plan_week.py` (bins work into available hours; reports overflow,
never silently drops), `export_ics.py` (stdlib, `Asia/Jerusalem` by default, DST-correct).

### 4.8 moodle-mcp (new, Python) + moodle-sync (new, skill)

**Server** — `servers/moodle-mcp/`, package `moodle_mcp`, FastMCP (`mcp` SDK), `httpx`, `keyring`.
Registered in the plugin's `.mcp.json`:

```json
{"mcpServers": {"moodle": {"command": "uv", "args": ["run", "--directory",
  "${CLAUDE_PLUGIN_ROOT}/servers/moodle-mcp", "moodle-mcp"]}}}
```

Login happens **outside Claude**, in a terminal: `moodle-mcp login https://moodle.bgu.ac.il`.
The CLI calls `tool_mobile_get_public_config`; if username/password login is enabled it prompts with
`getpass` and exchanges credentials once at `login/token.php` (service `moodle_mobile_app`); if the
site uses browser/SSO login it runs the mobile-app launch flow (`admin/tool/mobile/launch.php`,
local loopback listener, token payload decoded and signature-checked). Only the token is stored,
in the OS keychain (`keyring`, service `moodle-mcp`, key = site host); fallback file
`~/.config/moodle-mcp/credentials.json` mode 0600 with a warning. The password never touches disk or
Claude's context.

Tools (all read-only; every URL returned to the model has the token stripped):

| Tool | Returns |
|---|---|
| `moodle_status()` | site, logged-in user, token validity, what to do if not logged in |
| `list_courses()` | enrolled courses (id, shortname, fullname, term) |
| `get_course_contents(course_id)` | sections → modules → files (name, type, size, modified, url) |
| `list_assignments(course_ids?)` | assignments with due dates, intro text, attachments |
| `get_upcoming_events(days=30)` | calendar action events (deadlines, quizzes closing, …) |
| `get_grades(course_id)` | grade items for the logged-in user |
| `list_forum_discussions(course_id, limit=20)` | announcements + forum threads (text only) |
| `get_notifications(limit=20)` | popup notifications |
| `list_quizzes(course_id)` | quiz **metadata** only (name, open/close, attempts allowed) |
| `download_file(file_url, dest_dir)` | saves the file, returns local path + sha256 |
| `sync_course(course_id, dest_dir)` | downloads everything into the folder structure below, writes `.moodle-sync/manifest.json`, returns new/changed/removed |

Folder layout written by `sync_course`:

```
<dest>/<course shortname>/
├── materials/<section>/
├── assignments/<name>/brief.md + attachments
├── exams/past/            # anything whose name matches exam/test/מבחן/בוחן
├── announcements.md
├── grades.md
└── .moodle-sync/manifest.json   # {module_id, file, sha256, modified, synced_at}
```

**Skill** `moodle-sync` — thin: when the MCP is present, how to use the tools (sync, then run the
scanner on the downloaded folder, then report what's new, then hand deadlines to `study-planner`);
when it is not, the fallback (student downloads the course zip from Moodle or runs the scanner on
saved pages). Never answers quizzes, never submits, never asks for a password.

**Tests**: `respx`-mocked httpx against hand-written anonymised JSON fixtures for every tool; a test
that greps every tool result and every log line for the token; manifest diff tests; one manual
checklist (`servers/moodle-mcp/MANUAL_CHECKS.md`) for a live site.

## 5. Repository layout

```
academic-students/
├── .claude-plugin/{plugin.json, marketplace.json}
├── .mcp.json
├── skills/<eight skills>/{SKILL.md, references/, scripts/, assets/?, tests/, evals/}
├── servers/moodle-mcp/{pyproject.toml, src/moodle_mcp/, tests/, README.md, MANUAL_CHECKS.md}
├── shared/{disciplines/*.md, COURSE.template.md, ai-policy.md}
├── tools/{sync_shared.py, check_portability.py, trigger_evals/<skill>.json}
├── tests/                      # repo-level: structure, portability, shared sync, RTL of Hebrew docs
├── docs/{superpowers/{specs,plans}, architecture/{c4.md, decisions/ADR-*.md}, skill-conventions.md}
├── .github/workflows/{ci.yml, evals.yml}
├── CLAUDE.md  README.md  README.he.md  CONTRIBUTING.md  CHANGELOG.md  LICENSE  pyproject.toml
```

## 6. Testing strategy

| Layer | What | Tool | When |
|---|---|---|---|
| 1 static | manifest valid; frontmatter portable; every path a SKILL.md mentions exists; SKILL.md ≤ 300 lines; `shared/` copies in sync; Hebrew docs pass `check_rtl.py` | `claude plugin validate . --strict`, pytest | every PR |
| 2 unit | every script of every skill, every MCP tool (mocked HTTP) | pytest | every PR |
| 3 behaviour | each skill's `evals/<case>/` with/without plugin, 3 runs | `claude plugin eval` | manual / weekly / before release |
| 4 triggering | 20 queries per skill + cross-skill confusion matrix | skill-creator scripts | after a description changes |
| 5 human | real outputs reviewed | skill-creator viewer | each iteration |

Eval cases follow the `claude plugin eval` layout (`prompt.md`, `case.yaml` with
`schema_version: "1.1"`, `graders/NN-*.md`). Fixtures for evals are written for the tests —
no real assignments, no personal data. `evals/results/` is git-ignored.

## 7. Roadmap and gates

| Phase | Weeks | Scope | Gate |
|---|---|---|---|
| 1 Foundations | 1 | repo, manifest, marketplace, shared/, CI, CLAUDE.md, both existing skills migrated | installs in claude.ai and Claude Code; CI green |
| 2 Existing assets | 2–4 | scanner tests + benchmark; hebrew formats + glossary | first benchmark table; v0.1 to 5 friends |
| 3 Core | 5–8 | assignment-coach, academic-writing, exam-prep | 12-family matrix passes; 10 users across 3 faculties |
| 4 Complete & publish | 9–12 | lecture-notes, study-planner, moodle-mcp + moodle-sync, README with numbers | v1.0, LinkedIn post, Anthropic directory listing |

## 8. Open questions

- Does BGU's Moodle expose the mobile web service (test: does the official Moodle app log in)?
  If not, `moodle-sync` falls back to the zip/`.ics` paths and the browser-based sync is reconsidered.
- Whether the lab (Offensive AI Research Lab @BGU) can be named in the scanner benchmark write-up.
- BGU's academic-integrity regulation on AI use — wording in README must match it.
