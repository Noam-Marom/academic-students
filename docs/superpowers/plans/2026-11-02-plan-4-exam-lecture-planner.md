# Plan 4 — exam-prep, lecture-notes, study-planner

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three support skills with their scripts, tests and eval cases: past exams → practice (`exam-prep`), slides/recordings → summaries (`lecture-notes`), deadlines → weekly plan + `.ics` (`study-planner`).

**Architecture:** Each skill has 3 small stdlib-first scripts that produce JSON the skill then reasons over. Interfaces between skills are files: `exam-prep` emits `review-dates.json` that `study-planner` consumes; `lecture-notes` appends to the course glossary that `hebrew-with-english` reads; `study-planner` consumes `deadlines.json` that `moodle-sync` (Plan 5) emits.

**Tech Stack:** Python 3.10+, pytest; optional `python-pptx`, `pymupdf`/`pypdf`, `faster-whisper`; `zoneinfo` (stdlib) for `.ics`.

**Spec:** `docs/superpowers/specs/2026-11-02-academic-students-plugin-design.md` (§4.5–4.7)

## Global Constraints

- All of Plan 1's constraints; `shared/sync.json` adds `exam-prep`.
- JSON interchange files use these exact names and shapes:
  - `deadlines.json`: `[{"id": str, "course": str, "title": str, "due": "YYYY-MM-DDTHH:MM", "tz": "Asia/Jerusalem", "kind": "assignment|exam|quiz|other", "source": str, "weight": number|null, "estimate_hours": number|null}]`
  - `review-dates.json`: `[{"course": str, "topic": str, "dates": ["YYYY-MM-DD", …]}]`
  - `slides.json`: `[{"n": int, "title": str, "text": str, "notes": str, "hidden": bool}]`
  - `transcript.json`: `[{"start": float, "end": float, "text": str}]`
  - `aligned.json`: `[{"slide": int, "segments": [int, …]}]`
- Times are timezone-aware; default zone `Asia/Jerusalem`; `.ics` output includes a `VTIMEZONE` or uses UTC `Z` times (choose UTC — simpler and DST-correct; test pins a date across the DST change).
- Transcription never sends audio anywhere; `transcribe.py` runs only local models.

## Review Focus

1. Two past exams containing the same question with different numbering/whitespace/nikud: `question_bank.py` must dedupe them (normalise: strip nikud, punctuation, digits at line start, collapse whitespace) (Task 1 test).
2. A week where available hours < required hours: `plan_week.py` must report overflow with the items it could not place, never drop silently and never exceed availability (Task 7 test).
3. A deadline at `23:59` Israel time on a day in late October (DST ends): the `.ics` `DTSTART` in UTC must be `21:59Z` before the change and `20:59Z` after — pin both (Task 8 test).
4. A PPTX whose slide titles are empty (title in a text box, not a placeholder): `slides_extract.py` falls back to the first non-empty line of the slide as `title` (Task 4 test).
5. Alignment of a transcript to slides when the lecturer skips slides: `align.py` must allow non-monotonic mapping but prefer monotonic (tie-break by proximity to the previous matched slide) (Task 6 test).

---

### Task 1: `question_bank.py`

**Files:**
- Create: `skills/exam-prep/scripts/question_bank.py`
- Test: `skills/exam-prep/tests/test_question_bank.py`

**Interfaces:**
- Bank file: `bank.json` = `{"questions": [{"id": str (sha1[:10] of normalised text), "text": str, "topic": str|null, "type": str|null, "difficulty": 1..5|null, "points": number|null, "year": int|null, "source": str, "solution": str|null}]}`.
- `normalise(text) -> str`; `add(bank, q: dict) -> bool` (False if duplicate); `stats(bank) -> {"by_topic": {topic: {"count", "points", "years": [...]}}, "untagged": int}`. CLI: `question_bank.py add bank.json q.json`, `question_bank.py stats bank.json [--json]`, `question_bank.py list bank.json --topic T`.

- [ ] **Step 1: Failing tests** — add same question twice with different numbering → second returns False; nikud-only difference → duplicate; stats groups points per topic; `list --topic` filters.
- [ ] **Steps 2–5**; commit `feat(exam): question bank with dedupe and stats`

### Task 2: `mock_exam.py` and `anki_export.py`

**Files:**
- Create: `skills/exam-prep/scripts/mock_exam.py`, `scripts/anki_export.py`
- Test: `tests/test_mock_exam.py`, `tests/test_anki_export.py`

