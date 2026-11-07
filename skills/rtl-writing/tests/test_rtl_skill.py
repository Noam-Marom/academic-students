"""rtl-writing covers every right-to-left language and still answers to its old name."""
import pathlib
import re

import yaml

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]


def _fm_body():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return yaml.safe_load(m.group(1)), m.group(2)


def test_description_names_the_rtl_languages_and_the_old_command():
    fm, _ = _fm_body()
    assert fm["name"] == "rtl-writing"
    d = fm["description"]
    assert len(d) <= 1024
    for key in ["Hebrew", "Arabic", "Persian", "Urdu", "/hebrew-with-english", "/rtl-writing", "עברית", "العربية"]:
        assert key in d, key


def test_other_rtl_languages_have_their_reference():
    _, body = _fm_body()
    assert "references/arabic-persian-urdu.md" in body
    ref = (SKILL_DIR / "references/arabic-persian-urdu.md").read_text(encoding="utf-8")
    for key in ["openers", "ZWNJ", "Noto Naskh Arabic", "polyglossia", "w:bidi", "check_rtl.py"]:
        assert key in ref, key


def test_a_chat_reply_needs_no_file_read_and_no_tool_call():
    """Speed: the rules for chat live in SKILL.md itself, and a chat reply is written once, opener first,
    without a reference read or a checker run (the checker is for files and for reported slips)."""
    _, body = _fm_body()
    assert len(body.splitlines()) <= 75, "keep the skill short: it is loaded on every RTL reply"
    for example in ["השפה Python היא", "החברה Marvel", "**הכלי Podman:**", "מינוס 1", "משנת 2008"]:
        assert example in body, example
    assert "no tool call" in body
    assert "references/chat-markdown.md" not in body.split("## Chat replies")[1].split("\n## ")[0]


def test_files_are_still_checked_mechanically():
    _, body = _fm_body()
    files = body.split("## Files you write")[1].split("\n## ")[0]
    assert "scripts/check_rtl.py" in files and "check_docx_rtl.py" in files


def test_rules_are_applied_while_writing_not_in_a_planning_or_review_pass():
    """Speed: in a real claude.ai run the skill tripled the thinking time. The model must not plan every
    line's opener in its thinking or re-check the reply line by line; only headings get a second look."""
    _, body = _fm_body()
    chat = body.split("## Chat replies")[1].split("\n## ")[0]
    assert "glance down the left edge" not in chat
    assert "Choose each line's" not in chat
    assert "do not plan the reply line by line" in chat and "headings" in chat
