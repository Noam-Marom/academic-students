#!/usr/bin/env python3
"""Count the words of a paper the way a course counts them.

By default the reference list (everything after a heading named References, Bibliography, Works Cited,
ביבליוגרפיה, רשימת מקורות or מקורות) and Markdown footnote definitions (`[^1]: …`) are excluded; the
title page (everything before the first `##` heading or the first `---` rule) is excluded on request.
Fenced code blocks and Markdown markup are never counted as words. Hebrew and English tokens count alike;
a hyphenated or maqaf-joined word (well-known, בית־ספר) counts once.

Usage:
    python3 word_count.py PAPER.md|PAPER.docx [--limit N] [--include-refs] [--include-footnotes]
                          [--exclude-title-page] [--json]
Exit codes: 0 = within the limit (or no limit), 1 = over --limit, 2 = unreadable file / .docx without python-docx.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import docx  # type: ignore

    HAVE_DOCX = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    docx = None  # type: ignore
    HAVE_DOCX = False

REF_HEADINGS = ["References", "Bibliography", "Works Cited", "Reference List", "ביבליוגרפיה", "רשימת מקורות",
                "מקורות", "רשימה ביבליוגרפית"]
HEADING_LINE = re.compile(
    r"^\s*(?:#{1,6}\s*|\*\*|__)?\s*(" + "|".join(re.escape(h) for h in REF_HEADINGS) + r")\s*:?\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE,
)
FOOTNOTE_DEF = re.compile(r"^\s*\[\^\w+\]:")
FOOTNOTE_REF = re.compile(r"\[\^\w+\]")
FENCE = re.compile(r"^\s*(```|~~~)")
SECTION_HEADING = re.compile(r"^\s*#{2,6}\s+\S")
RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
# a word: letters/digits with internal hyphen, maqaf, apostrophe/geresh or gershayim (ד"ר, well-known, בית־ספר)
WORD = re.compile(r"[\w֐-׿]+(?:[-־'’׳\"״][\w֐-׿]+)*")
MD_INLINE = re.compile(r"(\*\*|__|\*|_|~~|`+)")
MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def _strip_markup(line: str) -> str:
    line = re.sub(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+(?:\[[ xX]\]\s+)?|\d+[.)]\s+)", "", line)
    line = MD_LINK.sub(r"\1", line)
    line = FOOTNOTE_REF.sub("", line)
    line = re.sub(r"<[^>]+>", " ", line)
    return MD_INLINE.sub(" ", line)


def _count_line(line: str) -> int:
    return len(WORD.findall(_strip_markup(line)))


def count_words(text: str, exclude_refs: bool = True, exclude_footnotes: bool = True,
                exclude_title_page: bool = False) -> dict:
    """Return {"words": total, "words_counted": after exclusions, "excluded_sections": [...]}."""
    lines = text.split("\n")
    total = 0
    counted = 0
    excluded: list[str] = []
    in_code = False
    in_refs = False
    in_title = exclude_title_page
    title_words = 0
    footnote_words = 0
    for line in lines:
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        hm = HEADING_LINE.match(line)
        if hm and not in_refs:
            in_refs = True
            if exclude_refs:
                excluded.append(hm.group(1))
            continue
        if in_title and (SECTION_HEADING.match(line) or RULE.match(line)):
            in_title = False
            if RULE.match(line):
                continue
        n = _count_line(line)
        total += n
        if in_refs and exclude_refs:
            continue
        if FOOTNOTE_DEF.match(line):
            if exclude_footnotes:
                footnote_words += n
                continue
        if in_title:
            title_words += n
            continue
        counted += n
    if footnote_words or (exclude_footnotes and any(FOOTNOTE_DEF.match(l) for l in lines)):
        excluded.append("footnotes")
    if exclude_title_page:
        excluded.append("title page")
    return {"words": total, "words_counted": counted, "excluded_sections": excluded}


def read_document(path: Path) -> str:
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
    ap.add_argument("--limit", type=int, help="word limit from the course rules; exit 1 when exceeded")
    ap.add_argument("--include-refs", action="store_true", help="count the reference list too")
    ap.add_argument("--include-footnotes", action="store_true", help="count footnote definitions too")
    ap.add_argument("--exclude-title-page", action="store_true", help="skip everything before the first ## heading or --- rule")
    ap.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = ap.parse_args(argv)
    try:
        text = read_document(Path(args.file))
    except ImportError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}) if args.json else str(exc), file=sys.stdout if args.json else sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        msg = f"cannot read {args.file}: {exc}"
        print(json.dumps({"ok": False, "error": msg}) if args.json else msg, file=sys.stdout if args.json else sys.stderr)
        return 2
    result = count_words(text, exclude_refs=not args.include_refs, exclude_footnotes=not args.include_footnotes,
                         exclude_title_page=args.exclude_title_page)
    over = args.limit is not None and result["words_counted"] > args.limit
    if args.json:
        print(json.dumps({"ok": not over, "limit": args.limit, **result}, ensure_ascii=False))
    else:
        excl = ", ".join(result["excluded_sections"]) or "nothing"
        print(f"{args.file}: {result['words_counted']} words counted ({result['words']} in total; excluded: {excl})")
        if args.limit is not None:
            print(f"limit {args.limit}: {'OVER by ' + str(result['words_counted'] - args.limit) if over else 'ok'}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
