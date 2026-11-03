#!/usr/bin/env python3
"""Export a weekly plan (`plan.json` from plan_week.py) or a deadline list (`deadlines.json`) as an `.ics` file.

RFC 5545 output: CRLF line endings, `PRODID:-//academic-students//EN`, one VEVENT per study block or deadline
with UID (stable across exports, so re-importing updates instead of duplicating), DTSTAMP, DTSTART/DTEND in
UTC (`...Z` — the local times are converted with `zoneinfo`, so the Israel DST change in late October is
handled), SUMMARY and DESCRIPTION (course + source). Lines are folded at 75 octets without splitting a
UTF-8 character, so long Hebrew titles survive Google Calendar, Outlook and Apple Calendar.
A deadline becomes a zero-length event at the due time; a study block spans its start–end.

Usage:
    export_ics.py plan.json|deadlines.json [--out plan.ics] [--tz Asia/Jerusalem] [--name academic-students] [--json]

Exit codes: 0 = written · 2 = usage / unreadable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def escape_text(s: str) -> str:
    return (str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n"))


def fold(line: str) -> str:
    """Fold one content line at 75 octets; continuation lines start with a space (which counts)."""
    out, cur, size, limit = [], "", 0, 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > limit:
            out.append(cur)
            cur, size, limit = " ", 1, 75
        cur += ch
        size += n
    out.append(cur)
    return "\r\n".join(out)


def _utc(local: str, tz: ZoneInfo) -> str:
    dt = datetime.strptime(local[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=tz)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16] + "@academic-students"


def _events(plan_or_deadlines, tz: ZoneInfo) -> list[dict]:
    events = []
    if isinstance(plan_or_deadlines, dict) and "blocks" in plan_or_deadlines:
        for b in plan_or_deadlines["blocks"]:
            events.append({"uid": _uid("block", b["date"], b["start"], str(b.get("deadline_id", "")), b.get("task", "")),
                           "start": _utc(f"{b['date']}T{b['start']}", tz), "end": _utc(f"{b['date']}T{b['end']}", tz),
                           "summary": b.get("task", ""), "description": f"study block for {b.get('deadline_id', '')}"})
        return events
    items = plan_or_deadlines.get("deadlines", []) if isinstance(plan_or_deadlines, dict) else plan_or_deadlines
    for d in items:
        zone = ZoneInfo(d.get("tz") or tz.key)
        start = _utc(d["due"], zone)
        course = d.get("course") or ""
        summary = f"{d.get('title', '')} ({course})" if course else d.get("title", "")
        desc = f"{course} — {d.get('kind', '')} — source: {d.get('source', '')}"
        if d.get("conflict"):
            desc += f" — other times seen: {', '.join(d['conflict'])}"
        events.append({"uid": _uid("deadline", str(d.get("id", "")), course, d.get("title", "")),
                       "start": start, "end": start, "summary": summary, "description": desc})
    return events


def to_ics(plan_or_deadlines, tz: str = "Asia/Jerusalem", calendar_name: str = "academic-students",
           dtstamp: datetime | None = None) -> str:
    zone = ZoneInfo(tz)
    stamp = (dtstamp or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//academic-students//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{escape_text(calendar_name)}"]
    for ev in _events(plan_or_deadlines, zone):
        lines += ["BEGIN:VEVENT", f"UID:{ev['uid']}", f"DTSTAMP:{stamp}", f"DTSTART:{ev['start']}",
                  f"DTEND:{ev['end']}", f"SUMMARY:{escape_text(ev['summary'])}",
                  f"DESCRIPTION:{escape_text(ev['description'])}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "".join(fold(ln) + "\r\n" for ln in lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="plan.json or deadlines.json")
    parser.add_argument("--out", default="plan.ics")
    parser.add_argument("--tz", default="Asia/Jerusalem")
    parser.add_argument("--name", default="academic-students", help="calendar name shown by the client")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.source).read_text(encoding="utf-8"))
        text = to_ics(data, tz=args.tz, calendar_name=args.name)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_bytes(text.encode("utf-8"))
    n = text.count("BEGIN:VEVENT")
    if args.json:
        print(json.dumps({"out": args.out, "events": n}, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {n} event(s). Import it in Google Calendar (Settings → Import) or open it in Outlook/Apple Calendar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
