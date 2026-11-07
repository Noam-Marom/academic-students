#!/usr/bin/env python3
"""Format a reference list from CSL-JSON items in APA 7 or IEEE, Hebrew entries included.

Built-in templates cover `article-journal`, `book`, `chapter`, `webpage` and `thesis`. With `citeproc-py`
installed and `--csl FILE` given, the CSL style file is used instead (any style). Hebrew items (Hebrew
letters in the family names or the title) get Hebrew connectors: `&` → `ו`, "In" → "בתוך", "(Ed.)" →
"(עורך)", "pp." → "עמ'", "n.d." → "ח"ת". APA lists Latin-alphabet entries first and Hebrew entries after
them, each block alphabetical, unless `--mixed` interleaves them by a transliteration of the family name.
IEEE numbers entries in the order given (citation order).

This script formats what it is given; it never invents a field. An item without a verifiable source
stays the author's responsibility (`[unverified]` is added by the skill, not here).

Usage:
    python3 format_refs.py REFS.json --style apa7|ieee [--mixed] [--csl FILE] [--json]
Exit codes: 0 = formatted, 1 = an item could not be formatted (reported), 2 = unreadable input / missing dependency / usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import citeproc  # type: ignore

    HAVE_CITEPROC = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    citeproc = None  # type: ignore
    HAVE_CITEPROC = False

HEBREW = re.compile(r"[֐-׿]")
STYLES = ("apa7", "ieee")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
MONTHS_HE = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
IEEE_MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
TRANSLIT = {"א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z", "ח": "ch", "ט": "t", "י": "y",
            "כ": "k", "ך": "k", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "a", "פ": "p",
            "ף": "p", "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r", "ש": "sh", "ת": "t"}


# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------

def is_hebrew(item: dict) -> bool:
    names = " ".join(a.get("family", "") + a.get("given", "") for a in item.get("author", []) or [])
    return bool(HEBREW.search(names + item.get("title", "")))


def _date_parts(item: dict) -> list:
    parts = (item.get("issued") or {}).get("date-parts") or [[]]
    return list(parts[0]) if parts and parts[0] else []


def year_of(item: dict, heb: bool) -> str:
    dp = _date_parts(item)
    if not dp:
        return "ח\"ת" if heb else "n.d."
    return str(dp[0])


def _initials(given: str, heb: bool) -> str:
    if not given:
        return ""
    if heb:
        return given.strip()[0] + "'"
    parts = re.split(r"[\s]+", given.strip())
    out = []
    for p in parts:
        if not p:
            continue
        if "-" in p:
            out.append("-".join(x[0] + "." for x in p.split("-") if x))
        else:
            out.append(p[0] + ".")
    return " ".join(out)


def _apa_name(a: dict, heb: bool) -> str:
    fam = a.get("family") or a.get("literal") or ""
    ini = _initials(a.get("given", ""), heb)
    if not fam:
        return ini
    return f"{fam}, {ini}" if ini else fam


def _vav(name: str) -> str:
    """Hebrew conjunction: attached to a Hebrew word (ולוי), hyphenated before a Latin one (ו-Smith)."""
    return ("ו" if HEBREW.match(name[:1]) else "ו-") + name


def apa_authors(authors: list[dict], heb: bool) -> str:
    names = [_apa_name(a, heb) for a in authors if a]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) > 20:
        names = names[:19] + ["…", names[-1]]
        return ", ".join(names[:-2]) + ", … " + names[-1]
    if heb:
        return ", ".join(names[:-1]) + " " + _vav(names[-1])
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    return ", ".join(names[:-1]) + ", & " + names[-1]


def _ieee_name(a: dict, heb: bool) -> str:
    fam = a.get("family") or a.get("literal") or ""
    ini = _initials(a.get("given", ""), heb)
    return f"{ini} {fam}".strip()


def ieee_authors(authors: list[dict], heb: bool) -> str:
    names = [_ieee_name(a, heb) for a in authors if a]
    if not names:
        return ""
    if len(names) > 6:
        return f"{names[0]} et al."
    if len(names) == 1:
        return names[0]
    if heb:
        return ", ".join(names[:-1]) + " " + _vav(names[-1])
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _pages(item: dict) -> str:
    p = str(item.get("page") or "").strip()
    return re.sub(r"\s*[-–—]+\s*", "–", p)


def _doi_url(item: dict) -> str:
    if item.get("DOI"):
        doi = item["DOI"].strip()
        return doi if doi.startswith("http") else f"https://doi.org/{doi}"
    return (item.get("URL") or "").strip()


def _end(s: str) -> str:
    return s if s.endswith((".", "?", "!")) else s + "."


# --------------------------------------------------------------------------------------------------
# APA 7
# --------------------------------------------------------------------------------------------------

def _apa_date(item: dict, heb: bool) -> str:
    dp = _date_parts(item)
    if not dp:
        return year_of(item, heb)
    if item.get("type") == "webpage" and len(dp) >= 2:
        month = (MONTHS_HE if heb else MONTHS)[int(dp[1]) - 1]
        if len(dp) >= 3:
            return f"{dp[0]}, {dp[2]} ב{month}" if heb else f"{dp[0]}, {month} {dp[2]}"
        return f"{dp[0]}, {month}"
    return str(dp[0])


def format_apa7(item: dict) -> str:
    heb = is_hebrew(item)
    t = item.get("type", "article-journal")
    authors = apa_authors(item.get("author") or [], heb)
    date = _apa_date(item, heb)
    title = (item.get("title") or "").strip()
    link = _doi_url(item)
    pages = _pages(item)
    container = (item.get("container-title") or "").strip()
    publisher = (item.get("publisher") or "").strip()

    if t == "article-journal":
        head = f"{authors} ({date}). " if authors else ""
        if not authors:
            head = f"{_end(title)} ({date}). "
            title = ""
        src = f"*{container}"
        if item.get("volume"):
            src += f", {item['volume']}*"
            if item.get("issue"):
                src += f"({item['issue']})"
        else:
            src += "*"
        if pages:
            src += f", {pages}"
        body = f"{head}{_end(title) + ' ' if title else ''}{src}."
    elif t == "book":
        head = f"{authors} ({date}). " if authors else ""
        body = f"{head}*{title}*." if authors else f"*{title}*. ({date})."
        if publisher:
            body += f" {publisher}."
    elif t == "chapter":
        editors = item.get("editor") or []
        ed_names = [f"{_initials(e.get('given', ''), heb)} {e.get('family', '')}".strip() for e in editors]
        if heb:
            ed_str = (", ".join(ed_names[:-1]) + " " + _vav(ed_names[-1])) if len(ed_names) > 1 else (ed_names[0] if ed_names else "")
            ed_label = "(עורכים)" if len(ed_names) > 1 else "(עורך)"
            inside = f"בתוך {ed_str} {ed_label}, " if ed_names else "בתוך "
            pp = f" (עמ' {pages})" if pages else ""
        else:
            ed_str = (", ".join(ed_names[:-1]) + ", & " + ed_names[-1]) if len(ed_names) > 2 else " & ".join(ed_names)
            ed_label = "(Eds.)" if len(ed_names) > 1 else "(Ed.)"
            inside = f"In {ed_str} {ed_label}, " if ed_names else "In "
            pp = f" (pp. {pages})" if pages else ""
        body = f"{authors} ({date}). {_end(title)} {inside}*{container}*{pp}."
        if publisher:
            body += f" {publisher}."
    elif t == "webpage":
        if authors:
            body = f"{authors} ({date}). *{title}*."
        else:
            body = f"*{title}*. ({date})."
        if container:
            body += f" {container}."
    elif t == "thesis":
        genre = (item.get("genre") or ("עבודת גמר" if heb else "Thesis")).strip()
        inst = publisher
        bracket = f" [{genre}, {inst}]" if inst else f" [{genre}]"
        body = f"{authors} ({date}). *{title}*{bracket}."
    else:
        body = f"{authors} ({date}). *{title}*." if authors else f"*{title}*. ({date})."
        if container:
            body += f" {container}."
        if publisher:
            body += f" {publisher}."
    if link:
        body += f" {link}"
    return body.strip()


# --------------------------------------------------------------------------------------------------
# IEEE
# --------------------------------------------------------------------------------------------------

def format_ieee(item: dict, n: int) -> str:
    heb = is_hebrew(item)
    t = item.get("type", "article-journal")
    authors = ieee_authors(item.get("author") or [], heb)
    year = year_of(item, heb)
    title = (item.get("title") or "").strip()
    container = (item.get("container-title") or "").strip()
    publisher = (item.get("publisher") or "").strip()
    place = (item.get("publisher-place") or "").strip()
    pages = _pages(item)
    vol, no, pp = ("כרך", "גיליון", "עמ'") if heb else ("vol.", "no.", "pp.")
    lead = f"[{n}] " + (f"{authors}, " if authors else "")

    if t == "article-journal":
        parts = [f"*{container}*"]
        if item.get("volume"):
            parts.append(f"{vol} {item['volume']}")
        if item.get("issue"):
            parts.append(f"{no} {item['issue']}")
        if pages:
            parts.append(f"{pp} {pages}")
        parts.append(year)
        if item.get("DOI"):
            parts.append(f"doi: {item['DOI']}")
        body = f'{lead}"{title}," ' + ", ".join(parts) + "."
    elif t == "book":
        pub = f"{place}: {publisher}" if place and publisher else (publisher or place)
        body = f"{lead}*{title}*. {pub + ', ' if pub else ''}{year}."
    elif t == "chapter":
        editors = item.get("editor") or []
        ed_names = [f"{_initials(e.get('given', ''), heb)} {e.get('family', '')}".strip() for e in editors]
        ed = ""
        if ed_names:
            ed = ", " + (" and ".join(ed_names) if len(ed_names) <= 2 else ", ".join(ed_names[:-1]) + ", and " + ed_names[-1])
            ed += ", Eds." if len(ed_names) > 1 else ", Ed."
        pub = f"{place}: {publisher}" if place and publisher else (publisher or place)
        body = f'{lead}"{title}," in *{container}*{ed} {pub + ", " if pub else ""}{year}{", " + pp + " " + pages if pages else ""}.'
    elif t == "webpage":
        dp = _date_parts(item)
        accessed = item.get("accessed", {}).get("date-parts", [[]])[0] if item.get("accessed") else []
        acc = ""
        if accessed and len(accessed) >= 3:
            acc = f" Accessed: {IEEE_MONTHS[int(accessed[1]) - 1]} {accessed[2]}, {accessed[0]}."
        site = f" {container}." if container else ""
        when = f" {year}." if dp else ""
        body = f'{lead}"{title}."{site}{when}{acc} [Online]. Available: {item.get("URL", "")}'.rstrip()
    elif t == "thesis":
        genre = (item.get("genre") or "Thesis").strip()
        genre_ieee = "Ph.D. dissertation" if re.search(r"doctor|ph\.?d", genre, re.I) else ("M.S. thesis" if re.search(r"master|m\.?s", genre, re.I) else genre)
        inst = ", ".join(x for x in (publisher, place) if x)
        body = f'{lead}"{title}," {genre_ieee}, {inst + ", " if inst else ""}{year}.'
    else:
        body = f"{lead}*{title}*. {container + ', ' if container else ''}{year}."
    return body.strip()


# --------------------------------------------------------------------------------------------------
# ordering and entry point
# --------------------------------------------------------------------------------------------------

def _sort_key_name(item: dict) -> str:
    authors = item.get("author") or []
    if authors:
        key = (authors[0].get("family") or authors[0].get("literal") or "")
    else:
        key = item.get("title") or ""
    return key.casefold()


def _translit(s: str) -> str:
    return "".join(TRANSLIT.get(ch, ch) for ch in s)


def sort_apa(items: list[dict], mixed: bool) -> list[dict]:
    def key(it):
        name = _sort_key_name(it)
        return (_translit(name) if mixed else name, year_of(it, is_hebrew(it)), (it.get("title") or "").casefold())
    if mixed:
        return sorted(items, key=key)
    latin = sorted([i for i in items if not is_hebrew(i)], key=key)
    heb = sorted([i for i in items if is_hebrew(i)], key=key)
    return latin + heb


def format_refs(items: list[dict], style: str, mixed: bool = False) -> list[str]:
    """Format CSL-JSON `items` in `style` ('apa7' or 'ieee'). APA output is sorted; IEEE keeps input order."""
    if style not in STYLES:
        raise ValueError(f"unknown style {style!r}; built-in styles: {', '.join(STYLES)} (use --csl for others)")
    if style == "apa7":
        return [format_apa7(i) for i in sort_apa(items, mixed)]
    return [format_ieee(i, n) for n, i in enumerate(items, 1)]


def format_with_csl(items: list[dict], csl_path: Path) -> list[str]:  # pragma: no cover - needs citeproc-py
    from citeproc import Citation, CitationItem, CitationStylesBibliography, CitationStylesStyle, formatter
    from citeproc.source.json import CiteProcJSON

    for n, it in enumerate(items):
        it.setdefault("id", f"ref{n}")
    source = CiteProcJSON(items)
    style = CitationStylesStyle(str(csl_path), validate=False)
    bib = CitationStylesBibliography(style, source, formatter.plain)
    for it in items:
        bib.register(Citation([CitationItem(it["id"])]))
    return [str(e) for e in bib.bibliography()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("refs", help="CSL-JSON file: a list of items")
    ap.add_argument("--style", choices=STYLES, default="apa7")
    ap.add_argument("--mixed", action="store_true", help="APA: interleave Hebrew and Latin entries by transliteration")
    ap.add_argument("--csl", help="CSL style file; used when citeproc-py is installed")
    ap.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = ap.parse_args(argv)

    def fail(msg: str, code: int) -> int:
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False) if args.json else msg,
              file=sys.stdout if args.json else sys.stderr)
        return code

    try:
        items = json.loads(Path(args.refs).read_text(encoding="utf-8"))
    except OSError as exc:
        return fail(f"cannot read {args.refs}: {exc.strerror or exc}", 2)
    except json.JSONDecodeError as exc:
        return fail(f"{args.refs} is not valid JSON: {exc}", 2)
    if isinstance(items, dict) and "items" in items:
        items = items["items"]
    if not isinstance(items, list):
        return fail("expected a JSON list of CSL-JSON items", 2)
    if args.csl:
        if not HAVE_CITEPROC:
            return fail("citeproc-py is not installed; run: pip install citeproc-py (or drop --csl for the built-in APA 7 / IEEE)", 2)
        entries = format_with_csl(items, Path(args.csl))
        style_name = Path(args.csl).stem
    else:
        entries = format_refs(items, args.style, mixed=args.mixed)
        style_name = args.style
    problems = [i for i, e in enumerate(entries) if not e or e.startswith("*.") or e.startswith(" (")]
    if args.json:
        print(json.dumps({"ok": not problems, "style": style_name, "entries": entries, "problems": problems}, ensure_ascii=False))
    else:
        for e in entries:
            print(e)
        for i in problems:
            print(f"item {i}: missing fields, check the entry", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
