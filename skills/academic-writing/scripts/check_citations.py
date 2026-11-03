#!/usr/bin/env python3
"""Check that every in-text citation has a reference-list entry and every entry is cited.

Handles the three citation families a student paper uses:
  * author-year  — (Smith, 2020), (Smith et al., 2019), Smith (2020), (כהן, 2020), (כהן ושות', 2019),
                   several in one parenthesis separated by ';', page numbers after the year;
  * numeric      — [1], [1, 3], [4–6]; list entries "[1] …" or "1. …";
  * footnote     — Markdown footnotes [^1] with "[^1]: …" definitions.
The reference list starts at a heading named References, Bibliography, Works Cited, ביבליוגרפיה,
רשימת מקורות or מקורות (Markdown heading, bold line or a line holding only that word).

Keys: author-year → "lastname|year" (first author only, Hebrew names supported, Hebrew-letter years
such as תש"ף kept as written); numeric/footnote → the number as a string.

Usage:
    python3 check_citations.py PAPER.md|PAPER.docx [--json]
Exit codes: 0 = consistent, 1 = orphans found, 2 = unreadable file / .docx without python-docx.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import docx  # type: ignore

    HAVE_DOCX = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    docx = None  # type: ignore
    HAVE_DOCX = False

Citation = dict  # {"key": str, "raw": str, "line": int, "style": "author-year"|"numeric"|"footnote"}

LIST_HEADINGS = ["references", "bibliography", "works cited", "reference list", "sources",
                 "ביבליוגרפיה", "רשימת מקורות", "מקורות", "רשימה ביבליוגרפית"]
HEADING_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*|__)?\s*(" + "|".join(re.escape(h) for h in LIST_HEADINGS) + r")\s*:?\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE,
)
HEB = r"֐-׿"
# A year: 2020, 2020a, n.d., בדפוס, or a Hebrew-letter year like תש"ף / תשפ"ד
YEAR = rf"(?:\d{{4}}[a-z]?|n\.d\.|בדפוס|in press|[{HEB}]{{2,4}}[\"״][{HEB}])"
NAME_TOKEN = rf"(?:[A-Z][A-Za-z'’\-]+|[{HEB}][{HEB}'’׳\-]*|de|van|von|der|la|le|al)"
ET_AL = r"(?:et\s+al\.?|ושות'|ושות׳|ואח'|ואח׳|ואחרים)"
# Narrative citation: Smith (2020), Smith et al. (2019), Smith and Lee (2020), כהן ושות' (2019)
NARRATIVE = re.compile(
    rf"((?:{NAME_TOKEN}\s*)+(?:(?:,|\s+(?:and|&|ו)\s+|\s+ו)(?:{NAME_TOKEN}\s*)+)*(?:\s*{ET_AL})?)\s*\(({YEAR})(?:[,:]\s*[^()]*)?\)"
)
PAREN = re.compile(r"\(([^()]*)\)")
PAREN_CITE = re.compile(rf"^\s*(.+?)[,،]?\s+({YEAR})(?:\s*[,:;]\s*(?:p{{1,2}}\.?|עמ'|עמ׳|pp?\b)?\s*[\d\-–,\s]+)?\s*$")
NUMERIC = re.compile(r"(?<!\^)\[(\d+(?:\s*[-–—,]\s*\d+)*)\](?!\()")
FOOTNOTE_REF = re.compile(r"\[\^(\w+)\](?!:)")
FOOTNOTE_DEF = re.compile(r"^\s*\[\^(\w+)\]:\s*(.*)$")
LIST_MARK = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|\[\d+\]\s*)")
ENTRY_NUMBER = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("״", '"').replace("׳", "'").replace("’", "'")
    s = re.sub(r"[\"'`.]", "", s)
    return re.sub(r"\s+", " ", s).strip().casefold()


def _first_author(authors: str) -> str:
    a = authors.strip().strip(",;")
    a = re.split(rf"\s*(?:,|;|&|\band\b|\s+ו(?=[{HEB}])|\s*{ET_AL})", a, maxsplit=1)[0]
    a = a.strip().strip(",")
    # drop initials glued to the name ("Smith J" in some styles)
    parts = a.split()
    if len(parts) > 1 and all(len(p.strip(".")) <= 2 for p in parts[1:]):
        a = parts[0]
    return _norm(a)


PARTICLES = {"van", "von", "de", "der", "den", "la", "le", "du", "da", "di", "ben", "bin", "abu", "al", "el",
             "mc", "mac", "st", "בן", "בת", "אבו", "אל", "בר"}


def _narrative_author(authors: str) -> str:
    """In running text ("As Smith and Lee (2020) argue") the words before the surname are prose, not names.
    Keep the last word of the first author chunk plus any name particles in front of it (van der Berg, Ben Gurion)."""
    first = re.split(rf"\s*(?:,|;|&|\band\b|\s+ו(?=[{HEB}])|\s*{ET_AL})", authors.strip(), maxsplit=1)[0].split()
    if not first:
        return ""
    keep = [first[-1]]
    for w in reversed(first[:-1]):
        if _norm(w) in PARTICLES:
            keep.insert(0, w)
        else:
            break
    return _norm(" ".join(keep))


def _key_author_year(authors: str, year: str, narrative: bool = False) -> str:
    author = _narrative_author(authors) if narrative else _first_author(authors)
    return f"{author}|{_norm(year)}"


def split_reference_list(text: str) -> tuple[str, str, int]:
    """Return (body, reference-list text, line number where the list starts; 0 when there is none)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if HEADING_LINE.match(line):
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:]), i + 1
    return text, "", 0


