# Grading protocol

How the judge turns instructions and a piece of work into a grade it can defend line by line.

## Contract

1. **Requirements.** Go through the instructions and number every explicit requirement: `R1` … `Rn`. Quote
   each one (shortened with … when long) with where it appears. "Explain", "justify", "use only course
   material", "include a figure", "max 1,500 words" are all requirements. An implicit expectation of the
   field (units on a final answer, a reference list) comes from the discipline pack and is marked `pack`.
2. **Rubric.**
   - An official rubric (in the assignment, on Moodle, in `COURSE.md`) is used exactly as given: its
     criteria, its weights, its level descriptions. Do not merge, split or reweight it.
   - No rubric → a **derived rubric**, labelled "derived rubric" in the report: one criterion per question
     with its stated points, or, for continuous work, the requirements grouped into 4–6 criteria weighted by
     how much of the instructions they take, plus the pack's "What graders look for". Say how it was derived
     in one line.
3. **Hard constraints.** Length, format, language, file type, citation style, deadline, collaboration rules.
   For each: is it met (measure it — count the words with a script, check the page count), and what penalty
   do the instructions attach? Only a stated penalty becomes a `penalties` entry in `scores.json`. An
   unstated one is reported under "risks" with no points.

## Passes

**Pass A.** For every criterion, in rubric order:
- the level or score, on the criterion's own scale;
- **evidence**: a quote of at most 25 words from the work with its location (page, question, line), or the
  element that is missing ("no justification for step 3");
- the reason, tied to a requirement (`R4`) or a pack rule;
  phrased as the rule that was broken, never as the corrected value or line;
- for numeric and code answers, the verification you ran (recomputed value, test that failed).

Grade what is on the page. Do not give credit for what the student "probably meant", and do not deduct for a
method that differs from the lecturer's when the instructions allow any valid method.

**Pass B** is blind to Pass A's numbers. By default it runs in the same context: grade the criteria in reverse
order, from a fresh read of the work, without scrolling back to Pass A's scores. Pass B records its own
evidence. In `strict` mode, or when the student asks for it, use a separate subagent that receives only the
contract and the work, never Pass A (slower, more independent).

**Reconcile.** `scripts/score_rubric.py` flags a criterion when the passes differ by more than 15% of its
maximum (exit 1). For each flag: put the two pieces of evidence side by side, decide which reading of the
work and the requirement is right, replace the outlier with the reconciled score, and run the script again.
Report the final range from the passes that remain.

The scores, piped to `scripts/score_rubric.py -` on stdin (or saved as `scores.json` in the scratch directory):

```json
{"criteria": [{"id": "Q1", "name": "Q1 proof", "max": 30, "passes": [24, 26]}],
 "penalties": [{"reason": "R7: 2 days late, 5 points per day", "points": 10}],
 "scale": {"max": 100, "pass": 60}}
```

## Deductions

- No named rule, no deduction. A correct answer that meets every requirement gets full marks; a nitpick a
  stricter grader *might* raise is listed under risks with no points.
- One fault, one deduction: an error carried forward into later steps costs once unless the rubric says
  otherwise ("follow-through" marking is the default in calculation courses).
- A correct answer reached by an unjustified step loses the justification points, not the answer points.
- Presentation and language are graded only as far as the rubric or the requirements weigh them.
- When the work is ambiguous, grade the reading a fair grader would take and say there was ambiguity.

## Report

1. The persona line.
2. **Estimated grade** — `final` on the course's scale and the `range`, pass or not when the pass mark is
   known; whether the rubric is official or derived.
3. **Per criterion** — table: criterion · max · score · evidence (quote + location) · why points were lost.
4. **Penalties and risks** — stated penalties applied, unstated risks listed.
5. **What would raise the grade most** — 3 to 5 items ordered by points gained per hour of work: where,
   which requirement, what a fix must achieve. Never the fixed text itself.
6. **What already earns credit** — brief, specific.
7. The caveat line from SKILL.md.

`compare` puts the two versions' tables side by side and lists the criteria that moved. `rubric` gives
sections 3 (as "what full marks looks like" per criterion), 4 and the most common ways to lose points, with
no grade. `strict` adds a second grade line, "harshest plausible grader", under the normal estimate.
