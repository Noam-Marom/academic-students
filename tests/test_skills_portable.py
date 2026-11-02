"""Every skill must work when its folder is uploaded to claude.ai on its own."""
import pathlib

import pytest

from tests.conftest import skill_dirs
from tools.check_portability import check_skill

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("skill", skill_dirs(), ids=lambda p: p.name)
def test_skill_is_portable(skill):
    assert check_skill(skill) == []


# --- unit tests for the checker itself, on synthetic skills -----------------------------------------

def make_skill(tmp_path: pathlib.Path, name: str, frontmatter: str, body: str) -> pathlib.Path:
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return d


def test_rejects_claude_code_only_frontmatter(tmp_path):
    d = make_skill(tmp_path, "s", 'name: s\ndescription: d\nargument-hint: "[file]"', "# s\n")
    assert any("argument-hint" in p for p in check_skill(d))


def test_rejects_name_mismatch_and_long_description(tmp_path):
    d = make_skill(tmp_path, "s", "name: other\ndescription: " + "x" * 1025, "# s\n")
    problems = check_skill(d)
    assert any("name" in p for p in problems)
    assert any("1024" in p for p in problems)


def test_rejects_missing_referenced_path_and_plugin_root(tmp_path):
    d = make_skill(tmp_path, "s", "name: s\ndescription: d",
                   "# s\nRun `scripts/missing.py` from ${CLAUDE_PLUGIN_ROOT}/x\n")
    problems = check_skill(d)
    assert any("scripts/missing.py" in p for p in problems)
    assert any("CLAUDE_PLUGIN_ROOT" in p for p in problems)


def test_rejects_long_body(tmp_path):
    d = make_skill(tmp_path, "s", "name: s\ndescription: d", "# s\n" + "line\n" * 301)
    assert any("300" in p for p in check_skill(d))


def test_clean_skill_passes(tmp_path):
    d = make_skill(tmp_path, "s", "name: s\ndescription: d\nlicense: MIT",
                   "# s\nRun `scripts/ok.py`.\n")
    (d / "scripts").mkdir()
    (d / "scripts" / "ok.py").write_text("", encoding="utf-8")
    assert check_skill(d) == []
