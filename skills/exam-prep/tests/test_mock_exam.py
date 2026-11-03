"""mock_exam.py: sample a mock exam from the bank by topic weights, deterministically."""
import json
import pathlib
import subprocess
import sys
from collections import Counter

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "mock_exam.py"


def make_bank(counts: dict[str, int], points: int = 10) -> dict:
    questions = []
    for topic, n in counts.items():
        for i in range(n):
            questions.append({"id": f"{topic}{i}", "text": f"{topic} question {i}", "topic": topic, "type": None,
                              "difficulty": None, "points": points, "year": 2020 + i, "source": "t.pdf", "solution": None})
    return {"questions": questions}


def topics(sample):
    return Counter(q["topic"] for q in sample)


def test_equal_weights_give_equal_shares(mock_exam):
    bank = make_bank({"A": 5, "B": 5})
    sample = mock_exam.build_mock(bank, {"A": 0.5, "B": 0.5}, n=4, seed=1, total_points=None)
    assert len(sample) == 4
    assert topics(sample) == {"A": 2, "B": 2}
    assert len({q["id"] for q in sample}) == 4  # without replacement


def test_same_seed_same_exam_different_seed_may_differ(mock_exam):
    bank = make_bank({"A": 8, "B": 8, "C": 8})
    w = {"A": 0.5, "B": 0.3, "C": 0.2}
    first = mock_exam.build_mock(bank, w, n=6, seed=42, total_points=None)
    second = mock_exam.build_mock(bank, w, n=6, seed=42, total_points=None)
    assert [q["id"] for q in first] == [q["id"] for q in second]
    others = {tuple(q["id"] for q in mock_exam.build_mock(bank, w, n=6, seed=s, total_points=None)) for s in range(10)}
    assert len(others) > 1


def test_largest_remainder_rounding(mock_exam):
    bank = make_bank({"A": 10, "B": 10, "C": 10})
    # 7 * (0.5, 0.3, 0.2) = 3.5, 2.1, 1.4 → floors 3,2,1 = 6; largest remainder is A (.5) → 4,2,1
    sample = mock_exam.build_mock(bank, {"A": 0.5, "B": 0.3, "C": 0.2}, n=7, seed=3, total_points=None)
    assert topics(sample) == {"A": 4, "B": 2, "C": 1}


def test_topic_with_too_few_questions_hands_its_share_to_others(mock_exam):
    bank = make_bank({"A": 1, "B": 10, "C": 10})
    sample = mock_exam.build_mock(bank, {"A": 0.5, "B": 0.25, "C": 0.25}, n=6, seed=7, total_points=None)
    counts = topics(sample)
    assert len(sample) == 6
    assert counts["A"] == 1
    assert counts["B"] + counts["C"] == 5


def test_weights_are_normalised_and_unknown_topics_ignored(mock_exam):
    bank = make_bank({"A": 5, "B": 5})
    sample = mock_exam.build_mock(bank, {"A": 3, "B": 1, "Z": 4}, n=4, seed=1, total_points=None)
    assert topics(sample) == {"A": 3, "B": 1}


def test_n_larger_than_bank_returns_everything_once(mock_exam):
    bank = make_bank({"A": 2, "B": 1})
    sample = mock_exam.build_mock(bank, {"A": 0.5, "B": 0.5}, n=10, seed=1, total_points=None)
    assert len(sample) == 3
    assert len({q["id"] for q in sample}) == 3


def test_total_points_rescales_points_proportionally(mock_exam):
    bank = make_bank({"A": 4, "B": 4}, points=10)
    sample = mock_exam.build_mock(bank, {"A": 0.5, "B": 0.5}, n=4, seed=1, total_points=100)
    assert sum(q["points"] for q in sample) == 100
    assert all(q["points"] == 25 for q in sample)
    # the bank itself is untouched
    assert all(q["points"] == 10 for q in bank["questions"])


def test_cli_writes_mock_json_and_is_seeded(tmp_path):
    bank_path = tmp_path / "bank.json"
    bank_path.write_text(json.dumps(make_bank({"A": 6, "B": 6})), encoding="utf-8")
    out = tmp_path / "mock.json"
    args = [sys.executable, "-I", str(SCRIPT), str(bank_path), "--weights", "A=0.5,B=0.5", "-n", "4",
            "--seed", "5", "--total-points", "100", "--out", str(out), "--json"]
    r = subprocess.run(args, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout)
    mock = json.loads(out.read_text(encoding="utf-8"))
    assert summary["n"] == 4 and summary["total_points"] == 100
    assert len(mock["questions"]) == 4 and mock["seed"] == 5
    out2 = tmp_path / "mock2.json"
    args2 = args[:-2] + [str(out2), "--json"]
    r2 = subprocess.run(args2, capture_output=True, text=True, cwd=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert json.loads(out2.read_text(encoding="utf-8"))["questions"] == mock["questions"]


def test_cli_rejects_bad_weights_with_exit_2(tmp_path):
    bank_path = tmp_path / "bank.json"
    bank_path.write_text(json.dumps(make_bank({"A": 2})), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(bank_path), "--weights", "A=abc", "-n", "2"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
