"""Minimal OOXML PowerPoint writer for tests — zipfile + hand-written XML, no python-pptx.

`build_pptx(path, slides)` where each slide is a dict:
    {"title": str|None, "body": [str, ...], "notes": str|None, "hidden": bool, "title_as_textbox": bool}

`title_as_textbox=True` writes the title as an ordinary text box (no title placeholder), which is how many
lecturers' decks look; the extractor must then fall back to the first non-empty paragraph.
Slide XML parts are written to the archive in reverse order and the relationship ids are shuffled, so an
extractor that trusts file names or zip order instead of presentation.xml gets the order wrong.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _shape(shape_id: int, name: str, paragraphs: list[str], ph_type: str | None) -> str:
    ph = f'<p:nvPr><p:ph type="{ph_type}"/></p:nvPr>' if ph_type else "<p:nvPr/>"
    body = "".join(f"<a:p><a:r><a:rPr lang=\"he-IL\"/><a:t>{escape(t)}</a:t></a:r></a:p>" for t in paragraphs)
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/>{ph}</p:nvSpPr>'
            f'<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{body}</p:txBody></p:sp>')


def _slide_xml(slide: dict) -> str:
    shapes = []
    sid = 2
    title = slide.get("title")
    if title is not None:
        ph = None if slide.get("title_as_textbox") else "title"
        shapes.append(_shape(sid, "Title 1" if ph else "TextBox 1", [title], ph))
        sid += 1
    body = slide.get("body") or []
    if body:
        shapes.append(_shape(sid, "Content Placeholder 2", body, "body"))
        sid += 1
    show = ' show="0"' if slide.get("hidden") else ""
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld {NS}{show}><p:cSld><p:spTree>'
            f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            f'{"".join(shapes)}</p:spTree></p:cSld></p:sld>')


def _notes_xml(notes: str, slide_number: int) -> str:
    paragraphs = notes.split("\n")
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:notes {NS}><p:cSld><p:spTree>'
            f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
            f'{_shape(2, "Slide Image Placeholder 1", [], "sldImg")}'
            f'{_shape(3, "Notes Placeholder 2", paragraphs, "body")}'
            f'{_shape(4, "Slide Number Placeholder 3", [str(slide_number)], "sldNum")}'
            f'</p:spTree></p:cSld></p:notes>')


def build_pptx(path: Path, slides: list[dict]) -> Path:
    path = Path(path)
    n = len(slides)
    # shuffled relationship ids: slide k gets rId(100 + (n - k)) so rId order is the reverse of slide order
    rids = {k: f"rId{100 + (n - k)}" for k in range(1, n + 1)}
    files: dict[str, str] = {}

    overrides = ['<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>']
    for k in range(1, n + 1):
        overrides.append(f'<Override PartName="/ppt/slides/slide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        if slides[k - 1].get("notes"):
            overrides.append(f'<Override PartName="/ppt/notesSlides/notesSlide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
    files["[Content_Types].xml"] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                                    '<Default Extension="xml" ContentType="application/xml"/>'
                                    + "".join(overrides) + "</Types>")
    files["_rels/.rels"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG_REL_NS}">'
                            f'<Relationship Id="rId1" Type="{REL_NS}/officeDocument" Target="ppt/presentation.xml"/></Relationships>')
    sld_ids = "".join(f'<p:sldId id="{255 + k}" r:id="{rids[k]}"/>' for k in range(1, n + 1))
    files["ppt/presentation.xml"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                     f'<p:presentation {NS}><p:sldMasterIdLst/><p:sldIdLst>{sld_ids}</p:sldIdLst>'
                                     f'<p:sldSz cx="12192000" cy="6858000"/></p:presentation>')
    pres_rels = "".join(f'<Relationship Id="{rids[k]}" Type="{REL_NS}/slide" Target="slides/slide{k}.xml"/>'
                        for k in range(n, 0, -1))
    files["ppt/_rels/presentation.xml.rels"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                                f'<Relationships xmlns="{PKG_REL_NS}">{pres_rels}</Relationships>')
    for k in range(n, 0, -1):  # reverse order on purpose
        slide = slides[k - 1]
        files[f"ppt/slides/slide{k}.xml"] = _slide_xml(slide)
        rels = [f'<Relationship Id="rId1" Type="{REL_NS}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>']
        if slide.get("notes"):
            rels.append(f'<Relationship Id="rId2" Type="{REL_NS}/notesSlide" Target="../notesSlides/notesSlide{k}.xml"/>')
            files[f"ppt/notesSlides/notesSlide{k}.xml"] = _notes_xml(slide["notes"], k)
        files[f"ppt/slides/_rels/slide{k}.xml.rels"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                                        f'<Relationships xmlns="{PKG_REL_NS}">{"".join(rels)}</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content.encode("utf-8"))
    return path
