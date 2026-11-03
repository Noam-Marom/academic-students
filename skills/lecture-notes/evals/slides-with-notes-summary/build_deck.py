#!/usr/bin/env python3
"""Write lecture5.pptx (synthetic, 4 slides, one hidden, speaker notes) with zipfile only. Usage: build_deck.py OUT"""
import sys
import zipfile
from xml.sax.saxutils import escape

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDES = [
    ("סנכרון: מבוא", ["מצב מרוץ (race condition): התוצאה תלויה בסדר הריצה", "קטע קריטי (critical section)"],
     "להדגיש: זה יופיע במבחן, תמיד שואלים על שלושת התנאים.", False),
    ("שלושת התנאים לפתרון", ["מניעה הדדית (mutual exclusion)", "התקדמות (progress)", "המתנה חסומה (bounded waiting)"], "", False),
    ("Peterson — הוכחה מלאה", ["הוכחת נכונות מלאה, לא נלמד השנה"], "שקף גיבוי, לא להציג.", True),
    ("סמפורים", ["wait(S): S = S - 1; אם S < 0 התהליך נחסם", "signal(S): S = S + 1; מעיר תהליך ממתין"],
     "לתת דוגמה של יצרן-צרכן עם חוצץ חסום.", False),
]


def sp(i, ph, paras):
    nv = f'<p:nvPr><p:ph type="{ph}"/></p:nvPr>' if ph else "<p:nvPr/>"
    body = "".join(f"<a:p><a:r><a:t>{escape(t)}</a:t></a:r></a:p>" for t in paras)
    return f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="s{i}"/><p:cNvSpPr/>{nv}</p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/>{body}</p:txBody></p:sp>'


def tree(inner):
    return f'<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>{inner}</p:spTree></p:cSld>'


def main(out):
    f = {}
    ov = '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
    ids, rels = "", ""
    for k, (title, body, notes, hidden) in enumerate(SLIDES, 1):
        ov += f'<Override PartName="/ppt/slides/slide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        ids += f'<p:sldId id="{255 + k}" r:id="rId{k}"/>'
        rels += f'<Relationship Id="rId{k}" Type="{R}/slide" Target="slides/slide{k}.xml"/>'
        show = ' show="0"' if hidden else ""
        f[f"ppt/slides/slide{k}.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><p:sld {NS}{show}>{tree(sp(2, "title", [title]) + sp(3, "body", body))}</p:sld>'
        srels = ""
        if notes:
            ov += f'<Override PartName="/ppt/notesSlides/notesSlide{k}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            srels = f'<Relationship Id="rId2" Type="{R}/notesSlide" Target="../notesSlides/notesSlide{k}.xml"/>'
            f[f"ppt/notesSlides/notesSlide{k}.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><p:notes {NS}>{tree(sp(2, "body", [notes]))}</p:notes>'
        f[f"ppt/slides/_rels/slide{k}.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PR}">{srels}</Relationships>'
    f["[Content_Types].xml"] = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                                f'<Default Extension="xml" ContentType="application/xml"/>{ov}</Types>')
    f["_rels/.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PR}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="ppt/presentation.xml"/></Relationships>'
    f["ppt/presentation.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><p:presentation {NS}><p:sldIdLst>{ids}</p:sldIdLst></p:presentation>'
    f["ppt/_rels/presentation.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PR}">{rels}</Relationships>'
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in f.items():
            z.writestr(name, text.encode("utf-8"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lecture5.pptx")
