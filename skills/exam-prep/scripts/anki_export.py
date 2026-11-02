#!/usr/bin/env python3
"""Export flashcards to the text format Anki imports (File → Import), Hebrew-safe, with MathJax formulas.

Input: a JSON list of cards `[{"front": str, "back": str, "tags": [str, ...]?}, ...]`.
Output: UTF-8 text, one card per line, fields separated by tabs, with Anki's header directives
(`#separator:tab`, `#html:true`, and `#tags column:3` when any card has tags). Inside a field:
newlines become `<br>`, tabs become four spaces, `$...$` becomes `\\(...\\)` and `$$...$$` becomes
`\\[...\\]` (Anki renders MathJax with those delimiters; a literal `$` would show as text).
Hebrew passes through untouched: Anki stores Unicode and renders each field's direction on its own.

Usage:
    anki_export.py cards.json --out cards.txt [--json]

Exit codes: 0 = written · 2 = usage / a card without front or back.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_DISPLAY = re.compile(r"\$\$(.+?)\$\$", re.S)
_INLINE = re.compile(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", re.S)


def convert_math(text: str) -> str:
    """`$$x$$` → `\\[x\\]`, `$x$` → `\\(x\\)`; display math first so its dollars are not read as two inline pairs."""
    text = _DISPLAY.sub(lambda m: "\\[" + m.group(1).strip() + "\\]", text)
    text = _INLINE.sub(lambda m: "\\(" + m.group(1).strip() + "\\)", text)
    return text


def clean_field(text: str) -> str:
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = convert_math(text)
    text = text.replace("\t", "    ")
    return text.replace("\n", "<br>")


def to_anki(cards: list[dict]) -> str:
    """Return the full import file text (header directives + one line per card)."""
    for i, c in enumerate(cards):
        if not isinstance(c, dict) or not str(c.get("front", "")).strip() or not str(c.get("back", "")).strip():
            raise ValueError(f"card {i} needs a non-empty front and back")
    with_tags = any(c.get("tags") for c in cards)
    lines = ["#separator:tab", "#html:true"]
    if with_tags:
        lines.append("#tags column:3")
    for c in cards:
        row = [clean_field(c["front"]), clean_field(c["back"])]
        if with_tags:
            tags = c.get("tags") or []
            row.append(" ".join(str(t).replace(" ", "_") for t in tags))
        lines.append("\t".join(row))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cards", help="JSON list of {front, back, tags?}")
    parser.add_argument("--out", default="cards.txt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        cards = json.loads(Path(args.cards).read_text(encoding="utf-8"))
        if isinstance(cards, dict) and "cards" in cards:
            cards = cards["cards"]
        if not isinstance(cards, list):
            raise ValueError("cards file must hold a JSON list")
        text = to_anki(cards)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(text, encoding="utf-8")
    if args.json:
        print(json.dumps({"out": args.out, "cards": len(cards)}, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(cards)} card(s). In Anki: File → Import, pick the deck, field separator is detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
