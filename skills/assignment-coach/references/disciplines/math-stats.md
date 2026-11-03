# Mathematics and statistics

## Degrees covered

- Mathematics (מתמטיקה), pure and applied tracks; mathematics combined with computer science, physics, economics or philosophy.
- Statistics (סטטיסטיקה), Statistics and Data Analysis, Statistics and Operations Research, Statistics and Data Science.
- Actuarial science and financial mathematics (מדעי האקטואריה, מתמטיקה פיננסית).
- Mathematics teaching tracks (הוראת המתמטיקה) and the B.Sc./B.Ed. mathematics majors in teacher colleges.
- The mathematics service courses every engineering, CS, economics and life-sciences student takes: Infinitesimal Calculus (אינפי), Linear Algebra, Discrete Mathematics, ODEs, Probability, Introduction to Statistics, Numerical Analysis. This pack applies to those courses regardless of the student's own degree.

## Typical deliverables

- Weekly problem sets (תרגילי בית): 4–8 exercises, handwritten and scanned or typeset in LaTeX; usually a small share of the grade but a prerequisite for the exam (מגן).
- Proof-based exams: closed book, sometimes with a one-page formula sheet; points per exercise, partial credit for correct partial arguments.
- Take-home midterms with a strict "course material only" rule.
- Computational statistics projects: a dataset, a research question, an R or Python notebook and a short report with figures and interpretation.
- Statistics exams mixing hand calculation (small samples, tables) with interpretation of printed software output.
- Seminar talk (סמינר) presenting a theorem, paper or chapter: a 45–90 minute board or slide talk plus a written summary.
- Numerical analysis assignments: implement a method, show convergence tables and plots, explain error behaviour.
- Final project or thesis in applied tracks: model, data, code, written report.

## Answer conventions

- A proof is an argument, not a list of equations. Standard shape: state the claim precisely (quantifiers, hypotheses), fix notation, name the method (direct, contrapositive, contradiction, induction, construction), argue each step with the theorem or definition that licenses it, close with a conclusion sentence and ∎ or □.
- Induction needs a visible base case, an explicit inductive hypothesis with the quantifier stated, and an inductive step that actually uses the hypothesis.
- "Show your work" in a calculation means: write the general formula first, substitute, simplify with visible intermediate steps, box or underline the final answer, and add a one-line sanity check (sign, order of magnitude, limiting case).
- Define every symbol you introduce. Distinguish a random variable X from a realisation x, a parameter μ from its estimate x̄ or μ̂, a population σ from a sample s.
- Statistical tests follow a fixed template: hypotheses H₀/H₁ in symbols and words; test chosen and why; assumptions checked (normality, independence, equal variance) with evidence; test statistic and its null distribution; p-value or critical region; decision at the stated α; conclusion in plain language with effect size and confidence interval.
- Report statistics in APA-style notation when the course is applied: t(28) = 2.31, p = .028, 95% CI [0.4, 3.1], d = 0.62.
- Counterexamples count as full proofs of a negative claim; one explicit counterexample, verified, is enough.
- When a theorem is used, check and state its hypotheses (continuity for the intermediate value theorem, finite variance for Chebyshev, independence for the CLT).
- Typeset in LaTeX when the course allows; if handwritten, number every exercise and page and scan in order.

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| Typesetting proofs and reports | LaTeX (TeX Live, TeXstudio) | Overleaf (browser), Typst web app |
| Symbolic computation | Mathematica, Maple | SymPy in Google Colab, SageMathCell, WolframAlpha free tier |
| Plotting functions and geometry | MATLAB | Desmos, GeoGebra (browser) |
| Numerical computation | MATLAB | Octave Online, NumPy/SciPy in Colab |
| Statistical analysis (point-and-click) | SPSS | JASP, Jamovi (both free desktop), PSPP |
| Statistical programming | R in RStudio | Posit Cloud (browser RStudio), R kernel in Colab |
| Probability tables and distributions | Printed tables | `scipy.stats`, R `pnorm`/`qt`, Stat Trek calculators |
| Checking a proof mechanically (optional) | Lean 4 with Mathlib | live.lean-lang.org playground |
| Scanning handwritten work | Flatbed scanner | Microsoft Lens, Adobe Scan (phone, free) |
| Reference management for seminar papers | Zotero | Zotero (free), BibTeX by hand |

