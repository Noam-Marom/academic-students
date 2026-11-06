#!/usr/bin/env python3
"""Split an assignment map among N group members — in parallel, as a serial relay, or chosen automatically.

    python3 split_work.py map.json --people 3 [--mode auto|parallel|serial] [--total-hours 20] [--json]

Input is the assignment map (schemas/assignment-map.schema.json). Each part's effort is its `estimate_hours`;
when missing it is the part's share of `--total-hours` by `weight`, or 2 hours.

Modes:
  parallel  list scheduling: the part with the longest remaining dependency chain goes first, to the member
            who is free earliest, never before the parts it depends on are done.
  serial    a relay: parts in dependency order, cut into N contiguous stages of about equal hours; member k
            starts when member k-1 hands over. Right for work that is one long chain (an essay, a pipeline).
  auto      serial when the parts form a single chain, parallel otherwise.

Every plan ends with an integration review (≥ 1 h, ~10% of the work) owned by the least-loaded member: one
person reads everything end to end for consistency of notation, style and references.

Exit codes: 0 plan produced, 2 usage error or an invalid map (unknown dependency, cycle).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_HOURS = 2.0


def _hours(questions: list[dict], total_hours: float | None) -> dict[str, float]:
    weights = [float(q.get("weight") or 0) for q in questions]
    wsum = sum(weights)
    out = {}
    for q, w in zip(questions, weights):
        if q.get("estimate_hours") is not None:
            out[q["id"]] = float(q["estimate_hours"])
        elif total_hours and wsum > 0:
            out[q["id"]] = round(total_hours * w / wsum, 2)
        else:
            out[q["id"]] = DEFAULT_HOURS
    return out


def _topo(questions: list[dict]) -> list[str]:
    ids = [q["id"] for q in questions]
    deps = {q["id"]: list(q.get("depends_on") or []) for q in questions}
    for i, ds in deps.items():
        for d in ds:
            if d not in deps:
                raise ValueError(f"part {i!r} depends on unknown part {d!r}")
    order, state = [], {}

    def visit(n, stack):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError("dependency cycle: " + " -> ".join(stack + [n]))
        state[n] = 1
        for d in deps[n]:
            visit(d, stack + [n])
        state[n] = 2
        order.append(n)

    for n in ids:
        visit(n, [])
    return order


def _critical_path(order, deps, hours):
    best, prev = {}, {}
    for n in order:
        p = max(deps[n], key=lambda d: best[d], default=None)
        best[n] = hours[n] + (best[p] if p is not None else 0)
        prev[n] = p
    end = max(order, key=lambda n: best[n])
    path = []
    while end is not None:
        path.append(end)
        end = prev[end]
    return path[::-1], max(best.values())


def _bottom_levels(order, deps, hours):
    children = {n: [] for n in order}
    for n in order:
        for d in deps[n]:
            children[d].append(n)
    level = {}
    for n in reversed(order):
        level[n] = hours[n] + max((level[c] for c in children[n]), default=0)
    return level


def _is_chain(order, deps):
    return all(deps[order[i]] == [order[i - 1]] for i in range(1, len(order))) and not deps[order[0]]


def split(amap: dict, people: int, mode: str = "auto", total_hours: float | None = None) -> dict:
    if people < 1:
        raise ValueError("people must be at least 1")
    questions = amap["questions"]
    order = _topo(questions)
    deps = {q["id"]: list(q.get("depends_on") or []) for q in questions}
    hours = _hours(questions, total_hours)
    if mode == "auto":
        mode = "serial" if len(order) > 1 and _is_chain(order, deps) else "parallel"
    if mode not in ("parallel", "serial"):
        raise ValueError(f"unknown mode {mode!r}")

    schedule: list[dict] = []
    free = {m: 0.0 for m in range(1, people + 1)}
    if mode == "parallel":
        level = _bottom_levels(order, deps, hours)
        end_of: dict[str, float] = {}
        pending = list(order)
        while pending:
            ready = [n for n in pending if all(d in end_of for d in deps[n])]
            n = max(ready, key=lambda x: (level[x], -order.index(x)))
            ready_at = max((end_of[d] for d in deps[n]), default=0.0)
            m = min(free, key=lambda k: (max(free[k], ready_at), free[k], k))
            start = max(free[m], ready_at)
            end_of[n] = start + hours[n]
            free[m] = end_of[n]
            schedule.append({"part": n, "member": m, "start": round(start, 2), "end": round(end_of[n], 2)})
            pending.remove(n)
    else:
        total = sum(hours[n] for n in order)
        target = total / people
        t, cum, member = 0.0, 0.0, 1
        for n in order:
            # move to the next member when this part's midpoint falls past the current member's share
            if member < people and cum + hours[n] / 2 > target * member:
                member += 1
            schedule.append({"part": n, "member": member, "start": round(t, 2), "end": round(t + hours[n], 2)})
            t += hours[n]
            cum += hours[n]
            free[member] = t

    members = []
    for m in range(1, people + 1):
        parts = [s["part"] for s in schedule if s["member"] == m]
        members.append({"member": m, "parts": parts, "hours": round(sum(hours[p] for p in parts), 2)})
    total = sum(hours.values())
    owner = min(members, key=lambda x: (x["hours"], x["member"]))["member"]
    integ_hours = max(1.0, round(0.1 * total, 1))
    work_end = max(s["end"] for s in schedule)
    path, path_hours = _critical_path(order, deps, hours)
    warnings = []
    if people > len(order):
        warnings.append(f"more people than parts ({people} > {len(order)}): pair up on the largest parts or split them")
    if mode == "serial" and people > 1:
        warnings.append("serial relay: members wait for each other; agree on hand-over dates")
    return {
        "mode": mode,
        "people": people,
        "members": members,
        "schedule": schedule,
        "critical_path": path,
        "critical_path_hours": round(path_hours, 2),
        "integration": {"member": owner, "hours": integ_hours,
                        "task": "read the whole submission end to end: one notation, one style, one reference list"},
        "makespan_hours": round(work_end + integ_hours, 2),
        "total_hours": round(total, 2),
        "warnings": warnings,
    }


def _print_plan(plan: dict) -> None:
    print(f"mode: {plan['mode']}, people: {plan['people']}, total {plan['total_hours']} h, "
          f"finished after {plan['makespan_hours']} h (critical path {' -> '.join(plan['critical_path'])}, "
          f"{plan['critical_path_hours']} h)")
    for m in plan["members"]:
        print(f"  member {m['member']}: {', '.join(m['parts']) or '—'}  ({m['hours']} h)")
    i = plan["integration"]
    print(f"  integration review: member {i['member']} ({i['hours']} h)")
    for w in plan["warnings"]:
        print("  ! " + w)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map")
    ap.add_argument("--people", type=int, required=True)
    ap.add_argument("--mode", default="auto", choices=["auto", "parallel", "serial"])
    ap.add_argument("--total-hours", type=float)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        plan = split(json.loads(Path(a.map).read_text(encoding="utf-8")), a.people, a.mode, a.total_hours)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"split_work: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(plan, ensure_ascii=False, indent=1))
    else:
        _print_plan(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
