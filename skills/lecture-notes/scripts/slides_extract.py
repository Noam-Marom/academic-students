#!/usr/bin/env python3
"""Extract slide text from a PPTX or PDF deck into `slides.json`.

Output shape (one object per slide, in presentation order):
    [{"n": int, "title": str, "text": str, "notes": str, "hidden": bool}, ...]

PPTX is read with zipfile + XML only (no python-pptx): slide order comes from `presentation.xml`'s
`sldIdLst` resolved through its relationships (never from file names), the title is the `title`/`ctrTitle`
placeholder or, when a deck puts titles in plain text boxes, the first non-empty paragraph; speaker notes come
from the slide's `notesSlide` (slide-number and slide-image placeholders skipped); `show="0"` marks a hidden
slide. PDF decks use PyMuPDF (`fitz`) when importable, else `pypdf`; the first non-empty line is the title.

Usage:
    slides_extract.py deck.pptx|deck.pdf [--out slides.json] [--json]

Exit codes: 0 = written · 2 = usage, unsupported file, or no PDF backend installed (message says what to install).
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
TITLE_TYPES = {"title", "ctrTitle"}
SKIP_PH_TYPES = {"sldNum", "sldImg", "dt", "ftr", "hdr"}


class MissingDependency(RuntimeError):
    """Raised when a PDF deck is given and neither PyMuPDF nor pypdf can be imported."""


# --- PPTX ------------------------------------------------------------------------------------------

def _rels(z: zipfile.ZipFile, part: str) -> dict[str, str]:
    """Relationship id → absolute part name, for the .rels file of `part`."""
    d, name = posixpath.split(part)
    rels_name = posixpath.join(d, "_rels", name + ".rels")
    if rels_name not in z.namelist():
        return {}
    root = ET.fromstring(z.read(rels_name))
    out = {}
    for rel in root.findall("rel:Relationship", NS):
        target = rel.get("Target", "")
        if rel.get("TargetMode") == "External":
            continue
        abs_target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(d, target))
        out[rel.get("Id", "")] = abs_target
    return out


def _rel_targets_by_type(z: zipfile.ZipFile, part: str, type_suffix: str) -> list[str]:
    d, name = posixpath.split(part)
    rels_name = posixpath.join(d, "_rels", name + ".rels")
    if rels_name not in z.namelist():
        return []
    root = ET.fromstring(z.read(rels_name))
    out = []
    for rel in root.findall("rel:Relationship", NS):
        if rel.get("Type", "").endswith("/" + type_suffix) and rel.get("TargetMode") != "External":
            target = rel.get("Target", "")
            out.append(target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(d, target)))
    return out


def _paragraph_text(p: ET.Element) -> str:
    parts: list[str] = []
    for node in p.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag == "br":
            parts.append("\n")
    return "".join(parts).strip()


def _shape_paragraphs(sp: ET.Element) -> list[str]:
    paras = []
    for p in sp.iter(f"{{{NS['a']}}}p"):
        t = _paragraph_text(p)
        if t:
            paras.append(t)
    return paras


def _ph_type(sp: ET.Element) -> str | None:
    ph = sp.find("./p:nvSpPr/p:nvPr/p:ph", NS)
    if ph is None:
        return None
    return ph.get("type", "body")  # a <p:ph/> with no type is a body placeholder


def _slide_shapes(root: ET.Element) -> list[ET.Element]:
    """Every p:sp in document order, including those nested in groups; graphic frames (tables) too."""
    shapes = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in ("sp", "graphicFrame"):
            shapes.append(node)
    return shapes


def _parse_slide(xml: bytes) -> dict:
    root = ET.fromstring(xml)
    hidden = root.get("show") == "0"
    title: str | None = None
    body: list[str] = []
    fallback_index: int | None = None
    for sp in _slide_shapes(root):
        ph = _ph_type(sp) if sp.tag.endswith("}sp") else None
        if ph in SKIP_PH_TYPES:
            continue
        paras = _shape_paragraphs(sp)
        if not paras:
            continue
        if ph in TITLE_TYPES and title is None:
            title = " ".join(paras)
            continue
        if title is None and fallback_index is None and ph is None:
            fallback_index = len(body)
        body.extend(paras)
    if title is None and body:
        # no title placeholder: the first non-empty paragraph of the slide is the title (and not repeated in text)
        idx = fallback_index if fallback_index is not None else 0
        title = body.pop(idx)
    return {"title": title or "", "text": "\n".join(body), "hidden": hidden}


def _parse_notes(xml: bytes) -> str:
    root = ET.fromstring(xml)
    paras: list[str] = []
    for sp in _slide_shapes(root):
        ph = _ph_type(sp) if sp.tag.endswith("}sp") else None
        if ph in SKIP_PH_TYPES:
            continue
        paras.extend(_shape_paragraphs(sp))
    return "\n".join(paras)


def extract_pptx(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        pres = "ppt/presentation.xml"
        if pres not in names:
            # unusual package layout: follow the package-level officeDocument relationship instead
            pres = next((t for t in _rels(z, "").values() if t.endswith("presentation.xml")), pres)
            if pres not in names:
                raise ValueError(f"{path.name}: not a PowerPoint package (no ppt/presentation.xml)")
        pres_rels = _rels(z, pres)
        root = ET.fromstring(z.read(pres))
        slide_parts = []
        for sld in root.findall("./p:sldIdLst/p:sldId", NS):
            rid = sld.get(f"{{{NS['r']}}}id")
            target = pres_rels.get(rid or "")
            if target and target in names:
                slide_parts.append(target)
        if not slide_parts:  # no sldIdLst (rare) → fall back to numeric file order
            slide_parts = sorted((n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                 key=lambda n: int(re.findall(r"\d+", n)[-1]))
        slides = []
        for i, part in enumerate(slide_parts, 1):
            data = _parse_slide(z.read(part))
            notes = ""
            for notes_part in _rel_targets_by_type(z, part, "notesSlide"):
                if notes_part in names:
                    notes = _parse_notes(z.read(notes_part))
                    break
            slides.append({"n": i, "title": data["title"], "text": data["text"], "notes": notes, "hidden": data["hidden"]})
        return slides


# --- PDF -------------------------------------------------------------------------------------------

def _pdf_backend():
    """Return ("fitz", module) or ("pypdf", module) or None."""
    try:
        import fitz  # type: ignore
        return ("fitz", fitz)
    except Exception:  # ImportError and the odd runtime error from a broken install
        pass
    try:
        import pypdf  # type: ignore
        return ("pypdf", pypdf)
    except Exception:
        return None


def _pdf_pages_text(path: Path) -> list[str]:
    backend = _pdf_backend()
    if backend is None:
        raise MissingDependency(
            "reading a PDF deck needs PyMuPDF or pypdf: `pip install pymupdf` (preferred) or `pip install pypdf`. "
            "Alternatively export the deck as .pptx and run this script on that.")
    kind, mod = backend
    pages: list[str] = []
    if kind == "fitz":
        with mod.open(str(path)) as doc:
            for page in doc:
                pages.append(page.get_text("text"))
    else:
        reader = mod.PdfReader(str(path))
        for page in reader.pages:
            pages.append(page.extract_text() or "")
    return pages


def extract_pdf(path: Path) -> list[dict]:
    slides = []
    for i, text in enumerate(_pdf_pages_text(path), 1):
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        title = lines[0] if lines else ""
        body = "\n".join(lines[1:])
        slides.append({"n": i, "title": title, "text": body, "notes": "", "hidden": False})
    return slides


# --- public ----------------------------------------------------------------------------------------

def extract(path: Path) -> list[dict]:
    """Return the slides.json list for a .pptx or .pdf deck. Raises MissingDependency / ValueError."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pptx":
        return extract_pptx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    raise ValueError(f"unsupported deck type {suffix!r}: give a .pptx or a .pdf (export .key/.odp to one of those)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", help=".pptx or .pdf")
    parser.add_argument("--out", default="slides.json")
    parser.add_argument("--json", action="store_true", help="print a one-line JSON summary")
    args = parser.parse_args(argv)
    deck = Path(args.deck)
    if not deck.exists():
        print(f"no such file: {deck}", file=sys.stderr)
        return 2
    try:
        slides = extract(deck)
    except MissingDependency as exc:
        print(f"skipped: {exc}", file=sys.stderr)
        return 2
    except (ValueError, zipfile.BadZipFile, ET.ParseError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(slides, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    summary = {"out": args.out, "slides": len(slides), "hidden": sum(1 for s in slides if s["hidden"]),
               "with_notes": sum(1 for s in slides if s["notes"]), "untitled": sum(1 for s in slides if not s["title"])}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {summary['slides']} slide(s), {summary['hidden']} hidden, "
              f"{summary['with_notes']} with speaker notes, {summary['untitled']} without a title")
    return 0


if __name__ == "__main__":
    sys.exit(main())
