# With `assignment-judge` (unedited output)

Prompt: *"If you were the professor teaching Linear Algebra 1 to first-year computer science students, what grade would my solution.md get for the assignment in assignment.md?"*

---

**Persona:** As a professor teaching Linear Algebra 1 to first-year computer science students, grading against the instructions (0–100 scale, no pass mark given):

## Estimated grade: about 70/100 (range 68–72)

| Q | Max | Score | Evidence and reason |
|---|---|---|---|
| 1 | 40 | **40** | "From the second equation y = 2x. Substituting: x + 2x = 3…". The method is valid, every step is shown, and the check against both equations meets "show every step". I recomputed it and the answer is correct. |
| 2 | 40 | **~10** (8–12) | "det(A) = 2·3 + 1·4 = 10". The 2×2 determinant is the product of the main diagonal *minus* the product of the off-diagonal, and you added them. This is a wrong formula, not an arithmetic slip, so the answer is wrong. The assignment says answers without justification get no credit, and you stated no formula. The partial credit is for using the right entries and the right pairing of products. |
| 3 | 20 | **20** | "(2, 4) = 2·(1, 2)… linearly dependent". The conclusion is correct and justified by an explicit multiple, as the question asks. |

The two grading passes agreed on every question, and the total was computed by the scoring script.

**What would raise the grade most:** Q2 is the only place you lose points, and it's worth about 30. Check which sign the 2×2 determinant formula uses between the two products. Then state the formula before substituting, because a first-year grader wants to see it written out. Your own sign check on Q1 shows you can verify results, so use it here too. The 10 is also a red flag you can test: the determinant tells you whether the matrix is invertible, and you can test that independently.

**Risks (no points taken):**
- Q1 is solid, but a strict grader might want you to say explicitly that the solution is unique.
- For Q3, you could mention that the set has two vectors and one is a multiple of the other, though what you wrote is enough.

*This is an estimate of how an expert grader would read the work against the instructions; it is not the course's grade, and your lecturer may weigh things differently.*

One note: the shell reported a read-only error about its working-directory tracking after each command. It didn't affect the scoring output.