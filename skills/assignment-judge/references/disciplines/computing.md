# Computing and information systems

## Degrees covered

- Computer Science (מדעי המחשב), Software Engineering (הנדסת תוכנה), Computer Engineering (הנדסת מחשבים).
- Information Systems Engineering (הנדסת מערכות מידע), Data Science / Data Engineering (מדעי הנתונים, הנדסת נתונים).
- Cyber and information security tracks, bioinformatics and computational biology (the computing half), digital humanities (the computing half).
- Programming service courses taken by every engineering, science and economics student: Introduction to CS, Data Structures, Algorithms, Operating Systems, Databases, Computer Networks, Machine Learning. This pack applies to those courses regardless of the student's own degree.

## Typical deliverables

- Programming assignments (תרגילי תכנות): code + tests + a short README or report; graded by an autograder, by a TA reading the code, or both.
- Dry/theoretical exercises (תרגילים יבשים): complexity analysis, correctness arguments, reductions, automata and language proofs, probability of algorithms.
- Semester projects in teams: requirements document, design (UML / architecture diagram), implementation in sprints, demo, retrospective.
- Lab reports in hardware and networks courses: measurements, Wireshark captures, timing tables.
- Exams: mixed dry questions and "write a function that…" on paper; often closed book with a formula/API sheet.
- Seminar: present a paper or a system, write a 10–20 page survey.
- Data-science assignments: a notebook with EDA, modelling, evaluation, and a written discussion of validity.

## Answer conventions

- Code answers are judged on correctness first, then on clarity, then on efficiency. A readable O(n log n) beats a clever unreadable O(n) in most courses unless the question is about the bound.
- A dry question has a fixed shape: claim → argument → conclusion. Complexity answers state the bound, name the dominant term, and justify it per loop or per recurrence (master theorem or unrolling).
- Correctness arguments name the invariant (loop invariant, inductive hypothesis on input size) and show initialisation, maintenance, termination.
- Reductions and hardness proofs go in the right direction; say explicitly which problem reduces to which and why the transformation is polynomial.
- "Implement X" means: compile cleanly with the course's flags, match the required signature exactly, handle the stated edge cases (empty input, single element, maximum size), and never print debug output to stdout when the autograder reads stdout.
- Identifiers, commands, file names and library names stay in English inside Hebrew text; prose and comments follow the course's language.
- Every number that comes from a measurement (running time, throughput, accuracy) comes with how it was measured (hardware, repetitions, dataset split).
- Machine-learning results report the split (train/validation/test), the metric and why it fits the problem, and a baseline.

## Tools and environments

| Task | Recommended | Free / browser alternative |
|---|---|---|
| C / C++ systems courses | gcc/clang on Linux, Valgrind, gdb | WSL2 on Windows; Compiler Explorer (godbolt.org) for snippets |
| Java | IntelliJ IDEA Community, JUnit 5 | VS Code + Extension Pack for Java |
| Python | VS Code / PyCharm, pytest, venv | Google Colab, Replit |
| Notebooks and data science | JupyterLab, pandas, scikit-learn | Colab, Kaggle Notebooks |
| Databases | PostgreSQL, DBeaver | SQLite in the browser (sqliteonline.com), db-fiddle |
| Networks | Wireshark, netcat, Mininet | Packet Tracer (free with a Cisco account) |
| Version control | Git + GitHub/GitLab, branches per feature | GitHub web editor for small fixes |
| Diagrams | draw.io, PlantUML, Mermaid | Mermaid in GitHub Markdown |
| Typesetting | LaTeX (Overleaf) for dry exercises | Markdown + pandoc; Typst |
| Automata, logic | JFLAP | Automaton Simulator (web) |

## What graders look for

- Tests exist and run; the autograder's interface is respected to the letter (file names, function signatures, output format).
- Edge cases handled and visibly thought about (a comment or a test per case).
- Complexity stated and correct; data structure chosen for a reason that is written down.
- Code that a TA can read in two minutes: short functions, meaningful names, no dead code, no commented-out blocks.
- The dry part uses the course's definitions and theorems, cited by name, not re-derived from scratch.
- A README that says how to build, how to run, what is not implemented and why.
- Honest measurement: a plot with axes, units and the number of runs beats a sentence saying "it was fast".
- Team projects: visible division of work, a commit history that is not one commit on the last night.

## Common mistakes

- Off-by-one errors at boundaries; forgetting the empty input; integer overflow in C; mutable default arguments in Python.
- Confusing worst-case, average-case and amortised complexity; claiming O(1) for a hash lookup without saying "expected".
- Proving a loop invariant that does not imply the postcondition.
- Reductions in the wrong direction ("A is hard because it reduces to SAT").
- Data leakage: normalising or feature-selecting on the whole dataset before the split; reporting test-set numbers chosen by peeking at the test set.
- Printing extra output that breaks the autograder; reading input with the wrong encoding (Hebrew text in files is UTF-8, not cp1255 — usually).
- Race conditions in threaded assignments that pass locally and fail under load; forgetting to join threads or free memory.
- Submitting without compiling once more from a clean clone.
- Copying code from the web without understanding it — the oral check (בדיקה פרונטלית) finds it immediately.

## Default citation style

IEEE in engineering faculties, ACM in computer-science departments; both numeric. A URL for documentation needs an access date. Papers are cited by venue and year, not by arXiv number alone when a published version exists. The course syllabus always overrides this default.

## Worked breakdown

Invented assignment: "HW4 — Multithreaded Web Crawler" in an Operating Systems course. Deliverables: `crawler.c`, `Makefile`, `report.pdf` (max 3 pages), due in 14 days, 10% of the final grade, pairs allowed.

| Part | Type | Weight | Depends on | Estimate |
|---|---|---|---|---|
| 1. URL queue with bounded capacity (producer/consumer) | code | 25 | — | 4 h |
| 2. Worker pool of N threads fetching URLs with sockets | code | 30 | 1 | 6 h |
| 3. Deadlock-free shutdown and signal handling | code | 15 | 2 | 3 h |
| 4. Measurements: throughput vs N on three sites, with a plot | analysis | 15 | 2 | 3 h |
| 5. Report: design, invariants of the queue, what breaks without the lock, results | essay | 15 | 1–4 | 3 h |

Suggested order: write the queue with a unit test that hammers it from two threads before touching sockets (part 1 is where most races live); then a single-threaded fetcher; then the pool; then shutdown; measure last. Environment: Linux with `gcc -Wall -Wextra -pthread -fsanitize=thread` for the race detector; Valgrind for leaks. Review first: the lecture on condition variables and the "lost wakeup" slide; `man 7 pthreads`; the course's coding standard. Constraints to check in the brief: whether `libcurl` is allowed (usually not — raw sockets are the point), the exact output format the autograder reads, and the page limit of the report. The policy line to look for: whether pair work means two names on one submission or two separate submissions.