**Interfaces:**
- `build_mock(bank, weights: dict[str, float], n: int, seed: int, total_points: int|None) -> list[q]` — samples without replacement proportionally to weights (largest-remainder rounding), deterministic for a seed; if a topic has fewer questions than its share, redistributes the remainder.
- `to_anki(cards: list[{"front","back","tags"?}]) -> str` — tab-separated, `\n` inside fields → `<br>`, `$…$`/`$$…$$` → `\(…\)`/`\[…\]`, tabs in fields escaped, UTF-8 with header line `#separator:tab` and `#html:true`. CLI `anki_export.py cards.json --out cards.txt`.

- [ ] **Step 1: Failing tests** — weights `{A: .5, B: .5}`, n=4 → 2+2; seed reproducibility; a topic with 1 question and share 3 → others fill; Anki: formula conversion, `<br>`, header lines, Hebrew preserved.
- [ ] **Steps 2–5**; commit `feat(exam): mock exam sampler and Anki export`

### Task 3: exam-prep SKILL.md, references, evals

**Files:**
- Create: `skills/exam-prep/SKILL.md`, `references/{classification.md, practice-formats.md, formula-sheet.md, course-profile.md (copy)}`, evals `{classify-three-past-exams, practice-not-copies, mock-exam-under-conditions, formula-sheet-page-limit, review-dates-emitted}`, `tools/trigger_evals/exam-prep.json`
- Modify: `shared/sync.json` (+ `exam-prep`)

- [ ] **Step 1: SKILL.md** — triggers ("יש לי מבחן", "מבחנים קודמים", "תכין לי מבחן דמה", "דף נוסחאות", "past exams", "mock exam"; negatives: a single homework question → coach); workflow (scan → classify into bank → topic map → practice/mock/formula sheet → `review-dates.json`); full solutions are expected here; never claims a question "will be on the exam", only frequency.
- [ ] **Step 2: references** — classification rubric (topic/type/difficulty anchors), practice-question quality rules (new numbers, new context, same skill), formula-sheet layout per page limit.
- [ ] **Step 3: evals** (fixtures: 3 synthetic short exams written in `files/`), graders assert topic table, non-copy practice, `review-dates.json` shape.
- [ ] **Step 4: Run** `sync_shared.py && pytest -q` → PASS; commit `feat(exam): skill, references, evals`

### Task 4: `slides_extract.py`

**Files:**
- Create: `skills/lecture-notes/scripts/slides_extract.py`
- Test: `skills/lecture-notes/tests/test_slides_extract.py` (+ `tests/pptx_builder.py` minimal OOXML writer)

**Interfaces:**
- `extract(path: Path) -> list[slide]` (→ `slides.json` shape). PPTX: zipfile + XML (no `python-pptx` needed): slide order from `presentation.xml` rels, title placeholder `type="title"|"ctrTitle"` else first non-empty paragraph, body text, `notesSlide` text, `show="0"` → hidden. PDF: `fitz` if importable else `pypdf`; title = first line. CLI `slides_extract.py deck --out slides.json`.

- [ ] **Step 1: Failing tests** — builder: 3 slides, one hidden, one with notes, one with no title placeholder → titles/notes/hidden as expected, order preserved; PDF path skipped if no backend.
- [ ] **Steps 2–5**; commit `feat(lecture): slide extraction (pptx/pdf)`

### Task 5: `transcribe.py`

**Files:**
- Create: `skills/lecture-notes/scripts/transcribe.py`
- Test: `skills/lecture-notes/tests/test_transcribe.py`

**Interfaces:**
- `transcribe(path, language="he", model="small") -> list[segment]` using `faster_whisper.WhisperModel` when importable; `--out transcript.json`. When not importable: exit 2 and print the install line (`pip install faster-whisper`) plus the manual alternative (student exports a transcript from Zoom/YouTube and passes it as `.vtt`/`.srt`; `convert_subtitles(path) -> list[segment]` handles `.vtt`/`.srt`).
- Test the parts that need no model: `.vtt` and `.srt` conversion; exit code 2 path when `faster_whisper` import is monkeypatched to fail.

- [ ] **Steps 1–5**; commit `feat(lecture): local transcription + subtitle import`

### Task 6: `align.py`

**Files:**
- Create: `skills/lecture-notes/scripts/align.py`
- Test: `skills/lecture-notes/tests/test_align.py`

