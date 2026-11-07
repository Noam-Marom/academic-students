"""Owner's rule (2026-11-07): the skills do what the student asks. A hint gets a hint, "solve it" gets the full
solution of the actual question, a scan gets a scan. No course-policy check, no question about the course's
rules, no reminder. Course rules are the student's responsibility (TERMS.md)."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
GATES = ["nearest permitted mode", "is a ceiling", "ask once what the course allows", "Under a restrictive",
         "explicit request + policy", "it does not make the work", "only when the course's AI policy permits",
         "permitted by `references/ai-policy.md`", "Read the row for the course's", "the policy was\n  mentioned",
         "under any\npolicy", "proceed as `limited`", "Under `forbidden`"]


def test_no_skill_gates_or_mentions_a_course_policy():
    for skill in SKILLS:
        body = skill.read_text(encoding="utf-8")
        for gate in GATES:
            assert gate not in body, f"{skill.parent.name}: {gate!r}"


def test_the_shared_rule_says_the_student_decides():
    text = (ROOT / "shared/ai-policy.md").read_text(encoding="utf-8")
    assert "the student decides" in text.lower()
    assert "no course-policy check" in text and "full solution of the actual question" in text
    assert "| `limited` |" not in text, "the old permission matrix is gone"


def test_coach_and_writing_solve_and_draft_on_request():
    coach = (ROOT / "skills/assignment-coach/SKILL.md").read_text(encoding="utf-8")
    writing = (ROOT / "skills/academic-writing/SKILL.md").read_text(encoding="utf-8")
    assert "the full solution of the actual question" in coach
    assert "on request" in writing.split("| `draft` |")[1].split("\n")[0]
