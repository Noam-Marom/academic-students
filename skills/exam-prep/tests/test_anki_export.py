"""anki_export.py: cards → Anki tab-separated import text with MathJax delimiters, Hebrew-safe."""
import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "anki_export.py"


def test_header_lines_and_tab_separation(anki_export):
    out = anki_export.to_anki([{"front": "What is a mutex?", "back": "A lock with one owner."}])
    lines = out.split("\n")
    assert lines[0] == "#separator:tab"
    assert lines[1] == "#html:true"
    assert "What is a mutex?\tA lock with one owner." in lines
    assert out.endswith("\n")


def test_newlines_become_br_and_tabs_are_escaped(anki_export):
    out = anki_export.to_anki([{"front": "line one\nline two", "back": "a\tb"}])
    row = out.strip().split("\n")[-1]
    assert row.count("\t") == 1  # exactly one separator: the field tab was escaped
    assert "line one<br>line two" in row
    assert "a\tb" not in row


def test_formulas_use_mathjax_delimiters(anki_export):
    out = anki_export.to_anki([{"front": "Inline $E = mc^2$ here", "back": "Display $$\\int_0^1 x\\,dx$$ done"}])
    assert "\\(E = mc^2\\)" in out
    assert "\\[\\int_0^1 x\\,dx\\]" in out
    assert "$" not in out


def test_hebrew_is_preserved_verbatim(anki_export):
    out = anki_export.to_anki([{"front": "מהו סמפור?", "back": "משתנה מונה עם wait ו-signal"}])
    assert "מהו סמפור?" in out
    assert "משתנה מונה עם wait ו-signal" in out


def test_tags_column_is_added_when_any_card_has_tags(anki_export):
    out = anki_export.to_anki([{"front": "a", "back": "b", "tags": ["os", "sync"]}, {"front": "c", "back": "d"}])
    rows = [ln for ln in out.split("\n") if ln and not ln.startswith("#")]
    assert rows[0] == "a\tb\tos sync"
    assert rows[1] == "c\td\t"
    assert "#tags column:3" in out


def test_cli_writes_utf8_file(tmp_path):
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps([{"front": "שאלה", "back": "תשובה $x^2$"}], ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "cards.txt"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(cards), "--out", str(out)],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    text = out.read_bytes().decode("utf-8")
    assert text.startswith("#separator:tab\n#html:true\n")
    assert "שאלה\tתשובה \\(x^2\\)" in text


def test_cli_rejects_card_without_front_or_back(tmp_path):
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps([{"front": "only front"}]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(cards), "--out", str(tmp_path / "x.txt")],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
    assert "back" in r.stderr
