# Physical sciences

## Degrees covered

- Physics (פיזיקה), Astrophysics and Astronomy (אסטרופיזיקה), Physics-Mathematics and Physics-CS double majors.
- Chemistry (כימיה), Chemistry-Biology, Materials Science, Chemical Physics.
- Earth sciences: Geology, Geophysics, Atmospheric and Oceanic Sciences, Environmental Sciences (the quantitative half).
- The physics and chemistry service courses taken by engineering, life-sciences and medicine students: Physics 1–2 (mechanics, electromagnetism), General and Organic Chemistry, Physical Chemistry, Physics Lab. This pack applies to those courses regardless of degree.

## Typical deliverables

- Weekly problem sets: derivations and numeric problems, handwritten or LaTeX, usually a prerequisite for the exam.
- Laboratory reports: aim, theory, setup, measurements with uncertainties, analysis (fits, error propagation), comparison with theory, conclusions. Lab courses have strict templates and pre-lab quizzes.
- Chemistry: lab notebooks checked in real time, synthesis reports with yield and characterisation (NMR, IR, MS), mechanism drawings with arrow pushing.
- Computational assignments: simulations (Monte Carlo, molecular dynamics, numerical ODEs) with plots and convergence discussion.
- Seminar talks on a paper; literature reviews in advanced courses.
- Exams: long derivation problems with partial credit; formula sheets common; a few conceptual short questions.

## Answer conventions

- Start from a physical principle stated in words and symbols (conservation of energy, Gauss's law, second law), not from a formula pulled from a sheet. Derive, then substitute.
- Draw the system: coordinates, forces/fields, boundaries, Gaussian surfaces, reaction coordinates. A labelled sketch is part of the answer.
- Dimensional analysis before and after: check the units of the final expression, then take limiting cases (m → 0, T → ∞, θ → 0) and say what they show.
- Numeric answers: SI units, significant figures matching the data, uncertainty when the inputs have one. Order-of-magnitude estimates are a legitimate answer type when asked for.
- Lab analysis: the fit model is written as an equation with named parameters; residuals are shown or discussed; chi-squared or R² reported with its meaning; error bars on every plotted point; uncertainty propagated with the formula shown once.
- Chemistry: balanced equations with states; mechanisms with every arrow starting at an electron source; stoichiometry tables; yields as actual/theoretical with the limiting reagent identified; safety notes where the course requires them.
- Vectors are marked as vectors; operators distinguished from scalars; indices summed explicitly or with a stated convention.

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| Data analysis and fits | Python (NumPy, SciPy `curve_fit`, Matplotlib), Origin | Colab; Desmos for quick fits; gnuplot |
| Symbolic algebra | Mathematica (campus), Maple | SymPy, WolframAlpha, SageMathCell |
| Simulations | Python, Julia, MATLAB | Colab; VPython (glowscript.org) |
| Molecules and mechanisms | ChemDraw (licence) | MarvinSketch (free academic), ChemSketch, Avogadro |
| Spectra | MestReNova (licence) | nmrium.org (browser), SpectraBase |
| Lab notebooks | Paper notebook (often mandatory), eLabFTW | Benchling (free tier) |
| Typesetting | LaTeX (Overleaf) with `siunitx`, `physics` packages | Typst; Markdown + pandoc |
| Astronomy | Astropy, DS9 | Stellarium (free), astropy in Colab |
| Geoscience | ArcGIS (licence), Petrel | QGIS, Generic Mapping Tools |
| Units and constants | `pint`, `scipy.constants` | NIST CODATA site |

## What graders look for

- The principle named and the derivation shown; a correct number with no derivation earns little.
- Diagrams with coordinates and sign conventions.
- Units, significant figures and uncertainties treated consistently.
- Limiting cases and sanity checks written down.
- Lab reports: raw data preserved, analysis reproducible, discrepancies explained physically (not "human error").
- Plots that stand alone: title, axes with units, legend, fitted curve with parameters and uncertainties.
- Chemistry: correct arrow pushing, balanced equations, yields that make sense, hazards acknowledged.
- Clear separation between what was measured, what was calculated and what was assumed.

## Common mistakes

- Radians vs degrees; forgetting the ½ in kinetic energy or the sign in potential energy; dropping vector nature.
- Using a formula outside its validity (small-angle, non-relativistic, ideal gas, dilute solution).
- Propagating uncertainty by adding absolute errors of multiplied quantities (relative errors add in quadrature).
- Fitting a line to data that curves, or fitting with no uncertainties and reporting 6-digit parameters.
- "Human error" as the explanation of every discrepancy.
- Significant-figure inflation from a calculator.
- Confusing heat and temperature, mass and weight, moles and molecules, concentration and amount.
- Mechanisms with arrows from positive to negative; unbalanced charges; wrong limiting reagent.
- Lab reports that narrate the procedure instead of analysing the data.

## Default citation style

Physics: AIP or APS style (numeric, journal abbreviations). Chemistry: ACS style (numeric or author-year, per journal). Earth sciences often use author-year (AGU/Harvard). Software and datasets are cited with version and DOI. The course syllabus always overrides this default.

## Worked breakdown

Invented assignment: "Lab 5 — Damped harmonic oscillator" in a first-year physics lab. Deliverables: a lab report (max 8 pages, template provided), the raw data file, and the analysis script; due 7 days after the lab session; 12% of the lab grade; pairs.

| Part | Type | Weight | Depends on | Estimate |
|---|---|---|---|---|
| 1. Theory: derive x(t) for underdamped motion, define Q and the decay time | proof | 15 | — | 1.5 h |
| 2. Data: amplitude vs time from the tracker video, with timing uncertainty | practical | 15 | — | 1 h (in lab) |
| 3. Analysis: fit the envelope, extract the decay constant and its uncertainty | analysis | 30 | 1, 2 | 3 h |
| 4. Comparison: damping coefficient vs the value from the drag model; residuals | analysis | 20 | 3 | 2 h |
| 5. Report writing and plots | essay | 20 | 1–4 | 3 h |

Suggested order: derivation first (it decides which parameters to fit); then load the data and plot it before fitting anything; fit with uncertainties (`curve_fit` with `absolute_sigma=True`); compare; write. Environment: Python in a notebook with NumPy/SciPy/Matplotlib; the course's report template in LaTeX or Word. Review first: the lecture on damped oscillations and the lab manual's section on uncertainty propagation. Constraints to check: whether the report must follow the template's section names exactly, the page limit, and whether the analysis script must be attached.
