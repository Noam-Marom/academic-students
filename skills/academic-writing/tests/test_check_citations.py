"""check_citations.py — in-text citations ⇄ reference list consistency, author-year / numeric / footnote,
Hebrew and English names."""
import json
import pathlib
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/check_citations.py"


@pytest.fixture(scope="module")
def cc(load_module):
    return load_module(SCRIPT, "writing_check_citations")


def doc(body: str, heading: str, entries: list[str]) -> str:
    return body + "\n\n## " + heading + "\n\n" + "\n".join(entries) + "\n"


# --- author-year ------------------------------------------------------------------------------------------

def test_matching_author_year_english(cc):
    text = doc("Prior work shows this (Smith, 2020).", "References", ["Smith, J. (2020). Title. *Journal*, 1(2), 3–4."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []
    assert out["style"] == "author-year"


def test_matching_author_year_hebrew(cc):
    text = doc("מחקרים קודמים הראו זאת (כהן, 2020).", "ביבליוגרפיה", ["כהן, א' (2020). שם הספר. הוצאה."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_hebrew_et_al_matches_first_author(cc):
    text = doc("כפי שנמצא (כהן ושות', 2019) וגם (לוי ואח', 2018).", "רשימת מקורות",
               ["כהן, א', לוי, ב' ומזרחי, ג' (2019). מאמר. כתב עת, 3, 1–10.",
                "לוי, ב', כהן, א' ודוד, ד' (2018). מאמר אחר. כתב עת, 2, 5–9."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_english_et_al_matches_first_author(cc):
    text = doc("As shown before (Smith et al., 2019).", "References",
               ["Smith, J., Lee, K., & Wu, X. (2019). Title. *Journal*, 2(1), 10–20."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_year_letter_suffix_matched_exactly(cc):
    text = doc("First (Smith, 2020a) and then (Smith, 2020b).", "References",
               ["Smith, J. (2020a). One. *J*, 1, 1–2.", "Smith, J. (2020b). Two. *J*, 1, 3–4."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_year_letter_suffix_mismatch_is_orphan(cc):
    text = doc("First (Smith, 2020c).", "References", ["Smith, J. (2020a). One. *J*, 1, 1–2."])
    out = cc.check(text)
    assert [c["key"] for c in out["orphans_in_text"]] == ["smith|2020c"]
    assert [c["key"] for c in out["orphans_in_list"]] == ["smith|2020a"]


def test_multiple_citations_in_one_parenthesis_and_narrative_form(cc):
    text = doc("Several studies (Smith, 2020; Lee & Wu, 2019, p. 4) agree, and Katz (2018) disagrees.",
               "References",
               ["Katz, R. (2018). A. *J*, 1, 1.", "Lee, K., & Wu, X. (2019). B. *J*, 1, 2.", "Smith, J. (2020). C. *J*, 1, 3."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []
    assert sorted(c["key"] for c in cc.extract_intext(text)) == ["katz|2018", "lee|2019", "smith|2020"]


def test_list_entry_never_cited_is_orphan_in_list(cc):
    text = doc("Only one is cited (Smith, 2020).", "Bibliography",
               ["Smith, J. (2020). C. *J*, 1, 3.", "Nobody, N. (2011). Unused. *J*, 9, 9."])
    out = cc.check(text)
    assert out["orphans_in_text"] == []
    assert [c["key"] for c in out["orphans_in_list"]] == ["nobody|2011"]
    assert out["orphans_in_list"][0]["raw"].startswith("Nobody")


def test_hebrew_letter_year_does_not_crash_and_matches_itself(cc):
    text = doc('כפי שנטען (כהן, תש"ף), הדבר נכון.', "מקורות", ['כהן, א\' (תש"ף). ספר. הוצאה.'])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_line_numbers_reported(cc):
    text = "line one\n\nsee (Smith, 2020)\n"
    [c] = cc.extract_intext(text)
    assert c["line"] == 3 and c["raw"] == "Smith, 2020" and c["style"] == "author-year"


# --- numeric --------------------------------------------------------------------------------------------

def test_numeric_orphan_in_text(cc):
    text = doc("As shown in [1] and [3].", "References", ["[1] J. Smith, \"A,\" *J*, 2020.", "[2] K. Lee, \"B,\" *J*, 2019."])
    out = cc.check(text)
    assert out["style"] == "numeric"
    assert [c["key"] for c in out["orphans_in_text"]] == ["3"]
    assert [c["key"] for c in out["orphans_in_list"]] == ["2"]


def test_numeric_ranges_and_lists_expand(cc):
    text = doc("See [1, 3] and [4–6].", "References", [f"[{i}] Author {i}, \"T,\" *J*, 2020." for i in range(1, 7)])
    out = cc.check(text)
    assert out["orphans_in_text"] == []
    assert [c["key"] for c in out["orphans_in_list"]] == ["2"]


def test_markdown_links_are_not_numeric_citations(cc):
    text = doc("See [the site](https://example.org) and [1].", "References", ["[1] J. Smith, \"A,\" *J*, 2020."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


def test_numbered_list_entries_without_brackets(cc):
    text = doc("See [1] and [2].", "References", ["1. J. Smith, \"A,\" *J*, 2020.", "2. K. Lee, \"B,\" *J*, 2019."])
    out = cc.check(text)
    assert out["orphans_in_text"] == [] and out["orphans_in_list"] == []


# --- footnotes --------------------------------------------------------------------------------------------

def test_footnote_style(cc):
    text = "A claim.[^1] Another.[^2]\n\n[^1]: Smith, J. (2020). A.\n[^3]: Unused note.\n"
    out = cc.check(text)
    assert out["style"] == "footnote"
    assert [c["key"] for c in out["orphans_in_text"]] == ["2"]
    assert [c["key"] for c in out["orphans_in_list"]] == ["3"]


# --- no citations -----------------------------------------------------------------------------------------

def test_no_citations_no_list(cc):
    out = cc.check("Just prose, nothing cited.\n")
    assert out == {"orphans_in_text": [], "orphans_in_list": [], "style": "none"}


# --- CLI and DOCX -----------------------------------------------------------------------------------------

def test_cli_json_and_exit_codes(tmp_path):
    f = tmp_path / "paper.md"
    f.write_text(doc("See (Smith, 2020) and (Lee, 2019).", "References", ["Smith, J. (2020). C. *J*, 1, 3."]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--json"], capture_output=True, text=True)
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False and [c["key"] for c in out["orphans_in_text"]] == ["lee|2019"]

    f.write_text(doc("See (Smith, 2020).", "References", ["Smith, J. (2020). C. *J*, 1, 3."]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--json"], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is True


def test_docx_input_is_read_with_python_docx(cc, tmp_path, minimal_docx):
    pytest.importorskip("docx")
    f = tmp_path / "paper.docx"
    minimal_docx(f, ["See (Smith, 2020) and (Lee, 2019).", "References", "Smith, J. (2020). C. J, 1, 3."])
    text = cc.read_document(f)
    out = cc.check(text)
    assert [c["key"] for c in out["orphans_in_text"]] == ["lee|2019"]


def test_docx_without_python_docx_exits_2(monkeypatch, load_module, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "docx", None)
    mod = load_module(SCRIPT, "writing_check_citations_nodocx")
    assert mod.HAVE_DOCX is False
    f = tmp_path / "paper.docx"
    f.write_bytes(b"PK\x03\x04")
    rc = mod.main([str(f)])
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert "python-docx" in err and "\n" not in err


def test_narrative_citation_ignores_leading_prose_words(cc):
    keys = sorted(c["key"] for c in cc.extract_intext("As Smith and Lee (2020) argue, על פי לוי (2018) הדבר נכון."))
    assert keys == ["smith|2020", "לוי|2018"]


def test_narrative_citation_keeps_particle_surnames(cc):
    keys = sorted(c["key"] for c in cc.extract_intext("Ben Gurion (1951) and van der Berg (2020) differ."))
    assert keys == ["ben gurion|1951", "van der berg|2020"]
