# Hebrew with English in chat and Markdown — the rules

These are the rules the skill applies to every reply and every Markdown file. `scripts/check_rtl.py` checks them mechanically; `--fix` proposes an opener for each failing line.

## Why lines break

The chat UI picks each line's direction (each paragraph, list item, heading or table cell) from the first
letter it contains. If that letter is Hebrew, the line renders RTL. If it is Latin (an English word, a
command, a file name, a URL), the whole line flips to LTR, its punctuation jumps to the wrong side, and
the Hebrew in it reads backwards. Markdown markers (`#`, `-`, `1.`, `>`, `**`) don't count. What counts is
the first real character after them. So the question for every line is: **what is the first word the
reader sees, and is it Hebrew?**

## Scope: the whole conversation, every piece of prose

- Apply this to every line of the reply, not just the opening paragraph. Most slips happen in the middle and
  at the end of long technical answers: in a list of tools, a table, a heading, or the line after a code block.
- **It persists.** After the skill is invoked, every later reply in this conversation follows these rules too,
  including short answers, follow-ups, error explanations, progress messages between tool calls, questions
  to the user (including multiple-choice option labels), and the final summary. It stops only when the user says so.
- Write in Hebrew even when the user writes in English or pastes English material. Technical terms, names,
  commands and identifiers stay in English inside Hebrew sentences.
- It also applies to Hebrew prose you write into files or documents in this conversation (a Markdown file,
  a doc, a README), unless the user wants a different format there.

## Rules

1. **Mandatory Hebrew start.** Every sentence, new line, paragraph, heading, table cell (header cells and
   the first column included) and bullet point must begin with a Hebrew word. A line that starts with an
   English word, a number, a symbol, an emoji, a quote mark, a link, a path or inline code breaks RTL rendering.
2. **English word starters.** If a line logically must start with an English term:
   - Preferred: reword so it opens with a natural Hebrew word. Usually one word is enough:
     - "Python is…" → "השפה Python היא…"
     - "Docker containers…" → "קונטיינרים של Docker…"
     - "`malloc` returns…" → "הפונקציה `malloc` מחזירה…"
     - "/etc/hosts maps…" → "הקובץ `/etc/hosts` ממפה…"
     - "3 steps" → "שלושה שלבים", or "יש 3 שלבים"
     - "v2.1 adds…" → "גרסה 2.1 מוסיפה…"
     - "https://… has the docs" → "התיעוד נמצא ב-https://…"
   - Natural Hebrew prefixes also work: "ב-Docker", "ה-API", "ל-Python", "מ-GitHub". The line starts with a
     Hebrew letter and still reads naturally.
   - Fallback when no Hebrew word fits (for example a table cell that holds only a name): prefix the English
     word with the Hebrew letter 'א' and no space, for example "אDocker".
3. **Punctuation anchoring.** Keep periods, commas, colons and parentheses inside a Hebrew sentence structure,
   around the English terms, so they don't jump to the wrong side. Avoid ending a line with an English term
   followed directly by punctuation. Close the sentence with a Hebrew word instead: "…ומריצים את הפקודה
   `make` בטרמינל." instead of "…ומריצים את `make`.", "…של אתגרי ה-CTF עצמם." instead of "…של ה-CTFs.".
   If no natural Hebrew ending fits, leave out the final period on that line rather than letting it jump.
4. **Lists, headings, labels.** Bullet and numbered items follow rule 1: "- הפונקציה fork יוצרת…", not
   "- fork creates…". Headings too: "## הגדרת Docker Compose", not "## Docker Compose Setup". Bold labels at
   the start of a line too: "**הכלי Podman:** …", not "**Podman:** …".
   **Labels that are terms of art are the most common slip.** Words like Train / Test / Validation, Input /
   Output, Pros / Cons, Baseline, Setup, Results, TL;DR, Note, Step 1, Q / A, Before / After, Server / Client
   feel like fixed names, so they get written in English automatically as the first word of a bullet. If the
   term must stay in English, put a Hebrew noun in front of it inside the label:
   - `- **Train (10):** 5 אתגרי…` → `- **סט ה-Train (10 אתגרים):** 5 אתגרי…`
   - `- **Test (6), held-out:** …` → `- **סט ה-Test (6, held-out):** …`
   - `**Input:** …` → `**הקלט:** …`, `**Pros:**` → `**יתרונות:**`, `**Step 1:**` → `**שלב 1:**`
5. **Tables.** Each cell is its own line for direction purposes. Start every cell, header included, with
   Hebrew: "| הכלי | יתרון |", "| הכלי Docker | נפוץ מאוד |". A cell that holds only a name can use
   "אDocker", or carry a Hebrew noun ("הכלי Docker", "הפקודה `ls`").
6. **Code.** Code blocks are exempt (they render LTR in their own block), but the line introducing a code
   block must start in Hebrew, and so must the line right after it. Inline code (`like_this`) must not be the
   first token of a line.

## High-risk spots (check these every time)

| Where it slips | Wrong | Right |
|---|---|---|
| Heading with a product name | `## Git Branching` | `## עבודה עם ענפים ב-Git` |
| Bold term-of-art label in a list | `- **Train (10):** …` | `- **סט ה-Train (10 אתגרים):** …` |
| Bold label | `**Note:** …` / `**Redis:** …` | `**הערה:** …` / `**השירות Redis:** …` |
| List of tools/functions | `- pthread_create – …` | `- הפונקציה pthread_create – …` |
| List item starting with code | ``- `ls -la` מציג…`` | ``- הפקודה `ls -la` מציגה…`` |
| Table first column / header | `\| Command \| What it does \|` | `\| הפקודה \| מה היא עושה \|` |
| Line after a code block | `Output: …` | `הפלט: …` |
| Number or step at line start | `2 threads run…` | `שני חוטים רצים…` |
| Path / URL / version at line start | `~/.bashrc is…` | `הקובץ `~/.bashrc` הוא…` |
| Short follow-up reply | `Yes, use `--force`.` | `כן, צריך להשתמש בדגל `--force`.` |
| Status line between tool calls | `Running tests…` | `מריץ את הבדיקות…` |
| First paragraph after a heading, opening with a name | `Marvel היא חברת קומיקס…` | `החברה Marvel היא חברת קומיקס…` |
| English name followed by a number in parentheses | `נפתחת ב-*Iron Man* (2008)` | `נפתחת בסרט *Iron Man* משנת 2008` |
| Function call with `()` in inline code | ``הקריאה `fork()` יוצרת…`` | ``הקריאה `fork` יוצרת…`` |
| English title with a colon, then a comma | `ב-*Avengers: Endgame* (2019), עם…` | `בסרט *Avengers: Endgame* משנת 2019, עם…` |

## How to write it (habit, not afterthought)

Choose each line's opening Hebrew word before writing the rest of the line. Fixing lines after the fact is
where slips survive. Words that open technical lines naturally: הפקודה, הפונקציה, הקובץ, המשתנה, הספרייה,
הכלי, השירות, הגרסה, השלב, הדגל, הפלט, הערך, השגיאה, התהליך, הנתיב, בקוד, כאן, למשל, כדי, אם, אחרי.
