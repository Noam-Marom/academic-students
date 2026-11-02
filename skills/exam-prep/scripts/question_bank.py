#!/usr/bin/env python3
"""Maintain a JSON bank of exam questions, deduplicated by normalised text.

Two past exams often carry the same question under a different number, with different whitespace,
or with and without nikud. The bank keys every question by the SHA-1 of its normalised text
(nikud stripped, leading numbering removed, punctuation dropped, whitespace collapsed, lower-cased),
so the same question is stored once and its frequency across years is visible in `stats`.

Bank shape (`bank.json`):
    {"questions": [{"id": str, "text": str, "topic": str|null, "type": str|null,
                    "difficulty": 1..5|null, "points": number|null, "year": int|null,
                    "source": str, "solution": str|null}]}

Usage:
    question_bank.py add   bank.json q.json [q2.json ...]   # q.json = one question object or a list
    question_bank.py stats bank.json [--json]
    question_bank.py list  bank.json [--topic T] [--year Y] [--json]

Exit codes: 0 = done · 1 = at least one question was a duplicate (add) · 2 = usage / unreadable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

FIELDS = ("id", "text", "topic", "type", "difficulty", "points", "year", "source", "solution")

# Hebrew points and cantillation marks (nikud, te'amim) live in U+0591..U+05C7 as combining marks.
_NIKUD = re.compile(r"[֑-ׇ]")
# "1.", "1)", "(1)", "א.", "א)", "(א)", "Q1", "שאלה 3", "Question 2:" at the start of a line
_NUMBERING = re.compile(
    r"^\s*(?:\(?(?:\d{1,3}|[a-zA-Z]|[א-ת]{1,2})[.)]\s*|(?:q|question|שאלה)\s*\d{1,3}\s*[.:)]?\s+)",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Return the dedupe key text: no nikud, no leading numbering, no punctuation, single spaces, lower case."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = _NIKUD.sub("", t)
    lines = [_NUMBERING.sub("", ln) for ln in t.splitlines()]
    t = " ".join(lines)
    t = _PUNCT.sub(" ", t)
    t = _WS.sub(" ", t).strip().lower()
    return t


def question_id(text: str) -> str:
    return hashlib.sha1(normalise(text).encode("utf-8")).hexdigest()[:10]


def _complete(q: dict) -> dict:
    """Return a question dict with every bank field present (missing ones → None) and its id set."""
    out = {k: q.get(k) for k in FIELDS}
    out["text"] = str(q.get("text", "")).strip()
    out["source"] = str(q.get("source", "") or "")
    out["id"] = question_id(out["text"])
    return out


def add(bank: dict, q: dict) -> bool:
    """Add `q` to `bank` (in place). Return False, and change nothing, when its normalised text is already there."""
    bank.setdefault("questions", [])
    item = _complete(q)
    if not item["text"]:
        raise ValueError("question has no text")
    if any(existing.get("id") == item["id"] for existing in bank["questions"]):
        return False
    bank["questions"].append(item)
    return True


def stats(bank: dict) -> dict:
    """Group count, total points and the sorted years per topic; count questions without a topic."""
    by_topic: dict[str, dict] = {}
    untagged = 0
    for q in bank.get("questions", []):
        topic = q.get("topic")
        if not topic:
            untagged += 1
            continue
        entry = by_topic.setdefault(topic, {"count": 0, "points": 0, "years": []})
        entry["count"] += 1
        if isinstance(q.get("points"), (int, float)):
            entry["points"] += q["points"]
        if q.get("year") is not None and q["year"] not in entry["years"]:
            entry["years"].append(q["year"])
    for entry in by_topic.values():
        entry["years"].sort()
    return {"by_topic": by_topic, "untagged": untagged}


def select(bank: dict, topic: str | None = None, year: int | None = None) -> list[dict]:
    out = []
    for q in bank.get("questions", []):
        if topic is not None and q.get("topic") != topic:
            continue
        if year is not None and q.get("year") != year:
            continue
        out.append(q)
    return out


def load_bank(path: Path) -> dict:
    if not path.exists():
        return {"questions": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise ValueError(f"{path} is not a question bank")
    return data


def save_bank(path: Path, bank: dict) -> None:
    path.write_text(json.dumps(bank, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _load_questions(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    return data if isinstance(data, list) else [data]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")
    p_add = sub.add_parser("add", help="add questions to the bank (creates it when missing)")
    p_add.add_argument("bank")
    p_add.add_argument("questions", nargs="+")
    p_add.add_argument("--json", action="store_true")
    p_stats = sub.add_parser("stats", help="count, points and years per topic")
    p_stats.add_argument("bank")
    p_stats.add_argument("--json", action="store_true")
    p_list = sub.add_parser("list", help="list questions, optionally filtered")
    p_list.add_argument("bank")
    p_list.add_argument("--topic")
    p_list.add_argument("--year", type=int)
    p_list.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_usage()
        return 2

    bank_path = Path(args.bank)
    try:
        if args.cmd == "add":
            bank = load_bank(bank_path)
            added, dups = [], []
            for qp in args.questions:
                for q in _load_questions(Path(qp)):
                    (added if add(bank, q) else dups).append(q.get("text", "")[:60])
            save_bank(bank_path, bank)
            if args.json:
                print(json.dumps({"added": len(added), "duplicates": len(dups), "total": len(bank["questions"])}, ensure_ascii=False))
            else:
                print(f"added {len(added)}, duplicates {len(dups)}, bank now holds {len(bank['questions'])} question(s)")
                for d in dups:
                    print(f"  duplicate: {d}")
            return 1 if dups else 0
        if not bank_path.exists():
            print(f"no such bank: {bank_path}", file=sys.stderr)
            return 2
        bank = load_bank(bank_path)
        if args.cmd == "stats":
            s = stats(bank)
            if args.json:
                print(json.dumps(s, ensure_ascii=False))
            else:
                print(f"{'topic':<30} {'count':>5} {'points':>7}  years")
                for topic, e in sorted(s["by_topic"].items(), key=lambda kv: (-kv[1]["points"], kv[0])):
                    print(f"{topic:<30} {e['count']:>5} {e['points']:>7}  {', '.join(str(y) for y in e['years'])}")
                print(f"untagged: {s['untagged']}")
            return 0
        if args.cmd == "list":
            items = select(bank, topic=args.topic, year=args.year)
            if args.json:
                print(json.dumps(items, ensure_ascii=False))
            else:
                for q in items:
                    print(f"[{q['id']}] ({q.get('topic') or '-'}, {q.get('points') or '?'} pts, {q.get('year') or '?'}) {q['text'][:100]}")
                print(f"{len(items)} question(s)")
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
