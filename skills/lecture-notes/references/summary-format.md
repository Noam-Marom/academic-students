# Lecture summary format

Every summary has the same five sections, in this order, so a student can scan a semester of summaries the same
way and so `exam-prep` can mine them later. Headings in the course's teaching language.

```markdown
# <course> — lecture <N>: <title from the slides>   (date if known)

## Concepts and definitions          (מושגים והגדרות)
## Formulas                          (נוסחאות)
## Examples                          (דוגמאות)
## Sounds like exam material         (נשמע כמו חומר למבחן)
## Open questions for the lecturer   (שאלות פתוחות למרצה)
```

## 1. Source discipline: what came from the lecture, what did not

- Everything in the summary comes from the slides, the speaker notes, or the transcript, in that order of trust.
  Speaker notes and hidden slides count as source (they are the lecturer's), but say "from the speaker notes"
  or "hidden slide 14" when you use them.
- Anything you add — a clarification, a missing step, a standard definition the lecturer did not state, an
  example of your own — is marked **[הרחבה]** (Hebrew summaries) or **[addition]** (English summaries)
  at the start of that sentence or bullet. The student must always know what the lecturer said and what Claude
  said. Unmarked additions are the one thing this format forbids.
- When the slides and the transcript disagree (a corrected formula, "the slide has a typo"), follow the
  transcript and note it: "the slide says X; in the lecture it was corrected to Y".
- When a transcript passage is unclear (bad audio, a mumbled number), write `[לא ברור בהקלטה]` / `[unclear in
  the recording]` instead of guessing.

## 2. Sections

**Concepts and definitions.** One bullet per term: the term in the course's language, the English term in
parentheses at first mention (the `rtl-writing` glossary rule), then the definition as the lecturer
gave it. Keep the lecturer's wording for definitions; it is what the exam will expect.

**Formulas.** LaTeX in `$...$` or `$$...$$`, each with a Hebrew/English label line, the meaning of every symbol,
and the condition under which it applies. Copy formulas from the slides exactly; re-derive or recompute only to
check them, never to "improve" them silently.

**Examples.** The lecture's examples, condensed: given → what was asked → the key step → the result. A worked
example you add is **[הרחבה]**.

**Sounds like exam material.** Only things with a signal in the source: the lecturer said "this will be on the
exam", "make sure you know", "students always get this wrong", "שימו לב", repeated it, or spent unusual time on
it; or the slide is marked as important. Quote or timestamp the signal (`[00:41:10]` or "slide 12"). Never
predict on your own; no signal → leave the section short.

**Open questions for the lecturer.** Gaps the student may want to ask about: a step skipped on a slide, a
contradiction, an undefined symbol, a question a student asked that was not answered. Phrase them as questions
the student could send.

## 3. Alignment, when there are slides and a transcript

Use `aligned.json` (from `scripts/align.py`): for each slide, the transcript segments spoken over it. Summarise
slide by slide internally, then merge into the five sections. Slides with no speech ("skipped in class") get one
line at the end: "slides 7–9 were not discussed in the lecture".

## 4. Course glossary

New terms go to the course glossary file next to the summaries: `<course>/glossary.md`, a table
`| עברית | English | הגדרה קצרה | הרצאה |` (or the English column order for English courses). Append only terms
that are not already there (compare case- and nikud-insensitively); never rewrite existing rows. Every row
starts with the Hebrew term so the table passes the RTL check. The `rtl-writing` skill reads this file
to keep the course's term choices consistent.

## 5. Length

Aim for one page per 45 minutes of lecture. A summary longer than the slides is a transcript, not a summary.
