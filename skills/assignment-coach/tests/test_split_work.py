"""split_work.py: divide an assignment map among N group members, serially or in parallel, respecting dependencies."""
import json
import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def sw(load_module, skill_dir):
    return load_module(skill_dir / "scripts" / "split_work.py", "coach_split_work")


def q(id_, hours, deps=()):
    return {"id": id_, "type": "other", "text": id_, "estimate_hours": hours, "depends_on": list(deps)}


def amap(*questions):
    return {"title": "HW", "questions": list(questions)}


def _member_of(plan, part):
    return next(s["member"] for s in plan["schedule"] if s["part"] == part)


def _slot(plan, part):
    return next(s for s in plan["schedule"] if s["part"] == part)


def test_independent_parts_are_balanced_in_parallel(sw):
    plan = sw.split(amap(q("1", 4), q("2", 4), q("3", 2), q("4", 2)), people=2, mode="parallel")
    loads = sorted(m["hours"] for m in plan["members"])
    assert loads == [6, 6]
    assert plan["makespan_hours"] == 6 + plan["integration"]["hours"]


def test_dependencies_are_respected(sw):
    plan = sw.split(amap(q("a", 3), q("b", 2, ["a"]), q("c", 2)), people=2, mode="parallel")
    assert _slot(plan, "b")["start"] >= _slot(plan, "a")["end"]


def test_critical_path_is_the_longest_dependency_chain(sw):
    plan = sw.split(amap(q("a", 3), q("b", 2, ["a"]), q("c", 1), q("d", 4, ["b"])), people=3, mode="parallel")
    assert plan["critical_path"] == ["a", "b", "d"]
    assert plan["critical_path_hours"] == 9


def test_chain_auto_selects_serial_relay(sw):
    plan = sw.split(amap(q("1", 2), q("2", 2, ["1"]), q("3", 2, ["2"]), q("4", 2, ["3"])), people=2, mode="auto")
    assert plan["mode"] == "serial"
    # contiguous stages: member 1 takes the first half of the chain, member 2 the second
    assert [_member_of(plan, p) for p in ["1", "2", "3", "4"]] == [1, 1, 2, 2]


def test_branching_work_auto_selects_parallel(sw):
    plan = sw.split(amap(q("1", 2), q("2", 2), q("3", 2), q("4", 2, ["1", "2"])), people=2, mode="auto")
    assert plan["mode"] == "parallel"


def test_cycle_is_rejected(sw):
    with pytest.raises(ValueError, match="cycle"):
        sw.split(amap(q("a", 1, ["b"]), q("b", 1, ["a"])), people=2, mode="parallel")


def test_more_people_than_parts_warns(sw):
    plan = sw.split(amap(q("1", 2), q("2", 2)), people=4, mode="parallel")
    assert any("more people than parts" in w for w in plan["warnings"])


def test_missing_estimates_fall_back_to_weights(sw):
    m = {"title": "HW", "questions": [
        {"id": "1", "type": "proof", "text": "", "weight": 30},
        {"id": "2", "type": "code", "text": "", "weight": 70}]}
    plan = sw.split(m, people=2, mode="parallel", total_hours=10)
    hours = {s["part"]: s["end"] - s["start"] for s in plan["schedule"]}
    assert hours == {"1": 3.0, "2": 7.0}


def test_integration_review_is_owned_by_the_least_loaded_member(sw):
    plan = sw.split(amap(q("1", 5), q("2", 1)), people=2, mode="parallel")
    assert plan["integration"]["member"] == _member_of(plan, "2")
    assert plan["integration"]["hours"] >= 1


def test_cli_json(tmp_path, skill_dir):
    f = tmp_path / "map.json"
    f.write_text(json.dumps(amap(q("1", 2), q("2", 2))), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(skill_dir / "scripts" / "split_work.py"), str(f), "--people", "2", "--json"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["people"] == 2


def test_cli_cycle_exits_2(tmp_path, skill_dir):
    f = tmp_path / "map.json"
    f.write_text(json.dumps(amap(q("a", 1, ["b"]), q("b", 1, ["a"]))), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(skill_dir / "scripts" / "split_work.py"), str(f), "--people", "2"],
                          capture_output=True, text=True)
    assert proc.returncode == 2 and "cycle" in proc.stderr


def test_interface_only_dependency_starts_after_a_joint_interface_agreement(sw):
    hard = sw.split(amap(q("2", 4), q("3", 3, ["2"])), people=2, mode="parallel")
    m = amap(q("2", 4), q("3", 3))
    m["questions"][1]["depends_on_interface"] = ["2"]
    soft = sw.split(m, people=2, mode="parallel")
    agree = _slot(soft, "interface")
    assert agree["member"] == "all" and agree["start"] == 0 and agree["end"] == 0.5
    assert _slot(soft, "3")["start"] == 0.5 and _member_of(soft, "3") != _member_of(soft, "2")
    assert soft["makespan_hours"] < hard["makespan_hours"]
    assert soft["critical_path"] == ["2"]


def test_interface_dependency_on_unknown_part_is_rejected(sw):
    m = amap(q("1", 1))
    m["questions"][0]["depends_on_interface"] = ["9"]
    with pytest.raises(ValueError, match="unknown"):
        sw.split(m, people=2)
