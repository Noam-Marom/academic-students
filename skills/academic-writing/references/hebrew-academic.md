# Academic Hebrew (עברית אקדמית)

Conventions examiners in Israeli universities expect, and the slips that cost points. Applies to Hebrew
papers in every discipline; the discipline pack's "Answer conventions" adds field-specific rules.

## Register

- Formal written register (לשון כתובה): "אשר", "כיצד", "על אף", "לפיכך"; no spoken forms ("כאילו", "בעצם", "איכשהו").
- Impersonal or first-person plural is standard ("נטען כי…", "בעבודה זו נבחן…"); first-person singular is
  accepted in reflections and increasingly in the humanities — check the course.
- Hedging: "ייתכן ש", "נראה כי", "הממצאים מצביעים על" — not "הוכח" for correlational findings.

## Terms

- First mention: Hebrew term + English in parentheses — "תוקף מבני (construct validity)"; afterwards the term the course uses.
- Acronyms: spelled out at first use with gershayim (ש"ח, ד"ר); English acronyms inside Hebrew keep Latin letters ("מודל ה-SEM").
- Transliterated names follow the source's own Hebrew spelling when one exists.

## Common slips

- Gender and number agreement across long sentences ("הממצאים שנמצאה" → "הממצאים שנמצאו").
- "של" chains → construct state (סמיכות) where natural: "השיטה של המחקר" → "שיטת המחקר".
- Calques from English: "לעשות הבדל", "לקחת החלטה" → "להבחין", "להחליט".
- Mixed tense in the methods section; use past tense for what was done.
- Overlong sentences joined with "ו-" — split them.
- Punctuation around English terms and numbers that breaks RTL rendering in Word: fix with the
  hebrew-with-english rules and check the DOCX for `w:bidi` (that skill's `check_docx_rtl.py` when present).

## Citations in Hebrew text

APA in Hebrew: (כהן, 2020), (כהן ולוי, 2019), (כהן ושות', 2018), English sources keep their Latin form
inside the Hebrew sentence: (Smith, 2020). Reference list: Latin entries then Hebrew entries, or as the
course says. Legal writing: the uniform citation rules (`citation-styles/hebrew-legal.md`).

## Before sending

Hebrew output (reply, Markdown, or text for a DOCX) passes `check_rtl.py` from the hebrew-with-english
skill with 0 errors.
