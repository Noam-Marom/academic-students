# Contributing

Thanks for helping. The most valuable contributions right now are **discipline knowledge** (what a
good answer looks like in your field, what graders want, which tools students really use) and **real-world
test cases** written for the tests, not copied from courses.

## Ground rules

- No real course material, no real exams, no personal data, no lecturers' or students' names. Fixtures are written for the tests.
- Nothing that helps a student cheat: no quiz answering, no submission automation, no "make it look human".
- No passwords anywhere. The Moodle server stores a revocable token in the OS keychain and nothing else.
- Scripts stay stdlib-first and degrade gracefully when an optional library is missing.
- Hebrew documents follow the RTL rules in `skills/rtl-writing/SKILL.md`; `tests/test_hebrew_docs.py` checks them.

## Setup

```
git clone https://github.com/Noam-Marom/academic-students
cd academic-students
python3 -m pip install pytest pyyaml          # test deps; optional extras: pymupdf python-docx pint jsonschema
python3 -m pytest -q
```

To try the plugin from your checkout in Claude Code: `/plugin marketplace add ./path/to/academic-students`
then `/plugin install academic-students@noam-academic`.

## Making a change

1. Open an issue first for anything bigger than a typo, so we agree on the shape.
2. Read `CLAUDE.md` (the briefing) and `docs/skill-conventions.md` (the rules every skill follows).
3. Tests first. Every script change comes with a failing test that the change makes pass.
4. If you touch `shared/`, run `python3 tools/sync_shared.py` and commit the copies it writes.
5. Before pushing: `python3 tools/sync_shared.py --check && python3 -m pytest -q && claude plugin validate .`.
6. Commit messages: `feat(skill): …`, `fix(skill): …`, `test: …`, `docs: …`, `chore: …`, `ci: …`.

## Adding or improving a discipline pack

Edit `shared/disciplines/<family>.md`. Keep the eight headings in order (a test checks them). Good additions:
a realistic worked breakdown, tools students actually use with free alternatives, the mistakes you saw
classmates make, what the grader in your department rewards. Hebrew terms inside English lines are welcome.

## Adding an eval case

`evals/<skill>/<case-name>/` (top level: `claude plugin eval` refuses eval dirs inside `skills/`) with `prompt.md` (a realistic student message), `case.yaml`
(`schema_version: "1.1"`), `graders/NN-*.md` (one verifiable statement each) and, if the case needs files,
`files/` plus `place-files.sh`. Evals run real models and cost money; they run on demand (`evals.yml`), not on PRs.

## Reporting a scanner miss or false alarm

Open an issue with a **synthetic** file that reproduces it (never a real assignment), the technique you used
to hide the text, and the scanner's output. If you can, add it to `skills/prompt-injection-scanner/tests/fixtures/make_fixtures.py`.

## Licensing of contributions

Contributions are licensed under the MIT License, the same as the project (inbound=outbound). Contribute only
material you wrote or have the right to license: no real course material, exams or personal data.

## Code of conduct

Be kind, assume good faith, and remember the users are students under deadline pressure.
