# Hebrew in Word (.docx)

Word does not guess direction from the text. Each paragraph has a base direction set by `w:bidi` in its
paragraph properties (`w:pPr`); without it the paragraph is left-to-right even if every letter is Hebrew, and
mixed English terms and punctuation land on the wrong side.

## The four properties that matter

| Property | Where | Effect |
|---|---|---|
| `<w:bidi/>` | `w:pPr` (paragraph) or the paragraph's style | Base direction RTL; also flips indents, list bullets and tab stops |
| `<w:jc w:val="both"/>` / `"left"`/`"right"` | `w:pPr` | Alignment. In an RTL paragraph `left`/`right` are physical; prefer `start`/`end` or `both` |
| `<w:rtl/>` | `w:rPr` (run) | Marks a run as RTL text (needed for Hebrew runs so digits and neutrals order correctly). English runs omit it |
| `<w:lang w:bidi="he-IL"/>`, `<w:rFonts w:cs="David"/>`, `<w:szCs>` | `w:rPr` | Complex-script language, font and size. Hebrew uses the *cs* (complex script) slots, not `w:ascii` |

Style inheritance: a paragraph whose `w:pStyle` points at a style with `w:bidi` (directly or through
`w:basedOn`) is RTL. Google Docs and LibreOffice exports often set bidi on the style only — that is fine.

## Setting it from python-docx

python-docx has no bidi property; append the element yourself:

```python
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def make_rtl(paragraph):
    ppr = paragraph._p.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.append(OxmlElement("w:bidi"))
    for run in paragraph.runs:
        if any("֐" <= c <= "׿" for c in run.text):
            rpr = run._r.get_or_add_rPr()
            rpr.append(OxmlElement("w:rtl"))
```

Better: set it once on the `Normal` style (`doc.styles["Normal"].element.get_or_add_pPr()` + `w:bidi`) so every
paragraph inherits it, then override only English-only paragraphs (code, references in English).

## Mixed lines

- Keep an English term in its own run without `w:rtl`; keep the Hebrew around it in RTL runs.
- Neutral characters (spaces, periods, parentheses) take the paragraph direction. End Hebrew sentences with a
  Hebrew word before the period (same rule as chat).
- Code blocks: separate paragraphs **without** `w:bidi`, monospace font, left-aligned.

## Lists, tables, numbers

- Lists in an RTL paragraph put the bullet on the right automatically once `w:bidi` is set.
- Tables: `<w:bidiVisual/>` in `w:tblPr` makes the first column the rightmost. Set it for Hebrew tables.
- Page numbers and headers/footers are separate parts (`header1.xml`, `footer1.xml`): set `w:bidi` there too.

## Checklist

1. `w:bidi` on every Hebrew paragraph or on its style.
2. `w:rtl` on Hebrew runs; none on English runs.
3. Complex-script font set (`w:rFonts w:cs`), e.g. David, Arial, Noto Sans Hebrew.
4. Tables with `w:bidiVisual`.
5. Run `scripts/check_docx_rtl.py file.docx` — it must report 0 paragraphs without RTL.
