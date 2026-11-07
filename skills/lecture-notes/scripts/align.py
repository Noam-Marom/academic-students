#!/usr/bin/env python3
"""Map transcript segments to the slides they were spoken over → `aligned.json`.

Input: `slides.json` ([{"n", "title", "text", "notes", "hidden"}]) and `transcript.json`
([{"start", "end", "text"}]). Output: one entry per slide, in slide order, each listing the indices
(0-based positions in the transcript) of the segments assigned to it:
    [{"slide": int, "segments": [int, ...]}, ...]

Scoring is stdlib only: tokens are lower-cased words with nikud and punctuation removed (Hebrew and Latin
alike; a Hebrew token also contributes its form without a leading ו/ה/ב/ל/מ/ש/כ prefix), weighted by IDF
across the slides, and compared by weighted Jaccard overlap. The best slide wins; a slide within `window`
of the previous assignment gets a small bonus so the path prefers to move forward or stay put, but a clear
overlap with a far slide still wins (lecturers skip and jump back). Ties go to the slide nearest the previous
one (forward before backward). A segment with no overlap at all (filler, "any questions?") attaches to the
previous slide, or to slide 1 before anything matched.

Usage:
    align.py slides.json transcript.json [--out aligned.json] [--window 3] [--json]

Exit codes: 0 = written · 2 = usage / unreadable input.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

_NIKUD = re.compile(r"[֑-ׇ]")
_WORD = re.compile(r"[\w]+", re.UNICODE)
_HEB_PREFIX = "והבלמשכ"
LOCAL_BONUS = 0.15      # multiplier bonus for slides within `window` of the previous assignment
TIE_EPSILON = 1e-9


def tokenize(text: str) -> set[str]:
    """Lower-case word tokens without nikud/punctuation; Hebrew words also yield their un-prefixed form."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _NIKUD.sub("", t).lower()
    tokens: set[str] = set()
    for w in _WORD.findall(t):
        if w.isdigit() or len(w) < 2:
            continue
        tokens.add(w)
        if "א" <= w[0] <= "ת" and len(w) >= 4 and w[0] in _HEB_PREFIX:
            tokens.add(w[1:])
    return tokens


def _slide_tokens(slide: dict) -> set[str]:
    return tokenize(" ".join(str(slide.get(k, "") or "") for k in ("title", "text", "notes")))


def _idf(slide_token_sets: list[set[str]]) -> dict[str, float]:
    n = len(slide_token_sets)
    df: dict[str, int] = {}
    for toks in slide_token_sets:
        for t in toks:
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}


def weighted_jaccard(a: set[str], b: set[str], idf: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    inter = sum(idf.get(t, 1.0) for t in a & b)
    if inter == 0.0:
        return 0.0
    union = sum(idf.get(t, 1.0) for t in a | b)
    return inter / union if union else 0.0


def align(slides: list[dict], segments: list[dict], window: int = 3) -> list[dict]:
    """Assign every segment to one slide. Returns one entry per slide (empty lists for slides nobody spoke over)."""
    order = [int(s["n"]) for s in slides]
    if not order:
        return []
    slide_tokens = [_slide_tokens(s) for s in slides]
    idf = _idf(slide_tokens)
    assigned: dict[int, list[int]] = {n: [] for n in order}
    prev_pos: int | None = None  # index into `slides` of the previous assignment
    for idx, seg in enumerate(segments):
        seg_tokens = tokenize(str(seg.get("text", "")))
        raw = [weighted_jaccard(seg_tokens, st, idf) for st in slide_tokens]
        if max(raw, default=0.0) <= 0.0:
            pos = prev_pos if prev_pos is not None else 0
        else:
            scored = []
            for pos_i, score in enumerate(raw):
                if score <= 0.0:
                    continue
                dist = abs(pos_i - prev_pos) if prev_pos is not None else 0
                bonus = LOCAL_BONUS if (prev_pos is not None and dist <= window) else 0.0
                scored.append((score * (1.0 + bonus), pos_i, dist))
            best = max(s for s, _, _ in scored)
            ties = [(d, 0 if (prev_pos is None or p >= prev_pos) else 1, p) for s, p, d in scored if best - s <= TIE_EPSILON]
            ties.sort()  # nearest to previous first; forward before backward at equal distance; then lower slide
            pos = ties[0][2]
        assigned[order[pos]].append(idx)
        prev_pos = pos
    return [{"slide": n, "segments": assigned[n]} for n in order]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slides", help="slides.json from slides_extract.py")
    parser.add_argument("transcript", help="transcript.json from transcribe.py")
    parser.add_argument("--out", default="aligned.json")
    parser.add_argument("--window", type=int, default=3, help="slides around the previous one that get a locality bonus")
    parser.add_argument("--json", action="store_true", help="print a one-line JSON summary")
    args = parser.parse_args(argv)
    try:
        slides = json.loads(Path(args.slides).read_text(encoding="utf-8"))
        segments = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
        if not isinstance(slides, list) or not isinstance(segments, list):
            raise ValueError("slides.json and transcript.json must each hold a JSON list")
        aligned = align(slides, segments, window=args.window)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(aligned, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    empty = [a["slide"] for a in aligned if not a["segments"]]
    summary = {"out": args.out, "slides": len(aligned), "segments": len(segments),
               "slides_without_speech": len(empty), "empty_slides": empty}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(segments)} segment(s) over {len(aligned)} slide(s); "
              f"{len(empty)} slide(s) with no speech" + (f": {empty}" if empty else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
