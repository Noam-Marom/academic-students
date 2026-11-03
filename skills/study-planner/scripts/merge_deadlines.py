#!/usr/bin/env python3
"""Merge deadlines from Moodle/Google `.ics` exports, `deadlines.json` files and `COURSE.md` profiles.

Output (`deadlines.json`), sorted by due time:
    [{"id": str, "course": str, "title": str, "due": "YYYY-MM-DDTHH:MM", "tz": "Asia/Jerusalem",
      "kind": "assignment|exam|quiz|other", "source": str, "weight": number|null, "estimate_hours": number|null,
      "conflict": ["YYYY-MM-DDTHH:MM", ...]   # only when sources disagree on the time}]

Sources:
  * `.ics` — every VEVENT: SUMMARY → title (a trailing "is due" is dropped), DTSTART → due (UTC `Z`, `TZID=`,
    floating, or an all-day `VALUE=DATE`, which means 23:59 that day), UID → id, CATEGORIES → course.
  * `.json` — already in the shape above (a list, or {"deadlines": [...]}).
  * `COURSE.md` — the frontmatter `deadlines:` list (`title`, `due`, `kind`, optional `weight`/`estimate_hours`);
    the frontmatter `course` names the course.
Duplicates share (normalised course, normalised title, due date). The earliest time is kept and the other
times go to `conflict`, so a disagreement between Moodle and the syllabus is shown, never silently dropped.

Usage:
    merge_deadlines.py SOURCE [SOURCE ...] [--out deadlines.json] [--tz Asia/Jerusalem] [--json]

Exit codes: 0 = written · 2 = usage / unreadable or unsupported source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Jerusalem"
FIELDS = ("id", "course", "title", "due", "tz", "kind", "source", "weight", "estimate_hours")
_KIND_PATTERNS = [
    ("exam", re.compile(r"\b(exam|midterm|final)\b|מבחן|מועד|בחינה", re.I)),
    ("quiz", re.compile(r"\bquiz\b|בוחן", re.I)),
    ("assignment", re.compile(r"\b(hw|homework|assignment|project|report|lab|is due)\b|\bhw\d|תרגיל|מטלה|הגשה|עבודה", re.I)),
]


def guess_kind(title: str) -> str:
    for kind, pat in _KIND_PATTERNS:
        if pat.search(title or ""):
            return kind
    return "other"


def _norm(s: str) -> str:
    s = re.sub(r"[֑-ׇ]", "", str(s or "")).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _make(course, title, due, kind, source, id_=None, weight=None, estimate=None, tz=DEFAULT_TZ) -> dict:
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    course = str(course or "").strip()
    kind = kind if kind in ("assignment", "exam", "quiz", "other") else guess_kind(title)
    if not id_:
        id_ = hashlib.sha1(f"{_norm(course)}|{_norm(title)}|{due}".encode("utf-8")).hexdigest()[:10]
    return {"id": str(id_), "course": course, "title": title, "due": due, "tz": tz, "kind": kind,
            "source": source, "weight": weight, "estimate_hours": estimate}


# --- .ics ------------------------------------------------------------------------------------------

def _unfold(text: str) -> list[str]:
    out: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _ics_text(v: str) -> str:
    return v.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _ics_due(value: str, params: dict, tz: ZoneInfo) -> str:
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}T23:59"
    m = re.fullmatch(r"(\d{8})T(\d{4})(\d{2})?(Z?)", value)
    if not m:
        raise ValueError(f"unreadable DTSTART {value!r}")
    naive = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M")
    if m.group(4) == "Z":
        aware = naive.replace(tzinfo=timezone.utc)
    elif "TZID" in params:
        aware = naive.replace(tzinfo=ZoneInfo(params["TZID"].strip('"')))
    else:
        aware = naive.replace(tzinfo=tz)
    return aware.astimezone(tz).strftime("%Y-%m-%dT%H:%M")


def parse_ics(path: Path, tz_name: str = DEFAULT_TZ) -> list[dict]:
    tz = ZoneInfo(tz_name)
    items, event = [], None
    for line in _unfold(path.read_text(encoding="utf-8-sig", errors="replace")):
        if line == "BEGIN:VEVENT":
            event = {}
            continue
        if line == "END:VEVENT" and event is not None:
            if "DTSTART" in event and "SUMMARY" in event:
                title = re.sub(r"\s+(is due|due)$", "", _ics_text(event["SUMMARY"][0]).strip(), flags=re.I)
                course = _ics_text(event.get("CATEGORIES", ("", {}))[0]).split(",")[0].strip()
                due = _ics_due(event["DTSTART"][0], event["DTSTART"][1], tz)
                items.append(_make(course, title, due, None, path.name, id_=event.get("UID", ("", {}))[0], tz=tz_name))
            event = None
            continue
        if event is None or ":" not in line:
            continue
        head, value = line.split(":", 1)
        name, *raw_params = head.split(";")
        params = dict(p.split("=", 1) for p in raw_params if "=" in p)
        event[name.upper()] = (value.strip(), {k.upper(): v for k, v in params.items()})
    return items


# --- COURSE.md -------------------------------------------------------------------------------------

def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(m.group(1)) or {}
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _mini_yaml(m.group(1))


def _scalar(v: str):
    v = v.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return float(v) if "." in v else int(v)
    return None if v in ("", "null", "~") else v


def _pairs(s: str) -> dict:
    out = {}
    for part in re.findall(r'(\w+)\s*:\s*("[^"]*"|\'[^\']*\'|[^,}]*)', s):
        out[part[0]] = _scalar(part[1])
    return out


def _mini_yaml(block: str) -> dict:
    """Stdlib fallback when PyYAML is absent: top-level scalars and a `deadlines:` list (flow or block style)."""
    data: dict = {}
    lines = block.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^(\w+):\s*(.*?)\s*(#.*)?$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        if key == "deadlines":
            if val.startswith("["):
                data[key] = [_pairs(x) for x in re.findall(r"\{([^}]*)\}", val)]
            else:
                items, cur = [], None
                for sub in lines[i + 1:]:
                    if sub and not sub.startswith((" ", "-")):
                        break
                    s = sub.strip()
                    if s.startswith("- "):
                        cur = {}
                        items.append(cur)
                        s = s[2:]
                    if cur is not None and ":" in s:
                        cur.update(_pairs(s))
                data[key] = items
        else:
            data[key] = _scalar(val)
    return data


def parse_course_md(path: Path, tz_name: str = DEFAULT_TZ) -> list[dict]:
    fm = _frontmatter(path.read_text(encoding="utf-8"))
    course = fm.get("course") or fm.get("code") or path.parent.name
    out = []
    for d in fm.get("deadlines") or []:
        if not isinstance(d, dict) or not d.get("title") or not d.get("due"):
            continue
        due = str(d["due"])
        due = due + "T23:59" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", due) else due[:16]
        out.append(_make(course, d["title"], due, d.get("kind"), str(path), weight=d.get("weight"),
                         estimate=d.get("estimate_hours"), tz=tz_name))
    return out


# --- json + merge ----------------------------------------------------------------------------------

def parse_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("deadlines", [])
    out = []
    for d in data:
        item = {k: d.get(k) for k in FIELDS}
        item["tz"] = item["tz"] or DEFAULT_TZ
        item["source"] = item["source"] or path.name
        item["kind"] = item["kind"] if item["kind"] in ("assignment", "exam", "quiz", "other") else guess_kind(item["title"])
        item["due"] = str(item["due"])[:16]
        if not item["id"]:
            item["id"] = _make(item["course"], item["title"], item["due"], item["kind"], "")["id"]
        if d.get("conflict"):
            item["conflict"] = list(d["conflict"])
        out.append(item)
    return out


def load(path: Path, tz_name: str = DEFAULT_TZ) -> list[dict]:
    path = Path(path)
    if path.suffix.lower() == ".ics":
        return parse_ics(path, tz_name)
    if path.suffix.lower() == ".json":
        return parse_json(path)
    if path.suffix.lower() == ".md":
        return parse_course_md(path, tz_name)
    raise ValueError(f"unsupported source {path.name}: give .ics, .json or COURSE.md")


def merge(sources: list[Path], tz_name: str = DEFAULT_TZ) -> list[dict]:
    """Load every source and deduplicate on (course, title, due date); see the module docstring."""
    groups: dict[tuple, list[dict]] = {}
    for src in sources:
        for d in load(Path(src), tz_name):
            key = (_norm(d["course"]), _norm(d["title"]), d["due"][:10])
            groups.setdefault(key, []).append(d)
    merged = []
    for items in groups.values():
        items.sort(key=lambda x: x["due"])
        keep = dict(items[0])
        times = sorted({x["due"] for x in items} | set(keep.get("conflict", [])))
        others = [t for t in times if t != keep["due"]]
        for other in items[1:]:
            for k in ("weight", "estimate_hours", "course"):
                if keep.get(k) in (None, "") and other.get(k) not in (None, ""):
                    keep[k] = other[k]
            if other["source"] not in keep["source"].split("; "):
                keep["source"] += "; " + other["source"]
        if others:
            keep["conflict"] = others
        else:
            keep.pop("conflict", None)
        merged.append(keep)
    return sorted(merged, key=lambda x: (x["due"], x["course"], x["title"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--out", default="deadlines.json")
    parser.add_argument("--tz", default=DEFAULT_TZ)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        items = merge([Path(s) for s in args.sources], args.tz)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    conflicts = [d for d in items if d.get("conflict")]
    if args.json:
        print(json.dumps({"out": args.out, "deadlines": len(items), "conflicts": len(conflicts)}, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(items)} deadline(s), {len(conflicts)} with conflicting times")
        for d in conflicts:
            print(f"  conflict: {d['course']} {d['title']}: {d['due']} vs {', '.join(d['conflict'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
