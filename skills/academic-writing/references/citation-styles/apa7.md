# APA 7th edition

Author–date. Social sciences, education, psychology, nursing, business.

## In-text and list rules

- Parenthetical: (Smith, 2020), (Smith & Lee, 2020), (Smith et al., 2019) for three or more authors; page for quotes: (Smith, 2020, p. 14).
- Narrative: Smith (2020) argues…; Hebrew: (כהן, 2020), (כהן ולוי, 2019), (כהן ושות', 2018), לפי כהן (2020).
- Same author, same year: 2020a, 2020b, ordered by title.
- Reference list: alphabetical by first author; hanging indent; DOI as https://doi.org/…; Latin-alphabet entries first, then Hebrew entries in Hebrew alphabetical order (the common Israeli convention; `format_refs.py --mixed` interleaves).

## Examples

1. Smith, J., & Lee, K. (2020). Title of article. *Journal Name, 12*(3), 45–67. https://doi.org/10.1000/xyz
2. Katz, R. (2018). *A book title in sentence case* (2nd ed.). Publisher.
3. Smith, J. (2018). A chapter. In J. Doe (Ed.), *The Book* (pp. 10–20). Press.
4. Smith, J. (2021, May 4). *A page*. Site Name. https://example.org/p
5. Smith, J. (2017). *A thesis* [Doctoral dissertation, Some University].
6. כהן, א' (2019). *שם הספר*. הוצאה.

## Checks

- Every in-text citation ⇄ list entry: `scripts/check_citations.py`.
- Entries with fields from the student's own source only; an entry that cannot be resolved (DOI, catalogue, database) is kept and marked `[unverified]`, never completed from memory.
