"""Eval cases and trigger-eval files follow docs/skill-conventions.md §2.5 and §2.6.

The `claude plugin eval` loader rejects unknown frontmatter keys and graders without `type:`; this test catches
that locally (evals are billed model runs, so the shape is checked before anyone pays to run them).
"""
import json
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPT_KEYS = {"tags", "max_turns", "timeout_seconds", "allowed_tools", "model", "disallowed_tools", "description"}
CASE_KEYS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome", "context", "execution"}
GRADER_TYPES = {"regex", "tool_order", "tool_used", "file_exists", "llm", "baseline"}
FORBIDDEN_CASE_NAMES = {"results", "mocks", "files", "true", "false", "null"}
NEAR_MISS_MIN = 8
QUERIES_PER_SKILL = 20


def _frontmatter(path: pathlib.Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    assert m, f"{path.relative_to(ROOT)}: frontmatter missing"
    data = yaml.safe_load(m.group(1)) or {}
    assert isinstance(data, dict), f"{path.relative_to(ROOT)}: frontmatter must be a mapping"
    return data, m.group(2)


def eval_cases() -> list[pathlib.Path]:
    return sorted(p.parent for p in (ROOT / "evals").glob("**/prompt.md") if "results" not in p.parts)


@pytest.mark.parametrize("case", eval_cases(), ids=lambda p: str(p.relative_to(ROOT / "evals")))
def test_eval_case_layout(case: pathlib.Path):
    rel = case.relative_to(ROOT)
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", case.name), f"{rel}: case name must be lowercase-with-hyphens"
    assert case.name not in FORBIDDEN_CASE_NAMES, f"{rel}: reserved case name"

    fm, body = _frontmatter(case / "prompt.md")
    assert set(fm) <= PROMPT_KEYS, f"{rel}/prompt.md: unknown frontmatter keys {sorted(set(fm) - PROMPT_KEYS)}"
    for key in ("tags", "max_turns", "timeout_seconds", "allowed_tools"):
        assert key in fm, f"{rel}/prompt.md: frontmatter lacks {key}"
    assert body.strip(), f"{rel}/prompt.md: empty prompt"
    assert "TODO" not in body, f"{rel}/prompt.md: still a template"

    case_yaml = case / "case.yaml"
    assert case_yaml.exists(), f"{rel}: case.yaml missing"
    data = yaml.safe_load(case_yaml.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert set(data) <= CASE_KEYS, f"{rel}/case.yaml: unknown keys {sorted(set(data) - CASE_KEYS)}"
    assert data.get("schema_version") == "1.1", f"{rel}/case.yaml: schema_version must be the string \"1.1\""
    assert data.get("name") == case.name, f"{rel}/case.yaml: name must equal the folder name"
    assert data.get("expected_outcome"), f"{rel}/case.yaml: expected_outcome missing"

    files_dir = case / "files"
    if files_dir.exists() and any(files_dir.iterdir()):
        assert (case / "place-files.sh").exists(), f"{rel}: files/ present but no place-files.sh"
        assert data.get("context", {}).get("scaffold_script") == "place-files.sh", \
            f"{rel}/case.yaml: context.scaffold_script must be place-files.sh when files/ exists"

    graders = sorted((case / "graders").glob("*.md"))
    assert graders, f"{rel}: no graders"
    for g in graders:
        assert re.fullmatch(r"\d{2}-[a-z0-9-]+\.md", g.name), f"{rel}/graders/{g.name}: name must be NN-slug.md"
        gfm, gbody = _frontmatter(g)
        assert gfm.get("type") in GRADER_TYPES, f"{rel}/graders/{g.name}: type must be one of {sorted(GRADER_TYPES)}"
        assert gfm.get("weight") == 1, f"{rel}/graders/{g.name}: weight must be 1"
        if gfm["type"] == "llm":
            assert gfm.get("focus") == "trace", f"{rel}/graders/{g.name}: llm graders use focus: trace"
            assert gbody.strip() and "TODO" not in gbody, f"{rel}/graders/{g.name}: empty or template criteria"


def trigger_files() -> list[pathlib.Path]:
    return sorted((ROOT / "tools" / "trigger_evals").glob("*.json"))


@pytest.mark.parametrize("path", trigger_files(), ids=lambda p: p.stem)
def test_trigger_evals_have_twenty_queries_and_eight_near_misses(path: pathlib.Path):
    assert (ROOT / "skills" / path.stem / "SKILL.md").exists(), f"{path.name}: no skill named {path.stem}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == QUERIES_PER_SKILL, f"{path.name}: need exactly {QUERIES_PER_SKILL} queries"
    for item in data:
        assert set(item) == {"query", "should_trigger"}, f"{path.name}: each item is {{query, should_trigger}}"
        assert isinstance(item["query"], str) and item["query"].strip()
        assert isinstance(item["should_trigger"], bool)
    negatives = [i for i in data if not i["should_trigger"]]
    assert len(negatives) >= NEAR_MISS_MIN, f"{path.name}: at least {NEAR_MISS_MIN} near-miss negatives"
    assert len({i["query"] for i in data}) == QUERIES_PER_SKILL, f"{path.name}: duplicate queries"


def test_evals_live_outside_skills_and_case_names_are_unique():
    # `claude plugin eval` refuses an --eval-dir inside skills/ (a loaded component directory), and filters
    # cases by name, so every case lives under evals/<skill>/ with a name used once.
    assert not list((ROOT / "skills").glob("*/evals")), "move skills/<name>/evals to evals/<name>"
    names = [c.name for c in eval_cases()]
    assert len(names) == len(set(names)), sorted({n for n in names if names.count(n) > 1})
    for c in eval_cases():
        assert (ROOT / "skills" / c.relative_to(ROOT / "evals").parts[0] / "SKILL.md").exists(), c


@pytest.mark.parametrize("case", [c for c in eval_cases() if (c / "place-files.sh").exists()],
                         ids=lambda p: str(p.relative_to(ROOT / "evals")))
def test_scaffold_script_runs_and_places_files(case, tmp_path):
    import subprocess
    proc = subprocess.run(["bash", str(case / "place-files.sh"), str(tmp_path)], cwd=tmp_path,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-500:]
    assert any(tmp_path.iterdir()), "the scaffold placed no files"
