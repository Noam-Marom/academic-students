"""merge_deadlines.py: .ics + deadlines.json + COURSE.md → one deduplicated deadlines.json."""
import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "merge_deadlines.py"
KEYS = {"id", "course", "title", "due", "tz", "kind", "source", "weight", "estimate_hours"}

ICS = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Moodle//EN",
    "BEGIN:VEVENT", "UID:1234@moodle.example", "SUMMARY:HW2 is due", "CATEGORIES:OS",
    "DTSTART:20261120T215900Z", "DTEND:20261120T215900Z", "END:VEVENT",
    "BEGIN:VEVENT", "UID:5678@moodle.example", "SUMMARY:Midterm exam", "CATEGORIES:Probability",
    "DTSTART;TZID=Asia/Jerusalem:20261201T090000", "END:VEVENT",
    "BEGIN:VEVENT", "UID:9@moodle.example", "SUMMARY:Quiz 3 closes", "CATEGORIES:OS",
    "DTSTART;VALUE=DATE:20261125", "END:VEVENT",
    "END:VCALENDAR", ""])


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_ics_events_become_deadlines_in_israel_time(tmp_path, merge_deadlines):
    items = merge_deadlines.merge([write(tmp_path, "moodle.ics", ICS)])
    by_title = {d["title"]: d for d in items}
    hw = by_title["HW2"]
    assert hw["due"] == "2026-11-20T23:59" and hw["tz"] == "Asia/Jerusalem"
    assert hw["course"] == "OS" and hw["kind"] == "assignment" and hw["id"] == "1234@moodle.example"
    assert by_title["Midterm exam"]["due"] == "2026-12-01T09:00" and by_title["Midterm exam"]["kind"] == "exam"
    assert by_title["Quiz 3 closes"]["due"] == "2026-11-25T23:59" and by_title["Quiz 3 closes"]["kind"] == "quiz"
    for d in items:
        assert KEYS <= set(d)


def test_ics_and_json_duplicate_merge_into_one_with_conflict(tmp_path, merge_deadlines):
    ics = write(tmp_path, "moodle.ics", ICS)
    js = write(tmp_path, "deadlines.json", json.dumps([
        {"id": "x1", "course": "os", "title": "HW2", "due": "2026-11-20T18:00", "tz": "Asia/Jerusalem",
         "kind": "assignment", "source": "syllabus", "weight": 5, "estimate_hours": 6}]))
    items = merge_deadlines.merge([ics, js])
    hw = [d for d in items if d["title"].lower() == "hw2"]
    assert len(hw) == 1
    assert hw[0]["due"] == "2026-11-20T18:00"          # the earliest time is kept
    assert hw[0]["conflict"] == ["2026-11-20T23:59"]   # the other time is reported, not dropped
    assert hw[0]["estimate_hours"] == 6 and hw[0]["weight"] == 5  # known fields fill in


def test_same_times_no_conflict_key(tmp_path, merge_deadlines):
    one = {"id": "a", "course": "OS", "title": "HW1", "due": "2026-11-10T23:59", "tz": "Asia/Jerusalem",
           "kind": "assignment", "source": "a", "weight": None, "estimate_hours": None}
    p1 = write(tmp_path, "a.json", json.dumps([one]))
    p2 = write(tmp_path, "b.json", json.dumps([dict(one, id="b", title="  hw1 ")]))
    items = merge_deadlines.merge([p1, p2])
    assert len(items) == 1 and "conflict" not in items[0]


def test_course_md_deadlines_are_merged(tmp_path, merge_deadlines):
    course = write(tmp_path, "COURSE.md", "---\ncourse: \"OS\"\nfamily: computing\n"
                   "deadlines: [{title: \"HW3\", due: \"2026-12-04T23:59\", kind: assignment, estimate_hours: 5}]\n"
                   "---\n\n# notes\n")
    items = merge_deadlines.merge([write(tmp_path, "moodle.ics", ICS), course])
    hw3 = [d for d in items if d["title"] == "HW3"]
    assert len(hw3) == 1
    assert hw3[0]["course"] == "OS" and hw3[0]["estimate_hours"] == 5 and hw3[0]["source"].endswith("COURSE.md")


def test_output_sorted_by_due(tmp_path, merge_deadlines):
    items = merge_deadlines.merge([write(tmp_path, "moodle.ics", ICS)])
    assert [d["due"] for d in items] == sorted(d["due"] for d in items)


def test_cli_writes_json_and_rejects_unknown_type(tmp_path):
    ics = write(tmp_path, "moodle.ics", ICS)
    out = tmp_path / "deadlines.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(ics), "--out", str(out), "--json"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 3
    assert json.loads(r.stdout)["deadlines"] == 3
    bad = write(tmp_path, "x.docx", "nope")
    r2 = subprocess.run([sys.executable, "-I", str(SCRIPT), str(bad)], capture_output=True, text=True, cwd=tmp_path)
    assert r2.returncode == 2
