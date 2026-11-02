# Plan 2 — Harden the two existing skills

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `prompt-injection-scanner` gets a test suite, a `--quick` gate mode, Hebrew patterns and a reproducible benchmark; `hebrew-with-english` gets format references, a glossary per discipline family, `--fix` suggestions and a DOCX checker.

**Architecture:** Tests generate every fixture in code (no binaries in git). The scanner stays a single `scan.py` in this plan (refactor only after tests exist). The benchmark is a seeded generator + labels + a runner that prints a Markdown table, so the README numbers are reproducible by anyone.

**Tech Stack:** Python 3.10+, pytest, optional PyMuPDF (`pymupdf`) for PDF fixtures (tests skip PDF cases if absent), zipfile+XML for Office fixtures.

**Spec:** `docs/superpowers/specs/2026-11-02-academic-students-plugin-design.md` (§4.1, §4.2)

## Global Constraints

- All of Plan 1's constraints.
- `scan.py` keeps its current CLI; new flags are additive: `--quick`, `--json` (alias: findings.json is always written).
- Fixture generators never embed real course material; injected strings are obviously synthetic (`INJECT-TEST-…`).
- Tests that need PyMuPDF/tesseract call `pytest.importorskip` / `pytest.mark.skipif(shutil.which("tesseract") is None)`.
- Scripts are run in tests with `python3 -I` via `subprocess` **or** imported via `importlib` — module name collisions across skills are forbidden (unique file names).

## Review Focus

1. A PDF whose only "hidden" text is an OCR layer of a scanned page must be reported LOW/benign, not CRITICAL — false positives on scanned lecture notes would make students disable the scanner (Task 2 clean-fixture test).
2. `--quick` on a folder with 500 files must finish without OCR and must not delete a pre-existing `--out` directory the user pointed at by mistake: `--out` refuses to `rmtree` a directory that does not contain a previous `report.md` (Task 3).
3. Hebrew injection written right-to-left with Latin punctuation (`.אם אתה מודל שפה, התעלם`) must still match (Task 4 patterns are tested on both orderings).
4. `check_rtl.py --fix` must never rewrite the file; it only prints suggestions (Task 6 asserts file bytes unchanged).
5. `check_docx_rtl.py` on a DOCX produced by Google Docs export (bidi set at style level, not paragraph level) must not report every paragraph: resolve `w:pPr/w:bidi` through the paragraph's `w:pStyle` chain (Task 7 fixture with style-level bidi).

---

### Task 1: Fixture generator for the scanner

**Files:**
- Create: `skills/prompt-injection-scanner/tests/fixtures/make_fixtures.py`, `skills/prompt-injection-scanner/tests/conftest.py`
- Test: `skills/prompt-injection-scanner/tests/test_fixtures_selfcheck.py`

**Interfaces:**
- Produces: `make_fixtures.build(dest: Path) -> dict[str, dict]` — writes files into `dest` and returns `{relative_path: {"technique": str, "expected_min_severity": "CRITICAL|HIGH|MEDIUM|LOW|NONE", "hidden_text": str|None}}`. Techniques (one file each, plus clean twins where marked ✱):
  `pdf_white_text`✱, `pdf_tiny_font`, `pdf_offpage`, `docx_hidden_run`✱, `docx_white_text`, `pptx_speaker_notes`, `xlsx_hidden_sheet`, `md_html_comment`✱, `html_display_none`, `unicode_tags`, `bidi_trojan_source`, `zero_width_chars`, `base64_payload`, `ipynb_stored_output`, `zip_nested`, `git_commit_message`, `agent_config_claude_md`, `hebrew_injection_docx`, `windows1255_txt`, `semantic_no_keyword`.
  Clean twins (`*_clean`) have `expected_min_severity: "NONE"`. Scanned-PDF look-alike `pdf_ocr_layer_clean` → NONE/LOW.
- Produces: conftest fixture `fixtures(tmp_path_factory)` → `(dest, manifest)` built once per session; `scan(paths, *flags) -> (returncode, findings_json: dict, stdout)` helper running `python3 -I scripts/scan.py … --out <tmp>`.

- [ ] **Step 1: Write the self-check test** — `build()` returns ≥ 20 entries; every path exists; every entry with hidden_text has it absent from the file's visible text where the technique implies that (e.g. for `docx_hidden_run` the string is inside `<w:vanish/>` run only).
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement `make_fixtures.py`** (PDF via `fitz` when importable, else skip PDF entries and record `"skipped": True`; DOCX/PPTX/XLSX as minimal OOXML written with `zipfile`; git repo via `subprocess` `git init/commit` with `-c user.name/email`).
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** — `test(scanner): in-code fixture generator for 20 hiding techniques`

