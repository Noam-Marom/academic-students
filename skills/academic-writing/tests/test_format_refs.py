"""format_refs.py — CSL-JSON items → APA 7 / IEEE reference entries, Hebrew entries handled."""
import json
import pathlib
import subprocess
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts/format_refs.py"


@pytest.fixture(scope="module")
def fr(load_module):
    return load_module(SCRIPT, "writing_format_refs")


ARTICLE = {
    "type": "article-journal",
    "author": [{"family": "Smith", "given": "John"}, {"family": "Lee", "given": "Kyung"}],
    "issued": {"date-parts": [[2020]]},
    "title": "Title of article",
    "container-title": "Journal Name",
    "volume": "12",
    "issue": "3",
    "page": "45-67",
    "DOI": "10.1000/xyz",
}
HEBREW_BOOK = {
    "type": "book",
    "author": [{"family": "כהן", "given": "אבי"}],
    "issued": {"date-parts": [[2019]]},
    "title": "שם הספר",
    "publisher": "הוצאה",
}


def test_apa7_journal_article_exact(fr):
    assert fr.format_refs([ARTICLE], "apa7") == [
        "Smith, J., & Lee, K. (2020). Title of article. *Journal Name, 12*(3), 45–67. https://doi.org/10.1000/xyz"
    ]


def test_ieee_journal_article_exact(fr):
    assert fr.format_refs([ARTICLE], "ieee") == [
        '[1] J. Smith and K. Lee, "Title of article," *Journal Name*, vol. 12, no. 3, pp. 45–67, 2020, doi: 10.1000/xyz.'
    ]


def test_apa7_hebrew_book_exact(fr):
    assert fr.format_refs([HEBREW_BOOK], "apa7") == ["כהן, א' (2019). *שם הספר*. הוצאה."]


def test_apa7_two_hebrew_authors_join_with_vav(fr):
    item = dict(HEBREW_BOOK, author=[{"family": "כהן", "given": "אבי"}, {"family": "לוי", "given": "בת-שבע"}])
    [entry] = fr.format_refs([item], "apa7")
    assert entry.startswith("כהן, א' ולוי, ב' (2019).")
    assert "&" not in entry


def test_apa7_three_latin_authors_and_no_issue_no_doi(fr):
    item = dict(ARTICLE, author=ARTICLE["author"] + [{"family": "Wu", "given": "Xin"}], DOI=None, issue=None, URL="https://example.org/a")
    del item["DOI"]
    del item["issue"]
    assert fr.format_refs([item], "apa7") == [
        "Smith, J., Lee, K., & Wu, X. (2020). Title of article. *Journal Name, 12*, 45–67. https://example.org/a"
    ]


def test_apa7_chapter_webpage_thesis_shapes(fr):
    chapter = {"type": "chapter", "author": [{"family": "Smith", "given": "John"}], "issued": {"date-parts": [[2018]]},
               "title": "A chapter", "container-title": "The Book", "editor": [{"family": "Doe", "given": "Jane"}],
               "page": "10-20", "publisher": "Press"}
    web = {"type": "webpage", "author": [{"family": "Smith", "given": "John"}], "issued": {"date-parts": [[2021, 5, 4]]},
           "title": "A page", "container-title": "Site Name", "URL": "https://example.org/p"}
    thesis = {"type": "thesis", "author": [{"family": "Smith", "given": "John"}], "issued": {"date-parts": [[2017]]},
              "title": "A thesis", "genre": "Doctoral dissertation", "publisher": "Some University"}
    out = fr.format_refs([chapter, web, thesis], "apa7")
    assert out == [  # same author → APA orders by year
        "Smith, J. (2017). *A thesis* [Doctoral dissertation, Some University].",
        "Smith, J. (2018). A chapter. In J. Doe (Ed.), *The Book* (pp. 10–20). Press.",
        "Smith, J. (2021, May 4). *A page*. Site Name. https://example.org/p",
    ]


def test_ieee_book_and_many_authors(fr):
    book = {"type": "book", "author": [{"family": f"Author{i}", "given": "A"} for i in range(7)],
            "issued": {"date-parts": [[2015]]}, "title": "Big Book", "publisher": "Pub", "publisher-place": "City"}
    assert fr.format_refs([book], "ieee") == ["[1] A. Author0 et al., *Big Book*. City: Pub, 2015."]


def test_ieee_numbers_follow_input_order(fr):
    out = fr.format_refs([HEBREW_BOOK, ARTICLE], "ieee")
    assert out[0].startswith("[1] א' כהן, *שם הספר*.") and out[1].startswith("[2] J. Smith")


def test_apa7_default_sort_latin_then_hebrew(fr):
    jones = dict(ARTICLE, author=[{"family": "Jones", "given": "Al"}])
    out = fr.format_refs([HEBREW_BOOK, ARTICLE, jones], "apa7")
    assert [e.split(",")[0] for e in out] == ["Jones", "Smith", "כהן"]


def test_apa7_mixed_sort_interleaves_by_transliteration(fr):
    jones = dict(ARTICLE, author=[{"family": "Jones", "given": "Al"}])
    out = fr.format_refs([HEBREW_BOOK, ARTICLE, jones], "apa7", mixed=True)
    assert [e.split(",")[0] for e in out] == ["Jones", "כהן", "Smith"]  # כ ≈ k sorts between J and S


def test_missing_date_and_missing_author(fr):
    item = {"type": "webpage", "title": "Anon page", "container-title": "Site", "URL": "https://example.org"}
    [entry] = fr.format_refs([item], "apa7")
    assert entry == "*Anon page*. (n.d.). Site. https://example.org"


def test_unknown_style_raises(fr):
    with pytest.raises(ValueError):
        fr.format_refs([ARTICLE], "chicago")


def test_cli_json_and_text(tmp_path):
    f = tmp_path / "refs.json"
    f.write_text(json.dumps([ARTICLE]), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--style", "ieee", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["style"] == "ieee" and out["entries"][0].startswith("[1] J. Smith")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(f), "--style", "apa7"], capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip().startswith("Smith, J., & Lee, K. (2020).")


def test_cli_csl_without_citeproc_exits_2(tmp_path, monkeypatch, load_module):
    monkeypatch.setitem(sys.modules, "citeproc", None)
    mod = load_module(SCRIPT, "writing_format_refs_nociteproc")
    f = tmp_path / "refs.json"
    f.write_text(json.dumps([ARTICLE]), encoding="utf-8")
    csl = tmp_path / "style.csl"
    csl.write_text("<style/>", encoding="utf-8")
    assert mod.main([str(f), "--style", "apa7", "--csl", str(csl)]) == 2


def test_cli_bad_input_exits_2(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(tmp_path / "none.json"), "--style", "apa7"], capture_output=True, text=True)
    assert r.returncode == 2