def extract_intext(text: str) -> list[Citation]:
    body, _, _ = split_reference_list(text)
    out: list[Citation] = []
    for n, line in enumerate(body.split("\n"), 1):
        line_wo_defs = "" if FOOTNOTE_DEF.match(line) else line
        for m in FOOTNOTE_REF.finditer(line_wo_defs):
            out.append({"key": m.group(1), "raw": m.group(0), "line": n, "style": "footnote"})
        for m in NUMERIC.finditer(line_wo_defs):
            for num in _expand_numbers(m.group(1)):
                out.append({"key": num, "raw": m.group(0), "line": n, "style": "numeric"})
        consumed: list[tuple[int, int]] = []
        for m in PAREN.finditer(line_wo_defs):
            inner = m.group(1)
            parts = [p for p in re.split(r"\s*;\s*", inner) if p.strip()]
            found = []
            for part in parts:
                pm = PAREN_CITE.match(part)
                if pm and re.search(rf"[A-Za-z{HEB}]", pm.group(1)):
                    found.append({"key": _key_author_year(pm.group(1), pm.group(2)), "raw": part.strip(),
                                  "line": n, "style": "author-year"})
            if found and len(found) == len(parts):
                out.extend(found)
                consumed.append(m.span())
        for m in NARRATIVE.finditer(line_wo_defs):
            if any(s <= m.start() < e for s, e in consumed):
                continue
            out.append({"key": _key_author_year(m.group(1), m.group(2), narrative=True), "raw": m.group(0).strip(),
                        "line": n, "style": "author-year"})
    return out


def _expand_numbers(spec: str) -> list[str]:
    nums: list[str] = []
    for chunk in re.split(r"\s*,\s*", spec):
        if re.search(r"[-–—]", chunk):
            a, b = re.split(r"\s*[-–—]\s*", chunk, maxsplit=1)
            lo, hi = int(a), int(b)
            if hi - lo > 500:
                nums.append(a)
                continue
            nums.extend(str(i) for i in range(lo, hi + 1))
        else:
            nums.append(chunk.strip())
    return nums