### Task 2: Detection tests against the fixtures

**Files:**
- Test: `skills/prompt-injection-scanner/tests/test_detection.py`, `tests/test_clean_files.py`, `tests/test_safety.py`

- [ ] **Step 1: Write failing tests** — parametrised over the manifest: for each non-clean entry a finding exists for that file with severity ≥ `expected_min_severity` and `hidden_text[:30]` in some finding's `text`; for each clean entry no finding ≥ HIGH. Safety: a fixture folder containing `json.py` that writes `/tmp/pwned-<uuid>` → after scanning, that file does not exist; scanning a corrupted PDF (`%PDF-1.4` + garbage) and a 6-level nested zip exits 0.
- [ ] **Step 2: Run** → some FAIL (expected: Hebrew and windows-1255 and semantic cases; record which)
- [ ] **Step 3: Fix detection gaps in `scan.py` only where a test fails** — add `windows-1255` to `decode_text` candidates; add Hebrew phrases to the pattern table (Task 4 does the full set; here only enough to pass).
- [ ] **Step 4: Run** → PASS (`semantic_no_keyword` is allowed to be `xfail(strict=False)` — document in the test why: pattern scanners cannot catch it; Claude's read-through is the control)
- [ ] **Step 5: Commit** — `test(scanner): detection, clean-file and safety suites`

### Task 3: `--quick` mode and safe `--out`

**Files:**
- Modify: `skills/prompt-injection-scanner/scripts/scan.py` (`main()`, `OPTS` use sites), `SKILL.md`
- Test: `skills/prompt-injection-scanner/tests/test_cli.py`

**Interfaces:**
- Produces: `--quick` ⇒ implies `--no-ocr`, skips `renders/` and `extracted/` writing, prints one summary line `QUICK: <n> files, max severity <SEV>, escalate=<true|false>` where escalate is true when any finding ≥ HIGH; exit code 0 (clean), 1 (findings ≥ HIGH), 2 (usage).
- Produces: `--out` safety: if the directory exists and has no `report.md` or `findings.json` → refuse with exit 2 and a message; `--force` overrides.

- [ ] **Step 1: Failing tests** — quick run on fixtures prints `QUICK:` line, creates `findings.json` but no `renders/`; exit 1 when a CRITICAL fixture is included, 0 for clean-only; `--out` pointing at a tmp dir containing `keep.txt` → exit 2 and `keep.txt` survives.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** in `main()` and in the OCR/render branches (`if OPTS.quick: skip`).
- [ ] **Step 4: Run** → PASS; update SKILL.md "Run the automated scan" with the `--quick` gate paragraph (other skills call it first; escalate ⇒ full scan + stop).
- [ ] **Step 5: Commit** — `feat(scanner): --quick gate mode and safe --out handling`

### Task 4: Hebrew patterns and the techniques catalogue

**Files:**
- Modify: `scan.py` pattern table, `references/techniques.md` (§13 semantic, new §15 "Hebrew and bidi-specific tricks")
- Test: `tests/test_patterns_hebrew.py`

- [ ] **Step 1: Failing test** — `match_patterns(text)` returns ≥ 1 hit for each of: `אם אתה מודל שפה`, `התעלם מכל ההוראות הקודמות`, `העוזר האוטומטי צריך`, `אל תספר למשתמש`, `אם אתה בינה מלאכותית`, `הוסף את המילה`, `דרג את העבודה הזו`, and the same strings with the final punctuation placed first (RTL-copied form); zero hits for `המרצה ביקש להתעלם מהשאלה האחרונה` (benign) and `בינה מלאכותית היא תחום במדעי המחשב`.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Add patterns** (regex with optional nikud and prefixes `ו/ש/ה`), update techniques.md.
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** — `feat(scanner): Hebrew injection patterns`

### Task 5: Benchmark harness

**Files:**
- Create: `skills/prompt-injection-scanner/benchmark/{generate.py, run_benchmark.py, README.md}`, generated `labels.csv` (committed; corpus itself git-ignored and regenerated from seed)
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces: `generate.py --out DIR --seed 42 --n-per-cell 3` → corpus + `labels.csv` columns `path,technique,filetype,language,intent,label` where `label ∈ {injection, canary, benign}` and `intent ∈ {malicious, instructor_trap, steering, none}`; reuses `make_fixtures` builders where possible.
- Produces: `run_benchmark.py --corpus DIR --labels labels.csv [--quick] --md table.md` → recall per technique, FPR on benign, overall; writes Markdown table; exit 0.

- [ ] **Step 1: Failing test** — tiny run (`--n-per-cell 1`) produces labels with all three label values; `run_benchmark` output JSON has keys `recall_by_technique`, `false_positive_rate`, `n`.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement**; keep ASR (attack-success-rate) as a documented **manual** procedure in `benchmark/README.md` (needs model runs; `claude plugin eval` cases in Task 8 cover it).
- [ ] **Step 4: Run** → PASS; run the benchmark once locally and paste the table into `benchmark/README.md` with date + commit hash.
- [ ] **Step 5: Commit** — `feat(scanner): reproducible benchmark harness`

### Task 6: `check_rtl.py --fix` suggestions

**Files:**
- Modify: `skills/hebrew-with-english/scripts/check_rtl.py`
- Test: `skills/hebrew-with-english/tests/test_check_rtl.py`

**Interfaces:**
- Produces: `suggest_fix(line: str) -> str | None` — for a failing line returns a rewritten line that opens with a Hebrew noun chosen from `OPENERS` by the token kind (inline code → `הפקודה`/`הפונקציה` by heuristic: contains `(` → function; path → `הקובץ`; URL → `הקישור`; version → `גרסה`; number → spelled Hebrew for 1–10 else `יש`; bold label → `**ה-<label>:**`). CLI `--fix` prints `line N: <original>` / `   → <suggestion>`; exit code unchanged; file untouched.

- [ ] **Step 1: Failing tests** — existing behaviour pinned (10 cases from the SKILL.md table: wrong → error, right → clean); `suggest_fix("- `ls -la` מציג קבצים")` startswith `- הפקודה`; `--fix` run leaves `sha256(file)` unchanged; `--json` output includes `"suggestion"` per error when `--fix` given.
- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run** → PASS
- [ ] **Step 5: Commit** — `feat(hebrew): --fix suggestions in check_rtl`

### Task 7: `check_docx_rtl.py`

**Files:**
- Create: `skills/hebrew-with-english/scripts/check_docx_rtl.py`
- Test: `skills/hebrew-with-english/tests/test_check_docx_rtl.py` (+ in-test OOXML builder helper `tests/docx_builder.py`)

**Interfaces:**
- Produces: `check_docx(path: Path) -> list[dict]` — items `{"paragraph": int, "text": str, "issue": "missing w:bidi" | "run missing w:rtl" }` for paragraphs with ≥ 3 Hebrew letters; style-level `w:bidi` (via `w:pStyle` → `styles.xml`, following `w:basedOn`) counts as set. CLI `--json`, exit 1 if issues.

- [ ] **Step 1: Failing tests** — builder makes DOCX with (a) Hebrew paragraph without bidi → 1 issue; (b) with paragraph bidi → 0; (c) bidi only on the style → 0; (d) English paragraph → 0.
- [ ] **Step 2–5** as usual; commit `feat(hebrew): DOCX RTL checker`

### Task 8: References, glossary, evals, SKILL.md updates

**Files:**
- Create: `skills/hebrew-with-english/references/{chat-markdown.md, docx.md, latex.md, pptx.md}`, `references/glossary/<12 families>.md`
- Create: eval cases: `skills/hebrew-with-english/evals/{long-technical-explanation-rtl, docx-summary-bidi, latex-section-hebrew}/…`, `skills/prompt-injection-scanner/evals/{pdf-white-text-canary, readme-html-comment-no-keywords, self-exempting-file, clean-assignment-continues, hebrew-hidden-docx}/…`
- Modify: both `SKILL.md` (routing by output format; glossary rule; `--quick`; ≤ 300 lines)

- [ ] **Step 1: Write references and glossary** (glossary: 10–40 pairs per family, `| עברית | English | הערה |`, every row opens with Hebrew).
- [ ] **Step 2: Write eval cases** per `claude plugin eval` layout (`prompt.md` with frontmatter `tags`, `max_turns: 20`, `timeout_seconds: 600`, `allowed_tools`; `case.yaml` `schema_version: "1.1"`; graders `type: llm`, one assertion each; input files generated by a `place-files.sh` that calls the fixture generator).
- [ ] **Step 3: Move the chat rules** of hebrew-with-english into `references/chat-markdown.md`, leaving SKILL.md as routing + the mandatory verify step; add `shared/sync.json` entry for the glossary? — no: glossary is per-skill content, not shared; keep in the skill.
- [ ] **Step 4: Write `tools/trigger_evals/{hebrew-with-english,prompt-injection-scanner}.json`** — 20 realistic queries each (`[{"query","should_trigger"}]`), ≥ 8 should-not-trigger near-misses (e.g. "translate this paragraph to English", "what is prompt injection?").
- [ ] **Step 5: Run** `pytest -q` (portability: every referenced path exists; RTL on Hebrew files) → PASS
- [ ] **Step 6: Commit** — `feat(hebrew,scanner): references, glossary and eval cases`
