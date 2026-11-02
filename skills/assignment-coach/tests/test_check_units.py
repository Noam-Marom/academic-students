"""check_units.py — final-answer lines must carry units; with pint, the unit must have the expected dimension."""
import json
import pathlib
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/check_units.py"


@pytest.fixture(scope="module")
def cu(load_module):
    return load_module(SCRIPT, "coach_check_units")


def test_hebrew_unit_word_after_number_is_not_bare(cu):
    assert cu.check_units("**תשובה:** 5 מטר") == []


def test_hebrew_gershayim_units(cu):
    assert cu.check_units('**תשובה סופית:** המהירות היא 3 ק"מ/שעה') == []
    assert cu.check_units("**תשובה:** 12 ק״ג") == []  # U+05F4 gershayim


def test_bare_number_on_answer_line_is_flagged(cu):
    out = cu.check_units("**Answer:** 42")
    assert out == [{"line": 1, "issue": "bare number", "value": "42"}]


def test_bare_number_inside_derivation_is_not_flagged(cu):
    text = "\n".join([
        "We start from F = ma.",
        "m = 2 and a = 21, so F = 42",
        "**Answer:** F = 42 N",
    ])
    assert cu.check_units(text) == []


def test_si_unit_with_slash_and_exponent(cu):
    assert cu.check_units("Final answer: a = 9.81 m/s^2") == []
    assert cu.check_units("∴ E = 3.2 kJ") == []
    assert cu.check_units("=> 50 %") == []


def test_number_attached_to_unit(cu):
    assert cu.check_units("**Answer:** 5m") == []
    assert cu.check_units("**Answer:** T = 300K, p = 2bar") == []


def test_unit_may_be_two_tokens_away(cu):
    assert cu.check_units("**Answer:** 42 ± 1 m") == []


def test_scientific_notation_is_one_number(cu):
    assert cu.check_units("**Answer:** c = 3 × 10^8 m/s") == []


def test_plain_word_after_number_does_not_count_as_unit(cu):
    out = cu.check_units("**Answer:** 7 people")
    assert out and out[0]["issue"] == "bare number" and out[0]["value"] == "7"


def test_line_numbers_are_reported(cu):
    text = "intro\n\n**תשובה:** 8\n"
    assert cu.check_units(text) == [{"line": 3, "issue": "bare number", "value": "8"}]


# --- dimension checks need pint -------------------------------------------------------------------------

def test_same_dimension_passes(cu):
    pytest.importorskip("pint")
    assert cu.check_units("Final answer: v = 3 m/s", expect="km/h") == []


def test_different_dimension_is_flagged(cu):
    pytest.importorskip("pint")
    out = cu.check_units("Final answer: v = 3 m/s", expect="kg")
    assert out == [{"line": 1, "issue": "dimension mismatch", "got": "m/s", "expected": "kg"}]


def test_hebrew_unit_word_maps_to_dimension(cu):
    pytest.importorskip("pint")
    assert cu.check_units('**תשובה:** 90 קמ"ש', expect="m/s") == []
    out = cu.check_units("**תשובה:** 5 מטר", expect="s")
    assert out and out[0]["issue"] == "dimension mismatch"


def test_dimensionless_expectation_accepts_bare_number(cu):
    pytest.importorskip("pint")
    assert cu.check_units("**Answer:** 0.5", expect="ratio") == []


def test_without_pint_dimension_check_is_skipped_gracefully(monkeypatch, load_module):
    monkeypatch.setitem(sys.modules, "pint", None)
    mod = load_module(SCRIPT, "coach_check_units_nopint")
    assert mod.HAVE_PINT is False
    assert mod.check_units("Final answer: v = 3 m/s", expect="kg") == []  # cannot judge → no finding
    assert mod.check_units("**Answer:** 42", expect="kg") == [{"line": 1, "issue": "bare number", "value": "42"}]


# --- CLI -----------------------------------------------------------------------------------------------

def test_cli_json_and_exit_codes(tmp_path):
    f = tmp_path / "sol.md"
    f.write_text("**Answer:** 42\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--json"], capture_output=True, text=True)
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False and out["findings"][0]["issue"] == "bare number"

    f.write_text("**Answer:** 42 m\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--json"], capture_output=True, text=True)
    assert r.returncode == 0
    assert json.loads(r.stdout)["findings"] == []


def test_cli_missing_file_is_usage_error(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(tmp_path / "none.md")], capture_output=True, text=True)
    assert r.returncode == 2
