"""export_ics.py: plan or deadlines → RFC 5545 calendar in UTC, CRLF, folded at 75 octets, DST-correct."""
import json
import pathlib
import re
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "export_ics.py"


def dl(id_, due, title="HW", course="OS"):
    return {"id": id_, "course": course, "title": title, "due": due, "tz": "Asia/Jerusalem", "kind": "assignment",
            "source": "moodle.ics", "weight": None, "estimate_hours": None}


def unfold(text):
    return re.sub(r"\r\n[ \t]", "", text)


def test_dst_pin_israel_summer_and_winter_time(export_ics):
    # Israel leaves summer time (UTC+3) on Sunday 2026-10-25; afterwards it is UTC+2.
    ics = export_ics.to_ics([dl("a", "2026-10-23T23:59"), dl("b", "2026-10-26T23:59")])
    starts = re.findall(r"^DTSTART:(\S+)\r$", unfold(ics), re.M)
    assert starts == ["20261023T205900Z", "20261026T215900Z"]


def test_crlf_line_endings_only(export_ics):
    ics = export_ics.to_ics([dl("a", "2026-11-20T23:59")])
    assert ics.endswith("\r\n")
    assert "\n" not in ics.replace("\r\n", "")


def test_header_and_nesting(export_ics):
    ics = unfold(export_ics.to_ics([dl("a", "2026-11-20T23:59"), dl("b", "2026-11-21T10:00")], calendar_name="סמסטר א"))
    lines = ics.split("\r\n")[:-1]
    assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR"
    assert "VERSION:2.0" in lines and "PRODID:-//academic-students//EN" in lines
    assert "X-WR-CALNAME:סמסטר א" in lines
    depth = 0
    for ln in lines:
        if ln.startswith("BEGIN:"):
            depth += 1
        elif ln.startswith("END:"):
            depth -= 1
        assert depth >= 0
    assert depth == 0
    assert lines.count("BEGIN:VEVENT") == 2 == lines.count("END:VEVENT")
    for block in re.findall(r"BEGIN:VEVENT\r\n(.*?)END:VEVENT", ics, re.S):
        for key in ("UID:", "DTSTAMP:", "DTSTART:", "DTEND:", "SUMMARY:", "DESCRIPTION:"):
            assert key in block
        assert re.search(r"^DTSTAMP:\d{8}T\d{6}Z\r$", block, re.M)


def test_long_hebrew_summary_folded_at_75_octets(export_ics):
    title = ("הגשת עבודה סמינריונית בנושא השפעת הרשתות החברתיות על השיח הציבורי בישראל "
             "כולל נספחים וטבלאות סיכום מלאות לכל הפרקים והמקורות")
    assert len(title) >= 120
    ics = export_ics.to_ics([dl("a", "2026-11-20T23:59", title=title)])
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75, line
    ics.encode("utf-8").decode("utf-8")  # folding never splits a multi-byte character
    assert title in unfold(ics)


def test_text_escaping(export_ics):
    ics = unfold(export_ics.to_ics([dl("a", "2026-11-20T23:59", title="HW1; part a, b\\c")]))
    assert "SUMMARY:HW1\; part a\\, b\\\\c (OS)" in ics


def test_plan_blocks_become_events(export_ics):
    plan = {"blocks": [{"date": "2026-10-25", "start": "18:00", "end": "20:00", "task": "OS: HW2", "deadline_id": "x"}],
            "overflow": []}
    ics = unfold(export_ics.to_ics(plan))
    assert "DTSTART:20261025T160000Z" in ics and "DTEND:20261025T180000Z" in ics
    assert "SUMMARY:OS: HW2" in ics


def test_uids_are_stable_and_unique(export_ics):
    items = [dl("a", "2026-11-20T23:59"), dl("b", "2026-11-21T23:59")]
    one, two = export_ics.to_ics(items), export_ics.to_ics(items)
    uids = re.findall(r"^UID:(.+)\r$", unfold(one), re.M)
    assert len(set(uids)) == 2 and uids == re.findall(r"^UID:(.+)\r$", unfold(two), re.M)


def test_cli(tmp_path):
    src = tmp_path / "deadlines.json"
    src.write_text(json.dumps([dl("a", "2026-10-23T23:59")]), encoding="utf-8")
    out = tmp_path / "plan.ics"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(src), "--out", str(out), "--json"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["events"] == 1
    assert b"\r\nDTSTART:20261023T205900Z\r\n" in out.read_bytes()
    bad = subprocess.run([sys.executable, "-I", str(SCRIPT), str(tmp_path / "missing.json")],
                         capture_output=True, text=True, cwd=tmp_path)
    assert bad.returncode == 2