def extract_reflist(text: str) -> list[Citation]:
    body, reflist, start = split_reference_list(text)
    out: list[Citation] = []
    # footnote definitions anywhere in the document
    for n, line in enumerate(text.split("\n"), 1):
        fm = FOOTNOTE_DEF.match(line)
        if fm:
            out.append({"key": fm.group(1), "raw": fm.group(2).strip(), "line": n, "style": "footnote"})
    if not reflist:
        return out
    for i, line in enumerate(reflist.split("\n")):
        if not line.strip() or re.match(r"^\s*#{1,6}\s", line) or FOOTNOTE_DEF.match(line):
            continue
        n = start + 1 + i
        num = ENTRY_NUMBER.match(line)
        raw = LIST_MARK.sub("", line, count=1).strip()
        if num and (num.group(1) or not re.match(rf"^\s*\d+[.)]\s+[A-Za-z{HEB}][^,]*,\s*[A-Z{HEB}]\S*\s*\(", line)):
            out.append({"key": num.group(1) or num.group(2), "raw": raw, "line": n, "style": "numeric"})
            continue
        ay = re.match(rf"^\s*(.+?)\s*\(({YEAR})\)", raw)
        if ay:
            out.append({"key": _key_author_year(ay.group(1), ay.group(2)), "raw": raw, "line": n, "style": "author-year"})
            continue
        # Chicago/MLA-like: "Smith, John. 2020. Title." or year anywhere
        ym = re.search(rf"\b({YEAR})\b", raw)
        if ym:
            out.append({"key": _key_author_year(raw[:ym.start()], ym.group(1)), "raw": raw, "line": n, "style": "author-year"})
    return out


def _dominant_style(cites: list[Citation]) -> str:
    if not cites:
        return "none"
    counts: dict[str, int] = {}
    for c in cites:
        counts[c["style"]] = counts.get(c["style"], 0) + 1
    return max(counts, key=counts.get)


def _year_digits(key: str) -> str:
    return re.sub(r"[a-z]$", "", key)


def check(text: str) -> dict:
    """Return {"orphans_in_text": [...], "orphans_in_list": [...], "style": str}."""
    intext = extract_intext(text)
    reflist = extract_reflist(text)
    style = _dominant_style(intext) if intext else (_dominant_style(reflist) if reflist else "none")
    list_keys = {c["key"] for c in reflist}
    list_loose = {_year_digits(c["key"]) for c in reflist}
    cited: set[str] = set()
    orphans_in_text: list[Citation] = []
    seen: set[str] = set()
    for c in intext:
        k = c["key"]
        if k in list_keys:
            cited.add(k)
        elif c["style"] == "author-year" and _year_digits(k) in list_loose and not re.search(r"\d{4}[a-z]$", k):
            # (Smith, 2020) against a list that only has Smith (2020a): accept, mark the loose match as cited
            cited.update(x for x in list_keys if _year_digits(x) == _year_digits(k))
        elif k not in seen:
            orphans_in_text.append(c)
            seen.add(k)
    orphans_in_list = [c for c in reflist if c["key"] not in cited]
    return {"orphans_in_text": orphans_in_text, "orphans_in_list": orphans_in_list, "style": style}


def read_document(path: Path) -> str:
    """Return the text of a .md/.txt/.tex file, or of a .docx (python-docx required)."""
    path = Path(path)
    if path.suffix.lower() == ".docx":
        if not HAVE_DOCX:
            raise ImportError("python-docx is not installed; run: pip install python-docx")
        d = docx.Document(str(path))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        return "\n".join(parts)
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="paper as .md/.txt/.tex or .docx")
    ap.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = ap.parse_args(argv)
    try:
        text = read_document(Path(args.file))
    except ImportError as exc:
        msg = str(exc)
        print(json.dumps({"ok": False, "error": msg}) if args.json else msg, file=sys.stdout if args.json else sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        msg = f"cannot read {args.file}: {exc}"
        print(json.dumps({"ok": False, "error": msg}) if args.json else msg, file=sys.stdout if args.json else sys.stderr)
        return 2
    result = check(text)
    ok = not result["orphans_in_text"] and not result["orphans_in_list"]
    if args.json:
        print(json.dumps({"ok": ok, **result}, ensure_ascii=False))
    else:
        print(f"style: {result['style']}")
        for c in result["orphans_in_text"]:
            print(f"  line {c['line']}: cited but not in the reference list: {c['raw']}")
        for c in result["orphans_in_list"]:
            print(f"  line {c['line']}: in the reference list but never cited: {c['raw'][:80]}")
        print(f"{args.file}: {len(result['orphans_in_text'])} orphan citation(s), {len(result['orphans_in_list'])} uncited entr(y/ies)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
