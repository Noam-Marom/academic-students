#!/usr/bin/env python3
"""Bin deadline work and review sessions into the student's real availability for one week.

Inputs: `deadlines.json` (from merge_deadlines.py), an availability file
`{"YYYY-MM-DD": [["HH:MM", "HH:MM"], ...]}` (free slots per day), the week's first day, and optionally
`review-dates.json` from exam-prep (`[{"course", "topic", "dates": [...]}]`).
Output (`plan.json`):
    {"blocks":   [{"date", "start", "end", "task", "deadline_id"}],
     "overflow": [{"deadline_id", "hours_unplaced"}]}

Rules: review dates inside the week become 1-hour blocks first (they are fixed to a day). Then deadlines,
earliest due first: each needs `estimate_hours` (default 3 for an assignment, 8 for an exam, 2 for a quiz or
other); a deadline due after this week gets only this week's proportional share. Work is spread across the
days before the due time — at most one block of up to 2 h per deadline per day per pass — with a minimum block
of 1 h. Blocks never overlap and never leave the free slots; whatever does not fit is listed in `overflow`,
never silently dropped. Deadlines already past are ignored.

Usage:
    plan_week.py deadlines.json availability.json --week-start YYYY-MM-DD [--review-dates review-dates.json]
                 [--out plan.json] [--json]

Exit codes: 0 = everything placed · 1 = overflow (some hours did not fit) · 2 = usage / unreadable input.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_HOURS = {"assignment": 3, "exam": 8, "quiz": 2, "other": 2}
MIN_BLOCK = 60
MAX_BLOCK = 120


def _m(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


class _Day:
    """Free intervals of one day, in minutes; `take` carves a block out of them."""

    def __init__(self, slots):
        self.free = sorted([_m(a), _m(b)] for a, b in slots if _m(b) > _m(a))

    def first_fit(self, need: int, limit: int | None = None) -> tuple[int, int] | None:
        for a, b in self.free:
            end = min(b, limit) if limit is not None else b
            if end - a >= need:
                return a, end
        return None

    def take(self, start: int, end: int) -> None:
        out = []
        for a, b in self.free:
            if end <= a or b <= start:
                out.append([a, b])
                continue
            if a < start:
                out.append([a, start])
            if end < b:
                out.append([end, b])
        self.free = out


def _hours_needed(d: dict, week_start: date, due: datetime) -> float:
    est = d.get("estimate_hours")
    total = float(est) if isinstance(est, (int, float)) and est > 0 else float(DEFAULT_HOURS.get(d.get("kind"), 2))
    days_to_due = (due.date() - week_start).days + 1
    if days_to_due > 7:  # back-planning: only this week's share of a later deadline
        total = math.ceil(total * 7 / days_to_due * 2) / 2
    return total


def plan_week(deadlines: list[dict], availability: dict, week_start: str, review_dates: list[dict] | None = None) -> dict:
    start = date.fromisoformat(week_start)
    week = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    days = {d: _Day(availability.get(d, [])) for d in week}
    blocks: list[dict] = []
    overflow: list[dict] = []

    for r in review_dates or []:
        for day in r.get("dates", []):
            if day not in days:
                continue
            rid = f"review:{r.get('course', '')}:{r.get('topic', '')}:{day}"
            fit = days[day].first_fit(MIN_BLOCK)
            if fit is None:
                overflow.append({"deadline_id": rid, "hours_unplaced": 1})
                continue
            s, e = fit[0], fit[0] + MIN_BLOCK
            days[day].take(s, e)
            blocks.append({"date": day, "start": _hhmm(s), "end": _hhmm(e),
                           "task": f"Review: {r.get('topic', '')} ({r.get('course', '')})", "deadline_id": rid})

    week_start_dt = datetime.combine(start, datetime.min.time())
    live = []
    for d in deadlines:
        due = datetime.strptime(str(d["due"])[:16], "%Y-%m-%dT%H:%M")
        if due > week_start_dt:
            live.append((due, str(d.get("id")), d))
    live.sort(key=lambda x: (x[0], x[1]))

    for due, did, d in live:
        remaining = round(_hours_needed(d, start, due) * 60)
        eligible = [day for day in week if day <= due.date().isoformat()]
        progress = True
        while remaining > 0 and progress:
            progress = False
            for day in eligible:
                if remaining <= 0:
                    break
                limit = _m(due.strftime("%H:%M")) if day == due.date().isoformat() else None
                fit = days[day].first_fit(MIN_BLOCK, limit)
                if fit is None:
                    continue
                length = min(max(remaining, MIN_BLOCK), MAX_BLOCK, fit[1] - fit[0])
                s, e = fit[0], fit[0] + length
                days[day].take(s, e)
                remaining -= length
                progress = True
                title = d.get("title", did)
                blocks.append({"date": day, "start": _hhmm(s), "end": _hhmm(e),
                               "task": f"{d.get('course', '')}: {title}".strip(": "), "deadline_id": did})
        if remaining > 0:
            overflow.append({"deadline_id": did, "hours_unplaced": round(remaining / 60, 2)})

    blocks.sort(key=lambda b: (b["date"], b["start"]))
    return {"blocks": blocks, "overflow": overflow}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deadlines")
    parser.add_argument("availability")
    parser.add_argument("--week-start", required=True)
    parser.add_argument("--review-dates")
    parser.add_argument("--out", default="plan.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        deadlines = json.loads(Path(args.deadlines).read_text(encoding="utf-8"))
        availability = json.loads(Path(args.availability).read_text(encoding="utf-8"))
        reviews = json.loads(Path(args.review_dates).read_text(encoding="utf-8")) if args.review_dates else None
        plan = plan_week(deadlines, availability, args.week_start, reviews)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    over = sum(o["hours_unplaced"] for o in plan["overflow"])
    if args.json:
        print(json.dumps({"out": args.out, "blocks": len(plan["blocks"]), "overflow_hours": over,
                          "overflow": plan["overflow"]}, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(plan['blocks'])} block(s); {over:g} hour(s) did not fit")
        for o in plan["overflow"]:
            print(f"  overflow: {o['deadline_id']} — {o['hours_unplaced']:g} h unplaced")
    return 1 if plan["overflow"] else 0


if __name__ == "__main__":
    sys.exit(main())
