#!/usr/bin/env python3
"""Render a Markdown solution to DOCX (and PDF) with correct text direction per paragraph.

Markdown subset: `#`–`######` headings, paragraphs, `-`/`*` bullets, `1.` numbered items, fenced code
blocks, `>` quotes, pipe tables, and inline **bold**, *italic*, `code`. Every paragraph or table cell that
contains Hebrew gets `w:bidi` and right alignment (the hebrew-with-english DOCX rules); code blocks stay
left-to-right in Consolas with no bidi, so identifiers and output read as written.

PDF goes through LibreOffice (`soffice --headless --convert-to pdf`) when it is installed; otherwise the
script says so and exits 2. Requires python-docx (`pip install python-docx`); without it, exit 2 with one line.

Usage:
    python3 render_solution.py SOLUTION.md --to docx|pdf --out FILE [--json]
Exit codes: 0 = written, 1 = input problem (unreadable, empty), 2 = missing dependency / converter / usage.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import docx  # type: ignore
    from docx.enum.text import WD_ALIGN_PARAGRAPH  # type: ignore
    from docx.oxml import OxmlElement  # type: ignore
    from docx.oxml.ns import qn  # type: ignore

    HAVE_DOCX = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    docx = None  # type: ignore
    HAVE_DOCX = False

HEBREW = re.compile(r"[֐-׿יִ-ﭏ]")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
FENCE = re.compile(r"^\s*(```|~~~)\s*(\w+)?\s*$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)")
CODE_FONT = "Consolas"


# --------------------------------------------------------------------------------------------------
# Markdown → blocks
# --------------------------------------------------------------------------------------------------

def parse_blocks(text: str) -> list[dict]:
    """Turn the Markdown subset into a flat list of blocks: heading, paragraph, bullet, number, code, quote, table."""
    blocks: list[dict] = []
    lines = text.split("\n")
    i = 0
    para: list[str] = []

    def flush_para():
        if para:
            blocks.append({"kind": "paragraph", "text": " ".join(s.strip() for s in para)})
            para.clear()

    while i < len(lines):
        line = lines[i]
        fence = FENCE.match(line)
        if fence:
            flush_para()
            marker = fence.group(1)
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(marker):
                code.append(lines[i])
                i += 1
            blocks.append({"kind": "code", "text": "\n".join(code), "lang": fence.group(2) or ""})
            i += 1
            continue
        if not line.strip():
            flush_para()
            i += 1
            continue
        h = HEADING.match(line)
        if h:
            flush_para()
            blocks.append({"kind": "heading", "level": len(h.group(1)), "text": h.group(2)})
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            flush_para()
            rows = [[c.strip() for c in stripped.strip("|").split("|")]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append({"kind": "table", "rows": rows})
            continue
        if stripped.startswith(">"):
            flush_para()
            blocks.append({"kind": "quote", "text": stripped.lstrip("> ").strip()})
            i += 1
            continue
        b = BULLET.match(line)
        if b:
            flush_para()
            blocks.append({"kind": "bullet", "text": b.group(1)})
            i += 1
            continue
        n = NUMBERED.match(line)
        if n:
            flush_para()
            blocks.append({"kind": "number", "text": n.group(1)})
            i += 1
            continue
        if re.match(r"^\s*(---+|\*\*\*+)\s*$", line):
            flush_para()
            i += 1
            continue
        para.append(line)
        i += 1
    flush_para()
    return blocks


# --------------------------------------------------------------------------------------------------
# blocks → DOCX
# --------------------------------------------------------------------------------------------------

def _set_bidi(paragraph, rtl: bool) -> None:
    pPr = paragraph._p.get_or_add_pPr()
    for old in pPr.findall(qn("w:bidi")):
        pPr.remove(old)
    if rtl:
        bidi = OxmlElement("w:bidi")
        pPr.append(bidi)
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _mark_run_rtl(run) -> None:
    rPr = run._r.get_or_add_rPr()
    if rPr.find(qn("w:rtl")) is None:
        rPr.append(OxmlElement("w:rtl"))


def _add_inline_runs(paragraph, text: str) -> None:
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            run = paragraph.add_run(piece[2:-2])
            run.bold = True
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            run.font.name = CODE_FONT
            run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), CODE_FONT)
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            run = paragraph.add_run(piece[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(piece)
        if HEBREW.search(run.text):
            _mark_run_rtl(run)


def _fill_paragraph(paragraph, text: str) -> None:
    _add_inline_runs(paragraph, text)
    _set_bidi(paragraph, bool(HEBREW.search(text)))


def _add_code(document, code: str) -> None:
    for line in code.split("\n") or [""]:
        p = document.add_paragraph()
        run = p.add_run(line)
        run.font.name = CODE_FONT
        run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:cs"), CODE_FONT)
        p.paragraph_format.space_after = 0
        _set_bidi(p, False)


def build_docx(blocks: list[dict]):
    document = docx.Document()
    for b in blocks:
        kind = b["kind"]
        if kind == "heading":
            p = document.add_heading("", level=min(b["level"], 9))
            _fill_paragraph(p, b["text"])
        elif kind == "paragraph":
            _fill_paragraph(document.add_paragraph(), b["text"])
        elif kind == "bullet":
            _fill_paragraph(document.add_paragraph(style="List Bullet"), b["text"])
        elif kind == "number":
            _fill_paragraph(document.add_paragraph(style="List Number"), b["text"])
        elif kind == "quote":
            _fill_paragraph(document.add_paragraph(style="Intense Quote"), b["text"])
        elif kind == "code":
            _add_code(document, b["text"])
        elif kind == "table":
            rows = b["rows"]
            ncols = max(len(r) for r in rows)
            table = document.add_table(rows=len(rows), cols=ncols)
            table.style = "Table Grid"
            hebrew_cells = sum(1 for r in rows for c in r if HEBREW.search(c))
            if hebrew_cells > (len(rows) * ncols) / 2:
                tblPr = table._tbl.tblPr
                tblPr.append(OxmlElement("w:bidiVisual"))
            for ri, row in enumerate(rows):
                for ci in range(ncols):
                    cell = table.cell(ri, ci)
                    cell_text = row[ci] if ci < len(row) else ""
                    p = cell.paragraphs[0]
                    _fill_paragraph(p, cell_text)
                    if ri == 0:
                        for run in p.runs:
                            run.bold = True
    return document


def _to_pdf(docx_path: Path, out_path: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise FileNotFoundError("LibreOffice (soffice) not found on PATH; install it or use --to docx")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(docx_path)],
                       check=True, capture_output=True, timeout=180)
        produced = Path(tmp) / (docx_path.stem + ".pdf")
        if not produced.exists():
            raise RuntimeError("LibreOffice ran but produced no PDF")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(produced, out_path)
    return out_path


def render(md_path: Path, out_path: Path, fmt: str) -> Path:
    """Render `md_path` to `out_path` as 'docx' or 'pdf'. Raises ImportError without python-docx,
    FileNotFoundError when a PDF is asked for and LibreOffice is missing."""
    if not HAVE_DOCX:
        raise ImportError("python-docx is not installed (pip install python-docx)")
    if fmt not in ("docx", "pdf"):
        raise ValueError(f"unknown format {fmt!r}; use docx or pdf")
    md_path, out_path = Path(md_path), Path(out_path)
    blocks = parse_blocks(md_path.read_text(encoding="utf-8"))
    document = build_docx(blocks)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "docx":
        document.save(str(out_path))
        return out_path
    with tempfile.TemporaryDirectory() as tmp:
        interim = Path(tmp) / (out_path.stem + ".docx")
        document.save(str(interim))
        return _to_pdf(interim, out_path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="Markdown solution")
    ap.add_argument("--to", choices=["docx", "pdf"], required=True, dest="fmt")
    ap.add_argument("--out", required=True, help="output file path")
    ap.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = ap.parse_args(argv)

    def fail(msg: str, code: int) -> int:
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        return code

    if not HAVE_DOCX:
        return fail("python-docx is not installed; run: pip install python-docx", 2)
    src = Path(args.source)
    if not src.is_file():
        return fail(f"cannot read {src}", 1)
    try:
        out = render(src, Path(args.out), args.fmt)
    except FileNotFoundError as exc:
        return fail(str(exc), 2)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return fail(f"PDF conversion failed: {exc}", 2)
    if args.json:
        print(json.dumps({"ok": True, "out": str(out), "format": args.fmt}, ensure_ascii=False))
    else:
        print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
