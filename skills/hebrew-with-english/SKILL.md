---
name: hebrew-with-english
description: "Write Hebrew with English technical terms so it renders right-to-left correctly, in chat and in files (Markdown, Word, LaTeX, PowerPoint). Use when the user types /hebrew-with-english or /academic-students:hebrew-with-english, when they complain that lines come out flipped, mirrored or with punctuation on the wrong side (\"השורות יוצאות הפוכות\", \"הנקודה קופצת\", \"הטקסט מתהפך\"), when they ask for a Hebrew document/summary/slide deck that contains English terms, or when another skill in this plugin is about to write Hebrew prose into a file. Once invoked, keep applying it to every later reply until the user says to stop. Do not trigger just because the user wrote in Hebrew, and not for translation requests."
license: MIT
---

# Hebrew with English (RTL-safe writing)

## Purpose

Mix Hebrew prose with English technical terms without breaking right-to-left rendering — in the chat UI, in
Markdown files, and in Word, LaTeX and PowerPoint documents. The failure this skill prevents looks small (a line
that starts with an English word flips to left-to-right, punctuation jumps to the wrong side) and reads as broken
to every Hebrew reader. The skill never translates technical terms: commands, identifiers, product names and
terms of art stay in English inside Hebrew sentences.

## When this triggers

- The user invokes it (`/hebrew-with-english`, `/academic-students:hebrew-with-english`) — then it stays on for
  the whole conversation until they say to stop.
- The user complains about direction: "השורות יוצאות הפוכות", "הנקודה קופצת לצד השני", "the Hebrew is mirrored".
- The user asks for Hebrew output that will contain English terms: a summary, a report, a `.docx`, a LaTeX
  section, slides.
- Another skill in this plugin (assignment-coach, academic-writing, exam-prep, lecture-notes, study-planner,
  moodle-sync) is about to write Hebrew prose into a file.

Not for: translating a text into English, questions about Hebrew grammar, or a Hebrew message that needs no
special handling (plain prose with no English tokens renders fine on its own).

## Workflow

1. **Pick the output format** and read the matching reference before writing:
   - chat reply or Markdown file → `references/chat-markdown.md` (the core rules: every line opens with a Hebrew
     word, punctuation anchoring, tables, code-block neighbours, bold labels).
   - Word document → `references/docx.md` (`w:bidi` on paragraphs, `w:rtl` on runs, styles, fonts).
   - LaTeX → `references/latex.md` (`polyglossia`, `\textenglish`, fonts, math inside Hebrew).
   - PowerPoint → `references/pptx.md` (`rtl="1"`, `rtlCol`, complex-script fonts).
2. **Terminology.** Look up the course's discipline family in `references/glossary/` (12 families; rule set in
   `references/glossary/README.md`): first mention = Hebrew term with the English in parentheses, afterwards
   whichever the course uses. A `COURSE.md` in the course folder may override individual terms.
3. **Write with the opening word chosen first.** For every line, heading, bullet, bold label and table cell,
   decide the Hebrew opener before the rest of the line. Fixing afterwards is where slips survive.
4. **Verify mechanically** (next section) before sending or saving. Then send the checked text word for word.

## Files in this skill

- `references/chat-markdown.md` — the rules, the high-risk spots table, the list of natural Hebrew openers.
- `references/docx.md`, `references/latex.md`, `references/pptx.md` — how direction works in each format and how to set it from code.
- `references/glossary/README.md` + `references/glossary/<family>.md` — Hebrew ⇄ English term pairs per discipline family.
- `scripts/check_rtl.py` — checks Markdown/chat text; `--fix` prints a suggested rewrite per failing line (never edits); `--json`.
- `scripts/check_docx_rtl.py` — lists Hebrew paragraphs in a `.docx` that lack `w:bidi` (resolves style inheritance); `--json`.

## Verify before sending (mandatory)

A mental read-through is not enough; the eye reads the content of a line and skips its first word. The check is
mechanical:

**When a shell is available** and the reply has any list, table, heading or bold label, or is longer than about
eight lines:
1. Write the full draft to a scratch file (`rtl_draft.md` in the scratch directory).
2. Run `python3 scripts/check_rtl.py rtl_draft.md --fix` (path relative to this skill folder).
3. Fix every ERROR and WARNING — the `→` suggestions are first candidates, not final wording — and re-run until
   it reports `0 errors, 0 warnings`.
4. Send the corrected draft word for word. Do not retype it from memory.

For a Word file: `python3 scripts/check_docx_rtl.py out.docx` must report 0 paragraphs without RTL.
For LaTeX: compile with XeLaTeX/LuaLaTeX; "Missing character" warnings mean a font without Hebrew glyphs.

**When no shell is available**, list to yourself the first word of every line (each heading, bullet, bold label,
table cell, the lines around each code block, and the last line) and confirm each is Hebrew; do the same for the
last token before each line's final punctuation. Fix any line that fails using rule 2 of the chat reference.
Two slips survive this check most often, so look for them by name:
- **The first sentence after a heading that opens with a name** (`Marvel היא…`, `Python היא…`). Put a Hebrew
  noun first: `החברה Marvel היא…`, `השפה Python היא…`.
- **Hebrew inside a code block** (comments, strings): it renders reversed. Comments in code are English;
  the Hebrew explanation goes in the prose after the block.
- **An English name followed by a number in parentheses** (`*Iron Man* (2008)`): the number renders on the wrong
  side of the name. Write the number in Hebrew words around it: `הסרט *Iron Man* משנת 2008`.

Skip the check only for a short reply of plain sentences with no list, table, heading or label.
