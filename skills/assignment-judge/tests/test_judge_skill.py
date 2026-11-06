"""The assignment-judge SKILL.md keeps the contract from docs/skill-conventions.md and the grading protocol."""
import json
import pathlib
import re

import pytest
import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]
SECTIONS = ["## Purpose", "## When this triggers", "## Workflow", "## Modes", "## Files in this skill",
            "## Verify before sending"]
EVALS = ["grade-with-persona-and-range", "instructions-are-the-contract", "injected-grade-instruction",
         "forbidden-policy-asks-first"]


def _skill():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert m, "SKILL.md must start with frontmatter"
    return yaml.safe_load(m.group(1)), m.group(2), text


def test_frontmatter_is_portable_bilingual_and_names_its_boundaries():
    fm, _, _ = _skill()
    assert set(fm) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    assert fm["name"] == "assignment-judge"
    desc = fm["description"]
    assert len(desc) <= 1024
    for phrase in ["מה הציון", "professor", "what grade would", "assignment-coach", "academic-writing", "exam-prep"]:
        assert phrase in desc, phrase
    assert re.search(r"do not|not for", desc, re.I)


def test_body_has_the_six_sections_in_order_and_fits():
    _, body, text = _skill()
    positions = [body.find(s + "\n") for s in SECTIONS]
    assert all(p >= 0 for p in positions), [s for s, p in zip(SECTIONS, positions) if p < 0]
    assert positions == sorted(positions)
    assert len(text.splitlines()) <= 300


def test_first_workflow_step_is_the_scanner_quick_gate():
    _, body, _ = _skill()
    workflow = body.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    first = re.search(r"^1\.\s+(.*?)(?=^\d+\.\s)", workflow, re.S | re.M).group(1)
    assert "prompt-injection-scanner" in first and "--quick" in first and "HIGH" in first


def test_body_routes_to_every_file():
    _, body, _ = _skill()
    for path in ["scripts/score_rubric.py", "references/grading-protocol.md", "references/calibration.md",
                 "references/ai-policy.md", "references/disciplines/", "assets/COURSE.template.md"]:
        assert path in body, path
        assert (SKILL_DIR / path).exists(), path
    assert "check_rtl.py" in body


def test_protocol_essentials_are_in_the_body():
    _, body, _ = _skill()
    for key in ["year", "degree", "instructions", "two independent passes", "evidence", "range"]:
        assert key in body, key
    assert re.search(r"estimate", body) and re.search(r"not the (course's|lecturer's) grade", body)
    assert re.search(r"never rewrites|does not rewrite|no silent fix", body, re.I)


def test_grading_protocol_reference():
    text = (SKILL_DIR / "references/grading-protocol.md").read_text(encoding="utf-8")
    for key in ["derived rubric", "Pass A", "Pass B", "blind", "reconcile", "score_rubric.py", "quote",
                "What would raise the grade", "What already earns credit"]:
        assert key in text, key


def test_calibration_reference_covers_years_and_scales():
    text = (SKILL_DIR / "references/calibration.md").read_text(encoding="utf-8")
    for key in ["first year", "master", "0–100", "letter", "UK", "pass mark"]:
        assert key in text, key


def test_policy_matrix_has_a_judge_column_and_body_does_not_restate_it():
    policy = (ROOT / "shared/ai-policy.md").read_text(encoding="utf-8")
    header = next(l for l in policy.splitlines() if l.startswith("| Value"))
    assert "`assignment-judge`" in header
    _, body, _ = _skill()
    for row in [l for l in policy.splitlines() if l.startswith("| `")]:
        assert row.split("|")[2].strip() not in body


def test_sync_json_lists_the_skill_and_copies_are_present():
    cfg = json.loads((ROOT / "shared/sync.json").read_text(encoding="utf-8"))
    for key in ["disciplines", "course_template", "ai_policy"]:
        assert "assignment-judge" in cfg[key], key
    assert (SKILL_DIR / "references/ai-policy.md").read_bytes() == (ROOT / "shared/ai-policy.md").read_bytes()


@pytest.mark.parametrize("case", EVALS)
def test_eval_case(case, eval_case_ok):
    eval_case_ok(SKILL_DIR / "evals" / case)


def test_trigger_evals(trigger_evals_ok):
    trigger_evals_ok(ROOT / "tools/trigger_evals/assignment-judge.json")


def test_hebrew_majority_markdown_passes_rtl(load_module):
    check_rtl = load_module(ROOT / "skills/hebrew-with-english/scripts/check_rtl.py", "judge_check_rtl")
    for p in SKILL_DIR.rglob("*.md"):
        t = p.read_text(encoding="utf-8")
        if p.name != "prompt.md" and len(re.findall(r"[֐-׿]", t)) > len(re.findall(r"[A-Za-z]", t)):
            assert check_rtl.check(t)[0] == [], p
