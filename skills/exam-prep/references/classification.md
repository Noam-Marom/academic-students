# Classifying past-exam questions

Every question of every past exam becomes one object in `bank.json` (`scripts/question_bank.py`). The
classification is what makes the topic map honest: if two graders would tag the same question differently, the
frequency table is noise. This file gives the anchors so the tags are consistent across exams and across sessions.

## The question object

```json
{"text": "the question, verbatim, including sub-items (a), (b)...",
 "topic": "one topic from the course's topic list",
 "type": "proof | calculation | code | short-answer | essay | multiple-choice | design | analysis | practical | other",
 "difficulty": 1,
 "points": 20,
 "year": 2024,
 "source": "2024-moed-a.pdf, Q3",
 "solution": null}
```

`solution` stays `null` at classification time. Solutions the exam came with go into the bank as-is; solutions
you write go in later, marked `"solution": "[written by Claude] ..."`, so the student can tell them apart.

## Splitting an exam into questions

- One numbered question = one object, **with** its sub-items. "3(a)…3(d)" is one question of type by its
  dominant sub-item; split only when the sub-items are on clearly different topics (then `source` says `Q3a`, `Q3b`).
- A question that gives a choice ("answer two of the following three") becomes one object per option, each with
  the points one option is worth, and a note in `source`: `Q5 (choose 2 of 3)`.
- Shared preamble ("The following three questions refer to the system described below…") is copied into the
  `text` of each question it belongs to; otherwise the question is meaningless on its own.
- Points: as printed. If the exam does not print them, divide 100 by the number of questions and say so in the
  topic map ("points estimated: the exam did not print them").
- Year: the exam's academic year as an integer (`2024` for תשפ"ד/2023–24; take the later calendar year). Moed A/B
  of the same year are two sources with the same `year`; the map shows years, the bank shows sources.

## Topic

Use the **course's own vocabulary**, in this order of preference:

1. the syllabus or `COURSE.md` topic list, when either exists;
2. the lecture or chapter titles in the course material the student handed over;
3. the discipline pack's typical topics (`references/disciplines/<family>.md`, "Typical deliverables" and
   "Worked breakdown");
4. your own label, lower-case, 1–3 words — and then reuse it exactly for every later question.

Keep the list short (6–15 topics for a semester course). A question that touches two topics gets the one it is
graded on: a dynamic-programming question that happens to use recursion is `dynamic programming`.

Record the topic in the course's teaching language, so the student recognises it on the topic map and the Anki
tags. English identifiers inside a Hebrew topic are fine (`תזמון CPU`).

## Type anchors

| Type | You see | Typical in |
|---|---|---|
| `proof` | "prove", "show that", "הוכיחו", "הראו כי"; a claim with quantifiers | math-stats, computing (theory), physical-sciences |
| `calculation` | numbers in, a number or expression out; units; "compute", "חשבו" | engineering, physical-sciences, economics-business, math-stats |
| `code` | write/complete/trace a program; pseudo-code accepted or required | computing, engineering |
| `short-answer` | define, explain in 2–3 sentences, "הגדירו", "הסבירו בקצרה"; ≤ 10 points | every family |
| `essay` | compare, discuss, evaluate, "דונו"; ≥ half a page expected | humanities, social-sciences, law, arts |
| `multiple-choice` | options a–e or Hebrew letters; one or more correct | life-sciences, medicine-clinical, economics-business |
| `design` | propose a system, plan, intervention, experiment; justify choices | engineering, architecture-design, computing, medicine-clinical |
| `analysis` | given a case/data/text/ruling, analyse it against the course's framework (IRAC, SOAP, close reading) | law, medicine-clinical, social-sciences, humanities |
| `practical` | perform a procedure; lab or studio task described on paper | life-sciences, arts, architecture-design |
| `other` | anything that does not fit; say in `source` why | — |

When a question mixes types, tag the type that carries most of the points.

## Difficulty anchors (1–5)

Difficulty is relative to the course, not to you. Anchor on what a student who did the homework needs:

| Level | Anchor |
|---|---|
| 1 | Recall or a one-step application of a definition; the lecture example with new numbers |
| 2 | A standard method applied once, as in the homework; no trap |
| 3 | Two methods combined, or one method with a twist the homework did not have (edge case, changed assumption) |
| 4 | Requires choosing the approach without a hint, or a short original argument; most students lose points here |
| 5 | A result not shown in the course, a construction, or a multi-part problem whose parts depend on each other |

Signals that raise the level: the question is last on the exam; it carries the most points for its length; it
says "in general", "for every", "necessary and sufficient"; it is the only question on its topic in that year.
Signals that lower it: the exam gives the formula, the data table, or a hint ("you may use…").

If you cannot tell, use 3 and move on — difficulty matters least of the five tags for the topic map.

## Recurrence and duplicates

`question_bank.py add` refuses an exact duplicate after normalisation (nikud, numbering, whitespace, punctuation
removed). That refusal **is** information: a question that appears in 2023 and 2024 verbatim is a strong
recurring pattern — record it in the topic map as "recurring verbatim: Q3 (2023), Q2 (2024)".

Questions that are the *same template with different numbers* are not caught by the normaliser. Tag them with the
same `topic` and `type` and write the template in the topic map ("every year: one producer–consumer question
with a bounded buffer, 20–25 points").

## What the topic map says — and what it never says

Say: "appeared in 4 of 5 exams", "average 22 points when it appears", "not examined since 2021", "in the syllabus,
never examined in the exams you gave me".

Never say: "this will be on the exam", "the lecturer always asks…", "you can skip X". Frequency is evidence about
the past; the student decides what to do with it. The one exception is a topic the syllabus names as mandatory
for the exam — quote the syllabus.
