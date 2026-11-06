# Hebrew in LaTeX

Use **XeLaTeX or LuaLaTeX** with `polyglossia` (or `babel` on LuaLaTeX). pdfLaTeX with the old `culmus`
setup still works on some machines but breaks easily; do not start a new document with it. On Overleaf set
Menu → Compiler → XeLaTeX.

## Minimal preamble (XeLaTeX)

```latex
\documentclass[12pt]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
\newfontfamily\hebrewfont[Script=Hebrew]{David CLM}      % or Noto Sans Hebrew, Frank Ruehl CLM
\newfontfamily\hebrewfonttt[Script=Hebrew]{Miriam Mono CLM}
\newfontfamily\englishfont{Latin Modern Roman}
\usepackage{amsmath}
\usepackage{bidi}   % load last; polyglossia loads it on XeLaTeX anyway
\begin{document}
\section{מבוא}
אלגוריתם \textenglish{Raft} מבטיח הסכמה בין שרתים גם כאשר חלק מהם נופלים.
\end{document}
```

"Missing character: There is no א in font …" means the font has no Hebrew glyphs: change `\hebrewfont`.

## Mixing languages

- Inline English inside Hebrew: `\textenglish{consensus}` (or `\LR{...}` from `bidi`). Inline Hebrew inside English: `\texthebrew{...}`.
- A whole English block (abstract, quotation, code listing caption): `\begin{english} … \end{english}`.
- Code: `\textenglish{\texttt{malloc}}`; listings environments are LTR by default.
- Math is always left-to-right; `\(x^2\)` and `\[ … \]` inside Hebrew paragraphs need no wrapping. Text inside
  math (`\text{...}`) follows the current language — wrap English labels in `\textenglish`.
- Numbers in Hebrew text render correctly; ranges with a hyphen (3–5) may need `\LR{3--5}`.

## Section titles, captions, tables

- English words inside `\section{}` must be wrapped: `\section{מנגנון \textenglish{Paxos}}`.
- `bidi` mirrors `tabular` column order in RTL context; write columns in reading order (right to left) or wrap
  the table in `\begin{english}` if it is English.
- Figure captions follow the paragraph language.

## Bibliography

biblatex + biber: give each entry `langid = {hebrew}` or `{english}`; with `\usepackage[style=apa]{biblatex}`
Hebrew entries are formatted with Hebrew punctuation. Keep separate `.bib` keys for Hebrew and English sources
if the department wants separate lists (`\printbibliography[keyword=hebrew]`).

## LuaLaTeX + babel alternative

```latex
\usepackage[bidi=basic]{babel}
\babelprovide[main, import]{hebrew}
\babelprovide[import]{english}
\babelfont[hebrew]{rm}{Noto Serif Hebrew}
```

## Checklist

1. XeLaTeX or LuaLaTeX selected.
2. A Hebrew-capable font set; no "Missing character" warnings.
3. Every English word in Hebrew text wrapped (`\textenglish`), including in titles.
4. Math left as is; text inside math wrapped.
5. Compile once and check the PDF visually around every English term.
