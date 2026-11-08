"""Owner's rule (2026-11-08): the plugin has no notion of a course AI policy at all. The skills do what the
student asks: a hint gets a hint, "solve it" gets the full solution of the actual question, a scan gets a scan.
No policy check, no question about what the course allows, no `ai_policy` field, no disclosure sentence.
Course rules are the student's responsibility (TERMS.md)."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
# Text that would bring the idea back: a policy field, a policy file, a disclosure sentence, or a question to the
# student about what the course allows.
CONCEPT = re.compile(r"ai[_-]policy|AI[- ]policy|allowed-with-disclosure|disclosure sentence|"
                     r"what (?:the|your) course allows|course(?:'s)? AI rules|מדיניות (?:ה-?)?AI|מדיניות בינה", re.I)
GATES = ["nearest permitted mode", "is a ceiling", "ask once what the course allows", "Under a restrictive",
         "explicit request + policy", "only when the course's AI policy permits", "proceed as `limited`",
         "Under `forbidden`"]


def _skill_files():
    for p in sorted((ROOT / "skills").rglob("*")):
        if p.is_file() and p.suffix in {".md", ".json", ".py", ".yaml", ".yml"} and "tests" not in p.parts \
                and "__pycache__" not in p.parts:
            yield p


def test_no_skill_file_carries_the_ai_policy_idea():
    hits = [f"{p.relative_to(ROOT)}: {m.group(0)!r}" for p in _skill_files()
            for m in [CONCEPT.search(p.read_text(encoding="utf-8", errors="ignore"))] if m]
    assert not hits, "\n".join(hits)


def test_no_skill_gates_on_a_course_policy():
    for skill in SKILLS:
        body = skill.read_text(encoding="utf-8")
        for gate in GATES:
            assert gate not in body, f"{skill.parent.name}: {gate!r}"


def test_shared_has_no_policy_file_and_sync_has_no_policy_target():
    assert not (ROOT / "shared/ai-policy.md").exists()
    assert "ai_policy" not in json.loads((ROOT / "shared/sync.json").read_text(encoding="utf-8"))
    assert not list((ROOT / "skills").glob("*/references/ai-policy.md"))


def test_course_template_has_no_policy_field():
    text = (ROOT / "shared/COURSE.template.md").read_text(encoding="utf-8")
    assert not CONCEPT.search(text), CONCEPT.search(text)


def test_coach_and_writing_solve_and_draft_on_request():
    coach = (ROOT / "skills/assignment-coach/SKILL.md").read_text(encoding="utf-8")
    writing = (ROOT / "skills/academic-writing/SKILL.md").read_text(encoding="utf-8")
    assert "the full solution of the actual question" in coach
    assert "on request" in writing.split("| `draft` |")[1].split("\n")[0]
