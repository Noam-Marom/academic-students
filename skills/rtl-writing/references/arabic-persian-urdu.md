# Arabic, Persian and Urdu

The bidi rules in `chat-markdown.md` are the same for every right-to-left script, and `scripts/check_rtl.py`
checks Arabic-script text exactly as it checks Hebrew. What changes is the vocabulary, the fonts and a few
script-specific details.

## Natural openers (the word that makes a line start right-to-left)

| Use | Arabic | Persian | Urdu |
|---|---|---|---|
| the command | الأمر `ls -la` | دستور `ls -la` | کمانڈ `ls -la` |
| the function | الدالة `malloc` | تابع `malloc` | فنکشن `malloc` |
| the file | الملف `main.c` | فایل `main.c` | فائل `main.c` |
| the language | لغة Python | زبان Python | زبان Python |
| the library | المكتبة NumPy | کتابخانه NumPy | لائبریری NumPy |
| the model | النموذج Transformer | مدل Transformer | ماڈل Transformer |
| note | ملاحظة: | نکته: | نوٹ: |

The checker's `--fix` suggestions are Hebrew; for these languages use the table above instead.

## Script details

- **ZWNJ (U+200C)** is part of Persian and Urdu spelling (`می‌شود`, `برنامه‌نویسی`). Never strip it and never
  replace it with a space; it is not a bidi control.
- **Digits:** Arabic-Indic (٠١٢٣) or Persian (۰۱۲۳) digits follow the course's usage; Western digits are fine in
  technical text. Either way a negative number needs the same care as in Hebrew (`check_rtl.py` flags it).
- **Kashida and diacritics** do not affect direction; leave them as the writer used them.

## Fonts and file formats

- **Word:** the same `w:bidi` / `w:rtl` settings as `docx.md`; set the complex-script font (`w:cs`) to a font
  with Arabic glyphs, e.g. Noto Naskh Arabic, Amiri, Vazirmatn (Persian) or Noto Nastaliq Urdu.
  `scripts/check_docx_rtl.py` checks Arabic-script paragraphs too.
- **LaTeX:** XeLaTeX or LuaLaTeX with polyglossia: `\setmainlanguage{arabic}` (or `persian`, `urdu`) and
  `\setotherlanguage{english}`, `\newfontfamily\arabicfont[Script=Arabic]{Amiri}`. For Persian, the
  `xepersian` package is the common alternative. English terms go in `\textenglish{…}` as in `latex.md`.
- **PowerPoint:** the same `rtl="1"` and complex-script font settings as `pptx.md`.
