"""Markdown -> Veriformis IR.

Built on markdown-it-py with GFM extensions (tables + strikethrough),
plus footnote and dollar-math plugins. Walks the flat token stream into
the canonical IR tree. Anything outside the canonical set is silently
dropped.

Provenance follows the extracted-stream contract: the canonical stream is
built incrementally as blocks are emitted — each top-level block's
``block_text()`` plus a ``"\\n\\n"`` separator — and every top-level block
carries ``span = Span(pos_before, pos_before + len(block_text))`` plus a
sequential ``block_index`` indexing that stream (never the raw file).
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin

import re
from pathlib import Path

from veriformis.ir import (
    Blockquote,
    Bold,
    Cell,
    Citation,
    Code,
    CodeBlock,
    Document,
    Endnote,
    EndnoteRef,
    Footnote,
    FootnoteRef,
    Heading,
    HorizontalRule,
    Image,
    Inline,
    Italic,
    LineBreak,
    Link,
    ListBlock,
    ListItem,
    Math,
    Paragraph,
    Span,
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    Text,
    block_text,
)
from veriformis.sources import ParseResult, register_source

ENDNOTE_PREFIX = "en:"

# Pandoc-style citation: ``[@key]`` or ``[@key, locator]``.
# Keys may contain letters, digits, and a conservative set of punctuation.
_CITATION_RE = re.compile(r"\[@([A-Za-z][\w:.\-]*)(?:,\s*([^\]]+))?\]")

# Pandoc attribute/anchor cruft (see _strip_pandoc_cruft).
#
# An empty-bracket span carrying an attribute block — ``[]{#id .anchor}`` —
# is removed wholesale (the optional whitespace before ``{`` is consumed so
# ``foo []{#a}`` collapses cleanly, not leaving a trailing space). What
# remains of a bare attribute block — ``{#id .class key=val}`` attached to a
# heading or word — is stripped separately. We only strip blocks that begin
# with ``#`` (id) or ``.`` (class): a leading ``#``/``.`` is the Pandoc
# attribute-block signature and avoids eating ordinary braces in prose.
_PANDOC_EMPTY_ANCHOR_RE = re.compile(r"\s*\[\]\{[^}]*\}")
_PANDOC_ATTR_BLOCK_RE = re.compile(r"\{[#.][^}]*\}")


def _make_parser() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark")
        .use(footnote_plugin)
        .use(dollarmath_plugin, allow_space=False, allow_digits=True)
        .enable(["table", "strikethrough"])
    )
    return md


def _parse_with_stream(source: str) -> tuple[Document, str]:
    """Parse markdown, attach provenance, return (document, stream).

    The stream is the canonical extracted text: top-level blocks' plain
    texts joined by ``"\\n\\n"``. Spans on the emitted blocks index it.
    """
    md = _make_parser()
    tokens = md.parse(source)
    doc = Document()
    _consume_blocks(tokens, 0, len(tokens), doc.children, doc)
    doc.children = _drop_empty_blocks(doc.children)
    return doc, _attach_provenance(doc)


def _attach_provenance(doc: Document) -> str:
    """Build the canonical stream from the final top-level blocks, setting
    each block's ``span`` (char offsets into the stream) and sequential
    ``block_index`` as its text is appended. Returns the stream."""
    parts: list[str] = []
    pos = 0
    for index, block in enumerate(doc.children):
        text = block_text(block)
        block.span = Span(pos, pos + len(text))
        block.block_index = index
        parts.append(text)
        parts.append("\n\n")
        pos += len(text) + 2
    if parts:
        parts.pop()  # drop the trailing separator
    return "".join(parts)


def parse_md(source: str) -> Document:
    """Library entry: parse a markdown string into a Document.

    Blocks carry spans into a canonical stream constructed the same way
    as ``parse_md_file`` (no SourceRef is registered)."""
    doc, _stream = _parse_with_stream(source)
    return doc


def parse_md_file(path: str | Path) -> ParseResult:
    """File entry: read, parse, register the source, return ParseResult."""
    p = Path(path)
    doc, stream = _parse_with_stream(p.read_text(encoding="utf-8"))
    source = register_source(p, "markdown", stream)
    doc.source_id = source.id
    return ParseResult(document=doc, source=source)


# ---------------------------------------------------------------------------
# Empty-node cleanup (post-parse)
# ---------------------------------------------------------------------------

# A Text value left behind by a Pandoc anchor that markdown-it parsed as
# literal emphasis markers: nothing but ``*`` repetitions (e.g. ``**`` or
# ``*``), optionally surrounded by whitespace. These carry no content and
# would otherwise leak into the output.
_STRAY_EMPHASIS_RE = re.compile(r"^\s*\*+\s*$")

# Wrapper inline nodes that are meaningless when they have no children.
_EMPTY_WRAPPERS = (Bold, Italic, Strikethrough, Superscript, Subscript)


def _clean_inlines(inlines: list) -> list:
    """Recursively drop empty emphasis wrappers and stray emphasis-marker
    Text nodes from an inline list.

    - ``Bold`` / ``Italic`` / ``Strikethrough`` / ``Superscript`` /
      ``Subscript`` with no remaining children are removed (Pandoc leaves
      empty ``****`` emphasis behind when it splits an anchor off a
      heading).
    - ``Text`` whose value is only ``*`` repetitions (``**``, ``*``) is
      removed — markdown-it parses a stray ``**`` as literal text, not
      emphasis.
    Wrappers carrying children are cleaned in place and kept.
    """
    out: list = []
    for node in inlines:
        if isinstance(node, Text):
            if _STRAY_EMPHASIS_RE.match(node.value):
                continue
            out.append(node)
        elif isinstance(node, _EMPTY_WRAPPERS):
            node.children = _clean_inlines(node.children)
            if node.children:
                out.append(node)
            # else: empty wrapper -> dropped
        elif isinstance(node, Link):
            node.children = _clean_inlines(node.children)
            out.append(node)
        else:
            out.append(node)
    return out


def _drop_empty_blocks(blocks: list) -> list:
    """Recursively clean inline content and drop blocks that became empty.

    A Paragraph whose inline content cleans down to nothing (it was only
    an anchor span, a stray ``**``, or an empty emphasis wrapper) is
    dropped entirely so it doesn't render as a blank stray paragraph.
    Headings are cleaned but never dropped — an empty heading is still a
    structural heading.
    """
    out: list = []
    for block in blocks:
        if isinstance(block, Paragraph):
            block.children = _clean_inlines(block.children)
            if _inlines_have_content(block.children):
                out.append(block)
            # else: empty paragraph -> dropped
        elif isinstance(block, Heading):
            block.children = _clean_inlines(block.children)
            out.append(block)
        elif isinstance(block, Blockquote):
            block.children = _drop_empty_blocks(block.children)
            out.append(block)
        elif isinstance(block, ListBlock):
            for item in block.items:
                item.children = _drop_empty_blocks(item.children)
            out.append(block)
        else:
            out.append(block)
    return out


def _inlines_have_content(inlines: list) -> bool:
    """True if the inline list carries any renderable content. A list of
    only whitespace-Text and/or bare ``LineBreak`` nodes counts as empty.

    Bare ``LineBreak`` nodes are excluded because Pandoc's
    empty-bold-with-hard-break artifact (``**\\`` then ``**``) parses to a
    Paragraph holding nothing but a ``LineBreak``. Such a paragraph carries
    no real content and would otherwise survive as a stray artifact. A
    paragraph with real content *plus* a LineBreak still has content via
    that real content, so genuine hard breaks are unaffected."""
    for node in inlines:
        if isinstance(node, Text):
            if node.value.strip():
                return True
        elif isinstance(node, LineBreak):
            continue
        else:
            # Any other non-Text inline (Image, Citation, refs, non-empty
            # wrappers, etc.) counts as content.
            return True
    return False


# ---------------------------------------------------------------------------
# Block-level walker
# ---------------------------------------------------------------------------

def _consume_blocks(
    tokens: list[Token], start: int, end: int, out: list, doc: Document | None = None
) -> int:
    """Walk tokens[start:end], append block nodes to ``out``, return next index.

    ``doc`` is the root Document; footnote definitions are stored on it.
    ``doc`` may be None for recursive calls where footnotes aren't expected
    (e.g., blockquote interiors), in which case footnote blocks are skipped.
    """
    i = start
    while i < end:
        tok = tokens[i]
        t = tok.type

        if t == "heading_open":
            level = int(tok.tag[1])
            j = _find_close(tokens, i + 1, end, "heading_close")
            inlines = _inline_children(tokens[i + 1 : j])
            out.append(Heading(level=level, children=inlines))
            i = j + 1

        elif t == "paragraph_open":
            j = _find_close(tokens, i + 1, end, "paragraph_close")
            inlines = _inline_children(tokens[i + 1 : j])
            # Standalone image paragraph -> promote to block Image
            if len(inlines) == 1 and isinstance(inlines[0], Image):
                out.append(inlines[0])
            else:
                out.append(Paragraph(children=inlines))
            i = j + 1

        elif t == "bullet_list_open":
            j = _find_close(tokens, i + 1, end, "bullet_list_close")
            items = _consume_list_items(tokens, i + 1, j)
            out.append(ListBlock(ordered=False, items=items))
            i = j + 1

        elif t == "ordered_list_open":
            j = _find_close(tokens, i + 1, end, "ordered_list_close")
            items = _consume_list_items(tokens, i + 1, j)
            out.append(ListBlock(ordered=True, items=items))
            i = j + 1

        elif t == "blockquote_open":
            j = _find_close(tokens, i + 1, end, "blockquote_close")
            inner: list = []
            _consume_blocks(tokens, i + 1, j, inner, doc)
            out.append(Blockquote(children=inner))
            i = j + 1

        elif t == "fence" or t == "code_block":
            lang = (tok.info or "").strip() or None
            text = tok.content.rstrip("\n")
            out.append(CodeBlock(text=text, language=lang))
            i += 1

        elif t == "hr":
            out.append(HorizontalRule())
            i += 1

        elif t == "table_open":
            j = _find_close(tokens, i + 1, end, "table_close")
            out.append(_consume_table(tokens, i + 1, j))
            i = j + 1

        elif t == "footnote_block_open":
            j = _find_close(tokens, i + 1, end, "footnote_block_close")
            if doc is not None:
                _consume_footnote_block(tokens, i + 1, j, doc)
            i = j + 1

        elif t == "math_block":
            source = (tok.content or "").strip("\n")
            out.append(Math(source=source, display=True))
            i += 1

        else:
            # Unknown / unsupported block token — skip it.
            i += 1

    return i


def _consume_footnote_block(
    tokens: list[Token], start: int, end: int, doc: Document
) -> None:
    """Walk the children of a footnote_block, populating ``doc.footnotes``
    or ``doc.endnotes`` depending on whether the label carries the
    endnote prefix."""
    i = start
    while i < end:
        tok = tokens[i]
        if tok.type == "footnote_open":
            label = (tok.meta or {}).get("label")
            # Fallback to meta['id'] if label is missing (shouldn't happen)
            raw_id = label if label is not None else str((tok.meta or {}).get("id", ""))
            j = _find_close(tokens, i + 1, end, "footnote_close")
            children: list = []
            # Walk the block-level children of this note. The plugin may
            # emit a footnote_anchor inline within the last paragraph — we
            # drop those during inline walking (they're a round-trip artifact).
            _consume_blocks(tokens, i + 1, j, children, doc)
            if raw_id.startswith(ENDNOTE_PREFIX):
                en_id = raw_id[len(ENDNOTE_PREFIX):]
                if en_id:
                    doc.endnotes[en_id] = Endnote(id=en_id, children=children)
            elif raw_id:
                doc.footnotes[raw_id] = Footnote(id=raw_id, children=children)
            i = j + 1
        else:
            i += 1


def _find_close(tokens: list[Token], start: int, end: int, close_type: str) -> int:
    """Return the index of the matching close token, accounting for nesting."""
    open_type = close_type.replace("_close", "_open")
    depth = 1
    i = start
    while i < end:
        t = tokens[i].type
        if t == open_type:
            depth += 1
        elif t == close_type:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Unmatched {open_type} in token stream")


def _consume_list_items(tokens: list[Token], start: int, end: int) -> list[ListItem]:
    items: list[ListItem] = []
    i = start
    while i < end:
        tok = tokens[i]
        if tok.type == "list_item_open":
            j = _find_close(tokens, i + 1, end, "list_item_close")
            inner: list = []
            _consume_blocks(tokens, i + 1, j, inner)
            checked = _detect_and_strip_task_marker(inner)
            items.append(ListItem(children=inner, checked=checked))
            i = j + 1
        else:
            i += 1
    return items


def _detect_and_strip_task_marker(blocks: list) -> bool | None:
    """If the first block is a Paragraph whose first inline is a Text
    starting with ``[ ]``, ``[x]``, or ``[X]`` followed by whitespace,
    strip that marker and return the checked state. Otherwise return
    None."""
    if not blocks or not isinstance(blocks[0], Paragraph):
        return None
    para = blocks[0]
    if not para.children or not isinstance(para.children[0], Text):
        return None
    txt = para.children[0].value
    if len(txt) < 4:
        return None
    if txt.startswith("[ ] "):
        para.children[0] = Text(value=txt[4:])
        return False
    if txt.startswith("[x] ") or txt.startswith("[X] "):
        para.children[0] = Text(value=txt[4:])
        return True
    return None


def _consume_table(tokens: list[Token], start: int, end: int) -> Table:
    headers: list[Cell] = []
    rows: list[list[Cell]] = []
    alignments: list = []

    i = start
    in_head = False
    in_body = False
    current_row: list[Cell] | None = None

    while i < end:
        tok = tokens[i]
        t = tok.type

        if t == "thead_open":
            in_head = True
            i += 1
        elif t == "thead_close":
            in_head = False
            i += 1
        elif t == "tbody_open":
            in_body = True
            i += 1
        elif t == "tbody_close":
            in_body = False
            i += 1
        elif t == "tr_open":
            current_row = []
            i += 1
        elif t == "tr_close":
            if in_head:
                headers = current_row or []
                # Capture alignments from header cells
                # (markdown-it places style="text-align:..." on th_open)
            elif in_body and current_row is not None:
                rows.append(current_row)
            current_row = None
            i += 1
        elif t in ("th_open", "td_open"):
            # Extract alignment from style attribute (header row only)
            if t == "th_open":
                style = _attr(tok, "style") or ""
                if "text-align:left" in style:
                    alignments.append("left")
                elif "text-align:center" in style:
                    alignments.append("center")
                elif "text-align:right" in style:
                    alignments.append("right")
                else:
                    alignments.append(None)
            close = "th_close" if t == "th_open" else "td_close"
            j = _find_close(tokens, i + 1, end, close)
            inlines = _inline_children(tokens[i + 1 : j])
            if current_row is not None:
                current_row.append(Cell(children=inlines))
            i = j + 1
        else:
            i += 1

    return Table(headers=headers, rows=rows, alignments=alignments)


def _attr(tok: Token, name: str) -> str | None:
    if not tok.attrs:
        return None
    val = tok.attrs.get(name)
    return val if val is None else str(val)


# ---------------------------------------------------------------------------
# Inline walker
# ---------------------------------------------------------------------------

def _inline_children(block_tokens: list[Token]) -> list[Inline]:
    """Given the tokens *inside* a heading/paragraph/cell (which should be
    exactly one `inline` token), return the parsed inline children."""
    for tok in block_tokens:
        if tok.type == "inline":
            return _walk_inline(tok.children or [])
    return []


def _strip_pandoc_cruft(value: str) -> str:
    """Remove Pandoc attribute/anchor cruft from a prose Text value.

    Pandoc emits attribute blocks (``{#id .class key=val}``) on headings
    and inline empty anchor spans (``[]{#id .anchor}``) that the canonical
    IR has no home for. They must not leak into the output as literal
    text. This runs only on ``Text`` node values (via ``_split_sup_sub``)
    so ``Code`` / ``CodeBlock`` content — which is literal — is untouched.

    Order matters:
    1. Drop empty-bracket anchor spans whole (``[]{...}``), consuming any
       leading whitespace so ``foo []{#a} bar`` -> ``foo bar`` without a
       doubled space.
    2. Drop any remaining bare attribute block (``{#id .class}``) — the
       form attached to headings/words with no bracket span.
    3. Collapse the double spaces a mid-line removal can produce and
       strip leading/trailing whitespace if the value reduced to nothing
       meaningful.
    """
    if "{" not in value:
        return value
    value = _PANDOC_EMPTY_ANCHOR_RE.sub("", value)
    value = _PANDOC_ATTR_BLOCK_RE.sub("", value)
    # Collapse runs of spaces left where cruft was excised mid-line.
    value = re.sub(r"  +", " ", value)
    # If stripping reduced the value to whitespace-only, normalise to "".
    if not value.strip():
        return ""
    return value


def _split_sup_sub(text_value: str) -> list[Inline]:
    """Split a raw text string into Text / Superscript / Subscript /
    Citation nodes.

    Pandoc conventions:
    - ``^content^`` — superscript; content must have no whitespace
    - ``~content~`` — subscript; same rule
    - ``[@key]`` / ``[@key, locator]`` — author-date citation

    The strikethrough marker ``~~`` is consumed by markdown-it-py's GFM
    plugin before text reaches here, so any ``~`` we see is literal or a
    subscript delimiter.

    Pandoc attribute/anchor cruft is stripped first (see
    ``_strip_pandoc_cruft``). This runs only on ``Text`` values, so
    code spans and code blocks — which never reach this function — keep
    their literal ``{#id}`` / ``[]{#a}`` content.
    """
    text_value = _strip_pandoc_cruft(text_value)
    # First pass: extract citation matches by scanning the whole string
    # for the regex. Citations are unambiguous (opening ``[@``), so we
    # can split around them before doing the character-by-character
    # sup/sub pass on the interstitial text.
    citation_segments: list[tuple[str, tuple | None]] = []  # (text, None) or ("", (key, locator))
    last = 0
    for m in _CITATION_RE.finditer(text_value):
        if m.start() > last:
            citation_segments.append((text_value[last:m.start()], None))
        key = m.group(1)
        locator = m.group(2)
        citation_segments.append(("", (key, locator)))
        last = m.end()
    if last < len(text_value):
        citation_segments.append((text_value[last:], None))
    if not citation_segments:
        citation_segments.append((text_value, None))

    result: list[Inline] = []
    for seg_text, cite in citation_segments:
        if cite is not None:
            key, locator = cite
            result.append(Citation(key=key, locator=locator))
            continue
        # Sup/sub pass on this segment of literal text
        result.extend(_split_sup_sub_only(seg_text))
    return result


def _split_sup_sub_only(text_value: str) -> list[Inline]:
    """The ``^X^`` / ``~X~`` scanner, split out so the citation pre-pass
    can call it on each literal-text segment."""
    result: list[Inline] = []
    buf: list[str] = []

    def flush_buf() -> None:
        if buf:
            result.append(Text(value="".join(buf)))
            buf.clear()

    i = 0
    n = len(text_value)
    while i < n:
        ch = text_value[i]
        if ch == "^":
            end = _find_marker(text_value, i + 1, "^")
            if end is not None:
                flush_buf()
                result.append(Superscript(children=[Text(value=text_value[i + 1 : end])]))
                i = end + 1
                continue
        elif ch == "~":
            end = _find_marker(text_value, i + 1, "~")
            if end is not None:
                flush_buf()
                result.append(Subscript(children=[Text(value=text_value[i + 1 : end])]))
                i = end + 1
                continue
        buf.append(ch)
        i += 1
    flush_buf()
    return result


def _find_marker(s: str, start: int, marker: str) -> int | None:
    """Return index of closing ``marker`` for a sup/sub span starting at
    ``start``, or ``None`` if the span isn't valid (empty, contains
    whitespace, or no close found)."""
    i = start
    while i < len(s):
        ch = s[i]
        if ch == marker:
            if i == start:
                return None  # empty content
            return i
        if ch.isspace():
            return None  # Pandoc rule: no whitespace in sup/sub content
        i += 1
    return None


def _walk_inline(children: list[Token]) -> list[Inline]:
    out: list[Inline] = []
    stack: list[list[Inline]] = [out]

    def push(node: Inline) -> None:
        stack[-1].append(node)

    def push_text(value: str) -> None:
        """Push text, but first split on Pandoc-style ``^sup^`` / ``~sub~``
        patterns. Strikethrough ``~~...~~`` is already consumed upstream by
        markdown-it-py's GFM plugin, so any ``~`` here is literal or a
        subscript marker."""
        for node in _split_sup_sub(value):
            push(node)

    i = 0
    while i < len(children):
        tok = children[i]
        t = tok.type

        if t == "text":
            if tok.content:
                push_text(tok.content)
        elif t == "softbreak":
            # Soft break: treat as a space in canonical form
            if stack[-1] and isinstance(stack[-1][-1], Text):
                stack[-1][-1].value += " "
            else:
                push(Text(value=" "))
        elif t == "hardbreak":
            push(LineBreak())
        elif t == "strong_open":
            node = Bold()
            push(node)
            stack.append(node.children)
        elif t == "strong_close":
            stack.pop()
        elif t == "em_open":
            node_i = Italic()
            push(node_i)
            stack.append(node_i.children)
        elif t == "em_close":
            stack.pop()
        elif t == "s_open":
            node_s = Strikethrough()
            push(node_s)
            stack.append(node_s.children)
        elif t == "s_close":
            stack.pop()
        elif t == "code_inline":
            push(Code(value=tok.content))
        elif t == "link_open":
            href = _attr(tok, "href") or ""
            title = _attr(tok, "title")
            node_l = Link(href=href, title=title)
            push(node_l)
            stack.append(node_l.children)
        elif t == "link_close":
            stack.pop()
        elif t == "image":
            alt = (tok.content or "").strip()
            src = _attr(tok, "src") or ""
            title = _attr(tok, "title")
            push(Image(alt=alt, src=src, title=title))
        elif t == "footnote_ref":
            label = (tok.meta or {}).get("label")
            raw_id = label if label is not None else str((tok.meta or {}).get("id", ""))
            if raw_id.startswith(ENDNOTE_PREFIX):
                en_id = raw_id[len(ENDNOTE_PREFIX):]
                if en_id:
                    push(EndnoteRef(id=en_id))
            elif raw_id:
                push(FootnoteRef(id=raw_id))
        elif t == "footnote_anchor":
            # Backlink anchor inside a footnote body — drop on ingest;
            # markdown-it regenerates it on the next parse.
            pass
        elif t == "math_inline":
            push(Math(source=tok.content or "", display=False))
        else:
            # Unknown inline token — skip silently
            pass

        i += 1

    return out
