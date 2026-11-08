"""tools/sync_shared.py copies shared/ sources into the skills that declare them, and --check detects drift."""
import json
import pathlib

from tools.sync_shared import sync


def make_root(tmp_path: pathlib.Path, sync_json: dict) -> pathlib.Path:
    (tmp_path / "shared" / "disciplines").mkdir(parents=True)
    (tmp_path / "shared" / "disciplines" / "a.md").write_text("# A\nbody\n", encoding="utf-8")
    (tmp_path / "shared" / "COURSE.template.md").write_text("---\ncourse: x\n---\n", encoding="utf-8")
    (tmp_path / "shared" / "sync.json").write_text(json.dumps(sync_json), encoding="utf-8")
    (tmp_path / "skills" / "x").mkdir(parents=True)
    return tmp_path


def test_sync_copies_disciplines_byte_for_byte(tmp_path):
    root = make_root(tmp_path, {"disciplines": ["x"]})
    written = sync(root, check=False)
    target = root / "skills/x/references/disciplines/a.md"
    assert target.read_bytes() == (root / "shared/disciplines/a.md").read_bytes()
    assert "skills/x/references/disciplines/a.md" in written


def test_check_reports_drift_without_writing(tmp_path):
    root = make_root(tmp_path, {"disciplines": ["x"]})
    sync(root, check=False)
    target = root / "skills/x/references/disciplines/a.md"
    target.write_text("edited copy\n", encoding="utf-8")
    assert sync(root, check=True) == ["skills/x/references/disciplines/a.md"]
    assert target.read_text(encoding="utf-8") == "edited copy\n"


def test_stale_copy_is_removed_and_reported(tmp_path):
    root = make_root(tmp_path, {"disciplines": ["x"]})
    stale_dir = root / "skills/x/references/disciplines"
    stale_dir.mkdir(parents=True)
    (stale_dir / "b.md").write_text("old\n", encoding="utf-8")
    assert "skills/x/references/disciplines/b.md" in sync(root, check=True)
    sync(root, check=False)
    assert not (stale_dir / "b.md").exists()


def test_course_template_target(tmp_path):
    root = make_root(tmp_path, {"course_template": ["x"]})
    sync(root, check=False)
    assert (root / "skills/x/assets/COURSE.template.md").exists()
    assert sync(root, check=True) == []


def test_in_sync_tree_reports_nothing(tmp_path):
    root = make_root(tmp_path, {"disciplines": ["x"]})
    sync(root, check=False)
    assert sync(root, check=True) == []
