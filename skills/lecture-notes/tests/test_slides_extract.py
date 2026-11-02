"""slides_extract.py: PPTX (zipfile + XML) and PDF decks → slides.json shape."""
import json
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "slides_extract.py"

DECK = [
    {"title": "מבוא לתזמון תהליכים", "body": ["התהליך (process) הוא תוכנית בריצה", "המתזמן (scheduler) בוחר מי רץ"]},
    {"title": "Hidden backup slide", "body": ["Extra proof we skip in class"], "hidden": True,
     "notes": "Only show if there is time.\nOtherwise skip to FCFS."},
    {"title": "Scheduling policies", "body": ["FCFS, SJF, Round Robin", "Context switch cost"], "title_as_textbox": True},
]


@pytest.fixture
def deck(tmp_path, pptx_builder):
    return pptx_builder.build_pptx(tmp_path / "lecture3.pptx", DECK)


def test_pptx_order_titles_notes_hidden(deck, slides_extract):
    slides = slides_extract.extract(deck)
    assert [s["n"] for s in slides] == [1, 2, 3]
    assert [s["title"] for s in slides] == ["מבוא לתזמון תהליכים", "Hidden backup slide", "Scheduling policies"]
    assert [s["hidden"] for s in slides] == [False, True, False]
    assert slides[1]["notes"] == "Only show if there is time.\nOtherwise skip to FCFS."
    assert slides[0]["notes"] == "" and slides[2]["notes"] == ""


def test_pptx_body_text_excludes_title_and_keeps_paragraphs(deck, slides_extract):
    slides = slides_extract.extract(deck)
    assert slides[0]["text"] == "התהליך (process) הוא תוכנית בריצה\nהמתזמן (scheduler) בוחר מי רץ"
    assert "מבוא לתזמון תהליכים" not in slides[0]["text"]


def test_pptx_title_falls_back_to_first_paragraph_when_no_placeholder(deck, slides_extract):
    slides = slides_extract.extract(deck)
    third = slides[2]
    assert third["title"] == "Scheduling policies"
    assert third["text"] == "FCFS, SJF, Round Robin\nContext switch cost"  # the fallback title is not repeated


def test_notes_skip_slide_number_placeholder(deck, slides_extract):
    slides = slides_extract.extract(deck)
    assert slides[1]["notes"].strip() != "2"
    assert "\n2" not in slides[1]["notes"] and not slides[1]["notes"].startswith("2")


def test_each_slide_has_exactly_the_interchange_keys(deck, slides_extract):
    for s in slides_extract.extract(deck):
        assert set(s) == {"n", "title", "text", "notes", "hidden"}
        assert isinstance(s["n"], int) and isinstance(s["hidden"], bool)
        for k in ("title", "text", "notes"):
            assert isinstance(s[k], str)


def test_pdf_deck_title_is_first_line(tmp_path, slides_extract):
    fitz = pytest.importorskip("fitz")
    pdf = tmp_path / "deck.pdf"
    doc = fitz.open()
    for title, body in [("Memory Hierarchy", "Registers, cache, RAM, disk"), ("Paging", "Pages and frames")]:
        page = doc.new_page()
        page.insert_text((72, 72), title, fontsize=20)
        page.insert_text((72, 120), body, fontsize=12)
    doc.save(str(pdf))
    doc.close()
    slides = slides_extract.extract(pdf)
    assert [s["n"] for s in slides] == [1, 2]
    assert slides[0]["title"] == "Memory Hierarchy"
    assert "Registers, cache, RAM, disk" in slides[0]["text"]
    assert slides[1]["title"] == "Paging"
    assert all(s["hidden"] is False and s["notes"] == "" for s in slides)


def test_pdf_without_any_backend_exits_2(tmp_path, slides_extract, monkeypatch):
    pdf = tmp_path / "deck.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    monkeypatch.setattr(slides_extract, "_pdf_backend", lambda: None)
    with pytest.raises(slides_extract.MissingDependency) as info:
        slides_extract.extract(pdf)
    assert "pymupdf" in str(info.value) or "pypdf" in str(info.value)


def test_cli_writes_slides_json(tmp_path, pptx_builder):
    deck = pptx_builder.build_pptx(tmp_path / "deck.pptx", DECK)
    out = tmp_path / "slides.json"
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(deck), "--out", str(out), "--json"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert summary["slides"] == 3 and summary["hidden"] == 1 and summary["with_notes"] == 1
    assert [s["n"] for s in data] == [1, 2, 3]


def test_cli_unsupported_extension_exits_2(tmp_path):
    bad = tmp_path / "deck.key"
    bad.write_bytes(b"x")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(bad)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
