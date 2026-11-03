#!/usr/bin/env python3
"""
Check Hebrew-with-English text for lines that would break right-to-left rendering.

A chat UI decides each paragraph's direction from the first "strong" letter it meets. If that
letter is Latin (an English word, a command, a path, a URL), the whole line flips to LTR and
punctuation jumps to the wrong side. This checker applies the skill's strict rule: after the
Markdown markers that start a line (#, -, *, 1., >, |, **, _), the first visible character must
be a Hebrew letter. Code blocks are skipped. Table rows are checked cell by cell.

Usage:
    python3 check_rtl.py FILE [FILE ...]      # or:  cat reply.md | python3 check_rtl.py -
    python3 check_rtl.py FILE --fix           # print a suggested rewrite for every failing line (file untouched)
Exit code: 0 = clean, 1 = violations found, 2 = usage. Use --json for machine-readable output.
"""
import json
import re
import sys

HEB = re.compile(r"[֐-׿יִ-ﭏ]")
LATIN = re.compile(r"[A-Za-z]")
FENCE = re.compile(r"^\s*(```|~~~)")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
# Markdown structure that renders as a marker, not as text
PREFIX = re.compile(r"^(?:\s+|#{1,6}\s+|>\s*|[-*+]\s+(?:\[[ xX]\]\s+)?|\d+[.)]\s+|\*\*|__|\*|_|~~)")


def strip_prefix(s: str) -> str:
    prev = None
    while prev != s:
        prev = s
        s = PREFIX.sub("", s, count=1)
    return s


def first_issue(text: str):
    """Return a description if `text` doesn't start with a Hebrew letter, else None."""
    body = strip_prefix(text)
    if not body.strip() or not any(c.isalpha() for c in body):
        return None  # nothing that can set a direction (e.g. a cell holding only "5" or "—")
    ch = body[0]
    if HEB.match(ch):
        return None
    if LATIN.match(ch):
        word = re.match(r"[\w.\-/]+", body)
        return f"starts with English '{word.group(0) if word else ch}'"
    if ch == "`":
        return "starts with inline code"
    if ch.isdigit():
        return "starts with a number"
    if ch in "[(":
        return f"starts with '{ch}' (link/parenthesis)"
    if ch in "\"'“”‘’«":
        return "starts with a quotation mark"
    if ch in "/~.\\":
        return "starts with a path"
    return f"starts with symbol {ch!r} (U+{ord(ch):04X})"


# --- suggestions (--fix) ----------------------------------------------------------------------------------
HEBREW_NUMBERS = {"1": "אחד", "2": "שני", "3": "שלושה", "4": "ארבעה", "5": "חמישה", "6": "שישה", "7": "שבעה",
                  "8": "שמונה", "9": "תשעה", "10": "עשרה"}
LABEL_WORDS = {"note": "הערה", "notes": "הערות", "input": "הקלט", "output": "הפלט", "pros": "יתרונות", "cons": "חסרונות",
               "example": "דוגמה", "examples": "דוגמאות", "result": "התוצאה", "results": "התוצאות", "summary": "סיכום",
               "warning": "אזהרה", "tip": "טיפ", "answer": "התשובה", "question": "השאלה", "step": "שלב", "goal": "המטרה",
               "setup": "ההתקנה", "usage": "השימוש", "before": "לפני", "after": "אחרי", "tl;dr": "בקצרה"}
TOKEN_RX = re.compile(r"^(?P<tok>`[^`]+`|https?://\S+|[~./\\][\w./~\\-]*|v?\d[\w.]*|[A-Za-z][\w.+#-]*)")


def _opener_for(token: str, rest: str) -> str | None:
    """Pick the Hebrew noun that naturally precedes an English token."""
    if token.startswith("`"):
        inner = token.strip("`")
        if "(" in inner or inner.endswith("()"):
            return "הפונקציה " + token
        if inner.startswith(("~", "/", "./", ".")) or "/" in inner or inner.startswith("."):
            return "הקובץ " + token
        return "הפקודה " + token
    if token.startswith("http"):
        return "הקישור " + token
    if token[0] in "~./\\":
        return "הקובץ `" + token + "`"
    m = re.match(r"^v?(\d+(?:\.\d+)+)$", token)
    if m:
        return "גרסה " + m.group(1)
    if token.isdigit():
        word = HEBREW_NUMBERS.get(token)
        return word if word else "יש " + token
    if re.match(r"^[A-Za-z]", token):
        if re.match(r"^\w+\(", rest) or rest.startswith("("):
            return "הפונקציה " + token
        return "ה-" + token
    return None


