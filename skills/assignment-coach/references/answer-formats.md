# Answer formats, by question type and genre

One section per `type` in the assignment map, then the genre-shaped deliverables that cut across types.
Each gives the skeleton graders expect and a five-line example. The discipline pack
(`references/disciplines/<family>.md`, "Answer conventions") refines these; the pack wins when they differ.

## Contents

- Question types: proof · calculation · code · essay · design · analysis · practical · other
- Genres: lab report (IMRaD) · legal problem (IRAC) · clinical case (SOAP / nursing process) · design
  project · studio and performance work · what stays the student's own

## `proof`

Skeleton: **Claim** (precise, quantifiers stated) → **Proof** (method named; each step with the
definition/theorem that licenses it; base case and inductive step for induction) → **∎**.

```
Claim. For every integer n, if n² is even then n is even.
Proof. By contrapositive: suppose n is odd, so n = 2k + 1 for some integer k.
Then n² = 4k² + 4k + 1 = 2(2k² + 2k) + 1, which is odd by definition.
Hence n² even ⇒ n even. ∎
(Used: definition of odd/even; closure of ℤ under + and ×.)
```

Graders reward: hypotheses stated, the method named, edge cases (n = 0, empty set, equality case).

## `calculation`

Skeleton: **Given** (symbols, values, units) → **Required** → **Solution** (general formula first,
then substitution, intermediate steps with units) → **Final answer** (boxed/bold, units, significant
figures as the course uses) → **Sanity check** (sign, magnitude, limiting case).

```
Given: m = 2.0 kg, a = 3.0 m/s². Required: F.
F = m·a = 2.0 kg × 3.0 m/s² = 6.0 kg·m/s²
**Final answer:** F = 6.0 N
Check: a few newtons for a 2 kg mass at ~⅓ g — plausible.
```

Run `scripts/check_units.py` on the final-answer lines; bare numbers are the most common lost point.
In Hebrew: `**תשובה סופית:** F = 6.0 ניוטון`.

## `code`

Skeleton: **Design** (data structures, invariants, why this approach) → **Implementation** (in the
course's environment and version; identifiers in English even in a Hebrew report) → **Tests** (the cases
from the assignment plus edge cases; how to run them) → **Complexity** (time and space, justified).

```
Design: a min-heap keyed by deadline; invariant: root = earliest task.
Implementation: heap.py — push/pop O(log n), peek O(1); see inline docstrings.
Tests: python3 -m pytest test_heap.py  → 12 passed (empty heap, duplicates, 10⁵ items).
Complexity: build O(n), each operation O(log n); space O(n).
Known limits: not thread-safe (not required by the assignment).
```

Code that was not executed is not an answer. State the exact command used to run it.

## `essay`

An essay-type question inside an assignment follows academic-writing's conventions (thesis → argument
→ evidence → counter-argument → conclusion; citation style of the course). The coach provides the map
entry and the constraints (length, sources allowed) and hands the writing to academic-writing. For the
`solve` mode this means: outline and argument structure here, and the prose through academic-writing's `draft`.

```
Question 3 (essay, 25 pts, ≤ 600 words, course readings only):
Thesis: Weber's bureaucracy is an ideal type, not a description — so "inefficient bureaucracies" do not refute it.
Para 1: the ideal-type method (Weber 1904/1949). Para 2: the six features. Para 3: the objection from
real cases (Merton 1940). Para 4: why the objection misreads the method. Conclusion: what the concept is for.
Sources: both from the course reader; citation style per COURSE.md (apa7).
```

## `design`

Skeleton: **Brief** (requirements and constraints restated) → **Concept** (the idea in one paragraph and
one sketch/diagram) → **Iterations** (what changed and why, with evidence) → **Rationale** (how each
requirement is met; trade-offs) → **Deliverable** in the required format (drawings, model, spec).

```
Brief: a shade structure for a 6×6 m schoolyard, no foundations, budget ₪20k.
Concept: tensile canopy on four existing fence posts; shade factor ≥ 80 %.
Iteration 2: posts cannot take lateral load → added two ground anchors (calc attached).
Rationale: meets shade and budget; trade-off: seasonal removal needed for winter wind.
Deliverables: plan 1:50, section, material list, load check.
```

## `analysis`

Skeleton: **Question and data** (what is asked; source and shape of the data) → **Method** (and why it
fits the data/design; assumptions checked) → **Results** (tables/figures with units and uncertainty) →
**Interpretation** (in the context of the question; limitations) → **Conclusion** (one paragraph).

```
Question: does the new layout reduce checkout time? Data: n = 48 timings per layout, seconds.
Method: Welch t-test (unequal variances; normality acceptable by Q–Q plot).
Result: t(91.3) = 2.41, p = .018, 95 % CI of the difference [1.2, 12.6] s, d = 0.49.
Interpretation: a moderate reduction; the CI excludes zero but the lower bound is small.
Limitation: one store, one week; no randomisation of customers.
```

