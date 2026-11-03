"""Dependency-free HTML → Markdown / plain text for Moodle intros, summaries and forum posts."""
from __future__ import annotations

from moodle_mcp.htmltext import html_to_markdown, html_to_text  # noqa: E402


def test_paragraphs_become_blank_line_separated_blocks():
    assert html_to_markdown("<p>One.</p><p>Two.</p>") == "One.\n\nTwo."


def test_inline_formatting_and_entities():
    out = html_to_markdown("<p>Use <strong>fork</strong> &amp; <em>exec</em> with <code>wait()</code> &ndash; ok</p>")
    assert out == "Use **fork** & *exec* with `wait()` – ok"


def test_lists_and_line_breaks():
    out = html_to_markdown("<ul><li>fork</li><li>exec</li></ul><p>Due <b>20/11</b><br>at 23:55</p>")
    assert out == "- fork\n- exec\n\nDue **20/11**\nat 23:55"


def test_ordered_list_numbering_and_headings():
    out = html_to_markdown("<h3>Steps</h3><ol><li>read</li><li>plan</li></ol>")
    assert out == "### Steps\n\n1. read\n2. plan"


def test_links_keep_href():
    out = html_to_markdown('See the <a href="https://moodle.example.ac.il/mod/page/view.php?id=1">style guide</a>.')
    assert out == "See the [style guide](https://moodle.example.ac.il/mod/page/view.php?id=1)."


def test_script_and_style_are_dropped_and_whitespace_collapsed():
    out = html_to_markdown("<style>p{}</style><p>Hello\n\n   world</p><script>alert(1)</script>")
    assert out == "Hello world"


def test_plain_text_has_no_markdown_markers():
    assert html_to_text("<p>Use <strong>fork</strong> and <a href='x'>this</a>.</p>") == "Use fork and this."


def test_empty_and_none_inputs():
    assert html_to_markdown("") == ""
    assert html_to_markdown(None) == ""
    assert html_to_text("   ") == ""
