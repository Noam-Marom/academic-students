"""The Moodle MCP is registered for the plugin, and the moodle-sync skill ships its evals and trigger queries."""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "moodle-sync"
EVAL_CASES = ["sync-then-scan", "no-mcp-fallback-zip", "refuses-password", "refuses-quiz"]


def test_mcp_json_registers_the_moodle_server_via_uv():
    cfg = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert cfg == {"mcpServers": {"moodle": {"command": "uv", "args": [
        "run", "--directory", "${CLAUDE_PLUGIN_ROOT}/servers/moodle-mcp", "moodle-mcp", "serve"]}}}
    assert (ROOT / "servers/moodle-mcp/pyproject.toml").exists()


def test_moodle_sync_skill_files_exist():
    for rel in ["SKILL.md", "references/without-mcp.md", "references/folder-layout.md"]:
        assert (SKILL / rel).exists(), rel
    for rel in ["README.md", "MANUAL_CHECKS.md"]:
        assert (ROOT / "servers/moodle-mcp" / rel).exists(), rel


def test_moodle_sync_description_is_bilingual():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    desc = fm["description"]
    assert any("֐" <= ch <= "׿" for ch in desc), "description needs Hebrew trigger phrases"
    assert "moodle" in desc.lower()


def test_eval_cases_have_the_plugin_eval_layout():
    for case in EVAL_CASES:
        d = ROOT / "evals/moodle-sync" / case
        assert (d / "prompt.md").exists(), case
        meta = yaml.safe_load((d / "case.yaml").read_text(encoding="utf-8"))
        assert meta["schema_version"] == "1.1" and meta["name"] == case and meta["expected_outcome"]
        assert sorted((d / "graders").glob("*.md")), f"{case}: no graders"


def test_refuses_password_case_checks_the_password_is_not_echoed():
    prompt = (ROOT / "evals/moodle-sync/refuses-password/prompt.md").read_text(encoding="utf-8")
    assert "hunter2" in prompt
    graders = " ".join(p.read_text(encoding="utf-8") for p in (ROOT / "evals/moodle-sync/refuses-password/graders").glob("*.md"))
    assert "hunter2" in graders and "moodle-mcp login" in graders


def test_trigger_evals_twenty_queries_with_near_miss_negatives():
    data = json.loads((ROOT / "tools/trigger_evals/moodle-sync.json").read_text(encoding="utf-8"))
    assert len(data) == 20
    assert all(set(q) == {"query", "should_trigger"} for q in data)
    assert sum(not q["should_trigger"] for q in data) >= 8
    assert sum(q["should_trigger"] for q in data) >= 8
    assert len({q["query"] for q in data}) == 20


def test_connect_order_is_server_then_auto_setup_then_browser_then_exports():
    body = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("## Workflow", 1)[1].split("\n## ", 1)[0]
    first = body.split("\n2. ", 1)[0]
    for key in ["scripts/setup_check.py", "references/connect.md", "references/via-browser.md",
                "references/without-mcp.md"]:
        assert key in first, key
    connect = (SKILL / "references/connect.md").read_text(encoding="utf-8")
    assert connect.index("setup_check.py") < connect.index("via-browser.md") < connect.index("without-mcp.md")
    assert "ask" in connect.lower() and "never" in connect.lower()


def test_browser_fallback_is_read_only_and_never_signs_in_for_the_student():
    text = (SKILL / "references/via-browser.md").read_text(encoding="utf-8")
    for key in ["read-only", "signs in", "Download course content", "Export calendar", "before downloading",
                "quiz", "submit", "prompt-injection-scanner"]:
        assert key in text, key
