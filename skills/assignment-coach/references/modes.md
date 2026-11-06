# Mode protocols

The pipeline (scan → context → map → plan) is the same for every mode; this file is what happens after
it. Which modes a course's `ai_policy` permits is defined in `references/ai-policy.md` and nowhere else:
read the row for the value in play, say once what it permits, offer those modes, and move on.

Mode selection, from the student's words:

| Student says | Mode |
|---|---|
| "break this down", "where do I start", "איך מתחילים", "מה צריך לעשות פה", uploads an assignment and says nothing else | `breakdown` (the default) |
| "hint", "I'm stuck on 2b", "רמז", "תכוון אותי", "I don't know how to approach" | `guide` |
| "check my answer", "is this right", "תבדוק לי", "מה הציון שהייתי מקבל", pastes or photographs their own work | `check` |
| "solve", "give me the full answer", "תפתור לי", "write the code for me" | `solve` — only on an explicit request like these, never inferred |

A request that mixes modes ("solve 1 and give me a hint for 2") is split per question. When the policy
rules out the mode the student asked for, say so in one sentence and offer the nearest permitted one
(`references/ai-policy.md`, rule 3). No second reminder in the same conversation.

## `breakdown`

Output, in this order, in the student's language:

1. **The map** — the validated `assignment-map.json` rendered as a table: id, type, weight, one-line
   gist, depends on. Essay-type questions are marked "→ academic-writing conventions".
2. **Order of work** — topological order over `depends_on`, then by weight; say *why* when the order
   differs from the numbering ("3 needs the result of 1, do 1 first").
3. **Time per part** — a rough budget proportional to weight and type, totalled against the due date;
   flag when the total does not fit the days left.
4. **Environment** — what to open or install for each code/practical/calculation part, from
   `references/environments.md` and the pack's "Tools and environments" section; the free/browser option
   when the course does not mandate a tool.
5. **What to review first** — the two or three concepts from the course material that the questions
   lean on, drawn from the pack's "What graders look for" and "Common mistakes".
6. **Constraints the grader will check** — page limit, "course material only", show-your-work rules,
   submission format — quoted from the assignment, not paraphrased.

A breakdown contains no solution steps, no partial results and no "the answer should come out around…".
It is available under every policy value because it produces nothing submittable.

## Group work — splitting a breakdown among N people