**Interfaces:**
- `align(slides, segments, window=3) -> list[{"slide": int, "segments": [int]}]` — tokenise (Hebrew + Latin, lowercase, strip nikud/punct), score each segment against each slide by Jaccard over tokens with IDF weighting; choose best slide, tie-break by proximity to previous assignment; segments with score 0 attach to the previous slide. CLI `align.py slides.json transcript.json --out aligned.json`.

- [ ] **Step 1: Failing tests** — 3 slides with distinct vocab, 6 segments → expected mapping; lecturer skips slide 2 → segments go to 1 then 3; a filler segment ("אוקיי, שאלות?") attaches to previous.
- [ ] **Steps 2–5**; commit `feat(lecture): transcript-to-slide alignment`

### Task 7: lecture-notes SKILL.md, references, evals; `merge_deadlines.py` + `plan_week.py`

**Files:**
- Create: `skills/lecture-notes/SKILL.md`, `references/{summary-format.md, legal-note.md}`, evals `{slides-with-notes-summary, transcript-hebrew-english-terms, marks-additions}`, `tools/trigger_evals/lecture-notes.json`
- Create: `skills/study-planner/scripts/merge_deadlines.py`, `scripts/plan_week.py`
- Test: `skills/study-planner/tests/test_merge_deadlines.py`, `tests/test_plan_week.py`

**Interfaces:**
- `merge(sources: list[Path]) -> list[deadline]` — accepts `.ics` (parse `VEVENT` `SUMMARY`, `DTSTART`, `UID`, `CATEGORIES`), `.json` (already `deadlines.json`), `COURSE.md` (frontmatter `deadlines:` list if present); dedupe key `(course_norm, title_norm, due_date)`; conflicting times for the same key → keep earliest, add `"conflict": [other_times]`.
- `plan_week(deadlines, availability: {"YYYY-MM-DD": [["HH:MM","HH:MM"], …]}, week_start: "YYYY-MM-DD", review_dates=None) -> {"blocks": [{"date","start","end","task","deadline_id"}], "overflow": [{"deadline_id","hours_unplaced"}]}` — back-plan: each deadline's `estimate_hours` (default 3 for assignment, 8 for exam) spread over available slots before `due`, earliest-deadline-first, minimum block 1h; never exceed availability.

- [ ] **Step 1: Failing tests** — ics+json duplicate → one item with `conflict` when times differ; `COURSE.md` deadlines merged; plan: 2 deadlines, 6 available hours, 10 required → `overflow` lists 4h for the later deadline, blocks never overlap and never exceed slots; review dates become 1h blocks.
- [ ] **Steps 2–4: Implement; write lecture-notes SKILL.md + references + evals**; run `pytest -q` → PASS
- [ ] **Step 5: Commit** — `feat(lecture,planner): lecture-notes skill; deadline merge and weekly planner`

### Task 8: `export_ics.py`, study-planner SKILL.md, evals

**Files:**
- Create: `skills/study-planner/scripts/export_ics.py`, `SKILL.md`, `references/{planning-rules.md, extension-request.md}`, evals `{three-courses-one-plan, overloaded-week-warning, calendar-needs-confirmation}`, `tools/trigger_evals/study-planner.json`
- Test: `skills/study-planner/tests/test_export_ics.py`

**Interfaces:**
- `to_ics(plan_or_deadlines, tz="Asia/Jerusalem", calendar_name="academic-students") -> str` — RFC 5545 text, CRLF line endings, `PRODID:-//academic-students//EN`, each block/deadline a `VEVENT` with `UID`, `DTSTAMP`, `DTSTART`/`DTEND` in UTC (`…Z`), `SUMMARY`, `DESCRIPTION` (course + source), lines folded at 75 octets. CLI `export_ics.py plan.json --out plan.ics`.

- [ ] **Step 1: Failing tests** — DST pin (Review Focus 3): `2026-10-23T23:59 Asia/Jerusalem` → `20261023T205900Z`; `2026-10-26T23:59` → `20261026T215900Z`; CRLF; folding of a 120-char Hebrew summary; valid `BEGIN/END` nesting.
- [ ] **Step 2–4: Implement; SKILL.md** (triggers: "תעשה לי סדר בהגשות", "מתי יש לי הגשות", "deadlines", "study plan"; Google Calendar only via connector after explicit yes; extension-request draft the student sends); references; evals.
- [ ] **Step 5: Run** `pytest -q` → PASS; commit `feat(planner): ics export, skill, references, evals`
