# Economics, accounting and business

## Degrees covered

- Economics (כלכלה), Economics and Management, Behavioural Economics.
- Accounting (חשבונאות), Accounting and Information Systems, Finance (מימון), Business Administration (מנהל עסקים, BA/MBA).
- Industrial Engineering and Management (the management half), Logistics, Hotel and Tourism Management, Public Administration (the budget side).

## Typical deliverables

- Problem sets: optimisation, equilibrium, elasticities, game-theory matrices, macro models with graphs.
- Econometrics projects: dataset, regression, diagnostics, interpretation (Stata/R output plus a write-up).
- Accounting exercises: journal entries, adjusting entries, financial statements, consolidation, tax calculations per Israeli standards.
- Finance: valuation models (DCF, NPV/IRR), portfolio exercises in Excel.
- Case studies (Harvard-style) with a recommendation memo; group business plans with a pitch.
- Exams: calculation + short explanation; accounting exams are long, procedural and graded line by line.

## Answer conventions

- Economics answers combine three layers: the model in symbols, the graph with labelled axes and curves, and one sentence of intuition. A graph without labels earns little.
- State assumptions (perfect competition, ceteris paribus, rational expectations) before deriving.
- Optimisation: objective, constraint, Lagrangian or substitution, first-order conditions, solution, second-order or economic sanity check.
- Regression results: coefficient, standard error, significance, interpretation in units ("one extra year of schooling is associated with 7.2% higher wages, holding experience constant"), and the identification caveat.
- Accounting: debits and credits balance in every entry; amounts in the course's currency with thousands separators; dates and account names exactly as the chart of accounts gives them; working papers shown.
- Finance: cash-flow timeline drawn; discount rate justified; sensitivity analysis on the key assumption.
- Case memos: recommendation first (bottom line up front), then analysis, alternatives and risks.

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| Spreadsheets and models | Excel (campus) | Google Sheets, LibreOffice Calc |
| Econometrics | Stata (campus), EViews | R (fixest, lm), Python statsmodels, gretl |
| Data | Bank of Israel, CBS (הלמ"ס), FRED | Same — all free |
| Graphs for answers | Excel charts, R ggplot2 | Desmos, GeoGebra |
| Accounting practice | Course software (Priority, Hashavshevet) | Spreadsheet templates |
| Financial data | Bloomberg/Refinitiv (lab) | TASE site, Yahoo Finance |
| Writing | Word | Google Docs |

## What graders look for

- Correct model and correctly labelled graphs; shifts shown with arrows and new equilibria marked.
- Intuition that matches the math; signs of effects stated and explained.
- Regression interpretation in real units, with causal language only when the design justifies it.
- Accounting entries that balance, follow the relevant standard (IFRS / Israeli GAAP) and are traceable to the source document.
- Excel models that are auditable: inputs separated from calculations, no hard-coded numbers in formulas.
- Recommendations that follow from the analysis and acknowledge risks.

## Common mistakes

- Confusing movement along a curve with a shift of the curve; mislabelled axes.
- Marginal vs average confusion; nominal vs real; percent vs percentage points.
- Interpreting correlation as causation in regressions; ignoring omitted-variable bias.
- Log-model interpretation errors (a coefficient on log(x) is not a unit effect).
- Accounting: reversing debit/credit; missing accruals; wrong period.
- NPV with inconsistent timing (annual rate on monthly flows).
- Case memos that summarise the case instead of recommending.

## Default citation style

APA 7 or Chicago author-date; economics journals use author-year (AEA style). Data sources are cited with the publishing body, series name and retrieval date. The course syllabus always overrides this default.

## Worked breakdown

Invented assignment: "Econometrics project — returns to education in Israel" in a second-year course. Deliverables: a Stata/R script, a 6-page report, due in 3 weeks; 25% of the grade; pairs.

| Part | Type | Weight | Depends on | Estimate |
|---|---|---|---|---|
| 1. Data cleaning from the provided CBS survey extract | practical | 15 | — | 3 h |
| 2. Baseline OLS of log wage on schooling and experience | analysis | 20 | 1 | 2 h |
| 3. Diagnostics: heteroskedasticity, robust SEs, functional form | analysis | 20 | 2 | 2 h |
| 4. Extension: add controls or an interaction, discuss omitted-variable bias | analysis | 20 | 3 | 3 h |
| 5. Report: question, data, results table, interpretation, limitations | essay | 25 | 2–4 | 4 h |

Suggested order: explore the data and plot wage against schooling before any regression; baseline; diagnostics; extension; write the report around one clean results table. Environment: R with `fixest` and `modelsummary`, or Stata with `esttab`. Review first: the lectures on OLS assumptions and log-linear interpretation. Constraints to check: which variables are allowed, the table format the lecturer wants, and whether code must be submitted.
