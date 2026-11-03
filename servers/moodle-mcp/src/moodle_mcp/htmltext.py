"""Small HTML → Markdown / plain-text converter (stdlib only).

Moodle returns assignment intros, section summaries, forum posts and feedback as HTML. The model needs the
text, not the tags, and the sync writes `brief.md` / `announcements.md`. This handles the tags Moodle's
editor produces (paragraphs, breaks, headings, lists, bold/italic/code, links) and drops the rest. It is a
converter, not a sanitiser: whatever it outputs is still course data, to be scanned before it is trusted.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

_BLOCK = {"p", "div", "section", "article", "blockquote", "table", "tr", "pre", "hr"}
_HEADINGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
_SKIP = {"script", "style", "head", "title"}


class _Converter(HTMLParser):
    def __init__(self, markdown: bool):
        super().__init__(convert_charrefs=True)
        self.markdown = markdown
        self.parts: list[str] = []
        self.lists: list[list] = []  # stack of [kind, counter]
        self.skip = 0
        self.href: str | None = None
        self.pre = 0

    # -- helpers ---------------------------------------------------------------------------------------

    def _emit(self, text: str) -> None:
        self.parts.append(text)

    def _mark(self, md: str) -> None:
        if self.markdown:
            self._emit(md)

    def _block_break(self) -> None:
        self._emit("\n\n")

    # -- parser callbacks --------------------------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
            return
        if tag in _BLOCK:
            self._block_break()
            if tag == "pre":
                self.pre += 1
                self._mark("```\n")
        elif tag in _HEADINGS:
            self._block_break()
            self._mark(_HEADINGS[tag] + " ")
        elif tag == "br":
            self._emit("\n")
        elif tag in ("ul", "ol"):
            self._block_break()
            self.lists.append([tag, 0])
        elif tag == "li":
            self._emit("\n")
            if self.lists:
                kind, _ = self.lists[-1]
                self.lists[-1][1] += 1
                indent = "  " * (len(self.lists) - 1)
                self._mark(f"{indent}{self.lists[-1][1]}. " if kind == "ol" else f"{indent}- ")
            else:
                self._mark("- ")
        elif tag in ("strong", "b"):
            self._mark("**")
        elif tag in ("em", "i"):
            self._mark("*")
        elif tag == "code" and not self.pre:
            self._mark("`")
        elif tag == "a":
            self.href = dict(attrs).get("href")
            self._mark("[")
        elif tag == "img":
            alt = dict(attrs).get("alt") or ""
            if alt:
                self._emit(f"[image: {alt}]")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag in _BLOCK:
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
                self._mark("\n```")
            self._block_break()
        elif tag in _HEADINGS:
            self._block_break()
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            self._block_break()
        elif tag in ("strong", "b"):
            self._mark("**")
        elif tag in ("em", "i"):
            self._mark("*")
        elif tag == "code" and not self.pre:
            self._mark("`")
        elif tag == "a":
            if self.href and self.markdown:
                self._emit(f"]({self.href})")
            else:
                self._mark("]")
            self.href = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            self._emit(data)
        else:
            self._emit(re.sub(r"\s+", " ", data))

    # -- result ----------------------------------------------------------------------------------------

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [line.strip() if not self.pre else line for line in raw.split("\n")]
        out = "\n".join(lines)
        out = re.sub(r"[ \t]+\n", "\n", out)
        out = re.sub(r"\n{3,}", "\n\n", out)
        if self.markdown:
            out = re.sub(r"\[\]\([^)]*\)", "", out)  # empty link text
        return out.strip()


def html_to_markdown(html: str | None) -> str:
    """Convert Moodle HTML to compact Markdown. Empty / None → ''."""
    if not html:
        return ""
    conv = _Converter(markdown=True)
    conv.feed(html)
    conv.close()
    return conv.text()


def html_to_text(html: str | None) -> str:
    """Convert Moodle HTML to plain text with the same block structure and no Markdown markers."""
    if not html:
        return ""
    conv = _Converter(markdown=False)
    conv.feed(html)
    conv.close()
    return conv.text()
