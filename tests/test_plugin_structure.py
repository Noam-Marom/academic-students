"""Repo-level checks for the plugin manifest and marketplace."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_plugin_manifest_fields():
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert m["name"] == "academic-students"
    assert m["version"] == "0.1.0"
    assert m["license"] == "MIT"
    assert m["author"]["name"]
    assert 40 <= len(m["description"]) <= 1024


def test_marketplace_points_at_root():
    m = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert m["name"] == "noam-academic"
    assert m["owner"]["name"]
    [p] = m["plugins"]
    assert p["name"] == "academic-students"
    assert p["source"] == "./"
    assert p["description"]


def test_no_bin_dir():
    # claude.ai refuses to install a plugin that ships a bin/ directory
    assert not (ROOT / "bin").exists()


def test_license_is_mit():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text and "Noam Marom" in text


def test_test_module_basenames_are_unique():
    # pytest's default import mode imports test files by basename; two test_cli.py files break collection
    import collections
    names = collections.Counter(p.name for p in ROOT.rglob("test_*.py")
                                if ".venv" not in p.parts and ".git" not in p.parts)
    assert [n for n, c in names.items() if c > 1] == []
