"""Minimal DOCX writer for tests (zipfile + hand-written OOXML). Supports paragraph-level and style-level bidi."""
from __future__ import annotations

import pathlib
import zipfile

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def para(text: str, *, bidi: bool = False, style: str | None = None, rtl_run: bool = False) -> str:
    ppr = ""
    if style or bidi:
        ppr = "<w:pPr>" + (f'<w:pStyle w:val="{style}"/>' if style else "") + ("<w:bidi/>" if bidi else "") + "</w:pPr>"
    rpr = "<w:rPr><w:rtl/></w:rPr>" if rtl_run else ""
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def styles(defs: dict[str, dict]) -> str:
    """defs: {style_id: {"bidi": bool, "basedOn": str|None}}"""
    parts = []
    for sid, d in defs.items():
        based = f'<w:basedOn w:val="{d["basedOn"]}"/>' if d.get("basedOn") else ""
        bidi = "<w:pPr><w:bidi/></w:pPr>" if d.get("bidi") else ""
        parts.append(f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{sid}"/>{based}{bidi}</w:style>')
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>{"".join(parts)}</w:styles>'


def write(path: pathlib.Path, paragraphs: list[str], style_defs: dict[str, dict] | None = None) -> pathlib.Path:
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{"".join(paragraphs)}</w:body></w:document>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/document.xml", doc)
        z.writestr("word/styles.xml", styles(style_defs or {}))
    return path
