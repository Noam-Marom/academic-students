# Practice questions, solutions, flashcards and mock exams — quality rules

Exam practice is the one place in this plugin where a full solution is the right output: nothing here is
submitted, the student is training. The quality bar is therefore not "is it allowed" but "does it train the
right skill".

## 1. New questions, same skill

A practice question is **new** when all three hold:

1. **New numbers or new objects.** Different values, a different graph, a different function, a different
   case, a different statute, a different data set. Changing one number in the original is not new.
2. **New surface context.** If the original was about a printer queue, make it an elevator, a hospital triage
   line, a ticket office. The student must recognise the pattern, not the story.
3. **Same skill, same type, same difficulty ± 1.** The topic map told you what was examined; the practice
   question trains exactly that skill. Do not drift to a harder or more interesting problem than the course asks.

Never reproduce a bank question verbatim or near-verbatim as a "practice" question. The student already has
those: that is what the past exams are for. The one case for reusing a bank question is explicitly labelled
re-doing a past exam under conditions (see mock exam below), and then it is presented as the original.

Mechanical check before sending: normalise your practice question the same way `scripts/question_bank.py`
normalises (nikud, numbering, punctuation, whitespace) and make sure it is not already in `bank.json`
(`question_bank.py add` on a copy of the bank returns exit 1 if it is). Also eyeball that no sentence longer than
eight words is copied from a bank question.

## 2. Solutions

Full, worked, and in the format the course grades — the discipline pack's "Answer conventions" section says what
that is. In every family:

- Start with what is given and what is asked (one line each), then the method, then the steps, then the answer.
- Show the step a grader would deduct points for skipping (the base case, the units check, the assumption test,
  the citation of the rule being applied).
- End with **one** of: a sanity check (order of magnitude, limiting case), a common wrong answer and why it is
  wrong, or the single idea the question tests. Pick the most useful; do not write all three.
- Numbers are recomputed in code before they are sent (a Python one-liner in the scratch directory is enough).
  Code is run. A proof is re-read for a hidden use of the thing being proved.
- Mark anything that goes beyond the course material **[הרחבה]** / **[beyond the course]** so the student does
  not learn a method the exam will not accept.

Solutions are revealed **after** the question, under a heading or in a separate file (`solutions.md`), never
inline — the student has to be able to try first.

## 3. Hint ladder (when the student asks for help on a practice question)

Three rungs, one at a time, next rung only on request or after an attempt:

1. **Direction** — which topic / which theorem / which section of the notes.
2. **Method** — the approach in one sentence, no numbers.
3. **First step** — the first line of the solution, then stop.

Then the full solution. The same ladder `assignment-coach` uses, so the student meets one habit.

## 4. Flashcards (Anki)

Cards go to `scripts/anki_export.py` as `[{"front", "back", "tags"}]`.

- One fact or one skill per card. "Define a semaphore" is a card; "Explain synchronisation" is not.
- Front: a question or a cue, not a heading. Back: the answer in ≤ 3 lines, plus the one detail that is usually
  forgotten.
- Formulas: write them in `$...$` (inline) or `$$...$$` (display); the exporter converts to MathJax delimiters.
- Tags: the topic exactly as it appears in `bank.json` (spaces become underscores), plus the course code when
  known. Example: `["תזמון_CPU", "202-1-3031"]`.
- Cloze-style cards are fine as plain front/back pairs ("The time complexity of heap-sort is …" / "O(n log n)").
- Hebrew cards need no special handling; Anki renders each field's direction on its own. Mixed Hebrew–English
  fields still follow the `hebrew-with-english` rule inside the field: start with the Hebrew word.
- Aim for 20–40 cards per topic that the map ranks high, 5–10 for the rest. More than ~150 cards for one exam is
  a sign of copying the notes rather than extracting what is tested.

## 5. Mock exam under course conditions

`scripts/mock_exam.py` samples the questions; this section is about how to present them.

- **Weights** come from the topic map: use the points share per topic (`stats --json` → `points` ÷ total), not
  raw counts, so a 30-point recurring question weighs more than three 5-point definitions.
- **Length and time** match the real exam when known (number of questions, total points, minutes, allowed
  materials — "דף נוסחאות בעמוד אחד", "closed book", "calculator allowed"). Unknown → ask it as one of the two
  profile questions, or default to the most recent past exam's shape and say so.
- **Header** on the mock: course, "מבחן דמה / mock exam", time allowed, materials allowed, points per question,
  the seed (so the same mock can be regenerated: `--seed N`).
- **Questions** can be bank questions (a real past exam re-done under conditions) **or** new practice
  questions. Say which: a mock built from bank questions is labelled "from the exams of 2022–2024"; a mock of
  new questions is labelled "new questions in the style of 2022–2024".
- **Solutions** go to a separate file or a clearly separated section the student opens after the time is up.
- **Grading after the attempt**, when the student sends answers: per question, points awarded and the reason for
  every point lost, in the course's grading conventions (partial credit rules from the discipline pack). Then one
  paragraph: the two topics to review first, pointing at the topic map.

## 6. Language

Practice questions and solutions are in the course's teaching language (`COURSE.md: language`), the exam's
language when the two differ. Hebrew output starts every line with a Hebrew word and is checked with
`hebrew-with-english/scripts/check_rtl.py` before it is sent (see SKILL.md, "Verify before sending").
