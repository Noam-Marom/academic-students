#!/usr/bin/env python3
"""Copy the shared/ sources of truth into the skills that declare them.

A skill folder must be self-contained (it may be uploaded to claude.ai on its own), so shared content is
copied, not linked. `shared/sync.json` says which skill gets what:

    {"disciplines": ["assignment-coach", ...],      # shared/disciplines/*.md -> skills/<s>/references/disciplines/
     "course_template": ["assignment-coach", ...],  # shared/COURSE.template.md -> skills/<s>/assets/COURSE.template.md
     "ai_policy": ["assignment-coach", ...]}        # shared/ai-policy.md -> skills/<s>/references/ai-policy.md

Usage:
    python3 tools/sync_shared.py            # write copies, delete stale ones
    python3 tools/sync_shared.py --check    # exit 1 and list every path that differs; write nothing
"""
from __future__ import annotations

import filecmp
import json
import shutil
import sys
from pathlib import Path

TARGETS = {
    # key in sync.json -> (source relative to shared/, destination relative to the skill dir, is_directory)
    "disciplines": ("disciplines", "references/disciplines", True),
    "course_template": ("COURSE.template.md", "assets/COURSE.template.md", False),
    "ai_policy": ("ai-policy.md", "references/ai-policy.md", False),
}


def _differs(src: Path, dst: Path) -> bool:
    return not dst.exists() or not filecmp.cmp(src, dst, shallow=False)


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def sync(root: Path, check: bool) -> list[str]:
    """Synchronise every declared target. Returns repo-relative paths that differ (check) or were written/removed."""
    root = Path(root)
    config = json.loads((root / "shared" / "sync.json").read_text(encoding="utf-8"))
    changed: list[str] = []
    for key, (src_rel, dst_rel, is_dir) in TARGETS.items():
        src = root / "shared" / src_rel
        for skill in config.get(key, []):
            dst = root / "skills" / skill / dst_rel
            if is_dir:
                wanted = {p.name: p for p in sorted(src.glob("*.md"))}
                existing = {p.name: p for p in dst.glob("*.md")} if dst.exists() else {}
                for name, s in wanted.items():
                    d = dst / name
                    if _differs(s, d):
                        changed.append(_rel(root, d))
                        if not check:
                            dst.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(s, d)
                for name, d in existing.items():
                    if name not in wanted:
                        changed.append(_rel(root, d))
                        if not check:
                            d.unlink()
            else:
                if _differs(src, dst):
                    changed.append(_rel(root, dst))
                    if not check:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst)
    return sorted(set(changed))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    check = "--check" in args
    root = Path(__file__).resolve().parents[1]
    changed = sync(root, check=check)
    if check:
        if changed:
            print("shared/ copies out of sync (run: python3 tools/sync_shared.py):")
            for p in changed:
                print("  " + p)
            return 1
        print("shared/ copies in sync")
        return 0
    for p in changed:
        print("synced " + p)
    print(f"{len(changed)} file(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
