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
