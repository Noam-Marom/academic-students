"""Every Hebrew Markdown document in the repo must render RTL correctly (the hebrew-with-english rules)."""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEBREW = re.compile(r"[֐-׿]")
LATIN = re.compile(r"[A-Za-z]")
SKIP_PARTS = {"evals", "fixtures", "results", ".superpowers", "node_modules", ".git", "corpus", "images"}  # docs/images holds raw before/after outputs, kept unedited


def hebrew_docs() -> list[pathlib.Path]:
    """A document is Hebrew when Hebrew letters outnumber Latin ones; English docs quoting Hebrew are exempt."""
    out = []
    for p in ROOT.rglob("*.md"):
        if SKIP_PARTS & set(p.relative_to(ROOT).parts):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        heb, lat = len(HEBREW.findall(text)), len(LATIN.findall(text))
        if heb >= 20 and heb > lat and not text.startswith("<!-- rtl-check: skip -->"):
            out.append(p)
    return sorted(out)


@pytest.mark.parametrize("doc", hebrew_docs(), ids=lambda p: str(p.relative_to(ROOT)))
def test_hebrew_doc_renders_rtl(doc, check_rtl):
    errors, _warnings = check_rtl.check(doc.read_text(encoding="utf-8"))
    assert errors == [], "\n".join(f"line {e['line']} ({e['where']}): {e['issue']} :: {e['text'][:80]}" for e in errors)
