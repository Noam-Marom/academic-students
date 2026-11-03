"""Checks shared by every skill's tests: the eval-case layout (docs/skill-conventions.md §2.5) and the trigger-eval
file (§2.6). Imported by path from skills/<skill>/tests/conftest.py; not a test module itself."""
import json
import pathlib
import re

import yaml

FORBIDDEN_NAMES = {"results", "mocks", "files", "true", "false", "null"}
MAX_FIXTURE_CHARS = 4000  # "one page": fixtures are short and written for the test


def _frontmatter(path: pathlib.Path) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path}: frontmatter missing"
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def check_case(case: pathlib.Path) -> None:
    assert case.is_dir(), f"missing eval case {case}"
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", case.name) and case.name not in FORBIDDEN_NAMES, case.name
    fm, body = _frontmatter(case / "prompt.md")
    assert isinstance(fm.get("tags"), list) and fm["tags"], f"{case.name}: prompt.md tags"
    assert isinstance(fm.get("max_turns"), int) and isinstance(fm.get("timeout_seconds"), int), case.name
    assert isinstance(fm.get("allowed_tools"), list) and fm["allowed_tools"], case.name
    assert body.strip(), f"{case.name}: empty prompt"
    cfg = yaml.safe_load((case / "case.yaml").read_text(encoding="utf-8"))
    assert cfg["schema_version"] == "1.1" and cfg["name"] == case.name, case.name
    assert isinstance(cfg.get("expected_outcome"), str) and cfg["expected_outcome"].strip(), case.name
    files = case / "files"
    if files.exists():
        script = (cfg.get("context") or {}).get("scaffold_script")
        assert script and (case / script).is_file(), f"{case.name}: context.scaffold_script missing"
        for f in files.rglob("*"):
            if f.is_file():
                assert f.stat().st_size <= MAX_FIXTURE_CHARS * 3, f"{f}: fixture longer than a page"
    graders = sorted((case / "graders").glob("*.md"))
    assert graders, f"{case.name}: no graders"
    for g in graders:
        assert re.fullmatch(r"\d{2}-[a-z0-9-]+\.md", g.name), g.name
        gfm, gbody = _frontmatter(g)
        assert gfm.get("type") == "llm" and gfm.get("focus") == "trace" and gfm.get("weight") == 1, g
        assert gbody.strip(), g


def check_trigger_file(path: pathlib.Path) -> None:
    items = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(items, list) and len(items) == 20, f"{path}: expected 20 queries"
    for it in items:
        assert set(it) == {"query", "should_trigger"} and isinstance(it["should_trigger"], bool) and it["query"].strip()
    assert sum(not it["should_trigger"] for it in items) >= 8, f"{path}: need >= 8 near-miss negatives"
    assert len({it["query"] for it in items}) == 20, f"{path}: duplicate queries"
