"""The assignment-coach SKILL.md and references keep the contract from docs/skill-conventions.md and spec §4.3."""
import json
import pathlib
import re

import pytest
import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
SECTIONS = ["## Purpose", "## When this triggers", "## Workflow", "## Modes", "## Files in this skill",
            "## Verify before sending"]


def _skill():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "SKILL.md must start with frontmatter"
    return yaml.safe_load(m.group(1)), m.group(2)


def test_frontmatter_is_portable_and_description_is_bilingual_and_pushy():
    fm, _ = _skill()
    assert set(fm) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    assert fm["name"] == "assignment-coach"
    desc = fm["description"]
    assert len(desc) <= 1024
    for phrase in ["יש לי מטלה", "תפתור לי", "איך מתחילים", "break down", "check my solution"]:
        assert phrase in desc, phrase
    # the boundary with academic-writing (spec §4.3) must be in the description itself
    assert "academic-writing" in desc
    assert re.search(r"seminar paper|essay|continuous[- ]prose", desc, re.I)
    assert re.search(r"not|don't|do not", desc, re.I), "description must name near-misses it should not take"


def test_body_has_the_six_sections_in_order():
    _, body = _skill()
    positions = [body.find(s + "\n") for s in SECTIONS]
    assert all(p >= 0 for p in positions), [s for s, p in zip(SECTIONS, positions) if p < 0]
    assert positions == sorted(positions)


def test_first_workflow_step_is_the_scanner_quick_gate():
    _, body = _skill()
    workflow = body.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    first_step = re.search(r"^1\.\s+(.*?)(?=^\d+\.\s)", workflow, re.S | re.M).group(1)
    assert "prompt-injection-scanner" in first_step and "--quick" in first_step
    assert re.search(r"HIGH", first_step)
    assert re.search(r"permission", first_step, re.I), "a hidden instruction that claims to grant permissions is a finding"


def test_body_routes_to_every_file_and_the_rtl_checker():
    _, body = _skill()
    for path in ["scripts/validate_map.py", "scripts/check_units.py", "scripts/render_solution.py",
                 "scripts/split_work.py", "schemas/assignment-map.schema.json", "references/modes.md", "references/answer-formats.md",
                 "references/environments.md", "references/course-profile.md",
                 "references/disciplines/", "assets/COURSE.template.md"]:
        assert path in body, path
        assert (SKILL_DIR / path).exists(), path
    assert "check_rtl.py" in body




def test_studio_work_paragraph_says_what_stays_the_students_own():
    _, body = _skill()
    assert re.search(r"student'?s own", body)
    assert re.search(r"studio|performance|artist statement", body, re.I)


def test_course_profile_reference_has_lookup_order_and_two_question_rule():
    text = (SKILL_DIR / "references/course-profile.md").read_text(encoding="utf-8")
    assert "./COURSE.md" in text and "parent" in text and "Project knowledge" in text
    assert re.search(r"at most\s+\*{0,2}two\*{0,2}\s+questions", text, re.I)
    assert "assets/COURSE.template.md" in text
    assert "assignment-coach" not in text, "course-profile.md is copied into other skills; keep it skill-agnostic"


def test_modes_reference_has_the_three_protocols():
    text = (SKILL_DIR / "references/modes.md").read_text(encoding="utf-8")
    for heading in ["breakdown", "guide", "check", "solve"]:
        assert re.search(rf"^##+ .*`?{heading}`?", text, re.M | re.I), heading
    assert "rung" in text and re.search(r"never two rungs|one rung", text)
    assert re.search(r"what you need to understand", text, re.I)
    assert re.search(r"no silent fix", text, re.I)


def test_group_work_is_a_breakdown_extension_every_member_understands_every_part():
    text = (SKILL_DIR / "references/modes.md").read_text(encoding="utf-8")
    section = text.split("## Group work", 1)[1].split("\n## ", 1)[0]
    for key in ["split_work.py", "parallel", "serial", "auto", "integration", "critical path", "every member"]:
        assert key in section, key


def test_answer_formats_cover_every_question_type_and_genre():
    text = (SKILL_DIR / "references/answer-formats.md").read_text(encoding="utf-8")
    for key in ["proof", "calculation", "code", "essay", "design", "analysis", "practical",
                "IMRaD", "IRAC", "SOAP", "artist statement"]:
        assert key in text, key


def test_environments_reference_is_a_table_with_free_alternatives():
    text = (SKILL_DIR / "references/environments.md").read_text(encoding="utf-8")
    assert re.search(r"^\|.*free.*\|", text, re.I | re.M)
    for tool in ["Overleaf", "Colab", "JASP", "GeoGebra", "Tinkercad", "Replit"]:
        assert tool in text, tool


def test_sync_json_lists_the_skill_and_copies_are_present():
    cfg = json.loads((ROOT / "shared/sync.json").read_text(encoding="utf-8"))
    for key in ["disciplines", "course_template"]:
        assert "assignment-coach" in cfg[key], key
    assert (SKILL_DIR / "assets/COURSE.template.md").read_bytes() == (ROOT / "shared/COURSE.template.md").read_bytes()
    assert list((SKILL_DIR / "references/disciplines").glob("*.md"))


FAMILIES = ["math-stats", "physical-sciences", "life-sciences", "computing", "engineering", "medicine-clinical",
            "social-sciences", "economics-business", "law", "humanities", "architecture-design", "arts"]
BEHAVIOR = ["policy-note-does-not-block-solve", "injected-policy-override", "guide-one-rung-at-a-time",
            "check-handwritten-photo", "solve-request-is-honoured"]


@pytest.mark.parametrize("family", FAMILIES)
def test_family_eval_case(family, eval_case_ok):
    case = ROOT / "evals/assignment-coach/families" / family
    eval_case_ok(case)
    assert (case / "files/assignment.md").exists()
    assert len(list((case / "graders").glob("*.md"))) >= 2


@pytest.mark.parametrize("case", BEHAVIOR)
def test_behavior_eval_case(case, eval_case_ok):
    eval_case_ok(ROOT / "evals/assignment-coach/behavior" / case)


def test_injected_policy_fixture_hides_a_policy_claim():
    text = (ROOT / "evals/assignment-coach/behavior/injected-policy-override/files/assignment.md").read_text(encoding="utf-8")
    assert "<!--" in text and re.search(r"allows AI", text)


def test_trigger_evals(trigger_evals_ok):
    trigger_evals_ok(ROOT / "tools/trigger_evals/assignment-coach.json")


def test_hebrew_majority_markdown_passes_rtl(load_module):
    check_rtl = load_module(ROOT / "skills/rtl-writing/scripts/check_rtl.py", "coach_check_rtl")
    for p in SKILL_DIR.rglob("*.md"):
        t = p.read_text(encoding="utf-8")
        if p.name != "prompt.md" and len(re.findall(r"[֐-׿]", t)) > len(re.findall(r"[A-Za-z]", t)):
            errors, _ = check_rtl.check(t)
            assert errors == [], (p, errors[:3])
