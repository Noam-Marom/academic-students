# Engineering

## Degrees covered

- Electrical and Computer Engineering (הנדסת חשמל ומחשבים), Electronics, Communications, Control.
- Mechanical Engineering (הנדסת מכונות), Aerospace, Mechatronics, Robotics.
- Civil and Structural Engineering (הנדסה אזרחית, הנדסת בניין), Environmental Engineering, Transportation.
- Industrial Engineering and Management (הנדסת תעשייה וניהול), Materials Engineering, Chemical Engineering, Biomedical Engineering (הנדסה ביו-רפואית), Nuclear Engineering.
- The engineering core every track shares: Statics, Dynamics, Thermodynamics, Fluids, Circuits, Signals and Systems, Control, Numerical Methods, Probability for Engineers.

## Typical deliverables

- Problem sets with numeric answers: given → required → solution → check; units everywhere.
- Lab reports: apparatus, procedure, raw data, processed data with uncertainty, comparison to theory, discussion of error sources.
- Design projects: specification, alternatives considered, calculations, drawings or schematics, bill of materials, safety and standards compliance, cost.
- Simulation assignments: MATLAB/Simulink, SPICE, finite-element or CFD models with convergence/mesh studies.
- Final project (פרויקט גמר): a year-long design-build-test with a poster, a report of 40–100 pages and a defence.
- Exams: multi-part numeric problems with partial credit for method; formula sheets usually allowed.

## Answer conventions

- Every quantity carries a unit and a sensible number of significant figures; the final answer is boxed with its unit. SI unless the course says otherwise; conversions written out.
- A problem solution has five parts: a sketch or free-body/circuit diagram with labels; given and required; assumptions and idealisations stated (rigid body, steady state, ideal op-amp, incompressible flow); the governing equation in symbols before numbers; a sanity check (sign, magnitude, limiting case, dimensional analysis).
- Free-body diagrams are not optional: forces, moments, reaction directions, coordinate axes, sign convention.
- Circuits: node/mesh equations written in symbols, reference directions shown, units on every element.
- Control and signals: state the domain (time/frequency), the transform pair used, stability criterion named.
- Design calculations cite the standard or handbook used (e.g. Eurocode, ASME, IEC) with the clause number when the course works with codes.
- Uncertainty is propagated, not ignored: a measured 9.78 ± 0.05 m/s² is a result; 9.78 alone is a number.

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| Numerical work | MATLAB (campus licence), NumPy/SciPy | GNU Octave, Octave Online, Python in Colab |
| Block diagrams, control | Simulink | Python `control` library; Scilab/Xcos |
| Circuit simulation | LTspice (free), Multisim | Falstad circuit simulator (browser), EveryCircuit |
| CAD | SolidWorks, Fusion 360 (student), AutoCAD | Onshape (browser), FreeCAD |
| FEM / CFD | ANSYS Student, COMSOL (licence) | CalculiX, OpenFOAM, SimScale (browser, limited) |
| Structural analysis | SAP2000, ETABS (licence) | OpenSees, Frame3DD, Ftool (free) |
| PCB | Altium (licence), KiCad | KiCad, EasyEDA (browser) |
| Embedded | STM32CubeIDE, Arduino IDE, PlatformIO | Wokwi (browser simulator), Tinkercad Circuits |
| Reports | LaTeX (Overleaf), Word with equation editor | Markdown + pandoc |
| Unit checking | — | `pint` (Python), WolframAlpha |

## What graders look for

- The diagram first. A missing free-body diagram or schematic loses points even when the number is right.
- Method marks: correct governing equation and assumptions earn most of the credit even if arithmetic slips.
- Units and significant figures consistent from first line to boxed answer.
- Assumptions stated explicitly and justified ("steady state because the transient is < 1% of the period").
- Lab reports: honest data, uncertainty handled, discrepancies with theory explained rather than hidden.
- Design: alternatives actually compared against criteria; a decision matrix; safety factors cited.
- Plots with labelled axes, units, legends, and the theory curve on the same axes as the data.
- Reproducibility: the simulation file or script attached; parameters in a table.

## Common mistakes

- Mixing unit systems mid-calculation (kN and N, mm and m); forgetting g in weight; degrees vs radians.
- Sign errors from an undeclared sign convention; moments taken about the wrong point.
- Plugging numbers in before simplifying symbolically, then losing track of what cancels.
- Treating a simulation output as truth without a convergence or mesh-independence check.
- Reporting 7 significant figures from a 3-figure measurement.
- Ignoring boundary conditions or initial conditions in differential-equation problems.
- Lab reports written as narratives of what the student did instead of what the data show.
- Copying a textbook example's assumptions into a problem where they do not hold (e.g. ideal gas at 200 bar).

## Default citation style

IEEE numeric. Standards are cited by designation and year (e.g. IEC 60950-1:2005), datasheets by manufacturer, part number and revision, with an access date for web sources. Civil engineering programmes sometimes use the Harvard author-year style. The course syllabus always overrides this default.

## Worked breakdown

Invented assignment: "Design of a pedestrian footbridge beam" in a second-year Strength of Materials course. Deliverables: a calculation report (max 10 pages, PDF), a hand sketch of the cross-section, and a spreadsheet; due in 3 weeks; 20% of the grade; individual.

| Part | Type | Weight | Depends on | Estimate |
|---|---|---|---|---|
| 1. Loads: dead, live (crowd), per the code clause given in the brief | calculation | 15 | — | 2 h |
| 2. Shear and moment diagrams for the simply supported span | calculation | 20 | 1 | 2 h |
| 3. Section selection from the steel table against bending and shear | design | 25 | 2 | 3 h |
| 4. Deflection check against the serviceability limit | calculation | 15 | 3 | 1.5 h |
| 5. Connection sketch and bolt check | design | 10 | 3 | 2 h |
| 6. Report: assumptions, calculations, conclusion, cost estimate | essay | 15 | 1–5 | 3 h |

Suggested order: parts 1–2 first (everything hangs on the moment); then pick a section and iterate between 3 and 4 since deflection often governs; connection last. Environment: a spreadsheet for the iteration (parts 3–4), hand calculations scanned for the diagrams, Ftool or a quick Python script to verify the moment diagram. Review first: the lecture on bending stress and the section-modulus table; the brief's load clause. Constraints to check: which code and partial safety factors the course uses, whether the report must be handwritten, the page limit.
