# Life sciences

## Degrees covered

- Biology (ביולוגיה), Life Sciences (מדעי החיים), Biotechnology (ביוטכנולוגיה), Molecular Biology, Microbiology, Neuroscience (מדעי המוח), Ecology and Evolution, Marine Biology, Agriculture and Plant Sciences, Animal Sciences.
- Biomedical Sciences (מדעים ביו-רפואיים) and the pre-clinical year of medicine and dentistry for the biology content.
- Bioinformatics and Computational Biology (the biology half).
- Biology service courses for chemistry, environmental science and psychology students.

## Typical deliverables

- Lab reports in a fixed structure (IMRaD): Introduction, Methods, Results, Discussion; figures with legends; statistics on the measurements.
- Lab notebook kept during the session, often checked and graded.
- Problem sets: genetics crosses and probabilities, enzyme kinetics calculations, dilution series, population-genetics and ecology models.
- Literature reviews and seminar presentations on primary papers; critical reading questions ("what control is missing?").
- Research proposals in advanced courses: question, hypothesis, aims, methods, expected results, pitfalls.
- Exams: short-answer and essay questions on mechanisms, plus calculations; some multiple choice in large courses.
- Bioinformatics assignments: scripts, pipelines, alignment or expression analysis with reproducible notebooks.

## Answer conventions

- Mechanistic answers follow cause → effect at the right level (molecule → cell → organism), name the molecules and the direction of regulation, and distinguish what is established from what is hypothesised.
- A lab report's Results section reports what was observed with numbers and figures; interpretation waits for the Discussion. Methods are past tense, passive or first person per the course, detailed enough to repeat.
- Figures: axes with units, error bars defined (SD or SEM, and n), statistical test named with p-value and the test statistic; legends that let the figure stand alone.
- Controls are part of every experimental answer: positive, negative, loading, vehicle. If asked to design an experiment, list the controls before the treatment groups.
- Calculations: dilutions as C₁V₁ = C₂V₂ with units; enzyme kinetics with Km and Vmax from the stated plot; genetics with the Punnett square or branch diagram shown and ratios reduced.
- Nomenclature: gene names italic, protein names roman; species names italic and binomial on first mention then abbreviated (Escherichia coli → E. coli); units SI with the standard biology exceptions (°C, L, min).
- Hebrew answers keep gene, protein, technique and reagent names in English (PCR, Western blot, GFP, CRISPR).

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| Statistics and plots | GraphPad Prism (licence), R | JASP, Jamovi, R in Colab, Python SciPy |
| Sequence analysis | Geneious (licence), SnapGene | Benchling (free), NCBI BLAST, UGENE, Biopython |
| Alignment and phylogeny | MEGA, MAFFT | EMBL-EBI web tools (Clustal Omega, MUSCLE) |
| Image analysis | ImageJ / Fiji | Fiji (free), QuPath |
| Expression / omics | R Bioconductor, Galaxy | Galaxy (usegalaxy.org), Colab |
| Structures | PyMOL (education licence), ChimeraX | Mol* viewer (RCSB), ChimeraX (free academic) |
| Reference management | Zotero, EndNote (campus) | Zotero, Paperpile trial |
| Lab notebook | Paper (often mandatory), eLabFTW | Benchling notebook |
| Figures | Illustrator (licence), BioRender (licence) | Inkscape, Matplotlib, BioRender free tier (watermark) |
| Writing | Word with EndNote/Zotero plug-in | Google Docs + Zotero connector, Overleaf |

## What graders look for

- Correct level of explanation with the actual molecules and directions, not vague "it affects".
- Every claim in a report tied to a figure or a cited source.
- Controls present and understood; limitations acknowledged in the Discussion.
- Statistics appropriate to the design (paired vs unpaired, parametric vs not) with n stated.
- Figures that can be read without the text; consistent units; error bars defined.
- Methods reproducible; reagent concentrations, times, temperatures and instruments given.
- Primary literature cited (the papers), not textbooks or websites, in advanced courses.
- Critical reading: identifying what a paper's data do and do not show.

## Common mistakes

- Describing results and interpretation in the same sentence; or interpreting before showing the data.
- "The results were as expected" with no numbers; p-values with no test name or n.
- SEM used to make error bars look small without saying so.
- Missing or wrong controls in experimental designs.
- Confusing correlation with causation in observational data; confusing transcription with translation; gene with protein.
- Dilution arithmetic errors (serial dilution factors multiplied wrong); unit slips (µM vs mM, µL vs mL).
- Species names not italic or capitalised wrongly; gene symbols inconsistent.
- Citing a review instead of the primary paper for a specific finding; citing an abstract without reading the paper.
- Plagiarised Methods copied from the lab manual without adapting to what was actually done.

## Default citation style

APA 7 or CSE (Council of Science Editors) name-year; some departments use Vancouver numeric (medicine-adjacent courses). Journal names in the style's abbreviation form; DOIs included. The course syllabus always overrides this default.

## Worked breakdown

Invented assignment: "Lab report 3 — Effect of temperature on catalase activity" in a first-year biology lab. Deliverables: IMRaD report (max 6 pages + appendix), raw data table, due 10 days after the lab; 15% of the lab grade; individual report on group data.

| Part | Type | Weight | Depends on | Estimate |
|---|---|---|---|---|
| 1. Introduction: enzyme kinetics background, hypothesis with predicted curve shape | essay | 15 | — | 2 h |
| 2. Methods: what the group did, written to be repeatable, with concentrations and timings | essay | 10 | — | 1 h |
| 3. Results: rate vs temperature plot with error bars, table of means ± SD, ANOVA or regression | analysis | 30 | raw data | 3 h |
| 4. Discussion: fit to the hypothesis, denaturation, limitations, one improvement | essay | 30 | 3 | 3 h |
| 5. References and formatting | other | 15 | 1, 4 | 1 h |

Suggested order: plot the data first (part 3) — the shape decides what the Introduction promises and what the Discussion explains; then Introduction, Methods, Discussion, references. Environment: JASP or Python for the statistics, a spreadsheet for the table, Zotero for 4–6 primary sources. Review first: the lecture on enzyme kinetics and denaturation; the lab manual's rubric. Constraints to check: whether figures count toward the page limit, the required citation style, and whether the group's raw data must be attached unchanged.
