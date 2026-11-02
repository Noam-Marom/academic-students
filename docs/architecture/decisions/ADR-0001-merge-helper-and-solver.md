# ADR-0001. Merge `assignment-helper` and `assignment-solver` into one `assignment-coach` skill with modes

- Status: accepted
- Date: 2026-11-02
- Deciders: Noam Marom
- Tags: skills, triggering, academic-integrity
- Elements: `ea:noam:academic-students:container:learning-skills`

## Context and Problem Statement

The original idea list had two skills for assignments: a *helper* (break down, where to start, which
environment, how to answer) and a *solver* (produce the full solution). Claude selects a skill from its
description; two skills whose descriptions both say "the user has an assignment" compete for the same
messages. The wrong one fires often, and a student who wanted hints gets a finished answer (or the reverse).
Both skills also need the same first 80% of work: scan the files, understand the course, map the assignment.

## Decision Drivers

- Triggering accuracy: one skill per *situation*, not per *depth of help*.
- Shared pipeline: scan → context → map → plan is identical for both.
- Academic-integrity posture: the depth of help must be a deliberate, visible choice gated by the course's AI policy, not an accident of which skill fired.
- Portfolio value: a skill that adapts its depth is a better story than two skills that overlap.

## Considered Options

1. Keep two skills, sharpen the descriptions to separate them.
2. One skill, `assignment-coach`, with four modes (`breakdown`, `guide`, `check`, `solve`); mode chosen from the request, default `breakdown`, `solve` only on explicit request and only within the policy.
3. One skill that always does everything (map + hints + solution) and lets the student ignore what they don't want.

## Decision Outcome

Chosen option: **2**, because the mode decision belongs *after* the shared pipeline has run and *after* the
policy is known, which is exactly where one skill can make it and two skills cannot. Option 3 was rejected
because producing a full solution the student did not ask for defeats the plugin's stance and the policy gate.

### Consequences

- Good: one description to tune; one eval suite; the policy ceiling is enforced in one place.
- Good: `solve` becomes a mode with its own verification protocol instead of a separate, less-controlled skill.
- Bad: `SKILL.md` must route between modes, which costs lines in a 300-line budget; mode protocols live in `references/modes.md`.
- Neutral: the boundary with `academic-writing` (continuous prose vs. discrete questions) still needs its own description sentence and a confusion-matrix eval.

## Pros and Cons of the Options

### 1. Two skills
- Good: each description is shorter.
- Bad: overlapping triggers; duplicated pipeline; depth of help decided by triggering luck.

### 2. One skill with modes
- Good: single pipeline, single policy gate, explicit depth.
- Bad: longer SKILL.md; needs clear mode-selection rules.

### 3. One skill, always full output
- Good: simplest to write.
- Bad: ignores policy; produces submittable work unasked; largest integrity risk.

## More Information

Spec §4.3; `shared/ai-policy.md` (what each mode may do under each policy).