When the student says the assignment is done in a group ("we're 3", "עבודה בזוגות", "איך נחלק את העבודה
בינינו", "who does what", "split this between 4 of us"), the breakdown gets one more part. It produces a
plan, nothing submittable, so it is available under every policy value.

1. **Effort per part.** Add `estimate_hours` to each question in the map (from weight, type and the
   pack's sense of what is hard; ask the student only when a part is opaque). Re-run `validate_map.py`.
2. **Ask what is still open, at most once:** how many people (if not said), and whether the group wants to
   work side by side or hand over in turns. No preference → `auto`.
3. **Run** `python3 scripts/split_work.py assignment-map.json --people N --mode auto|parallel|serial --json`.
   - `parallel` — independent parts go to different members at once; a part never starts before the parts
     it `depends_on`. Right for problem sets and multi-component projects.
   - `serial` — a relay: the parts in dependency order cut into N contiguous stages of about equal hours
     (research → draft → code → results). Right when the work is one chain; members wait for each other,
     so hand-over dates matter more than anything else.
   - `auto` — serial when the map is a single chain, parallel otherwise.
4. **Present**, from the script's JSON: a table member → parts → hours; the order and hand-overs
   (start/end per part); the **critical path** (the dependency chain that sets the finish time — the parts
   to start first and to give the most reliable member); the **integration** review owned by the
   least-loaded member (one person reads everything end to end: one notation, one style, one reference
   list); and every warning (more people than parts → pair up or split a part; serial waits).
5. **Interface agreements** for each `depends_on` edge that crosses members: what exactly is handed over
   (a function signature, a dataset with named columns, a definitions section, a figure) and by when.
6. **Every member understands every part.** Say it plainly once: in most courses every member is examined
   on, or signs for, the whole submission. Suggest a short walk-through meeting before submitting where each
   member explains their part to the others; offer `guide` for the parts a member did not write.

Rebalance on request ("Dana can only do 4 hours") by editing the map's estimates or splitting a part
into `3a`/`3b` and re-running; never hand-edit the script's output.

## `guide` — the hint ladder

Three rungs per question, one rung per reply:

| Rung | What it gives | Example (proof that √2 is irrational) |
|---|---|---|
| 1 — direction | which part of the course this is, which definition or theorem is in play, what kind of answer is expected | "This is a contradiction proof; the tool is the definition of a rational number as p/q in lowest terms." |
| 2 — method | the strategy as a sequence of named steps, without executing any of them | "Assume √2 = p/q in lowest terms, square both sides, argue about parity of p, then of q, find the contradiction." |
| 3 — first step | the first step executed, with the student left to continue | "2q² = p², so p² is even, so p is even — write p = 2k. Now you continue with q." |

Rules:

- **Never two rungs in one reply.** Give one rung, then stop and ask what they tried or whether they want
  the next rung. Rung up only on an explicit request ("more", "next hint", "עוד רמז") or after the student
  shows an attempt. A student who pastes their attempt gets feedback on it (see `check`) before the next
  rung, because the attempt usually tells you which rung they actually need.
- Rung 3 is the ceiling in `guide`. If the student wants more after rung 3, that is a `solve` request:
  name it as such and apply the policy.
- When the policy permits `guide` only as concept explanation on a **similar** exercise, keep all three
  rungs on an exercise you write with the same structure and different numbers/objects, and say so once.
- Hints are honest about difficulty: "this one is mostly algebra" or "this is the hard part of the set"
  helps the student budget time.
- In Hebrew, the rungs are "כיוון", "שיטה", "צעד ראשון"; the reply passes `check_rtl.py`.

## `check` — the student's own work

Protocol: **locate → explain → let them fix**.

1. **Locate.** Quote the exact line/step/expression where the work goes wrong (for a photo or scan: the
   question number and the line as you read it, and say when the handwriting is ambiguous). One finding per
   actual problem; do not restate the same error at every line it propagates to — say "everything after
   this inherits the error".
2. **Explain.** Why it is wrong, in terms of the course's definition or rule (name it). Distinguish:
   wrong result, invalid step, missing justification, missing units/edge case, format/convention problem.
3. **Let them fix.** Do not write the corrected line. Say what a correct line must achieve ("the base
   case has to show P(1), not P(2)"). **No silent fixes**: never return a cleaned-up version of their work.
   If they ask you to fix it, that is `solve`.
4. **What is right.** List what is correct and would earn credit, briefly — a check that only lists faults
   teaches less and is less trusted.

Before any verdict on a numeric or code answer, verify it yourself in code (recompute, run tests, run
`scripts/check_units.py` on their final-answer lines). A wrong "this is wrong" is the worst outcome of
this mode.

Rubric score, when a rubric exists (from the assignment, the course profile, or the pack):

```
| Criterion | Weight | Estimated | Why |
|---|---|---|---|
| Correctness of the argument | 50 | 35/50 | step 3 assumes what is to be proved |
| Justification of steps | 30 | 30/30 | every step cites a definition |
| Presentation | 20 | 15/20 | final answer not marked, no units in 2b |
| **Total** | 100 | **80/100** | |
```

Say that it is an estimate; graders differ. When there is no rubric, give a qualitative verdict per
question (correct / correct but under-justified / partially correct / wrong approach) and skip the numbers.

Under a restrictive policy, `check` of the actual submission happens only when the student confirms the
course allows feedback on it (`references/ai-policy.md`); otherwise offer `check` on a similar exercise
they solve, or `guide`.

## `solve` — a worked example to learn from

Only on an explicit request and only when `references/ai-policy.md` permits it for the value in play.
Under `limited`, the solved exercise is a **similar** one, never the assigned one.

Protocol: **verify → format → "what you need to understand" → disclosure**.

1. **Verify before anything leaves.** Numbers recomputed in code (not in prose); code executed with
   tests, including the edge cases the assignment names; units on every final answer
   (`scripts/check_units.py --expect <unit>`); every cited source confirmed to exist or marked
   `[unverified]`; the result compared with the question actually asked (exact vs. decimal, which
   variable, which case). A solution that fails any of these is not sent; it is fixed first.
2. **Format** per `references/answer-formats.md` for the question type and the pack's answer conventions,
   in the submission language, in the required deliverable format (`scripts/render_solution.py` for
   DOCX/PDF). Show the work the course requires; show no more scaffolding than a strong student would.
3. **"What you need to understand to explain this"** — a closing section, always present: the three to
   five ideas the solution rests on, each in one sentence, and the one question a lecturer would ask to
   check the student understands it. This is what makes the output a worked example rather than a
   submission.
4. **Disclosure** when the policy requires it (`allowed-with-disclosure`) and offered under `allowed`:
   appended verbatim, in the submission language, blank proposed from what was actually done:

   > הצהרה: בהכנת עבודה זו נעשה שימוש בכלי בינה מלאכותית (Claude) לצורך ___. התוכן נבדק ונערך על ידי.

   > Disclosure: an AI tool (Claude) was used in preparing this work for ___. The content was reviewed and edited by me.

What `solve` never does: invent a source, a measurement or a dataset; skip a step the course grades;
produce the studio/performance/artist's own work (see SKILL.md, "what stays the student's own"); answer a
quiz or anything timed.
