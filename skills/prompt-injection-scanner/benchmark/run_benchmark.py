#!/usr/bin/env python3
"""Run scan.py over a labelled corpus and report recall per technique and the false-positive rate.

    python3 run_benchmark.py --corpus corpus --labels corpus/labels.csv [--quick] [--md table.md] [--json result.json]

A labelled file counts as *detected* when the scanner reports a finding for it at HIGH or above (the level at which
the skill stops and asks the user). A benign file counts as a *false positive* under the same rule.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SCAN_PY = HERE.parent / "scripts" / "scan.py"
LOUD = {"CRITICAL", "HIGH"}


def run(corpus: pathlib.Path, labels_csv: pathlib.Path, quick: bool = False, out_dir: pathlib.Path | None = None) -> dict:
    corpus = pathlib.Path(corpus)
    rows = list(csv.DictReader(open(labels_csv, encoding="utf-8")))
    out_dir = pathlib.Path(out_dir) if out_dir else pathlib.Path(tempfile.mkdtemp(prefix="bench-"))
    cmd = [sys.executable, "-I", str(SCAN_PY), str(corpus), "--out", str(out_dir / "scan"), "--no-ocr", "--force"]
    if quick:
        cmd.append("--quick")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
    findings = json.loads((out_dir / "scan" / "findings.json").read_text(encoding="utf-8"))["findings"]
    loud_files = {f["file"] for f in findings if f["severity"] in LOUD}

    def detected(rel: str) -> bool:
        # the scanner names files as "<corpus name>/<relative path>" (and sub-entries of archives with " › ")
        return any(lf == f"{corpus.name}/{rel}" or lf.startswith(f"{corpus.name}/{rel} ") or lf.startswith(f"{corpus.name}/{rel} ›")
                   for lf in loud_files)

    per_tech: dict[str, dict] = {}
    n = {"injection": 0, "canary": 0, "benign": 0}
    hits = {"injection": 0, "canary": 0, "benign": 0}
    for r in rows:
        t = per_tech.setdefault(r["technique"], {"positives": 0, "detected": 0, "benign": 0, "false_positives": 0})
        d = detected(r["path"])
        n[r["label"]] += 1
        hits[r["label"]] += int(d)
        if r["label"] == "benign":
            t["benign"] += 1
            t["false_positives"] += int(d)
        else:
            t["positives"] += 1
            t["detected"] += int(d)
    recall_by_technique = {t: (v["detected"] / v["positives"] if v["positives"] else None) for t, v in per_tech.items()}
    positives = n["injection"] + n["canary"]
    result = {
        "mode": "quick" if quick else "full",
        "n": n,
        "recall_overall": (hits["injection"] + hits["canary"]) / positives if positives else None,
        "recall_injection": hits["injection"] / n["injection"] if n["injection"] else None,
        "recall_canary": hits["canary"] / n["canary"] if n["canary"] else None,
        "false_positive_rate": hits["benign"] / n["benign"] if n["benign"] else None,
        "recall_by_technique": recall_by_technique,
        "false_positives_by_technique": {t: v["false_positives"] for t, v in per_tech.items()},
        "scanner_exit_code": proc.returncode,
    }
    lines = ["| Technique | Files | Recall (≥ HIGH) | False positives |", "|---|---|---|---|"]
    for t, v in sorted(per_tech.items()):
        rec = f"{v['detected']}/{v['positives']} ({100 * v['detected'] / v['positives']:.0f}%)" if v["positives"] else "—"
        lines.append(f"| `{t}` | {v['positives'] + v['benign']} | {rec} | {v['false_positives']}/{v['benign']} |")
    lines.append(f"| **all** | {sum(n.values())} | **{100 * result['recall_overall']:.1f}%** | "
                 f"**{hits['benign']}/{n['benign']} ({100 * result['false_positive_rate']:.1f}%)** |")
    result["md_table"] = "\n".join(lines)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    result = run(pathlib.Path(a.corpus), pathlib.Path(a.labels), quick=a.quick)
    if a.md:
        pathlib.Path(a.md).write_text(result["md_table"] + "\n", encoding="utf-8")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(result["md_table"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
