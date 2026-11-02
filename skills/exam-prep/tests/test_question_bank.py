"""question_bank.py: a JSON bank of exam questions, deduplicated by normalised text."""
import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "question_bank.py"


def q(text, **extra):
    base = {"text": text, "topic": None, "type": None, "difficulty": None, "points": None,
            "year": None, "source": "exam.pdf", "solution": None}
    base.update(extra)
    return base


# --- normalise -------------------------------------------------------------------------------------

def test_normalise_strips_numbering_whitespace_punctuation_and_nikud(question_bank):
    n = question_bank.normalise
    assert n("3. מהו  זמן הריצה של   QuickSort?") == n("(1) מהו זמן הריצה של QuickSort")
    assert n("שָׁלוֹם עוֹלָם") == n("שלום עולם")
    assert n("Prove   that\n\tn log n = O(n^2).") == n("prove that n log n = o(n^2)")
    assert n("") == ""


# --- add / dedupe ----------------------------------------------------------------------------------

def test_same_question_with_different_numbering_is_a_duplicate(question_bank):
    bank = {"questions": []}
    assert question_bank.add(bank, q("1. הוכיחו כי כל עץ בעל n צמתים מכיל n-1 קשתות.", year=2023)) is True
    assert question_bank.add(bank, q("4)  הוכיחו   כי כל עץ בעל n צמתים מכיל n-1 קשתות", year=2024)) is False
    assert len(bank["questions"]) == 1


def test_nikud_only_difference_is_a_duplicate(question_bank):
    bank = {"questions": []}
    assert question_bank.add(bank, q("הַגְדִּירוּ סֶמָפוֹר בִּינָארִי")) is True
    assert question_bank.add(bank, q("הגדירו סמפור בינארי")) is False
    assert len(bank["questions"]) == 1


def test_distinct_questions_are_both_kept_and_get_sha1_ids(question_bank):
    import hashlib
    bank = {"questions": []}
    assert question_bank.add(bank, q("What is a mutex?")) is True
    assert question_bank.add(bank, q("What is a semaphore?")) is True
    ids = [x["id"] for x in bank["questions"]]
    assert len(set(ids)) == 2
    expected = hashlib.sha1(question_bank.normalise("What is a mutex?").encode("utf-8")).hexdigest()[:10]
    assert ids[0] == expected


def test_add_fills_missing_fields_with_none_and_keeps_source(question_bank):
    bank = {"questions": []}
    question_bank.add(bank, {"text": "Define deadlock.", "source": "2022-moed-a.pdf"})
    stored = bank["questions"][0]
    for key in ("topic", "type", "difficulty", "points", "year", "solution"):
        assert key in stored and stored[key] is None
    assert stored["source"] == "2022-moed-a.pdf"


# --- stats -----------------------------------------------------------------------------------------

def test_stats_groups_count_points_and_years_per_topic(question_bank):
    bank = {"questions": []}
    question_bank.add(bank, q("Q1 Explain the dining philosophers problem.", topic="synchronisation", points=20, year=2022))
    question_bank.add(bank, q("Q2 Implement a barrier with semaphores.", topic="synchronisation", points=15, year=2023))
    question_bank.add(bank, q("Q3 Compare paging and segmentation.", topic="memory", points=25, year=2023))
    question_bank.add(bank, q("Q4 What does the scheduler do on a tick?", points=10, year=2023))
    s = question_bank.stats(bank)
    assert s["by_topic"]["synchronisation"] == {"count": 2, "points": 35, "years": [2022, 2023]}
    assert s["by_topic"]["memory"] == {"count": 1, "points": 25, "years": [2023]}
    assert s["untagged"] == 1


# --- CLI -------------------------------------------------------------------------------------------

def run(*args, cwd):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd)


def test_cli_add_stats_and_list_filter(tmp_path):
    bank = tmp_path / "bank.json"
    q1 = tmp_path / "q1.json"
    q2 = tmp_path / "q2.json"
    q3 = tmp_path / "q3.json"
    q1.write_text(json.dumps(q("1. Explain paging.", topic="memory", points=20, year=2022)), encoding="utf-8")
    q2.write_text(json.dumps(q("2) Explain   paging", topic="memory", points=20, year=2023)), encoding="utf-8")
    q3.write_text(json.dumps(q("Define a race condition.", topic="synchronisation", points=10, year=2023)), encoding="utf-8")

    assert run("add", str(bank), str(q1), cwd=tmp_path).returncode == 0
    dup = run("add", str(bank), str(q2), cwd=tmp_path)
    assert dup.returncode == 1  # duplicate is a "finding", not an error
    assert run("add", str(bank), str(q3), cwd=tmp_path).returncode == 0

    data = json.loads(bank.read_text(encoding="utf-8"))
    assert len(data["questions"]) == 2

    stats = run("stats", str(bank), "--json", cwd=tmp_path)
    assert stats.returncode == 0
    parsed = json.loads(stats.stdout)
    assert parsed["by_topic"]["memory"]["count"] == 1
    assert parsed["untagged"] == 0

    listed = run("list", str(bank), "--topic", "memory", "--json", cwd=tmp_path)
    assert listed.returncode == 0
    items = json.loads(listed.stdout)
    assert [i["topic"] for i in items] == ["memory"]


def test_cli_usage_error_exits_2(tmp_path):
    assert run(cwd=tmp_path).returncode == 2
    assert run("stats", str(tmp_path / "missing.json"), cwd=tmp_path).returncode == 2
