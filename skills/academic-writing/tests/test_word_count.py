"""word_count.py — words per course rules: bibliography, footnotes and (optionally) the title page excluded."""
import json
import pathlib
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/word_count.py"


@pytest.fixture(scope="module")
def wc(load_module):
    return load_module(SCRIPT, "writing_word_count")


def test_counts_hebrew_and_english_tokens(wc):
    out = wc.count_words("שלום עולם, hello world.")
    assert out["words"] == 4 and out["words_counted"] == 4 and out["excluded_sections"] == []


def test_hyphen_and_maqaf_words_count_once(wc):
    assert wc.count_words("well-known בית־ספר")["words_counted"] == 2


def test_markdown_markup_is_not_counted(wc):
    text = "# כותרת\n\n- **פריט** ראשון\n- `code` here\n\n> ציטוט\n"
    assert wc.count_words(text)["words_counted"] == 6  # כותרת פריט ראשון code here ציטוט


def test_hebrew_bibliography_heading_excluded(wc):
    text = "מילה אחת שתיים שלוש.\n\n## ביבליוגרפיה\n\nכהן, א' (2019). שם הספר. הוצאה.\n"
    out = wc.count_words(text)
    assert out["words_counted"] == 4
    assert out["words"] > out["words_counted"]
    assert out["excluded_sections"] == ["ביבליוגרפיה"]


@pytest.mark.parametrize("heading", ["References", "Bibliography", "Works Cited", "רשימת מקורות", "מקורות"])
def test_every_reference_heading_is_excluded(wc, heading):
    text = f"one two three\n\n## {heading}\n\nSmith, J. (2020). Title.\n"
    out = wc.count_words(text)
    assert out["words_counted"] == 3 and out["excluded_sections"] == [heading]


def test_references_can_be_kept(wc):
    text = "one two three\n\n## References\n\nSmith, J. (2020). Title.\n"
    out = wc.count_words(text, exclude_refs=False)
    assert out["words_counted"] == out["words"] and out["excluded_sections"] == []


def test_footnote_definitions_excluded_but_markers_ignored(wc):
    text = "A claim.[^1] Another claim.\n\n[^1]: Smith, J. (2020). A long footnote with many words.\n"
    out = wc.count_words(text)
    assert out["words_counted"] == 4
    assert "footnotes" in out["excluded_sections"]
    assert wc.count_words(text, exclude_footnotes=False)["words_counted"] == out["words"]


def test_title_page_excluded_on_request(wc):
    text = "# A Title\n\nDana Student\nCourse 101\n\n## Introduction\n\nfour words are here\n"
    assert wc.count_words(text)["words_counted"] == 11  # 2 + 2 + 2 + 1 + 4
    out = wc.count_words(text, exclude_title_page=True)
    assert out["words_counted"] == 5  # "Introduction" + four words
    assert "title page" in out["excluded_sections"]


def test_code_blocks_are_not_prose(wc):
    text = "two words\n\n```python\nprint('not counted at all')\n```\n"
    assert wc.count_words(text)["words_counted"] == 2


def test_cli_limit_exit_code_and_json(tmp_path):
    f = tmp_path / "essay.md"
    f.write_text(" ".join(f"w{i}" for i in range(12)) + "\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--limit", "10", "--json"], capture_output=True, text=True)
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["words_counted"] == 12 and out["limit"] == 10 and out["ok"] is False
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--limit", "12"], capture_output=True, text=True)
    assert r.returncode == 0


def test_docx_input(wc, tmp_path, minimal_docx):
    pytest.importorskip("docx")
    f = tmp_path / "essay.docx"
    minimal_docx(f, ["שלוש מילים כאן", "References", "Smith, J. (2020). T."])
    assert wc.count_words(wc.read_document(f))["words_counted"] == 3


def test_docx_without_python_docx_exits_2(monkeypatch, load_module, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "docx", None)
    mod = load_module(SCRIPT, "writing_word_count_nodocx")
    f = tmp_path / "essay.docx"
    f.write_bytes(b"PK\x03\x04")
    assert mod.main([str(f)]) == 2
    err = capsys.readouterr().err.strip()
    assert "python-docx" in err and "\n" not in err
