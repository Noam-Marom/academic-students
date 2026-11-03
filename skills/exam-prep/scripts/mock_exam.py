#!/usr/bin/env python3
"""Sample a mock exam from a question bank, by topic weights, reproducibly.

Given `bank.json` (see question_bank.py) and weights per topic (usually the frequency × points share from
`question_bank.py stats`), pick `n` questions without replacement so that each topic gets its proportional
share (largest-remainder rounding). A topic that has fewer questions than its share gives the remainder to
the other topics. The same seed always yields the same exam, so a student can regenerate or share it.

Usage:
    mock_exam.py bank.json --weights "sync=0.4,memory=0.35,fs=0.25" -n 6 [--seed 1] [--total-points 100]
                 [--out mock.json] [--json]

Output (`mock.json`): {"seed": int, "n": int, "total_points": int|null, "weights": {...},
                        "questions": [bank question objects, points rescaled when --total-points is given]}
Exit codes: 0 = written · 2 = usage / bad weights / unreadable bank.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path


def _normalise_weights(weights: dict[str, float], available: dict[str, int]) -> dict[str, float]:
    """Keep only topics that exist in the bank with a positive weight; scale to sum 1."""
    kept = {t: float(w) for t, w in weights.items() if t in available and available[t] > 0 and float(w) > 0}
    total = sum(kept.values())
    if total <= 0:
        raise ValueError("no weighted topic has questions in the bank")
    return {t: w / total for t, w in kept.items()}


def allocate(weights: dict[str, float], available: dict[str, int], n: int) -> dict[str, int]:
    """Largest-remainder apportionment of `n` slots across topics, capped by availability.

    When a topic is capped below its share, the freed slots are re-apportioned among the uncapped topics,
    repeatedly, until every slot is placed or every topic is exhausted.
    """
    alloc = {t: 0 for t in weights}
    remaining = n
    active = dict(weights)
    while remaining > 0 and active:
        total_w = sum(active.values())
        shares = {t: remaining * w / total_w for t, w in active.items()}
        floors = {t: int(s) for t, s in shares.items()}
        leftover = remaining - sum(floors.values())
        # largest remainder first; ties broken by weight then name so the result is deterministic
        order = sorted(active, key=lambda t: (-(shares[t] - floors[t]), -active[t], t))
        for t in order[:leftover]:
            floors[t] += 1
        capped_any = False
        for t, want in floors.items():
            room = available[t] - alloc[t]
            take = min(want, room)
            alloc[t] += take
            if take < want or alloc[t] >= available[t]:
                capped_any = True
        remaining = n - sum(alloc.values())
        active = {t: w for t, w in active.items() if alloc[t] < available[t]}
        if not capped_any and remaining > 0:
            # cannot happen (floors + leftover == remaining), guard against an infinite loop anyway
            break
    return alloc


def build_mock(bank: dict, weights: dict[str, float], n: int, seed: int, total_points: int | None) -> list[dict]:
    """Return `n` questions (fewer if the bank is smaller), sampled per topic weights, deterministic for `seed`."""
    by_topic: dict[str, list[dict]] = {}
    for q in bank.get("questions", []):
        if q.get("topic"):
            by_topic.setdefault(q["topic"], []).append(q)
    available = {t: len(qs) for t, qs in by_topic.items()}
    w = _normalise_weights(weights, available)
    n = max(0, min(n, sum(available[t] for t in w)))
    alloc = allocate(w, available, n)
    rng = random.Random(seed)
    chosen: list[dict] = []
    for topic in sorted(alloc):
        pool = sorted(by_topic[topic], key=lambda q: q.get("id", ""))
        chosen.extend(copy.deepcopy(q) for q in rng.sample(pool, alloc[topic]))
    rng.shuffle(chosen)
    if total_points is not None and chosen:
        _rescale_points(chosen, total_points)
    return chosen


def _rescale_points(questions: list[dict], total_points: int) -> None:
    """Scale points so they sum to `total_points`; questions without points share the total equally."""
    raw = [q.get("points") if isinstance(q.get("points"), (int, float)) and q["points"] > 0 else None for q in questions]
    if any(r is None for r in raw):
        raw = [1.0] * len(questions)
    s = sum(raw)
    exact = [total_points * r / s for r in raw]
    floors = [int(e) for e in exact]
    leftover = total_points - sum(floors)
    order = sorted(range(len(questions)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:leftover]:
        floors[i] += 1
    for q, p in zip(questions, floors):
        q["points"] = p


def parse_weights(spec: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"weight {part!r} is not topic=number")
        topic, _, value = part.partition("=")
        try:
            out[topic.strip()] = float(value)
        except ValueError as exc:
            raise ValueError(f"weight for {topic.strip()!r} is not a number: {value!r}") from exc
    if not out:
        raise ValueError("no weights given")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bank")
    parser.add_argument("--weights", required=True, help='"topic=weight,topic=weight" (any positive numbers)')
    parser.add_argument("-n", type=int, required=True, help="number of questions")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--total-points", type=int, default=None)
    parser.add_argument("--out", default="mock.json")
    parser.add_argument("--json", action="store_true", help="print a one-line JSON summary")
    args = parser.parse_args(argv)
    try:
        bank = json.loads(Path(args.bank).read_text(encoding="utf-8"))
        weights = parse_weights(args.weights)
        questions = build_mock(bank, weights, n=args.n, seed=args.seed, total_points=args.total_points)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    mock = {"seed": args.seed, "n": len(questions), "total_points": args.total_points, "weights": weights,
            "questions": questions}
    Path(args.out).write_text(json.dumps(mock, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary = {"out": args.out, "n": len(questions), "total_points": args.total_points,
               "by_topic": {t: sum(1 for q in questions if q.get("topic") == t) for t in sorted(weights)}}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(questions)} question(s), seed {args.seed}")
        for t, c in summary["by_topic"].items():
            print(f"  {t}: {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
