"""check_docx_rtl.py: Hebrew paragraphs need w:bidi (directly or through their style chain)."""
import json
import pathlib
import subprocess
import sys

import docx_builder as b

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_docx_rtl.py"
HEB = "זהו משפט בעברית עם מונח Docker באמצע."


def test_hebrew_paragraph_without_bidi_is_reported(tmp_path, docx_rtl):
    f = b.write(tmp_path / "a.docx", [b.para(HEB)])
    issues = docx_rtl.check_docx(f)
    assert len(issues) == 1 and issues[0]["paragraph"] == 1 and issues[0]["issue"] == "missing w:bidi"


def test_paragraph_level_bidi_is_fine(tmp_path, docx_rtl):
    f = b.write(tmp_path / "b.docx", [b.para(HEB, bidi=True)])
    assert docx_rtl.check_docx(f) == []


def test_style_level_bidi_counts_including_basedon_chain(tmp_path, docx_rtl):
    defs = {"HebBase": {"bidi": True}, "HebBody": {"bidi": False, "basedOn": "HebBase"}}
    f = b.write(tmp_path / "c.docx", [b.para(HEB, style="HebBody")], defs)
    assert docx_rtl.check_docx(f) == []


def test_english_paragraph_is_ignored(tmp_path, docx_rtl):
    f = b.write(tmp_path / "d.docx", [b.para("Plain English paragraph with no Hebrew.")])
    assert docx_rtl.check_docx(f) == []


def test_short_hebrew_fragment_is_ignored(tmp_path, docx_rtl):
    f = b.write(tmp_path / "e.docx", [b.para("See figure א.")])
    assert docx_rtl.check_docx(f) == []


def test_cli_json_and_exit_code(tmp_path):
    f = b.write(tmp_path / "f.docx", [b.para(HEB), b.para(HEB, bidi=True)])
    proc = subprocess.run([sys.executable, str(SCRIPT), str(f), "--json"], capture_output=True, text=True)
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert len(data[str(f)]) == 1
    ok = b.write(tmp_path / "g.docx", [b.para(HEB, bidi=True)])
    assert subprocess.run([sys.executable, str(SCRIPT), str(ok)], capture_output=True).returncode == 0
