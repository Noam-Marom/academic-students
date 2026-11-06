"""The skills follow the open Agent Skills format and install in other agents, not only Claude."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE_ONLY = ["claude.ai", "Claude Code", "Claude in Chrome", "Claude Desktop", "Claude desktop", "desktop app"]


def test_gemini_extension_manifest_matches_the_plugin():
    ext = json.loads((ROOT / "gemini-extension.json").read_text(encoding="utf-8"))
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert ext["name"] == plugin["name"] and ext["version"] == plugin["version"]
    moodle = ext["mcpServers"]["moodle"]
    assert moodle["command"] == "uv" and "${extensionPath}" in " ".join(moodle["args"])
    assert (ROOT / ext["contextFileName"]).is_file()


def test_agents_md_briefs_any_coding_agent():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "CLAUDE.md" in text and "TDD" in text and "password" in text


def test_skill_bodies_name_no_claude_only_product():
    for skill_md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        body = skill_md.read_text(encoding="utf-8").split("---", 2)[2]
        hits = [t for t in CLAUDE_ONLY if t in body]
        assert not hits, f"{skill_md.parent.name}: {hits}"


def test_readme_installs_in_every_agent():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for key in ["npx skills add Noam-Marom/academic-students", "gemini extensions install", "Codex", "Gemini CLI",
                "Cursor", "Copilot", "ChatGPT"]:
        assert key in text, key
