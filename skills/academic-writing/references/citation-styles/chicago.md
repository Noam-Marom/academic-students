# Chicago 17th edition

Notes–bibliography (humanities, history) or author–date (sciences). Default here: notes–bibliography.

## In-text and list rules

- Footnote at first citation, full: 1. John Smith, *Title of Book* (City: Publisher, 2020), 45.
- Later citations, short: 2. Smith, *Title of Book*, 47. "Ibid." is discouraged in the 17th edition.
- Bibliography alphabetical, surname first, hanging indent.
- Hebrew sources in Hebrew script with the same punctuation; a transliterated title in brackets if the course requires it.

## Examples

1. Smith, John. *Title of Book*. City: Publisher, 2020.
2. Smith, John, and Kyung Lee. "Title of Article." *Journal Name* 12, no. 3 (2020): 45–67. https://doi.org/10.1000/xyz.
3. Katz, Ruth. "A Chapter." In *The Book*, edited by Jane Doe, 10–20. City: Press, 2018.
4. Site Name. "A Page." May 4, 2021. https://example.org/p.
5. Smith, John. "A Thesis." PhD diss., Some University, 2017.
6. כהן, אבי. *שם הספר*. תל אביב: הוצאה, 2019.

## Checks

- Every in-text citation ⇄ list entry: `scripts/check_citations.py`.
- Entries with fields from the student's own source only; an entry that cannot be resolved (DOI, catalogue, database) is kept and marked `[unverified]`, never completed from memory.
