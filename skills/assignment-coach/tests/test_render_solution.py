"""render_solution.py — Markdown solution → DOCX (RTL paragraphs where there is Hebrew) → PDF via LibreOffice."""
import json
import os
import pathlib
import stat
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/render_solution.py"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SAMPLE = """# פתרון תרגיל 3

## שאלה 1

הפונקציה `fork` יוצרת תהליך חדש, ולכן **שני** תהליכים מדפיסים.

```c
int main(void) {
    fork();
    printf("hi\\n");
}
```

- הפלט מודפס פעמיים
- הסדר אינו מובטח

1. ראשית נבדוק את ערך ההחזרה
2. לאחר מכן נטפל בשגיאה

| המשתנה | הערך |
|---|---|
| pid | 0 |
| rc | -1 |

Final answer: 2 processes.
"""


@pytest.fixture(scope="module")
def rs(load_module):
    pytest.importorskip("docx")
    return load_module(SCRIPT, "coach_render_solution")


@pytest.fixture(scope="module")
def rendered(rs, tmp_path_factory):
    import docx

    d = tmp_path_factory.mktemp("render")
    src = d / "solution.md"
    src.write_text(SAMPLE, encoding="utf-8")
    out = rs.render(src, d / "solution.docx", "docx")
    assert out.exists() and out.suffix == ".docx"
    return docx.Document(str(out))


def _has_bidi(paragraph) -> bool:
    pPr = paragraph._p.pPr
    return pPr is not None and pPr.find(f"{W}bidi") is not None


def _texts(doc):
    return [p.text for p in doc.paragraphs]


def test_hebrew_paragraph_gets_bidi_and_right_alignment(rendered):
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    p = next(p for p in rendered.paragraphs if p.text.startswith("הפונקציה"))
    assert _has_bidi(p)
    assert p.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.RIGHT


def test_code_block_paragraph_is_ltr_monospace_without_bidi(rendered):
    code = [p for p in rendered.paragraphs if "fork();" in p.text or "int main" in p.text]
    assert code, _texts(rendered)
    for p in code:
        assert not _has_bidi(p)
        assert all(r.font.name == "Consolas" for r in p.runs)


def test_english_final_answer_paragraph_has_no_bidi(rendered):
    p = next(p for p in rendered.paragraphs if p.text.startswith("Final answer"))
    assert not _has_bidi(p)


def test_headings_map_to_heading_styles(rendered):
    h1 = next(p for p in rendered.paragraphs if p.text == "פתרון תרגיל 3")
    h2 = next(p for p in rendered.paragraphs if p.text == "שאלה 1")
    assert h1.style.name == "Heading 1"
    assert h2.style.name == "Heading 2"
    assert _has_bidi(h1)


def test_bullets_and_numbers_use_list_styles(rendered):
    bullet = next(p for p in rendered.paragraphs if p.text == "הפלט מודפס פעמיים")
    number = next(p for p in rendered.paragraphs if p.text.startswith("ראשית"))
    assert bullet.style.name == "List Bullet"
    assert number.style.name == "List Number"
    assert _has_bidi(bullet) and _has_bidi(number)


def test_table_cells_preserved(rendered):
    assert len(rendered.tables) == 1
    t = rendered.tables[0]
    assert len(t.rows) == 3 and len(t.columns) == 2  # header + 2 body rows
    assert t.cell(0, 0).text == "המשתנה" and t.cell(0, 1).text == "הערך"
    assert t.cell(1, 0).text == "pid" and t.cell(1, 1).text == "0"
    assert t.cell(2, 0).text == "rc" and t.cell(2, 1).text == "-1"


def test_inline_bold_and_code_become_runs(rendered):
    p = next(p for p in rendered.paragraphs if p.text.startswith("הפונקציה"))
    assert any(r.bold and r.text == "שני" for r in p.runs)
    assert any(r.font.name == "Consolas" and r.text == "fork" for r in p.runs)
    assert "**" not in p.text and "`" not in p.text


# --- PDF path ---------------------------------------------------------------------------------------------

def test_pdf_without_soffice_exits_2(rs, tmp_path, monkeypatch):
    monkeypatch.setattr(rs.shutil, "which", lambda name: None)
    src = tmp_path / "s.md"
    src.write_text("# T\n\nhello\n", encoding="utf-8")
    rc = rs.main([str(src), "--to", "pdf", "--out", str(tmp_path / "s.pdf")])
    assert rc == 2


def test_pdf_with_fake_soffice(rs, tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake = fake_bin / "soffice"
    # mimics `soffice --headless --convert-to pdf --outdir DIR FILE`: writes DIR/<stem>.pdf
    fake.write_text("#!/bin/sh\nout=''\nwhile [ $# -gt 1 ]; do if [ \"$1\" = '--outdir' ]; then out=$2; fi; shift; done\n"
                    "f=$(basename \"$1\" .docx)\nprintf '%%PDF-1.4 fake' > \"$out/$f.pdf\"\n", encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(fake_bin) + os.pathsep + os.environ.get("PATH", ""))
    src = tmp_path / "s.md"
    src.write_text("# כותרת\n\nשלום\n", encoding="utf-8")
    out = rs.render(src, tmp_path / "final.pdf", "pdf")
    assert out == tmp_path / "final.pdf" and out.read_bytes().startswith(b"%PDF")


# --- CLI / degradation ------------------------------------------------------------------------------------

def test_cli_docx_json(tmp_path):
    pytest.importorskip("docx")
    src = tmp_path / "s.md"
    src.write_text("# T\n\nשלום עולם\n", encoding="utf-8")
    out = tmp_path / "s.docx"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(src), "--to", "docx", "--out", str(out), "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"ok": True, "out": str(out), "format": "docx"}
    assert out.exists()


def test_without_python_docx_exits_2_with_one_line(monkeypatch, load_module, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "docx", None)
    mod = load_module(SCRIPT, "coach_render_solution_nodocx")
    assert mod.HAVE_DOCX is False
    src = tmp_path / "s.md"
    src.write_text("hello\n", encoding="utf-8")
    rc = mod.main([str(src), "--to", "docx", "--out", str(tmp_path / "s.docx")])
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert "python-docx" in err and "\n" not in err