def suggest_fix(line: str) -> str | None:
    """Return a rewritten line that opens with Hebrew, or None when the line is already fine or has no safe fix.
    Never applied automatically: the writer chooses the wording; this is the first candidate."""
    if first_issue(line) is None:
        return None
    m = PREFIX.match(line)
    prefix = ""
    body = line
    while m and m.group(0):
        prefix += m.group(0)
        body = body[m.end():]
        m = PREFIX.match(body)
    # bold label at the start: **Note:** / **Train (10):**
    lab = re.match(r"^([^*\n]+?)(:?)\*\*(.*)$", body) if prefix.endswith(("**", "__")) else None
    if lab:
        label, colon, tail = lab.group(1), lab.group(2), lab.group(3)
        key = label.strip().lower().rstrip(":")
        heb = LABEL_WORDS.get(key)
        new_label = heb if heb else ("ה-" + label.strip())
        return f"{prefix}{new_label}{colon}**{tail}"
    t = TOKEN_RX.match(body)
    if not t:
        return None
    token = t.group("tok")
    rest = body[t.end():]
    # heading made of English words: suggest a Hebrew noun then the original words
    if prefix.lstrip().startswith("#") and re.match(r"^[A-Za-z][A-Za-z ]+$", body.strip()):
        return f"{prefix}עבודה עם {body.strip()}"
    opener = _opener_for(token, rest)
    if opener is None:
        return None
    rest = re.sub(r"^\s+(?:is|are|has|have|adds?|returns?|maps?|runs?|shows?|steps?)\b", "", rest)
    return f"{prefix}{opener}{rest}"


# An English run (optionally *emphasised*) followed by "(digits…)" inside a Hebrew line: renderers that isolate
# emphasis spans resolve the parentheses against the Hebrew context and the number jumps to the other side of
# the name ("ב-(2008) Iron Man"). Writing the number in a Hebrew phrase avoids it: "משנת 2008", "(שנת 2008)".
EN_THEN_NUMBER_PARENS = re.compile(r"[A-Za-z0-9][\w:'’.!?&+-]*[*_`]*\s*\(\s*\d[^)֐-׿]*\)")


def midline_issue(text: str):
    if HEB.search(text) and EN_THEN_NUMBER_PARENS.search(text):
        return "English name followed by a number in parentheses (it renders on the wrong side); write 'משנת 2008' or '(שנת 2008)'"
    return None


def ending_issue(text: str):
    """Warn when a line ends with an English token followed by punctuation (punctuation may jump)."""
    t = text.rstrip()
    if re.search(r"[A-Za-z0-9`)\]][.,:;!?]$", t) and HEB.search(t):
        return "ends with English/code + punctuation (punctuation may jump sides)"
    return None


def check(text: str):
    errors, warnings = [], []
    in_code = False
    lines = text.split("\n")
    for n, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code or not line.strip():
            continue
        if line.startswith("    ") and not strip_prefix(line).startswith(("-", "*")) and n > 1 and \
                (not lines[n - 2].strip() or lines[n - 2].startswith("    ")) and not HEB.search(line):
            continue  # indented code block
        stripped = line.strip()
        if stripped.startswith("|") or (stripped.count("|") >= 2 and not stripped.startswith(("-", "*", "#"))):
            if TABLE_SEP.match(stripped):
                continue
            cells = [c for c in stripped.strip("|").split("|")]
            for ci, cell in enumerate(cells, 1):
                if not cell.strip():
                    continue
                issue = first_issue(cell.strip())
                if issue:
                    errors.append({"line": n, "where": f"table cell {ci}", "issue": issue, "text": cell.strip()})
            continue
        if re.match(r"^\s*(<[^>]+>|!\[|---+\s*$|\*\*\*+\s*$)", line):
            if re.match(r"^\s*(---+|\*\*\*+)\s*$", line):
                continue
        issue = first_issue(line)
        if issue:
            errors.append({"line": n, "where": "line start", "issue": issue, "text": line.strip()})
        mid = midline_issue(line)
        if mid:
            errors.append({"line": n, "where": "mid-line", "issue": mid, "text": line.strip()})
        end = ending_issue(line)
        if end:
            warnings.append({"line": n, "where": "line end", "issue": end, "text": line.strip()})
    if in_code:
        warnings.append({"line": len(lines), "where": "file", "issue": "unclosed code fence", "text": ""})
    return errors, warnings


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    fix = "--fix" in sys.argv
    if not args:
        print(__doc__)
        sys.exit(2)
    total = 0
    out = {}
    for a in args:
        text = sys.stdin.read() if a == "-" else open(a, encoding="utf-8").read()
        errs, warns = check(text)
        total += len(errs)
        if fix:
            src_lines = text.split("\n")
            for e in errs:
                e["suggestion"] = suggest_fix(src_lines[e["line"] - 1]) if e["where"] == "line start" else None
        out[a] = {"errors": errs, "warnings": warns}
        if not as_json:
            print(f"== {a}: {len(errs)} errors, {len(warns)} warnings")
            for e in errs:
                print(f"  ERROR line {e['line']} ({e['where']}): {e['issue']}  ::  {e['text'][:90]}")
                if fix and e.get("suggestion"):
                    print(f"     → {e['suggestion'][:120]}")
            for w in warns:
                print(f"  warn  line {w['line']}: {w['issue']}  ::  {w['text'][:90]}")
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
