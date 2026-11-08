"""validate_map.py — the assignment map (spec §4.3) is checked against schemas/assignment-map.schema.json.

Both code paths (jsonschema installed / hand-rolled fallback) must pass the same tests, so every test runs
twice: once with the real `jsonschema` import and once with the import blocked.
"""
import json
import pathlib
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/validate_map.py"


@pytest.fixture(params=[True, False], ids=["jsonschema", "fallback"])
def vm(request, monkeypatch, load_module):
    use_jsonschema = request.param
    if use_jsonschema:
        pytest.importorskip("jsonschema")
    else:
        monkeypatch.setitem(sys.modules, "jsonschema", None)  # makes `import jsonschema` raise ImportError
    mod = load_module(SCRIPT, f"coach_validate_map_{'js' if use_jsonschema else 'fallback'}")
    assert mod.HAVE_JSONSCHEMA is use_jsonschema, "the test must exercise the code path it claims to"
    return mod


def minimal_map() -> dict:
    return {
        "title": "HW3",
        "questions": [{"id": "1a", "type": "proof", "text": "Prove that the sum of two even numbers is even."}],
    }


def full_map() -> dict:
    return {
        "course": "Operating Systems",
        "family": "computing",
        "title": "HW3",
        "deliverables": [{"name": "report.pdf", "format": "pdf"}],
        "questions": [
            {"id": "1", "type": "code", "weight": 60, "text": "Implement a thread pool.", "depends_on": []},
            {"id": "2", "type": "analysis", "weight": 40, "text": "Measure the speed-up.", "depends_on": ["1"]},
        ],
        "constraints": ["max 5 pages", "only course material"],
        "show_work": True,
        "due": "2026-11-20",
    }


def test_schema_file_exists_and_is_json():
    schema = json.loads((SKILL_DIR / "schemas/assignment-map.schema.json").read_text(encoding="utf-8"))
    assert schema["type"] == "object"
    assert set(schema["required"]) == {"title", "questions"}


def test_valid_minimal_map(vm):
    assert vm.validate_map(minimal_map()) == []


def test_valid_full_map(vm):
    assert vm.validate_map(full_map()) == []


def test_missing_title_is_one_message(vm):
    m = minimal_map()
    del m["title"]
    errors = vm.validate_map(m)
    assert len(errors) == 1
    assert "title" in errors[0]


def test_empty_questions_rejected(vm):
    m = minimal_map()
    m["questions"] = []
    assert any("questions" in e for e in vm.validate_map(m))


def test_unknown_question_type_names_the_path(vm):
    m = minimal_map()
    m["questions"][0]["type"] = "quiz"
    errors = vm.validate_map(m)
    assert len(errors) == 1
    assert "questions[0].type" in errors[0] and "quiz" in errors[0]


def test_question_missing_required_field(vm):
    m = minimal_map()
    del m["questions"][0]["text"]
    assert any("questions[0]" in e and "text" in e for e in vm.validate_map(m))


def test_depends_on_unknown_id(vm):
    m = minimal_map()
    m["questions"][0]["depends_on"] = ["9z"]
    errors = vm.validate_map(m)
    assert len(errors) == 1
    assert "depends_on" in errors[0] and "9z" in errors[0]


def test_weights_summing_to_zero_is_valid(vm):
    m = full_map()
    for q in m["questions"]:
        q["weight"] = 0
    assert vm.validate_map(m) == []


def test_negative_weight_rejected(vm):
    m = full_map()
    m["questions"][0]["weight"] = -5
    assert any("questions[0].weight" in e for e in vm.validate_map(m))


def test_estimate_hours_must_be_positive_number(vm):
    m = minimal_map()
    m["questions"][0]["estimate_hours"] = 2.5
    assert vm.validate_map(m) == []
    m["questions"][0]["estimate_hours"] = 0
    assert any("questions[0].estimate_hours" in e for e in vm.validate_map(m))
    m["questions"][0]["estimate_hours"] = "two"
    assert any("questions[0].estimate_hours" in e for e in vm.validate_map(m))


def test_due_must_be_iso_date(vm):
    m = minimal_map()
    m["due"] = "20-11-2026"
    errors = vm.validate_map(m)
    assert len(errors) == 1
    assert "due" in errors[0]


def test_due_may_be_null(vm):
    m = minimal_map()
    m["due"] = None
    assert vm.validate_map(m) == []



def test_not_an_object(vm):
    assert vm.validate_map(["not", "a", "map"]) != []


def test_cli_json_output_and_exit_codes(tmp_path):
    bad = tmp_path / "bad.json"
    m = minimal_map()
    del m["title"]
    bad.write_text(json.dumps(m), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(bad), "--json"], capture_output=True, text=True)
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert any("title" in e for e in out["errors"])

    good = tmp_path / "good.json"
    good.write_text(json.dumps(minimal_map()), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(good), "--json"], capture_output=True, text=True)
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"ok": True, "errors": []}


def test_cli_unreadable_file_is_usage_error(tmp_path):
    missing = tmp_path / "nope.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(missing), "--json"], capture_output=True, text=True)
    assert r.returncode == 2
    out = json.loads(r.stdout)
    assert out["ok"] is False and any("nope.json" in e for e in out["errors"])


def test_depends_on_interface_must_name_existing_ids(vm):
    m = minimal_map()
    m["questions"][0]["depends_on_interface"] = ["nope"]
    assert any("depends_on_interface" in e for e in vm.validate_map(m))
