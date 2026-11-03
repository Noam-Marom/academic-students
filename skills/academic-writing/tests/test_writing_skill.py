"""The academic-writing SKILL.md, references and evals keep the contract from docs/skill-conventions.md and spec §4.4."""
import json
import pathlib
import re

import pytest
import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
SECTIONS = ["## Purpose", "## When this triggers", "## Workflow", "## Modes", "## Files in this skill",
            "## Verify before sending"]
GENRES = ["seminar-paper", "imrad-lab-report", "literature-review", "research-proposal", "legal-opinion",
          "clinical-case-study", "policy-paper", "reflection", "artist-statement", "abstract"]
STYLES = ["apa7", "ieee", "chicago", "mla", "vancouver", "hebrew-legal"]
EVALS = ["plan-seminar-sociology", "feedback-lab-report-4-planted-issues", "edit-english-hebrew-speaker-errors",
         "cite-no-fabrication", "mixed-hebrew-english-reflist", "forbidden-policy-draft-request"]
HEB = re.compile(r"[֐-׿]")


def _skill():
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"), re.S)
    assert m
    return yaml.safe_load(m.group(1)), m.group(2)


def test_frontmatter_portable_and_description_bilingual_with_boundary():
    fm, _ = _skill()
    assert set(fm) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    assert fm["name"] == "academic-writing"
    desc = fm["description"]
    assert len(desc) <= 1024 and HEB.search(desc)
    for phrase in ["עבודה סמינריונית", "רשימת מקורות", "seminar paper", "references"]:
        assert phrase in desc, phrase
    assert "assignment-coach" in desc and re.search(r"discrete questions", desc)
    assert re.search(r"Do NOT", desc)


def test_six_sections_in_order_and_scanner_first():
    _, body = _skill()
    pos = [body.find(s + "\n") for s in SECTIONS]
    assert all(p >= 0 for p in pos) and pos == sorted(pos)
    workflow = body.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    first = re.search(r"^1\.\s+(.*?)(?=^\d+\.\s)", workflow, re.S | re.M).group(1)
    assert "prompt-injection-scanner" in first and "--quick" in first and "HIGH" in first
    assert re.search(r"polic", first, re.I)


def test_modes_never_invent_and_checks_named():
    _, body = _skill()
    for mode in ["plan", "feedback", "edit", "cite", "draft"]:
        assert f"`{mode}`" in body
    assert "[unverified]" in body and "check_citations.py" in body and "check_rtl.py" in body
    assert re.search(r"language", body, re.I)


def test_disclosure_quoted_verbatim_and_matrix_not_restated():
    policy = (ROOT / "shared/ai-policy.md").read_text(encoding="utf-8")
    _, body = _skill()
    for q in re.findall(r"^> (.+)$", policy.split("## Disclosure sentence", 1)[1], re.M):
        assert q in body
    for row in [l for l in policy.splitlines() if l.startswith("| `")]:
        assert row.split("|")[2].strip() not in body


def test_every_mentioned_file_exists():
    _, body = _skill()
    for path in ["scripts/check_citations.py", "scripts/format_refs.py", "scripts/word_count.py",
                 "references/genres/", "references/hebrew-academic.md", "references/english-academic.md",
                 "references/citation-styles/", "references/rubric-default.md", "references/course-profile.md",
                 "references/ai-policy.md", "references/disciplines/", "assets/COURSE.template.md"]:
        assert path in body and (SKILL_DIR / path).exists(), path


def test_course_profile_is_a_verbatim_copy_of_the_coach_one():
    a = (ROOT / "skills/assignment-coach/references/course-profile.md").read_bytes()
    assert (SKILL_DIR / "references/course-profile.md").read_bytes() == a


@pytest.mark.parametrize("genre", GENRES)
def test_genre_files_have_structure_rewards_and_five_mistakes(genre):
    text = (SKILL_DIR / f"references/genres/{genre}.md").read_text(encoding="utf-8")
    assert "## Structure" in text and "## What examiners reward" in text
    mistakes = text.split("## Common mistakes", 1)[1]
    assert len(re.findall(r"^\d+\.\s", mistakes, re.M)) == 5


@pytest.mark.parametrize("style", STYLES)
def test_citation_style_has_six_examples_incl_hebrew(style):
    text = (SKILL_DIR / f"references/citation-styles/{style}.md").read_text(encoding="utf-8")
    examples = text.split("## Examples", 1)[1].split("\n## ", 1)[0]
    entries = re.findall(r"^\d+\.\s+(.*)$", examples, re.M)
    assert len(entries) == 6
    assert any(HEB.search(e) for e in entries)


def test_english_error_list_has_fifteen_items():
    text = (SKILL_DIR / "references/english-academic.md").read_text(encoding="utf-8")
    section = text.split("## Errors Hebrew speakers make", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"^\d+\.\s", section, re.M)) == 15
    for topic in ["article", "preposition", "tense", "word order"]:
        assert topic in section.lower()


def test_rubric_default_is_five_by_four():
    text = (SKILL_DIR / "references/rubric-default.md").read_text(encoding="utf-8")
    rows = [l for l in text.splitlines() if l.startswith("| **")]
    assert len(rows) == 5
    assert all(len([c for c in r.strip("|").split("|")]) == 5 for r in rows)  # criterion + 4 levels


def test_sync_json_lists_the_skill():
    cfg = json.loads((ROOT / "shared/sync.json").read_text(encoding="utf-8"))
    for key in ["disciplines", "course_template", "ai_policy"]:
        assert "academic-writing" in cfg[key]
    assert (SKILL_DIR / "references/ai-policy.md").read_bytes() == (ROOT / "shared/ai-policy.md").read_bytes()


def test_hebrew_majority_markdown_passes_rtl(check_rtl_mod):
    for p in SKILL_DIR.rglob("*.md"):
        if p.name == "prompt.md":
            continue
        t = p.read_text(encoding="utf-8")
        if len(HEB.findall(t)) > len(re.findall(r"[A-Za-z]", t)):
            errors, _ = check_rtl_mod.check(t)
            assert errors == [], (p, errors[:3])


@pytest.mark.parametrize("case", EVALS)
def test_eval_cases_follow_conventions(case, eval_case_ok):
    eval_case_ok(SKILL_DIR / "evals" / case)


def test_trigger_evals(trigger_evals_ok):
    trigger_evals_ok(ROOT / "tools/trigger_evals/academic-writing.json")