## What graders look for

- Logical validity above everything: a correct conclusion reached by an invalid step earns little.
- Every nontrivial step justified by a named definition, theorem or earlier result; routine algebra may be compressed.
- Correct handling of quantifiers and their order ("for every ε there exists δ", not the reverse).
- Edge cases handled explicitly: n = 0 or 1, the empty set, zero denominators, equality cases in inequalities.
- Consistent and defined notation; no symbol appears before it is introduced.
- The right statistical procedure for the design and data type, with assumptions checked rather than assumed.
- Interpretation in the context of the question, not only "reject H₀".
- A clearly marked final answer that matches the question asked (units, exact form vs. decimal, interval vs. point).
- Clean presentation: numbered exercises, readable handwriting or clean LaTeX, no scratch work mixed with the final argument.

## Common mistakes

- Assuming the claim in the course of proving it (circular reasoning), often disguised as "suppose the statement holds".
- Induction with no base case, or an inductive step that never uses the inductive hypothesis.
- Dividing by an expression that may be zero, or taking a square root without checking sign.
- Swapping ∀ and ∃, or negating a quantified statement incorrectly.
- Using a theorem outside its hypotheses (differentiating a function not known to be differentiable, applying the CLT to n = 5).
- Reading p > .05 as "there is no effect", or p < .05 as "the effect is large".
- Confusing the standard deviation of the data with the standard error of the mean.
- Rounding intermediate results, so the final answer is off in the third digit and fails the autograder.
- Ignoring independence or random-sampling assumptions in probability and statistics problems.
- Submitting scratch work: three attempts on the page with no indication of which is the answer.

## Default citation style

Problem sets rarely cite anything beyond "Theorem 4.2 from the lecture notes" or a textbook page, and that is the expected form. For seminar papers and projects the mathematics default is the AMS style (amsplain or amsalpha, numeric, via BibTeX) and the applied-statistics default is APA 7. The course syllabus always overrides this default.

## Worked breakdown

### The assignment

"Problem Set 6 — Markov chains and limit theorems", from a second-year probability course. Deliverables: one PDF (handwritten scan or LaTeX) with exercises 1–3, plus one `.ipynb` or `.py` file and a one-page figure summary for exercise 4. Due in nine days. Constraint from the sheet: "only material covered up to lecture 10".

### Map

| Part | Type | Weight | Depends on | Est. time | Tool |
|---|---|---|---|---|---|
| Q1 Prove the given 3-state transition matrix is irreducible and aperiodic, hence has a unique stationary distribution | proof | 20 | — | 1.5 h | paper / Overleaf |
| Q2 Compute the stationary distribution and the expected hitting time of state 3 from state 1 | calculation | 25 | Q1 (uses existence) | 1.5 h | paper, SymPy to verify |
| Q3 Bound P(|S̄ₙ − μ| > 0.1) with Chebyshev for n = 100, then approximate with the CLT and compare | calculation + short argument | 25 | — | 1.5 h | paper, `scipy.stats` |
| Q4 Simulate the chain for 10⁴ steps, plot empirical state frequencies against the Q2 answer, half-page discussion | code | 30 | Q2 | 2.5 h | Colab (NumPy, matplotlib) |

### Order and timing

1. Review first (1 h): lecture notes 8–10 on irreducibility, periodicity, the stationary-distribution theorem, hitting-time equations, Chebyshev's inequality and the statement of the CLT. Write down the exact statement of each theorem the set will need.
2. Q2 before Q1 is tempting because it is mechanical, but do Q1 first: proving uniqueness tells you what Q2's linear system must look like and catches a mis-copied matrix early.
3. Q2, then verify the stationary vector with SymPy (`Matrix.nullspace`) — verification is allowed, the written solution must show the hand computation.
4. Q4 the same day as Q2 while the numbers are fresh; the simulation is a direct check on Q2 and a wrong answer will show as a persistent gap in the plot.
5. Q3 last; it is independent, and leaving it for day 2 avoids context switching between chain and limit theorems.
6. Final pass (45 min): every exercise ends with a boxed answer or ∎; every theorem used is named; the notebook runs top to bottom from a fresh kernel with a fixed random seed.

Total: about 9.5 hours over three sittings. If time is short, Q4's plot and a two-sentence discussion earn most of its 30 points; polish the discussion last.
