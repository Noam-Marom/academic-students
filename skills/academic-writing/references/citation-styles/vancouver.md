# Vancouver (ICMJE)

Numeric. Medicine, nursing, public health.

## In-text and list rules

- In text: superscript or bracketed numbers in order of first citation: (1), [1] or ¹ — as the course specifies.
- Reference list by number; surname then initials without periods; up to six authors, then "et al.".
- Journal titles abbreviated per NLM (PubMed) catalogue.
- Hebrew articles: the original Hebrew title, or an English translation in brackets followed by "Hebrew." as PubMed does.

## Examples

1. Smith J, Lee K. Title of article. J Name. 2020;12(3):45-67. doi:10.1000/xyz
2. Katz R. A book title. 2nd ed. City: Publisher; 2018.
3. Doe J. A chapter. In: Roe R, editor. The book. City: Press; 2018. p. 10-20.
4. Site Name. A page [Internet]. 2021 [cited 2026 Nov 2]. Available from: https://example.org/p
5. Smith J, Lee K, Wu X, Katz R, Doe J, Roe R, et al. A large trial. Lancet. 2019;393:1-9.
6. כהן א, לוי ב. שם המאמר. הרפואה. 2019;158(4):230-4.

## Checks

- Every in-text citation ⇄ list entry: `scripts/check_citations.py`.
- Entries with fields from the student's own source only; an entry that cannot be resolved (DOI, catalogue, database) is kept and marked `[unverified]`, never completed from memory.
