---
type: llm
focus: trace
weight: 1
---

A file named review-dates.json is written (under the course folder, e.g. exam-prep/review-dates.json) and its
content is a JSON list in which every element has exactly the keys "course" (string), "topic" (string) and
"dates" (a list of strings in YYYY-MM-DD form). The trace shows the file being validated (parsed with Python
or inspected) before the reply.
