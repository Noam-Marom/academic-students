#!/usr/bin/env python3
"""Build the release zips.

    python3 tools/package.py [--out dist] [--json]

Writes
  dist/academic-students-<version>.zip   the whole plugin (manifest at the zip root): install it in Claude Code
                                         with `claude --plugin-dir <zip>`, or upload it as a custom plugin
  dist/skills/<skill>.zip                one skill per zip (`<skill>/SKILL.md` inside), for uploading single
                                         skills in claude.ai → Customize → Skills

Only files tracked by git go in (untracked corpora and caches never ship), minus what users do not need:
tests, evals, benchmarks, docs, caches. Timestamps are fixed, so the same commit always gives the same bytes.
Refuses to build a plugin that has a top-level `bin/` (claude.ai rejects it).

Exit codes: 0 built, 2 refused (bin/, missing manifest).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL = [".claude-plugin", ".mcp.json", "skills", "servers", "README.md", "README.he.md", "LICENSE", "CHANGELOG.md"]
SKIP_PARTS = {"tests", "evals", "benchmark", "docs", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
SKIP_NAMES = {"uv.lock", ".DS_Store", "MANUAL_CHECKS.md"}
EPOCH = (1980, 1, 1, 0, 0, 0)


def _tracked(root: Path) -> list[Path]:
    if (root / ".git").exists():
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
        return [root / p for p in out.decode().split("\0") if p and (root / p).is_file()]
    return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]


def _wanted(rel: Path) -> bool:
    if rel.parts[0] not in TOP_LEVEL:
        return False
    return not (SKIP_PARTS & set(rel.parts[:-1])) and rel.name not in SKIP_NAMES and rel.suffix != ".pyc"


def _write(zpath: Path, entries: list[tuple[str, Path]]) -> None:
    zpath.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, src in sorted(entries):
            info = zipfile.ZipInfo(arc, date_time=EPOCH)
            info.external_attr = (0o755 if src.stat().st_mode & 0o111 else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, src.read_bytes())


def build(root: Path, out: Path) -> dict:
    manifest = root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        raise ValueError(f"no .claude-plugin/plugin.json under {root}")
    if (root / "bin").exists():
        raise ValueError("the plugin has a top-level bin/ directory; claude.ai refuses to install it")
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    files = [(p.relative_to(root), p) for p in _tracked(root)]
    files = [(rel, p) for rel, p in files if _wanted(rel)]

    plugin_zip = out / f"{meta['name']}-{meta.get('version', '0.0.0')}.zip"
    _write(plugin_zip, [(rel.as_posix(), p) for rel, p in files])

    skills = {}
    for skill_md in sorted((root / "skills").glob("*/SKILL.md")):
        name = skill_md.parent.name
        entries = [(Path(*rel.parts[1:]).as_posix(), p) for rel, p in files
                   if rel.parts[:2] == ("skills", name)]
        z = out / "skills" / f"{name}.zip"
        _write(z, entries)
        skills[name] = str(z)
    return {"plugin": str(plugin_zip), "skills": skills}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        report = build(Path(a.root), Path(a.out))
    except ValueError as exc:
        print(f"package: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"plugin: {report['plugin']}")
        for name, z in report["skills"].items():
            print(f"skill:  {z}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
