# Planning rules

How `scripts/plan_week.py` decides, and what the skill adds around it. The script is deterministic; the
judgement (estimates, availability, what to tell the student) is here.

## 1. Inputs, and where each comes from

| Input | Source | If missing |
|---|---|---|
| Deadlines | `deadlines.json` from `moodle-sync`, Moodle calendar `.ics` export, `COURSE.md` `deadlines:`, syllabus dates the student pastes | ask for the Moodle calendar export (Calendar → Export → all events → `.ics`) |
| Estimates | `estimate_hours` per deadline; the student's own sense ("HW in this course takes me ~6 hours") | defaults: assignment 3 h, exam 8 h, quiz/other 2 h — say they are defaults and ask once whether to adjust |
| Availability | the student: free slots per day for the week, `{"YYYY-MM-DD": [["HH:MM","HH:MM"], ...]}` | ask once: "Which hours are free this week?" Offer a typical pattern to edit (weekday evenings 18:00–21:00, Friday morning) — never assume nights or Shabbat |
| Review dates | `review-dates.json` from `exam-prep` | none — exams then get only their estimate hours |

Availability is what the student will really do, not what is theoretically free. Lectures, work shifts, travel
(the trip home before the weekend), reserve duty and sleep are not study time. When the student says "I'm free
all day Sunday", plan at most 6 h of it.

## 2. What the planner does

1. Review dates inside the week → 1-hour blocks first (spaced repetition only works on its day).
2. Deadlines, earliest due first. A deadline due inside the week gets its whole estimate; one due later gets
   this week's proportional share (estimate × 7 / days until due), so a big project is back-planned across weeks.
3. Work is spread: at most one block of 1–2 h per deadline per day per pass, so one assignment does not eat a
   whole evening before the next one is even started. Minimum block 1 h; nothing after the due time.
4. Blocks never overlap and never leave the free slots. Whatever does not fit is `overflow`, with the hours.

## 3. Overload warning (two weeks ahead)

Run the planner on this week **and** the next one. If either reports overflow, or the required hours exceed
80% of the available hours, warn once, at the top of the reply, with numbers:
"בשבוע של 16.11 חסרות 7 שעות: תרגיל 3 (4 שעות) ובוחן 2 (3 שעות) לא נכנסים." Then offer the options, in this
order: move work earlier into this week's spare hours; lower an estimate the student thinks is too high; add
availability; ask for an extension (`references/extension-request.md`). Never drop an item to make the plan fit,
and never schedule beyond the availability the student gave.

## 4. Conflicts between sources

`merge_deadlines.py` keeps the earliest time and lists the others in `conflict`. Tell the student once, per
conflict, which sources disagree ("Moodle says 23:59, the syllabus says 18:00") and plan for the earliest.
Moodle is usually right about the submission box; the syllabus is right about intent — the student checks.

## 5. Output to the student

- A table per day: date · time · task · course (Hebrew-first cells when the reply is Hebrew).
- The overflow list, if any, with the hours and the suggestion.
- The `.ics` file path (`scripts/export_ics.py`), with one line on importing it (Google Calendar → Settings →
  Import; Outlook/Apple: open the file).
- Google Calendar events directly, only via the Google Calendar connector, only after the student said yes to
  the exact list of events shown — never as a side effect of planning.
