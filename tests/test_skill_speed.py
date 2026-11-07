"""Speed budget: no skill makes the model run the RTL checker on a chat reply (that means drafting the whole
reply into a tool call, re-running until clean, and retyping it). Files are checked; replies follow the rules."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_rtl_checker_is_for_files_not_chat_replies():
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        if skill.parent.name == "rtl-writing":
            continue
        for line in skill.read_text(encoding="utf-8").splitlines():
            if "check_rtl.py" in line:
                low = line.lower()
                assert "file" in low and "repl" not in low, f"{skill.parent.name}: {line.strip()}"


def test_judge_second_pass_needs_no_subagent_by_default():
    body = (ROOT / "skills/assignment-judge/SKILL.md").read_text(encoding="utf-8")
    step = body.split("5. **Grade in two independent passes**")[1].split("\n6. ")[0]
    assert "in the same context" in step and "only in `strict` mode" in step


FAST = ["assignment-coach", "academic-writing", "assignment-judge", "exam-prep", "lecture-notes",
        "study-planner", "moodle-sync"]


def _body(name):
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_every_task_skill_has_a_fast_path_before_its_workflow():
    """The common request is served first; the full workflow is for the full job."""
    for name in FAST:
        body = _body(name)
        assert "## Fast path" in body, name
        assert body.index("## Fast path") < body.index("## Workflow"), name
        fast = body.split("## Fast path")[1].split("\n## ")[0]
        assert len(fast.splitlines()) <= 22, f"{name}: keep the fast path short"


def test_questions_are_asked_only_when_a_wrong_guess_is_costly():
    for name in FAST:
        fast = _body(name).split("## Fast path")[1].split("\n## ")[0]
        assert "assume" in fast.lower() and "one line" in fast, name


def test_coach_writes_the_map_only_for_the_whole_assignment():
    fast = _body("assignment-coach").split("## Fast path")[1].split("\n## ")[0]
    assert "assignment-map.json" in fast and "one question" in fast


def test_exam_prep_builds_the_bank_only_from_past_exams():
    fast = _body("exam-prep").split("## Fast path")[1].split("\n## ")[0]
    assert "question_bank.py" in fast and "no past exams" in fast
