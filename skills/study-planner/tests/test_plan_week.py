"""plan_week.py: bin deadline work into available hours; overflow is reported, never dropped, never over-booked."""
import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "plan_week.py"
WEEK = "2026-11-08"  # Sunday


def d(id_, due, kind="assignment", est=None, course="OS"):
    return {"id": id_, "course": course, "title": id_, "due": due, "tz": "Asia/Jerusalem", "kind": kind,
            "source": "t", "weight": None, "estimate_hours": est}


def minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def assert_within_and_disjoint(blocks, availability):
    by_date = {}
    for b in blocks:
        s, e = minutes(b["start"]), minutes(b["end"])
        assert e - s >= 60, f"block shorter than 1h: {b}"
        assert any(minutes(a) <= s and e <= minutes(z) for a, z in availability.get(b["date"], [])), f"outside slots: {b}"
        by_date.setdefault(b["date"], []).append((s, e))
    for spans in by_date.values():
        spans.sort()
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            assert e1 <= s2, f"overlap {spans}"


def test_overflow_reports_unplaced_hours_of_later_deadline(plan_week):
    availability = {"2026-11-08": [["18:00", "21:00"]], "2026-11-09": [["18:00", "21:00"]]}  # 6 hours
    deadlines = [d("late", "2026-11-13T23:59", est=6), d("early", "2026-11-12T23:59", est=4)]
    plan = plan_week.plan_week(deadlines, availability, WEEK)
    placed = {}
    for b in plan["blocks"]:
        placed[b["deadline_id"]] = placed.get(b["deadline_id"], 0) + (minutes(b["end"]) - minutes(b["start"])) / 60
    assert placed == {"early": 4, "late": 2}
    assert plan["overflow"] == [{"deadline_id": "late", "hours_unplaced": 4}]
    assert_within_and_disjoint(plan["blocks"], availability)
    assert sum(placed.values()) <= 6


def test_defaults_three_hours_assignment_eight_hours_exam(plan_week):
    availability = {f"2026-11-{day:02d}": [["08:00", "20:00"]] for day in range(8, 15)}
    plan = plan_week.plan_week([d("hw", "2026-11-14T12:00"), d("ex", "2026-11-14T12:00", kind="exam")], availability, WEEK)
    hours = {}
    for b in plan["blocks"]:
        hours[b["deadline_id"]] = hours.get(b["deadline_id"], 0) + (minutes(b["end"]) - minutes(b["start"])) / 60
    assert hours == {"hw": 3, "ex": 8}
    assert plan["overflow"] == []
    assert_within_and_disjoint(plan["blocks"], availability)


def test_no_work_after_the_due_time(plan_week):
    availability = {"2026-11-08": [["10:00", "12:00"]], "2026-11-09": [["10:00", "14:00"]]}
    plan = plan_week.plan_week([d("hw", "2026-11-09T11:00", est=4)], availability, WEEK)
    for b in plan["blocks"]:
        assert (b["date"], b["end"]) <= ("2026-11-09", "11:00")
    assert plan["overflow"] == [{"deadline_id": "hw", "hours_unplaced": 1}]


def test_review_dates_become_one_hour_blocks(plan_week):
    availability = {"2026-11-10": [["17:00", "20:00"]], "2026-11-11": [["17:00", "18:30"]]}
    review = [{"course": "Prob", "topic": "Poisson", "dates": ["2026-11-10", "2026-11-11", "2026-12-01"]}]
    plan = plan_week.plan_week([], availability, WEEK, review_dates=review)
    rv = [b for b in plan["blocks"] if b["deadline_id"].startswith("review:")]
    assert [(b["date"], minutes(b["end"]) - minutes(b["start"])) for b in rv] == [("2026-11-10", 60), ("2026-11-11", 60)]
    assert all("Poisson" in b["task"] for b in rv)
    assert plan["overflow"] == []  # 2026-12-01 is outside this week, not overflow


def test_review_with_no_room_is_overflow(plan_week):
    plan = plan_week.plan_week([], {"2026-11-10": [["17:00", "17:30"]]}, WEEK,
                               review_dates=[{"course": "Prob", "topic": "CLT", "dates": ["2026-11-10"]}])
    assert plan["blocks"] == []
    assert plan["overflow"] == [{"deadline_id": "review:Prob:CLT:2026-11-10", "hours_unplaced": 1}]


def test_past_deadlines_ignored_and_never_exceeds_availability(plan_week):
    availability = {"2026-11-08": [["09:00", "10:00"], ["12:00", "13:30"]]}
    plan = plan_week.plan_week([d("old", "2026-11-01T23:59", est=5), d("hw", "2026-11-08T23:59", est=5)], availability, WEEK)
    assert all(b["deadline_id"] == "hw" for b in plan["blocks"])
    assert_within_and_disjoint(plan["blocks"], availability)
    assert plan["overflow"][0]["deadline_id"] == "hw" and plan["overflow"][0]["hours_unplaced"] > 0


def test_cli_round_trip(tmp_path):
    (tmp_path / "deadlines.json").write_text(json.dumps([d("hw", "2026-11-12T23:59", est=2)]), encoding="utf-8")
    (tmp_path / "availability.json").write_text(json.dumps({"2026-11-09": [["18:00", "21:00"]]}), encoding="utf-8")
    out = tmp_path / "plan.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "deadlines.json", "availability.json", "--week-start", WEEK,
                        "--out", str(out), "--json"], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    plan = json.loads(out.read_text(encoding="utf-8"))
    assert plan["blocks"][0]["deadline_id"] == "hw" and plan["overflow"] == []
    assert json.loads(r.stdout)["overflow_hours"] == 0


def test_cli_overflow_exits_1(tmp_path):
    (tmp_path / "deadlines.json").write_text(json.dumps([d("hw", "2026-11-12T23:59", est=9)]), encoding="utf-8")
    (tmp_path / "availability.json").write_text(json.dumps({"2026-11-09": [["18:00", "21:00"]]}), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), "deadlines.json", "availability.json", "--week-start", WEEK],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 1
    assert "hw" in r.stdout
