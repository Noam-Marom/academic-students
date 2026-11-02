#!/usr/bin/env python3
"""Check that a skill folder is portable: it must work when uploaded to claude.ai on its own.

Rules (from docs/skill-conventions.md):
  * frontmatter keys only from the six claude.ai accepts: name, description, license, compatibility, metadata, allowed-tools
  * name == folder name, <= 64 chars; description <= 1024 chars
  * SKILL.md body <= 300 lines (progressive disclosure: knowledge goes to references/)
  * every scripts/ references/ assets/ schemas/ path mentioned in the body exists inside the skill folder
  * no ${CLAUDE_PLUGIN_ROOT} (not available on claude.ai)

Usage: python3 tools/check_portability.py skills/<name> [skills/<other> ...]   (exit 1 if problems)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
MAX_BODY_LINES = 300
PATH_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|schemas)/[\w./-]+?)(?=[\s`'\")\]>,;:]|$)")


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", text, re.S)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1)) or {}
    return (data if isinstance(data, dict) else {}), m.group(2)


def check_skill(skill_dir: Path) -> list[str]:
    skill_dir = Path(skill_dir)
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir.name}: SKILL.md missing"]
    text = skill_md.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if not fm:
        problems.append(f"{skill_dir.name}: frontmatter missing or unparsable")
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        problems.append(f"{skill_dir.name}: frontmatter keys not portable to claude.ai: {sorted(extra)}")
    name = str(fm.get("name", ""))
    if name != skill_dir.name:
        problems.append(f"{skill_dir.name}: frontmatter name {name!r} != folder name")
    if len(name) > 64:
        problems.append(f"{skill_dir.name}: name longer than 64 chars")
    desc = str(fm.get("description", ""))
    if not desc:
        problems.append(f"{skill_dir.name}: description missing")
    if len(desc) > 1024:
        problems.append(f"{skill_dir.name}: description longer than 1024 chars ({len(desc)})")
    body_lines = body.count("\n") + (0 if body.endswith("\n") or not body else 1)
    if body_lines > MAX_BODY_LINES:
        problems.append(f"{skill_dir.name}: SKILL.md body has {body_lines} lines (max {MAX_BODY_LINES})")
    if "${CLAUDE_PLUGIN_ROOT}" in text:
        problems.append(f"{skill_dir.name}: uses ${{CLAUDE_PLUGIN_ROOT}}, which claude.ai does not provide")
    for ref in sorted(set(PATH_RE.findall(body))):
        candidate = ref.rstrip(".")
        if not (skill_dir / candidate).exists():
            problems.append(f"{skill_dir.name}: SKILL.md mentions {candidate} but it does not exist in the skill folder")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print(__doc__)
        return 2
    total = 0
    for a in args:
        for p in check_skill(Path(a)):
            print(p)
            total += 1
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
