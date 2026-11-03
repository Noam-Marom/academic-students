"""Course sync: folder layout, exam detection, manifest diff, and a run that downloads only what changed."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("httpx")

from moodle_mcp import sync  # noqa: E402
from moodle_mcp.errors import AuthError, TransportError  # noqa: E402

from moodle_fixtures import SITE, load_fixture  # noqa: E402


def course() -> dict:
    return load_fixture("courses.json")[0]


def contents() -> list:
    return load_fixture("course_contents.json")


def assignments() -> list:
    return load_fixture("assignments.json")["courses"][0]["assignments"]


def by_path(items: list[dict]) -> dict[str, dict]:
    out = {i["rel_path"]: i for i in items}
    assert len(out) == len(items), "rel_paths must be unique"
    return out


# --- naming helpers ----------------------------------------------------------------------------------

def test_slug_ascii_hebrew_and_fallback():
    assert sync.slug("Week 1 - Processes") == "week-1-processes"
    assert sync.slug("OSTEP - Processes chapter") == "ostep-processes-chapter"
    assert sync.slug("מבחן מועד א 2025 עם פתרון") == "מבחן-מועד-א-2025-עם-פתרון"
    assert sync.slug("   ") == "item" and sync.slug("", fallback="section") == "section"
    assert len(sync.slug("x" * 200)) <= 60


@pytest.mark.parametrize("name, expected", [
    ("מבחן מועד א 2025 עם פתרון", True), ("בוחן 1 פתרון", True), ("מועד ב 2024", True),
    ("Midterm exam 2024", True), ("Final 2023 with solutions", True), ("Quiz 1 - Processes", True),
    ("Practice test", True), ("Lecture 2 slides", False), ("Latest syllabus", False),
    ("Programming contest rules", False), ("exam-2025-moed-a.pdf", True),
])
def test_is_exam_material(name, expected):
    assert sync.is_exam_material(name) is expected


# --- plan --------------------------------------------------------------------------------------------

def test_plan_sync_layout_matches_spec(tmp_path):
    items = by_path(sync.plan_sync(course(), contents(), assignments(), tmp_path))
    # same filename in two sections: both kept, path includes the section
    assert items["materials/01-week-1-processes/slides.pdf"]["module_id"] == 1004
    assert items["materials/02-week-2-threads/slides.pdf"]["module_id"] == 1008
    assert "materials/01-week-1-processes/slides-handout.pdf" in items
    # folder module: own subfolder, filepath kept
    assert items["materials/01-week-1-processes/code-examples/fork_demo.c"]["kind"] == "material"
    assert items["materials/01-week-1-processes/code-examples/extra/Makefile"]["timemodified"] == 1793690100
    # url module -> .url.md carrying the link
    link = items["materials/01-week-1-processes/ostep-processes-chapter.url.md"]
    assert link["kind"] == "url" and link["fileurl"] == "https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf"
    # Hebrew exam name -> exams/past
    exam = items["exams/past/exam-2025-moed-a.pdf"]
    assert exam["kind"] == "exam" and exam["module_id"] == 1009
    assert exam["fileurl"].startswith(f"{SITE}/webservice/pluginfile.php/")
    # assignments: brief.md + attachments
    brief = items["assignments/homework-1-processes/brief.md"]
    assert brief["kind"] == "assignment" and brief["module_id"] == 1007 and brief["fileurl"] is None
    assert "**shell**" in brief["content"] and "2026-11-20T23:55:00+02:00" in brief["content"]
    assert "<" not in brief["content"]
    assert items["assignments/homework-1-processes/hw1-brief.pdf"]["kind"] == "assignment"
    assert "assignments/homework-2-threads/brief.md" in items
    # nothing for the label, the forum, the assign module itself or the quiz module
    assert {i["module_id"] for i in items.values()} == {1004, 1005, 1006, 1008, 1009, 1007, 1012}
    for item in items.values():
        assert set(item) >= {"module_id", "filename", "rel_path", "fileurl", "timemodified", "kind"}
        assert item["kind"] in {"material", "assignment", "exam", "url", "label"}
        assert ".." not in item["rel_path"] and not item["rel_path"].startswith("/")


def test_plan_sync_module_without_contents_does_not_crash(tmp_path):
    secs = contents()
    for m in secs[1]["modules"]:
        m.pop("contents", None)
    items = sync.plan_sync(course(), secs, [], tmp_path)
    assert all(not i["rel_path"].startswith("materials/01-") for i in items)


def test_plan_sync_resolves_rel_path_collisions(tmp_path):
    secs = contents()
    dup = copy.deepcopy(secs[2]["modules"][1])  # the exam resource, again as another module
    dup["id"] = 1099
    secs[2]["modules"].append(dup)
    paths = [i["rel_path"] for i in sync.plan_sync(course(), secs, [], tmp_path)]
    assert len(paths) == len(set(paths))
    assert sum(p.startswith("exams/past/exam-2025-moed-a") for p in paths) == 2


def test_course_root_uses_a_filesystem_safe_shortname(tmp_path):
    root = sync.course_root(tmp_path, {"id": 12, "shortname": "OS 2026/A:*"})
    assert root.parent == tmp_path and "/" not in root.name[0:] and ":" not in root.name and "*" not in root.name
    assert sync.course_root(tmp_path, {"id": 7, "shortname": ""}).name == "course-7"


# --- manifest and diff -------------------------------------------------------------------------------

def test_manifest_roundtrip_and_missing(tmp_path):
    path = tmp_path / ".moodle-sync" / "manifest.json"
    assert sync.Manifest.load(path) is None
    m = sync.Manifest(course_id=12, synced_at="2026-11-02T20:00:00+02:00",
                      items={"1004/slides.pdf": {"rel_path": "materials/01-x/slides.pdf", "sha256": "ab", "timemodified": 1}})
    m.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"course_id", "synced_at", "items"}
    assert sync.Manifest.load(path) == m


def test_item_key_is_module_id_and_filename_with_subpath():
    assert sync.item_key({"module_id": 1004, "filename": "slides.pdf", "filepath": "/"}) == "1004/slides.pdf"
    assert sync.item_key({"module_id": 1005, "filename": "Makefile", "filepath": "/extra/"}) == "1005/extra/Makefile"
    assert sync.item_key({"module_id": 1007, "filename": "brief.md"}) == "1007/brief.md"


def test_diff_new_changed_removed(tmp_path):
    items = sync.plan_sync(course(), contents(), assignments(), tmp_path)
    first = sync.diff(None, items)
    assert sorted(first["new"]) == sorted(sync.item_key(i) for i in items) and first["changed"] == [] and first["removed"] == []
    old = sync.Manifest(course_id=12, synced_at="x", items={
        sync.item_key(i): {"rel_path": i["rel_path"], "sha256": "s", "timemodified": i["timemodified"]} for i in items})
    old.items["9999/gone.pdf"] = {"rel_path": "materials/03-old/gone.pdf", "sha256": "s", "timemodified": 1}
    changed_items = copy.deepcopy(items)
    target = next(i for i in changed_items if i["rel_path"] == "materials/01-week-1-processes/slides.pdf")
    target["timemodified"] += 60
    d = sync.diff(old, changed_items)
    assert d["new"] == [] and d["changed"] == ["1004/slides.pdf"] and d["removed"] == ["9999/gone.pdf"]


# --- run_sync with a stub client ----------------------------------------------------------------------

class StubClient:
    """A MoodleClient stand-in: fixtures for `call`, counted fake downloads."""

    def __init__(self):
        self.site = SITE
        self.token = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
        self.userid = 42
        self.contents = contents()
        self.downloads: list[str] = []
        self.fail_urls: set[str] = set()
        self.auth_dead = False

    def call(self, wsfunction, **params):
        if self.auth_dead:
            raise AuthError("invalidtoken", "re-authenticate")
        return {
            "core_webservice_get_site_info": lambda: load_fixture("site_info.json"),
            "core_enrol_get_users_courses": lambda: load_fixture("courses.json"),
            "core_course_get_contents": lambda: self.contents,
            "mod_assign_get_assignments": lambda: load_fixture("assignments.json"),
            "mod_forum_get_forums_by_courses": lambda: load_fixture("forums.json"),
            "mod_forum_get_forum_discussions": lambda: load_fixture("discussions.json") if params["forumid"] == 7
            else {"discussions": [], "warnings": []},
            "gradereport_user_get_grade_items": lambda: load_fixture("grades.json"),
        }[wsfunction]()

    def download(self, fileurl, dest):
        if fileurl in self.fail_urls:
            raise TransportError("HTTP 500 downloading <token>")
        self.downloads.append(fileurl)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = f"content of {fileurl}".encode()
        dest.write_bytes(data)
        return dest, hashlib.sha256(data).hexdigest()


def test_run_sync_first_run_downloads_everything_and_writes_side_files(tmp_path):
    client = StubClient()
    report = sync.run_sync(client, 12, tmp_path)
    root = tmp_path / "OS-2026A"
    assert report["course"] == "OS-2026A" and report["root"] == str(root)
    assert (root / "materials/01-week-1-processes/slides.pdf").exists()
    assert (root / "materials/02-week-2-threads/slides.pdf").exists()
    assert (root / "materials/01-week-1-processes/code-examples/extra/Makefile").exists()
    assert (root / "exams/past/exam-2025-moed-a.pdf").exists()
    url_md = (root / "materials/01-week-1-processes/ostep-processes-chapter.url.md").read_text(encoding="utf-8")
    assert "https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf" in url_md
    brief = (root / "assignments/homework-1-processes/brief.md").read_text(encoding="utf-8")
    assert "Homework 1 - Processes" in brief and "**shell**" in brief
    assert (root / "assignments/homework-1-processes/hw1-brief.pdf").exists()
    ann = (root / "announcements.md").read_text(encoding="utf-8")
    assert "Homework 1 published" in ann and "Welcome to Operating Systems" in ann and "<p>" not in ann
    assert ann.index("Homework 1 published") < ann.index("Welcome to Operating Systems")  # newest first
    grades = (root / "grades.md").read_text(encoding="utf-8")
    assert "88.00" in grades and "Course total" in grades
    manifest = json.loads((root / ".moodle-sync/manifest.json").read_text(encoding="utf-8"))
    assert manifest["course_id"] == 12 and manifest["synced_at"]
    assert manifest["items"]["1004/slides.pdf"]["rel_path"] == "materials/01-week-1-processes/slides.pdf"
    assert len(manifest["items"]["1004/slides.pdf"]["sha256"]) == 64
    assert manifest["items"]["1007/brief.md"]["sha256"] == hashlib.sha256(brief.encode("utf-8")).hexdigest()
    assert len(client.downloads) == 7  # 6 course files + 1 assignment attachment
    assert report["downloaded"] == 7 and len(report["new"]) == len(manifest["items"])
    assert report["changed"] == [] and report["removed"] == [] and report["errors"] == []
    assert client.token not in json.dumps(report)
    assert report["manifest"] == str(root / ".moodle-sync/manifest.json")


def test_run_sync_second_run_downloads_nothing(tmp_path):
    client = StubClient()
    sync.run_sync(client, 12, tmp_path)
    client.downloads.clear()
    report = sync.run_sync(client, 12, tmp_path)
    assert client.downloads == [] and report["downloaded"] == 0
    assert report["new"] == [] and report["changed"] == [] and report["removed"] == []
    assert report["unchanged"] == 10  # 7 files + 1 .url.md + 2 brief.md


def test_run_sync_changed_file_is_redownloaded_and_removed_is_reported_not_deleted(tmp_path):
    client = StubClient()
    sync.run_sync(client, 12, tmp_path)
    client.downloads.clear()
    slides = client.contents[1]["modules"][0]["contents"][0]
    assert slides["filename"] == "slides.pdf"
    slides["timemodified"] += 3600
    del client.contents[2]["modules"][0]  # week 2 slides disappear from Moodle
    report = sync.run_sync(client, 12, tmp_path)
    assert report["changed"] == ["materials/01-week-1-processes/slides.pdf"]
    assert report["removed"] == ["materials/02-week-2-threads/slides.pdf"]
    assert client.downloads == [slides["fileurl"]]
    assert (tmp_path / "OS-2026A/materials/02-week-2-threads/slides.pdf").exists(), "never deletes originals"
    manifest = json.loads((tmp_path / "OS-2026A/.moodle-sync/manifest.json").read_text(encoding="utf-8"))
    assert "1008/slides.pdf" not in manifest["items"]


def test_run_sync_without_download_indexes_only(tmp_path):
    client = StubClient()
    report = sync.run_sync(client, 12, tmp_path, download=False)
    root = tmp_path / "OS-2026A"
    assert client.downloads == [] and report["downloaded"] == 0 and report["skipped_download"] == 7
    assert (root / "assignments/homework-1-processes/brief.md").exists()
    assert (root / "materials/01-week-1-processes/ostep-processes-chapter.url.md").exists()
    assert not (root / "materials/01-week-1-processes/slides.pdf").exists()
    manifest = json.loads((root / ".moodle-sync/manifest.json").read_text(encoding="utf-8"))
    assert "1004/slides.pdf" not in manifest["items"], "an undownloaded file is not recorded as synced"


def test_run_sync_records_per_file_errors_and_continues(tmp_path):
    client = StubClient()
    bad = client.contents[1]["modules"][0]["contents"][0]["fileurl"]
    client.fail_urls.add(bad)
    report = sync.run_sync(client, 12, tmp_path)
    assert len(report["errors"]) == 1
    assert report["errors"][0]["rel_path"] == "materials/01-week-1-processes/slides.pdf"
    assert "500" in report["errors"][0]["error"] and client.token not in report["errors"][0]["error"]
    assert len(client.downloads) == 6
    manifest = json.loads((tmp_path / "OS-2026A/.moodle-sync/manifest.json").read_text(encoding="utf-8"))
    assert "1004/slides.pdf" not in manifest["items"], "a failed download is retried next time"


def test_run_sync_auth_error_propagates(tmp_path):
    client = StubClient()
    client.auth_dead = True
    with pytest.raises(AuthError):
        sync.run_sync(client, 12, tmp_path)
    assert not (tmp_path / "OS-2026A").exists()


def test_run_sync_unknown_course_id_falls_back_to_generic_folder(tmp_path):
    client = StubClient()
    report = sync.run_sync(client, 99, tmp_path, download=False)
    assert report["course"] == "course-99" and (tmp_path / "course-99" / ".moodle-sync/manifest.json").exists()
