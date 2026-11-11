"""tools/package.py builds the release zips: one plugin zip and one zip per skill, deterministic and clean."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "package.py"
SKILLS = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), "--json"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return out, json.loads(proc.stdout)


def _names(z):
    with zipfile.ZipFile(z) as f:
        return f.namelist()


def test_plugin_zip_has_manifest_at_root_and_every_skill(built):
    out, report = built
    version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())["version"]
    z = out / f"academic-students-{version}.zip"
    assert report["plugin"] == str(z)
    names = _names(z)
    assert ".claude-plugin/plugin.json" in names and ".mcp.json" in names
    for s in SKILLS:
        assert f"skills/{s}/SKILL.md" in names, s
    assert any(n.startswith("servers/moodle-mcp/src/moodle_mcp/") for n in names)


@pytest.mark.parametrize("excluded", ["tests/", "/evals/", "__pycache__", ".git/", "docs/", ".github/", "tools/", "bin/"])
def test_plugin_zip_leaves_out_development_files(built, excluded):
    out, report = built
    bad = [n for n in _names(report["plugin"]) if excluded in "/" + n]
    assert bad == [], bad[:3]


def test_one_zip_per_skill_with_skill_md_under_its_folder(built):
    out, report = built
    assert sorted(report["skills"]) == SKILLS
    for s in SKILLS:
        names = _names(out / "skills" / f"{s}.zip")
        assert f"{s}/SKILL.md" in names
        assert all(n.startswith(f"{s}/") for n in names)
        assert not any("/tests/" in n or "/evals/" in n or "__pycache__" in n for n in names)


def test_build_is_deterministic(built, tmp_path):
    out, report = built
    proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(tmp_path), "--json"], capture_output=True, text=True)
    again = json.loads(proc.stdout)
    digest = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    assert digest(again["plugin"]) == digest(report["plugin"])
    assert digest(tmp_path / "skills" / "assignment-coach.zip") == digest(out / "skills" / "assignment-coach.zip")


def test_refuses_a_bin_directory(tmp_path):
    spec = importlib.util.spec_from_file_location("tools_package", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fake = tmp_path / "plugin"
    (fake / ".claude-plugin").mkdir(parents=True)
    (fake / ".claude-plugin/plugin.json").write_text('{"name": "x", "version": "0.0.1"}')
    (fake / "bin").mkdir()
    with pytest.raises(ValueError, match="bin/"):
        mod.build(fake, tmp_path / "out")


def test_release_workflow_builds_and_uploads_on_version_tags():
    import yaml
    wf = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert on["push"]["tags"] == ["v*"]
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job.get("steps", []))
    assert "tools/package.py" in steps and "pytest" in steps and "gh release" in steps
    assert "plugin.json" in steps, "the tag must be checked against the manifest version"


def test_release_workflow_attaches_zips_to_a_release_made_in_the_ui():
    """Publishing a release on github.com creates the tag first: the release already exists, so the
    workflow must upload into it (not fail on `gh release create`) and be re-runnable by hand."""
    import yaml
    wf = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert "workflow_dispatch" in on, "a failed or skipped release must be re-runnable for a given tag"
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job.get("steps", []))
    assert "gh release view" in steps and "gh release upload" in steps and "--clobber" in steps


def test_install_guide_covers_every_surface():
    text = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for key in ["claude plugin marketplace add Noam-Marom/academic-students",
                "claude plugin install academic-students@noam-academic",
                "Add marketplace", "releases/latest", "skills/", "moodle-mcp login"]:
        assert key in text, key


def test_a_version_bump_on_main_publishes_the_release_and_the_directory_build():
    """Owner's rule (2026-11-11): every plugin version gets a GitHub Release, automatically. A push to main
    that changes plugin.json's version creates tag v<version>, the release with its zips, and refreshes the
    directory branch; a version that already has a release is skipped."""
    import yaml
    wf = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert on["push"]["branches"] == ["main"]
    assert ".claude-plugin/plugin.json" in on["push"]["paths"]
    steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["release"]["steps"])
    assert "--target" in steps and "already released" in steps
    assert wf["jobs"]["directory"]["uses"] == "./.github/workflows/directory.yml"
    assert wf["jobs"]["directory"]["needs"] == "release"
    d = yaml.safe_load((ROOT / ".github/workflows/directory.yml").read_text())
    assert "workflow_call" in d.get("on", d.get(True))


def test_a_new_plugin_version_on_main_releases_itself_and_rebuilds_the_directory():
    """Owner's rule (2026-11-11): every version bump in plugin.json gets its GitHub Release automatically,
    and the directory branch is rebuilt from it; an existing release is never recreated."""
    import yaml
    wf = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text())
    on = wf.get("on", wf.get(True))
    assert on["push"]["branches"] == ["main"] and on["push"]["paths"] == [".claude-plugin/plugin.json"]
    steps = " ".join(str(s.get("run", "")) for job in wf["jobs"].values() for s in job.get("steps", []))
    assert "already released" in steps, "a push that does not change the version must not re-release"
    calls = [j for j in wf["jobs"].values() if j.get("uses") == "./.github/workflows/directory.yml"]
    assert calls and "release" in str(calls[0].get("needs"))
    d = yaml.safe_load((ROOT / ".github/workflows/directory.yml").read_text())
    assert "workflow_call" in d.get("on", d.get(True))
