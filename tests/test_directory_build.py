"""tools/build_directory.py: the clean tree published to the `directory` branch for the Claude plugin directory.

Only what an installer needs (skills, manifest, icon, README, license, changelog). No local MCP server (it does
not run on claude.ai, and the directory will accept local servers only from Verified organizations), no tests,
evals, docs or dev files (they caused most of the portal's policy holds)."""
import importlib.util
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("build_directory", ROOT / "tools/build_directory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path_factory.mktemp("directory")
    mod.build(ROOT, out)
    return out


def _files(out):
    return [p for p in out.rglob("*") if p.is_file()]


def test_ships_every_skill_with_the_manifest_readme_and_license(built):
    assert (built / ".claude-plugin/plugin.json").is_file()
    for name in ["README.md", "LICENSE", "CHANGELOG.md"]:
        assert (built / name).is_file(), name
    assert sorted(p.parent.name for p in built.glob("skills/*/SKILL.md")) == SKILLS


def test_leaves_out_the_local_server_and_every_dev_file(built):
    rels = [p.relative_to(built).as_posix() for p in _files(built)]
    for banned in [".mcp.json", "CLAUDE.md", "AGENTS.md", "GEMINI.md", "pyproject.toml",
                   ".claude-plugin/marketplace.json"]:
        assert banned not in rels, banned
    for prefix in ["servers/", "tests/", "evals/", "docs/", "tools/", "shared/", ".github/"]:
        assert not any(r.startswith(prefix) for r in rels), prefix
    assert not any(re.search(r"/(tests|evals|benchmark|__pycache__)/", "/" + r) for r in rels)


def test_only_text_files_and_the_icon_inside_the_portal_limits(built):
    files = _files(built)
    assert len(files) <= 512
    for p in files:
        rel = p.relative_to(built).as_posix()
        if rel == ".claude-plugin/icon.png":
            continue
        assert p.suffix.lower() not in {".png", ".gif", ".jpg", ".jpeg", ".docx", ".pdf", ".zip", ".pyc"}, rel
        assert p.stat().st_size < 256 * 1024, rel


def test_readme_links_resolve_inside_the_build_or_point_to_github(built):
    text = (built / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'src="([^"]+)"', text)
    for t in targets:
        if t.startswith(("http://", "https://", "#", "mailto:")):
            continue
        assert (built / t.split("#")[0]).exists(), t
    assert "https://raw.githubusercontent.com/Noam-Marom/academic-students/main/docs/images/scanner-demo.gif" in text


def test_readme_says_the_moodle_server_comes_with_the_github_install(built):
    text = (built / "README.md").read_text(encoding="utf-8")
    assert "Plugin directory build" in text and "github.com/Noam-Marom/academic-students" in text


def test_manifest_matches_main(built):
    import json
    assert json.loads((built / ".claude-plugin/plugin.json").read_text()) == \
        json.loads((ROOT / ".claude-plugin/plugin.json").read_text())


def test_a_workflow_publishes_the_build_to_the_directory_branch():
    wf = yaml.safe_load((ROOT / ".github/workflows/directory.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert "workflow_dispatch" in on and on["push"]["tags"] == ["v*"]
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job["steps"])
    assert "tools/build_directory.py" in steps and "pytest" in steps and "directory" in steps


def test_manifest_fills_the_directory_listing_links():
    """The portal reads these from plugin.json; without them it guessed the demo GIF as 'Documentation'."""
    import json
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    repo = "https://github.com/Noam-Marom/academic-students"
    assert m["repository"] == repo and m["homepage"] == repo
    assert m["documentationUrl"] == f"{repo}#readme"
    assert m["supportUrl"] == f"{repo}/discussions"
    assert m["privacyPolicyUrl"] == f"{repo}/blob/main/PRIVACY.md"
    assert (ROOT / "PRIVACY.md").is_file()


ALLOWED = {".md", ".txt", ".json", ".yaml", ".yml"}


def test_only_file_types_the_directory_accepts_from_unverified_publishers(built):
    """The directory refused v0.3.1: an organization that is not Verified may ship only Markdown, text, JSON,
    YAML and images (the icon). No scripts, nothing that starts with #!."""
    for p in _files(built):
        rel = p.relative_to(built).as_posix()
        if rel in {".claude-plugin/icon.png", "LICENSE"}:
            continue
        assert p.suffix.lower() in ALLOWED, rel
        assert not p.read_bytes().startswith(b"#!"), rel


def test_each_skill_does_script_steps_itself_without_telling_the_student(built):
    for skill in built.glob("skills/*/SKILL.md"):
        body = skill.read_text(encoding="utf-8")
        assert "## Directory edition" in body, skill.parent.name
        note = body.split("## Directory edition")[1].split("\n## ")[0]
        assert "do that step yourself" in note and "never mention" in note.lower()
        assert "github" not in note.lower()
        fm = body.split("---", 2)[1]
        assert "Directory edition" not in fm, "frontmatter stays untouched"
