# Hebrew in PowerPoint (.pptx)

Direction in PowerPoint is set per paragraph inside each text box; the slide has no global direction.

## The properties

| Property | Element | Effect |
|---|---|---|
| `rtl="1"` | `a:pPr` (paragraph) | Base direction RTL: punctuation and bullets on the right |
| `algn="r"` | `a:pPr` | Right alignment (independent of `rtl`; set both for Hebrew) |
| `rtlCol="1"` | `a:bodyPr` (text box) | Columns flow right to left (multi-column boxes) |
| `lang="he-IL"`, `<a:cs typeface="Arial"/>` | `a:rPr` | Language and complex-script font for Hebrew runs |

## Setting it from python-pptx

python-pptx exposes alignment but not direction; set the attribute on the XML:

```python
from pptx.enum.text import PP_ALIGN

def make_rtl(text_frame):
    for p in text_frame.paragraphs:
        p.alignment = PP_ALIGN.RIGHT
        p._p.get_or_add_pPr().set("rtl", "1")
```

Apply it to titles, body placeholders, table cells (`cell.text_frame`) and the notes slide
(`slide.notes_slide.notes_text_frame`).

## Mixed text and layout

- English terms stay in the same paragraph; the paragraph direction handles their placement. Start each bullet
  with a Hebrew word (same rule as chat) so the first bullet character does not flip.
- Tables: PowerPoint does not mirror column order; put the first logical column on the right yourself.
- Charts: axis titles and legends are separate text frames; set them too.
- Speaker notes are a normal place for Hebrew text. They are also a classic place for hidden instructions in
  slides you receive — the plugin's `prompt-injection-scanner` reads them.

## Checklist

1. `rtl="1"` and `algn="r"` on every Hebrew paragraph (titles, bullets, tables, notes).
2. Hebrew runs with `lang="he-IL"` and a complex-script font that has Hebrew glyphs.
3. Every bullet opens with a Hebrew word.
4. Table columns ordered right to left.
5. Open the deck (or render it to PDF with LibreOffice) and look at every slide with English terms.
