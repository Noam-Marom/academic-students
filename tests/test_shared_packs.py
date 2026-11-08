"""shared/ is the single source of truth for discipline packs, and the course-profile template."""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared"

FAMILIES = [
    "math-stats", "physical-sciences", "life-sciences", "computing", "engineering",
    "medicine-clinical", "social-sciences", "economics-business", "law", "humanities",
    "architecture-design", "arts",
]

PACK_HEADINGS = [
    "## Degrees covered",
    "## Typical deliverables",
    "## Answer conventions",
    "## Tools and environments",
    "## What graders look for",
    "## Common mistakes",
    "## Default citation style",
    "## Worked breakdown",
]

PROFILE_KEYS = [
    "course", "code", "institution", "degree", "family", "language", "submission_language",
    "citation_style", "submission_format", "environment", "grading",
]


def _frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "file must start with a YAML frontmatter block"
    return yaml.safe_load(m.group(1)) or {}


@pytest.mark.parametrize("family", FAMILIES)
def test_pack_exists_with_fixed_headings_in_order(family):
    path = SHARED / "disciplines" / f"{family}.md"
    assert path.exists(), f"missing pack {path}"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("# "), "first line must be the H1 title"
    assert len(lines) >= 40, f"{family}: pack is too thin ({len(lines)} lines)"
    positions = [text.find(h + "\n") for h in PACK_HEADINGS]
    assert all(p >= 0 for p in positions), f"{family}: missing headings {[h for h, p in zip(PACK_HEADINGS, positions) if p < 0]}"
    assert positions == sorted(positions), f"{family}: headings out of order"


def test_course_template_has_every_profile_key():
    text = (SHARED / "COURSE.template.md").read_text(encoding="utf-8")
    fm = _frontmatter(text)
    for key in PROFILE_KEYS:
        assert key in fm, f"COURSE.template.md frontmatter lacks {key}"
    assert fm["family"] in FAMILIES



def test_shared_copies_in_sync():
    from tools.sync_shared import sync
    assert sync(ROOT, check=True) == []
