#!/usr/bin/env python3
"""Build the clean tree that the `directory` branch holds, for Anthropic's plugin directory.

    python3 tools/build_directory.py --out build/directory [--json]

Only what someone who installs the plugin from the directory needs: the skills (without tests, evals or
benchmarks), the manifest and icon, README, LICENSE and CHANGELOG. Left out on purpose:

  - the local Moodle MCP server (.mcp.json, servers/): it does not run on claude.ai, and the directory will
    accept local servers only from Verified organizations. moodle-sync falls back to the browser and to
    Moodle's own exports; the server stays in the GitHub marketplace install.
  - dev files (tests, evals, docs, tools, shared/, CLAUDE.md, workflows): they gave the portal's validator
    most of its policy holds and nobody who installs the plugin needs them.

README links to files that are not in the build are rewritten to GitHub (images to raw.githubusercontent).
Only files tracked by git go in. Exit codes: 0 built, 2 refused (no manifest).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/Noam-Marom/academic-students"
RAW = "https://raw.githubusercontent.com/Noam-Marom/academic-students/main"
KEEP_TOP = {"README.md", "LICENSE", "CHANGELOG.md"}
KEEP_MANIFEST = {".claude-plugin/plugin.json", ".claude-plugin/icon.png"}
SKIP_PARTS = {"tests", "evals", "benchmark", "__pycache__", ".pytest_cache"}
BINARY = {".png", ".gif", ".jpg", ".jpeg", ".docx", ".pdf", ".zip", ".pptx", ".xlsx", ".pyc", ".ico"}
IMAGE = {".png", ".gif", ".jpg", ".jpeg", ".svg", ".webp"}
NOTE = (f"> **Plugin directory build.** This copy is built for Anthropic's plugin directory and leaves out the "
        f"local Moodle MCP server; moodle-sync works through your browser or Moodle's exports. For the server, "
        f"install from GitHub: [{REPO.removeprefix('https://')}]({REPO}).\n\n")


def _tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p and (root / p).is_file()]


def _wanted(rel: str) -> bool:
    parts = rel.split("/")
    if rel in KEEP_TOP or rel in KEEP_MANIFEST:
        return True
    if parts[0] != "skills" or SKIP_PARTS & set(parts[:-1]):
        return False
    return Path(rel).suffix.lower() not in BINARY


def _readme(text: str, out: Path) -> str:
    def fix(target: str) -> str:
        if target.startswith(("http://", "https://", "#", "mailto:")) or (out / target.split("#")[0]).exists():
            return target
        path = target.split("#")[0]
        if Path(path).suffix.lower() in IMAGE:
            return f"{RAW}/{target}"
        kind = "tree" if not Path(path).suffix else "blob"
        return f"{REPO}/{kind}/main/{target}"

    text = re.sub(r"\]\(([^)\s]+)\)", lambda m: f"]({fix(m.group(1))})", text)
    text = re.sub(r'src="([^"]+)"', lambda m: f'src="{fix(m.group(1))}"', text)
    lines = text.split("\n")
    # the note goes after the title and badges, before the pitch
    at = next((i for i, l in enumerate(lines) if i > 0 and l.startswith("**")), 1)
    return "\n".join(lines[:at]) + "\n" + NOTE + "\n".join(lines[at:])


def build(root: Path, out: Path) -> dict:
    if not (root / ".claude-plugin/plugin.json").is_file():
        raise ValueError(f"no .claude-plugin/plugin.json under {root}")
    if out.exists():
        for child in out.iterdir():
            if child.name != ".git":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    files = [r for r in _tracked(root) if _wanted(r)]
    for rel in files:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    readme = out / "README.md"
    readme.write_text(_readme(readme.read_text(encoding="utf-8"), out), encoding="utf-8")
    return {"out": str(out), "files": len(files)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "build" / "directory"))
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        report = build(Path(a.root), Path(a.out))
    except ValueError as exc:
        print(f"build_directory: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report) if a.json else f"directory build: {report['files']} files in {report['out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
