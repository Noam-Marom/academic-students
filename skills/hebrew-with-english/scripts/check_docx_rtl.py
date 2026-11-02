#!/usr/bin/env python3
"""Check a Word document for Hebrew paragraphs that are not marked right-to-left.

Word decides a paragraph's base direction from `w:bidi` in the paragraph properties — directly, or inherited
through the paragraph's style chain (`w:pStyle` → `styles.xml`, following `w:basedOn`). Hebrew text in a
paragraph without it renders left-to-right: punctuation jumps, mixed English terms land on the wrong side.
This checker lists such paragraphs. It reads the .docx with zipfile + XML only (no python-docx needed) and never
modifies the file.

Usage:
    python3 check_docx_rtl.py FILE.docx [FILE2.docx ...] [--json]
Exit code: 0 = every Hebrew paragraph is RTL, 1 = issues found, 2 = usage / unreadable file.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
HEB = re.compile(r"[א-ת]")
MIN_HEBREW_LETTERS = 3


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def _style_bidi_map(z: zipfile.ZipFile) -> dict[str, bool]:
    """style id -> whether its pPr (or any ancestor's) sets w:bidi."""
    try:
        root = ET.fromstring(z.read("word/styles.xml"))
    except KeyError:
        return {}
    own: dict[str, bool] = {}
    based: dict[str, str | None] = {}
    for st in root.findall("w:style", NS):
        sid = st.get(_q("styleId"))
        if not sid:
            continue
        ppr = st.find("w:pPr", NS)
        own[sid] = ppr is not None and ppr.find("w:bidi", NS) is not None
        bo = st.find("w:basedOn", NS)
        based[sid] = bo.get(_q("val")) if bo is not None else None
    resolved: dict[str, bool] = {}

    def resolve(sid: str, seen: frozenset = frozenset()) -> bool:
        if sid in resolved:
            return resolved[sid]
        if sid in seen or sid not in own:
            return False
        val = own[sid] or (resolve(based[sid], seen | {sid}) if based.get(sid) else False)
        resolved[sid] = val
        return val

    return {sid: resolve(sid) for sid in own}


def check_docx(path: Path) -> list[dict]:
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        styles = _style_bidi_map(z)
        root = ET.fromstring(z.read("word/document.xml"))
    issues: list[dict] = []
    for i, p in enumerate(root.iter(_q("p")), 1):
        text = "".join(t.text or "" for t in p.iter(_q("t")))
        if len(HEB.findall(text)) < MIN_HEBREW_LETTERS:
            continue
        ppr = p.find("w:pPr", NS)
        direct = ppr is not None and ppr.find("w:bidi", NS) is not None
        if direct:
            continue
        style_el = ppr.find("w:pStyle", NS) if ppr is not None else None
        sid = style_el.get(_q("val")) if style_el is not None else None
        if sid and styles.get(sid):
            continue
        issues.append({"paragraph": i, "text": text[:80], "issue": "missing w:bidi"})
    return issues


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    files = [a for a in args if not a.startswith("--")]
    as_json = "--json" in args
    if not files:
        print(__doc__)
        return 2
    out: dict[str, list[dict]] = {}
    total = 0
    for f in files:
        try:
            issues = check_docx(Path(f))
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
            print(f"!! {f}: not a readable .docx ({e})", file=sys.stderr)
            return 2
        out[f] = issues
        total += len(issues)
        if not as_json:
            print(f"== {f}: {len(issues)} Hebrew paragraph(s) without RTL")
            for it in issues:
                print(f"  paragraph {it['paragraph']}: {it['issue']}  ::  {it['text']}")
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
