#!/usr/bin/env python3
"""The arithmetic of a grade estimate, so no total is ever added up in prose.

    python3 score_rubric.py rubric-scores.json [--json]

Input:
    {"criteria": [{"id": "q1", "name": "Correctness", "max": 30, "passes": [22, 24]}, ...],
     "penalties": [{"reason": "late 1 day", "points": 5} | {"percent": 10} | {"cap": 60}],
     "scale": {"max": 100, "pass": 56}}

`passes` holds the score each independent grading pass gave the criterion (one or more). The criterion's
score is their mean, its range is [min, max]. Passes that differ by more than 15% of the criterion's
maximum are a disagreement: re-read the evidence and reconcile before reporting.

The raw total is normalised to `scale.max` (default 100), then penalties apply in order: `points` subtracts
on the final scale, `percent` takes that share of the grade, `cap` limits the grade. Never below 0.

Exit codes: 0 scored, 1 scored but passes disagree (reconcile first), 2 invalid input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DISAGREEMENT = 0.15


def _apply(grade: float, penalties: list[dict]) -> float:
    for p in penalties:
        if "points" in p:
            grade -= float(p["points"])
        if "percent" in p:
            grade *= 1 - float(p["percent"]) / 100
        if "cap" in p:
            grade = min(grade, float(p["cap"]))
    return max(0.0, grade)


def _num(x: float):
    x = round(x, 2)
    return int(x) if x == int(x) else x


def score(data: dict) -> dict:
    criteria = data.get("criteria") or []
    if not criteria:
        raise ValueError("no criteria")
    seen, rows = set(), []
    for c in criteria:
        cid = c.get("id")
        if cid in seen:
            raise ValueError(f"duplicate criterion id {cid!r}")
        seen.add(cid)
        mx = float(c.get("max", 0))
        if mx <= 0:
            raise ValueError(f"{cid}: max must be > 0")
        passes = [float(s) for s in c.get("passes", [])]
        if not passes:
            raise ValueError(f"{cid}: at least one pass score is needed")
        for s in passes:
            if s < 0:
                raise ValueError(f"{cid}: negative score {s}")
            if s > mx:
                raise ValueError(f"{cid}: score {s} exceeds max {mx}")
        lo, hi = min(passes), max(passes)
        rows.append({"id": cid, "name": c.get("name", cid), "max": _num(mx), "score": _num(sum(passes) / len(passes)),
                     "low": _num(lo), "high": _num(hi), "disagreement": (hi - lo) > DISAGREEMENT * mx})
    scale = data.get("scale") or {}
    smax = float(scale.get("max", 100))
    total_max = sum(r["max"] for r in rows)
    raw = sum(r["score"] for r in rows)
    penalties = data.get("penalties") or []

    def final(points):
        return _num(_apply(points / total_max * smax, penalties))

    out = {
        "criteria": rows,
        "raw": _num(raw),
        "max": _num(total_max),
        "final": final(raw),
        "scale_max": _num(smax),
        "range": [final(sum(r["low"] for r in rows)), final(sum(r["high"] for r in rows))],
        "penalties": penalties,
        "disagreements": [r["id"] for r in rows if r["disagreement"]],
    }
    if "pass" in scale:
        out["passed"] = out["final"] >= float(scale["pass"])
    return out


def _print(r: dict) -> None:
    print(f"{'criterion':<28}{'max':>6}{'score':>8}  range")
    for c in r["criteria"]:
        flag = "  ! passes disagree" if c["disagreement"] else ""
        print(f"{c['name'][:27]:<28}{c['max']:>6}{c['score']:>8}  {c['low']}–{c['high']}{flag}")
    for p in r["penalties"]:
        print(f"penalty: {p.get('reason', '')} {({k: v for k, v in p.items() if k != 'reason'})}")
    passed = "" if "passed" not in r else ("  (pass)" if r["passed"] else "  (below the pass mark)")
    print(f"final: {r['final']}/{r['scale_max']}  range {r['range'][0]}–{r['range'][1]}{passed}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = score(json.loads(Path(a.file).read_text(encoding="utf-8")))
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"score_rubric: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=1)) if a.json else _print(r)
    return 1 if r["disagreements"] else 0


if __name__ == "__main__":
    sys.exit(main())
