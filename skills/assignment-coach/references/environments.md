# Environments: which tool for which task, and the free way in

Students run this on laptops with nothing installed, on a phone between classes, or in a lab where only
the course's software exists. For each kind of task: the tool most courses assume, a free or browser
alternative that produces the same deliverable, and what to do when the course mandates something else.
The discipline pack's "Tools and environments" section is more specific; it wins when they differ.

| Task kind | Usually assumed | Free / browser alternative | When the course mandates a tool |
|---|---|---|---|
| Typesetting proofs, reports, theses | LaTeX (TeX Live, TeXstudio) | Overleaf (browser; Hebrew via XeLaTeX + polyglossia), Typst web app | Use it: graders open the course's template; export PDF from whatever you write in |
| Word processing, Hebrew RTL documents | Microsoft Word | LibreOffice Writer, Google Docs (RTL paragraphs supported) | Submit DOCX from Word if asked; `scripts/render_solution.py` makes a DOCX with correct `w:bidi` |
| Handwritten work to submit | Scanner | Microsoft Lens, Adobe Scan, Google Drive scan (phone, free) | Follow page order/number rules; one PDF, not photos |
| Python / data science notebooks | Jupyter in Anaconda | Google Colab (browser, GPU), Kaggle notebooks, JupyterLite | Match the course's Python version and library pins; Colab ≠ course grader's environment — test locally if you can |
| C / C++ / systems programming | gcc/clang on Linux, Makefiles | Replit, GitHub Codespaces (free tier), WSL on Windows | Compile with the exact flags the course grades with (`-std=c11 -Wall -Werror`…); Replit's gcc differs — verify on the course server |
| Java / C# / Kotlin | IntelliJ / Visual Studio / Android Studio | Replit, OnlineGDB, GitHub Codespaces | Project structure and JDK version as the course states; no IDE-specific files in the submission |
| Web development | VS Code + Node | StackBlitz, CodeSandbox, Glitch | Deliver the repo layout the course grades, with the `README` they ask for |
| Databases / SQL | PostgreSQL / MySQL / Oracle | SQLite (built in to Python), DB Fiddle, SQLiteOnline | Oracle/MSSQL dialect differences matter — test the final queries on the course's engine |
| MATLAB computation | MATLAB (university licence) | GNU Octave (desktop), Octave Online, NumPy/SciPy in Colab | Submit `.m` files that run in MATLAB; Octave accepts most but not all syntax |
| Symbolic maths | Mathematica, Maple | SymPy (Colab), SageMathCell, WolframAlpha free tier | Show the steps by hand when "show your work" is required; the CAS checks, it does not replace |
| Plotting / geometry | MATLAB, Mathematica | Desmos, GeoGebra (browser), matplotlib in Colab | Axis labels, units, legends as the course's figure rules require |
| Statistics (point-and-click) | SPSS | JASP, Jamovi (free desktop), PSPP | Report the statistics in the course's format (APA tables), whatever produced them |
| Statistics (programming) | R / RStudio | Posit Cloud (browser RStudio), R kernel in Colab | Set the seed the course specifies; attach the script |
| Circuits / electronics | LTspice, Multisim, Altium | Falstad circuit simulator, Tinkercad Circuits (browser), KiCad (free desktop) | Simulate in the mandated tool for the screenshot they grade; design elsewhere if you like |
| CAD / 3-D modelling | SolidWorks, AutoCAD, Revit | Onshape (browser, free for education), FreeCAD, Tinkercad (simple parts), SketchUp Free | Deliver the native file format they ask for; converters lose constraints |
| GIS / maps | ArcGIS | QGIS (free desktop), Google Earth Web | Projections and CRS as the course states |
| Chemistry drawing | ChemDraw | MarvinJS (browser), ChemSketch (free), PubChem sketcher | IUPAC names from the tool, checked by hand |
| Bioinformatics | course servers / Linux cluster | Galaxy (usegalaxy.org), NCBI BLAST web, UCSC Genome Browser, Colab | Record tool versions and parameters — reproducibility is graded |
| Reference management | EndNote | Zotero (free, Word/LibreOffice/Docs plugins, Hebrew entries fine), JabRef for BibTeX | Export in the course's style; `academic-writing`'s `format_refs.py` for APA 7 / IEEE from CSL-JSON |
| Presentations | PowerPoint | Google Slides, LibreOffice Impress, Canva (free tier) | RTL text boxes per slide; `rtl-writing` has the PPTX rules |
| Qualitative analysis (coding interviews) | NVivo, ATLAS.ti | Taguette (free), QualCoder, a spreadsheet with a codebook | Export code frequencies the way the course's template shows |
| Economics / finance modelling | Excel, Stata, EViews | Google Sheets, LibreOffice Calc, Python (pandas/statsmodels) in Colab, Gretl | Stata `.do` files if required: write them, run on the lab machine |
| Music notation / audio | Sibelius, Finale, Pro Tools | MuseScore (free desktop), Flat.io (browser), Audacity, Reaper (evaluation) | Export MusicXML/PDF/WAV as asked; the student makes the music |
| Video / image editing | Premiere, Photoshop | DaVinci Resolve (free), Kdenlive, GIMP, Photopea (browser), Krita | Resolution/codec exactly as the brief says |
| Flashcards and spaced repetition | — | Anki (free desktop/Android), AnkiWeb | `exam-prep` exports Anki decks |
| Formal proof checking (optional) | — | Lean 4 playground (live.lean-lang.org), Coq jsCoq | Only when the course uses it; a checked proof still needs the written argument |

## Rules of thumb

- **The grader's environment wins.** A program that runs in Replit and fails on the course server is
  wrong. Ask which compiler/version/flags are graded, put them in `COURSE.md` (`environment:`), and test
  there before submission when at all possible.
- **Free first for exploration, mandated tool for the deliverable.** Think in Desmos, submit the MATLAB
  figure. Draft in Google Docs, submit the Word file with the course's template.
- **Never hide the tool.** If a tool produced a result (a CAS, a statistics package, a simulator), the
  answer names it when the course expects to know, and shows the hand steps when "show your work" applies.
- **Phone-only student.** Scanning (Lens/Adobe Scan), Colab, Overleaf, Google Docs/Sheets, Desmos, GeoGebra,
  Flat.io and Onshape all work in a mobile browser; that covers most weekly assignments.
- **University licences.** Most Israeli universities give students MATLAB, Office 365, SolidWorks/AutoCAD
  (via Autodesk Education) and SPSS for free — check the computing centre's page before paying or
  settling for an alternative.
