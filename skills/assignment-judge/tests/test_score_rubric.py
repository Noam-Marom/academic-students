"""score_rubric.py: the arithmetic of a grade estimate — weighted total, two blind passes, penalties, scale."""
import json
import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def sr(load_module, skill_dir):
    return load_module(skill_dir / "scripts" / "score_rubric.py", "judge_score_rubric")


def rubric(*criteria, **kw):
    return {"criteria": [{"id": i, "name": i, "max": m, "passes": list(p)} for i, m, p in criteria], **kw}


def test_weighted_total_on_the_default_100_scale(sr):
    r = sr.score(rubric(("argument", 50, [35]), ("justification", 30, [30]), ("presentation", 20, [15])))
    assert r["raw"] == 80 and r["max"] == 100
    assert r["final"] == 80


def test_points_not_summing_to_100_are_normalised_to_the_scale(sr):
    r = sr.score(rubric(("q1", 10, [8]), ("q2", 10, [6]), scale={"max": 20}))
    assert r["final"] == 14.0


def test_two_passes_give_mean_and_range(sr):
    r = sr.score(rubric(("q1", 30, [20, 24]), ("q2", 70, [60, 60])))
    [c1, _] = r["criteria"]
    assert c1["score"] == 22 and (c1["low"], c1["high"]) == (20, 24)
    assert r["final"] == 82 and r["range"] == [80, 84]


def test_large_disagreement_between_passes_is_flagged(sr):
    r = sr.score(rubric(("q1", 30, [10, 20]), ("q2", 70, [60, 62])))
    assert r["disagreements"] == ["q1"]
    assert r["criteria"][1]["disagreement"] is False


@pytest.mark.parametrize("penalty,final", [
    ({"reason": "late 1 day", "points": 5}, 75),
    ({"reason": "late", "percent": 10}, 72),
    ({"reason": "over the page limit", "cap": 60}, 60),
    ({"reason": "plagiarised figure", "points": 500}, 0),
])
def test_penalties(sr, penalty, final):
    r = sr.score(rubric(("all", 100, [80]), penalties=[penalty]))
    assert r["final"] == final


def test_pass_mark(sr):
    assert sr.score(rubric(("all", 100, [57]), scale={"max": 100, "pass": 56}))["passed"] is True
    assert sr.score(rubric(("all", 100, [50]), scale={"max": 100, "pass": 56}))["passed"] is False
    assert "passed" not in sr.score(rubric(("all", 100, [50])))


@pytest.mark.parametrize("bad,msg", [
    (rubric(("q1", 10, [11])), "exceeds"),
    (rubric(("q1", 10, [-1])), "negative"),
    (rubric(("q1", 10, [5]), ("q1", 10, [5])), "duplicate"),
    ({"criteria": []}, "no criteria"),
    (rubric(("q1", 0, [0])), "max"),
    (rubric(("q1", 10, [])), "pass"),
])
def test_invalid_rubrics_are_rejected(sr, bad, msg):
    with pytest.raises(ValueError, match=msg):
        sr.score(bad)


def _run(skill_dir, tmp_path, data, *args):
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run([sys.executable, str(skill_dir / "scripts" / "score_rubric.py"), str(f), *args],
                          capture_output=True, text=True)


def test_cli_exit_codes(skill_dir, tmp_path):
    ok = _run(skill_dir, tmp_path, rubric(("q1", 10, [8, 8])), "--json")
    assert ok.returncode == 0 and json.loads(ok.stdout)["final"] == 80
    assert _run(skill_dir, tmp_path, rubric(("q1", 10, [2, 9]))).returncode == 1  # reconcile first
    bad = _run(skill_dir, tmp_path, rubric(("q1", 10, [11])))
    assert bad.returncode == 2 and "exceeds" in bad.stderr
