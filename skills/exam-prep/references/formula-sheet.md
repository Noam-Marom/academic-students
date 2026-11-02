# Formula sheet within the allowed page limit

A formula sheet (דף נוסחאות) is only useful if the exam allows it, and only legal if it fits the rule exactly.
Both facts come from the course, not from the plugin.

## 1. Establish the rule first

Before writing anything, know (from `COURSE.md`, the syllabus, the past exams' cover page, or the student):

- **Allowed at all?** Many exams forbid it. If unknown, ask — it is one of the two profile questions. If the
  student does not know, produce the sheet anyway, labelled "for studying; check whether the exam allows it".
- **Size**: pages and sides ("עמוד אחד, צד אחד", "2 sides A4"), paper size, sometimes a font-size floor.
- **Content rules**: formulas only? Worked examples allowed? Handwritten only (then the sheet is a draft the
  student copies by hand)? Must it be submitted with the exam?
- **Provided sheet**: some courses hand out a fixed sheet. Then the job is a *complement* — what the student
  needs that is **not** on the official sheet — and the official sheet's content is excluded.

State the rule in one line at the top of the sheet ("Course rule: one A4 side, formulas only — syllabus §5").

## 2. What goes on it — in this order

1. Formulas the topic map ranks high and that are long or easy to misremember (constants, sign conventions,
   normalisation factors, boundary conditions).
2. Definitions with a precise condition the grader checks (ε-δ, a well-formed statement of a theorem with its
   hypotheses, the elements of a legal test, diagnostic criteria with their thresholds).
3. Procedures as numbered steps in telegraphic form (the hypothesis-test template, the master theorem cases,
   IRAC, the nursing process).
4. Conversion tables and constants, units.
5. One worked micro-example only when the course allows examples and the method is otherwise too abstract.

Leave out: anything the student will remember anyway, derivations, prose explanations, the course's provided
material, trivia from topics never examined (the topic map's "never examined" list is the cut list).

## 3. Fitting the page

Budget per A4 side at a readable size (≈ 10 pt, two columns): about 60–80 short lines or 35–45 formulas with a
label each. Plan the sheet as a table of (item, priority 1–3, estimated lines) and cut from priority 3 up until
it fits. Report what was cut and why so the student can trade.

Layout that survives printing and reading under time pressure:

- Two columns; one topic per block with a bold heading in the course's vocabulary; blocks in the topic map's
  order of weight, heaviest first.
- Every formula labelled with its name and when it applies ("Bayes — when P(B) > 0"); symbols defined once at
  the top in a two-line legend.
- Hebrew blocks: start every line with a Hebrew word (the `hebrew-with-english` rules); formulas themselves are
  LTR and sit on their own line or after a Hebrew label.
- No colour dependence (it will be photocopied), no tiny subscripts in a smaller font than the floor.

## 4. Output formats

- **Markdown** (default): headings per topic, formulas in `$...$`, a note on the page limit. The student pastes
  it into a document or prints it.
- **LaTeX** when the student works in LaTeX or the course requires a typeset sheet: `multicol` two columns,
  `\small`, `geometry` margins 1 cm, Hebrew via `polyglossia` — see `hebrew-with-english/references/latex.md`.
  Compile locally and count pages before sending; a sheet that spills onto a second page breaks the rule.
- **DOCX** when the student says Word: build it as Markdown first, then render via `assignment-coach`'s
  `render_solution.py` when available; RTL paragraphs need `w:bidi`.
- **Handwritten-only rule**: produce the Markdown as a copying draft and say so; order the items so the student
  can copy top-down and stop when the page is full.

## 5. Verify before sending

- The page limit is stated on the sheet and the estimated length is under it (count lines; for LaTeX/DOCX, the
  rendered page count).
- Every formula was checked against the course material (slides, book) or recomputed; a formula from memory that
  could not be checked is marked **[unverified]**, never silently included.
- Nothing from the course's own provided sheet is duplicated when such a sheet exists.
- Hebrew text passes `check_rtl.py` with 0 errors.