## `practical`

Lab or field tasks, software exercises, fieldwork logs. Skeleton: **Aim** → **Procedure as performed**
(deviations from the handout noted) → **Observations/raw data** (as recorded, units, uncertainty) →
**Processing** → **Result and error discussion** → **Answers to the handout's questions**, numbered as asked.

```
Aim: measure g with a simple pendulum.
Procedure: L = 0.850 ± 0.002 m; 10 oscillations × 5 trials; deviation: timed 10 not 20 (room time).
Data: T̄ = 1.851 ± 0.006 s.
Result: g = 4π²L/T² = 9.79 ± 0.07 m/s² (error propagation shown in appendix).
Q3: the systematic error is the reaction time at start/stop → dominated by T.
```

## `other`

Anything that fits none of the above (a translation, a reading summary, a peer review, a poster). Use the
pack's "Typical deliverables" and ask the student what the grader has asked for; mirror the structure of
the question in the answer and number parts exactly as the assignment does.

---

## Lab report — IMRaD

**Introduction** (question, background, hypothesis) → **Methods** (reproducible; materials; analysis
plan) → **Results** (figures/tables first, prose that points at them, no interpretation) → **Discussion**
(interpretation, comparison with literature, limitations, next step) → **References**; abstract last.

```
Title: Effect of light intensity on photosynthetic rate in Elodea.
Intro: ends with "We hypothesised that O₂ production rises with intensity and saturates above ~200 µmol m⁻² s⁻¹."
Methods: 5 intensities × 3 replicates, bubbles/min at 22 °C; one-way ANOVA.
Results: Fig. 1 — rate rises to 180 µmol m⁻² s⁻¹ then plateaus; F(4,10) = 18.2, p < .001.
Discussion: saturation consistent with Calvin-cycle limitation (textbook ch. 10); limitation: bubble count ≠ volume.
```

## Legal problem — IRAC (and the Israeli variant)

**Issue** (the legal question, each one separately) → **Rule** (statute section, case law, with
pinpoint citations) → **Application** (facts to rule, both sides, the stronger argument and why) →
**Conclusion** (the answer, hedged as the law requires). Israeli courses often expect the pattern
"שאלה משפטית → הדין → יישום → מסקנה" plus the counter-argument (טענת הנגד) explicitly.

```
Issue: did Dana's email amount to an offer under the Contracts Law (General Part), 1973?
Rule: s. 2 — a proposal is an offer if it shows intent to be bound and is sufficiently definite; CA 1932/90 ...
Application: price and quantity stated → definite; "let me know what you think" → intent doubtful; the
stronger view is an invitation to treat, because ...
Conclusion: likely no offer; therefore no contract on Roi's "yes". Counter-argument: ... (weaker because ...).
```

Citations follow `hebrew-legal` (or the course's style); an authority that cannot be verified is marked
`[unverified]` and never invented.

## Clinical case — SOAP / nursing process

**S**ubjective (what the patient reports) → **O**bjective (vitals, exam, labs, with units and reference
ranges) → **A**ssessment (differential, ranked, with the reasoning) → **P**lan (investigations,
management, follow-up, patient education). Nursing courses use ADPIE: Assessment → Diagnosis (NANDA
wording) → Planning (SMART goals) → Implementation → Evaluation.

```
S: 54 M, 2 h crushing chest pain radiating to left arm, nausea; smoker.
O: BP 150/95, HR 104, SpO₂ 96 % RA; ECG: ST elevation II, III, aVF; troponin pending.
A: inferior STEMI (most likely); DDx: pericarditis (no positional pain), aortic dissection (equal BPs).
P: activate cath lab; aspirin 300 mg PO, ticagrelor 180 mg; morphine titrated; serial troponin; smoking cessation.
Learning point: inferior STEMI — check right-sided leads (V4R) before nitrates.
```

Fictional patients only; never a real record. Doses as the course's formulary states them, with units.

## Design project (architecture, product, UX)

Brief → research (precedents, site/users, constraints) → concept → development (iterations with
evidence: tests, feedback, calculations) → final proposal (drawings/prototype) → rationale and
reflection. Each iteration is dated and says what changed and why — that history is most of the grade.

## Studio and performance work (arts, music, dance, theatre, creative writing)

Process documentation (sketchbook, rehearsal log, drafts), the work itself, a reflection (what was
intended, what happened, what was learned) and an artist statement (first person, 150–300 words,
what the work is about and how it is made). Critique responses use: describe → analyse → interpret →
evaluate.

### Creative and personal work

In studio, performance and creative-writing courses the coach breaks down the brief, explains the
conventions, suggests precedents and, when the student asks, writes or drafts what they ask for. A reflective
journal or artist statement is written from what the student tells you about their own experience: ask the
questions that surface it, and never invent experiences.
