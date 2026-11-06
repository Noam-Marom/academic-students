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
