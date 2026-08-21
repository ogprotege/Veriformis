"""Markdown -> Veriformis IR.

Built on markdown-it-py with GFM extensions (tables + strikethrough),
plus footnote and dollar-math plugins. Walks the flat token stream into
the canonical IR tree. Anything outside the canonical set is recorded in
the mandatory parse report before it is omitted.

Provenance follows the extracted-stream contract. Body, footnote, and endnote
blocks enter one deterministic canonical stream. Every source block carries
a span and unique block index into that stream.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin

import re
from pathlib import Path

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.identity import sha256_digest
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
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    Text,
    attach_canonical_provenance,
)
from veriformis.sources import ParseResult, register_source

ENDNOTE_PREFIX = "en:"
PARSER_VERSION = "1.2.0"

# Pandoc-style citation: ``[@key]`` or ``[@key, locator]``.
# Keys may contain letters, digits, and a conservative set of punctuation.
_CITATION_RE = re.compile(r"\[@([A-Za-z][\w:.\-]*)(?:,\s*([^\]]+))?\]")

# Pandoc cleanup is intentionally conservative. An attribute block must start
# with a syntactically valid id/class and every remaining atom must also be a
# valid id, class, or key/value attribute. Bare blocks are removed only at the
# end of a heading. This prevents ordinary prose such as
# ``{.not-an-attribute}`` from being reinterpreted and deleted.
_PANDOC_NAME = r"[A-Za-z_][A-Za-z0-9_.:-]*"
_PANDOC_VALUE = r'(?:"[^"{}\n]*"|\'[^\'{}\n]*\'|[^\s{}\n]+)'
_PANDOC_ATOM = rf"(?:[.#]{_PANDOC_NAME}|{_PANDOC_NAME}={_PANDOC_VALUE})"
_PANDOC_ATTR_BODY = rf"[.#]{_PANDOC_NAME}(?:[ \t]+{_PANDOC_ATOM})*"
_PANDOC_EMPTY_ANCHOR_RE = re.compile(rf"\[\]\{{{_PANDOC_ATTR_BODY}\}}")
_PANDOC_TRAILING_ATTR_RE = re.compile(rf"\{{{_PANDOC_ATTR_BODY}\}}(?=[ \t]*$)")

_FOOTNOTE_DEFINITION_RE = re.compile(r"^[ \t]{0,3}\[\^([^\] \r\n]+)\]:")

# The footnote plugin recognizes definitions inside blockquotes and list
# items (verified empirically), so the raw pre-pass must see through leading
# container markers to inventory the same definitions the plugin resolves.
_CONTAINER_MARKER_RE = re.compile(
    r"[ \t]{0,3}(?:>[ \t]?|[-*+][ \t]+|\d{1,9}[.)][ \t]+)"
)

_SUPPORTED_TOKEN_TYPES = {
    "blockquote_close",
    "blockquote_open",
    "bullet_list_close",
    "bullet_list_open",
    "code_block",
    "code_inline",
    "em_close",
    "em_open",
    "fence",
    "footnote_anchor",
    "footnote_block_close",
    "footnote_block_open",
    "footnote_close",
    "footnote_open",
    "footnote_ref",
    "hardbreak",
    "heading_close",
    "heading_open",
    "hr",
    "image",
    "inline",
    "link_close",
    "link_open",
    "list_item_close",
    "list_item_open",
    "math_block",
    "math_inline",
    "ordered_list_close",
    "ordered_list_open",
    "paragraph_close",
    "paragraph_open",
    "s_close",
    "s_open",
    "softbreak",
    "strong_close",
    "strong_open",
    "table_close",
    "table_open",
    "tbody_close",
    "tbody_open",
    "td_close",
    "td_open",
    "text",
    "th_close",
    "th_open",
    "thead_close",
    "thead_open",
    "tr_close",
    "tr_open",
}


def _make_parser() -> MarkdownIt:
    md = (
        MarkdownIt("commonmark")
        .use(footnote_plugin)
        .use(dollarmath_plugin, allow_space=False, allow_digits=True)
        .enable(["table", "strikethrough"])
    )
    # markdown-it records the normalized reference label on reference-link
    # tokens only when this option is enabled. That gives the loss inventory
    # an exact used/unused signal without re-parsing raw brackets heuristically.
    md.options["store_labels"] = True
    return md


def _parse_with_stream(source: str) -> tuple[Document, str, list[dict]]:
    """Parse markdown, attach provenance, return (document, stream).

    The stream is the canonical extracted text: top-level blocks' plain
    texts joined by ``"\\n\\n"``. Spans on the emitted blocks index it.
    """
    md = _make_parser()
    environment: dict = {}
    tokens = md.parse(source, environment)
    diagnostic_specs = _diagnostic_specs(tokens, source, environment)
    doc = Document()
    _consume_blocks(tokens, 0, len(tokens), doc.children, doc)
    doc.children = _drop_empty_blocks(doc.children)
    return doc, attach_canonical_provenance(doc), diagnostic_specs


def _diagnostic_specs(
    tokens: list[Token], source: str, environment: dict
) -> list[dict]:
    """Inventory every known omission before the token stream is consumed."""
    specs = _source_definition_diagnostic_specs(source, tokens, environment)

    def walk(
        items: list[Token],
        inherited_map: list[int] | None,
        prefix: tuple[int, ...],
        *,
        heading_inline: bool = False,
    ) -> None:
        inline_depth = 0
        for index, token in enumerate(items):
            if token.nesting < 0:
                inline_depth = max(0, inline_depth - 1)
            token_path = prefix + (index,)
            location_map = token.map or inherited_map
            child_is_heading = (
                token.type == "inline"
                and index > 0
                and items[index - 1].type == "heading_open"
            )
            if token.type in {"html_block", "html_inline"}:
                start, end = location_map or [0, 1]
                specs.append(
                    {
                        "code": f"markdown.{token.type.replace('_', '-')}-omitted",
                        "location": DiagnosticLocation(
                            kind="text",
                            line_start=start + 1,
                            line_end=max(start + 1, end),
                        ),
                        "message": "Raw HTML is outside the canonical Markdown IR and was omitted.",
                        "severity": "warning",
                        "disposition": "omitted",
                        "loss_kind": "text"
                        if token.type == "html_block"
                        else "structure",
                        "details": {
                            "token_type": token.type,
                            "token_path": list(token_path),
                            "content_sha256": sha256_digest(token.content or ""),
                        },
                    }
                )
            elif token.type not in _SUPPORTED_TOKEN_TYPES:
                start, end = location_map or [0, 1]
                specs.append(
                    {
                        "code": "markdown.unsupported-token-omitted",
                        "location": DiagnosticLocation(
                            kind="text",
                            line_start=start + 1,
                            line_end=max(start + 1, end),
                        ),
                        "message": (
                            f"Markdown token {token.type!r} is outside the canonical IR "
                            "and was omitted."
                        ),
                        "severity": "warning",
                        "disposition": "omitted",
                        "loss_kind": "unknown",
                        "details": {
                            "token_type": token.type,
                            "token_tag": token.tag,
                            "token_nesting": token.nesting,
                            "token_path": list(token_path),
                            "content_sha256": sha256_digest(token.content or ""),
                        },
                    }
                )
            if token.type == "ordered_list_open":
                start_value = (token.attrs or {}).get("start", 1)
                if str(start_value) != "1":
                    start, end = location_map or [0, 1]
                    specs.append(
                        {
                            "code": "markdown.ordered-list-start-omitted",
                            "location": DiagnosticLocation(
                                kind="text",
                                line_start=start + 1,
                                line_end=max(start + 1, end),
                            ),
                            "message": (
                                "The ordered-list starting ordinal has no canonical "
                                "IR field and was omitted."
                            ),
                            "severity": "warning",
                            "disposition": "omitted",
                            "loss_kind": "metadata",
                            "details": {
                                "start": str(start_value),
                                "token_path": list(token_path),
                            },
                        }
                    )
            elif token.type == "softbreak":
                start, end = location_map or [0, 1]
                specs.append(
                    {
                        "code": "markdown.softbreak-normalized",
                        "location": DiagnosticLocation(
                            kind="text",
                            line_start=start + 1,
                            line_end=max(start + 1, end),
                        ),
                        "message": "A Markdown soft line break was normalized to one space.",
                        "severity": "info",
                        "disposition": "normalized",
                        "loss_kind": "presentation",
                        "details": {"token_path": list(token_path)},
                    }
                )
            if token.type == "text" and token.content:
                start, end = location_map or [0, 1]
                occupied: list[tuple[int, int]] = []
                for match in _PANDOC_EMPTY_ANCHOR_RE.finditer(token.content):
                    occupied.append(match.span())
                    specs.append(
                        {
                            "code": "markdown.pandoc-anchor-omitted",
                            "location": DiagnosticLocation(
                                kind="text",
                                line_start=start + 1,
                                line_end=max(start + 1, end),
                            ),
                            "message": (
                                "A Pandoc empty anchor has no canonical IR node and was omitted."
                            ),
                            "severity": "warning",
                            "disposition": "omitted",
                            "loss_kind": "metadata",
                            "details": {
                                "token_path": list(token_path),
                                "content_sha256": sha256_digest(match.group(0)),
                                "text_start": match.start(),
                                "text_end": match.end(),
                            },
                        }
                    )
                trailing_matches = (
                    list(_PANDOC_TRAILING_ATTR_RE.finditer(token.content))
                    if (
                        heading_inline
                        and inline_depth == 0
                        and not _later_inline_content(items, index)
                    )
                    else []
                )
                for match in trailing_matches:
                    if any(
                        left <= match.start() and match.end() <= right
                        for left, right in occupied
                    ):
                        continue
                    specs.append(
                        {
                            "code": "markdown.pandoc-attributes-omitted",
                            "location": DiagnosticLocation(
                                kind="text",
                                line_start=start + 1,
                                line_end=max(start + 1, end),
                            ),
                            "message": (
                                "Pandoc attributes have no canonical IR field and were omitted."
                            ),
                            "severity": "warning",
                            "disposition": "omitted",
                            "loss_kind": "metadata",
                            "details": {
                                "token_path": list(token_path),
                                "content_sha256": sha256_digest(match.group(0)),
                                "text_start": match.start(),
                                "text_end": match.end(),
                            },
                        }
                    )
            if token.children and token.type != "image":
                walk(
                    token.children,
                    location_map,
                    token_path,
                    heading_inline=heading_inline or child_is_heading,
                )
            if token.nesting > 0:
                inline_depth += 1

    walk(tokens, None, ())
    return specs


def _later_inline_content(tokens: list[Token], index: int) -> bool:
    """Return whether a later sibling contributes canonical inline content."""
    content_types = {
        "code_inline",
        "footnote_ref",
        "hardbreak",
        "image",
        "math_inline",
        "softbreak",
        "text",
    }
    return any(
        token.type in content_types and (token.type != "text" or bool(token.content))
        for token in tokens[index + 1 :]
    )


def _source_definition_diagnostic_specs(
    source: str,
    tokens: list[Token],
    environment: dict,
) -> list[dict]:
    """Inventory source definitions that Markdown tokenization can discard.

    markdown-it resolves definitions before emitting its token stream. A raw
    pre-pass is therefore required to catch duplicates and unused link
    definitions with truthful source-line locations.
    """
    specs: list[dict] = []
    seen_footnotes: dict[str, int] = {}
    footnote_definitions: dict[str, tuple[int, int, int]] = {}
    duplicate_footnotes: set[str] = set()
    duplicate_specs: list[tuple[str, dict]] = []
    literal_lines = {
        line_index
        for token in tokens
        if token.type in {"code_block", "fence", "html_block"} and token.map
        for line_index in range(token.map[0], token.map[1])
    }

    for line_number, line in enumerate(source.splitlines(keepends=True), start=1):
        content = line.rstrip("\r\n")
        if line_number - 1 in literal_lines:
            continue
        offset = 0
        footnote = _FOOTNOTE_DEFINITION_RE.match(content)
        if footnote is None:
            offset = _container_marker_offset(content)
            if offset:
                footnote = _FOOTNOTE_DEFINITION_RE.match(content[offset:])
        if footnote:
            raw_label = footnote.group(1)
            # The footnote plugin treats labels as case-sensitive identities,
            # unlike CommonMark link-reference labels.
            label = raw_label
            column_start = offset + footnote.start() + 1
            column_end = offset + footnote.end() + 1
            first_line = seen_footnotes.get(label)
            if first_line is not None:
                duplicate_footnotes.add(label)
                duplicate_specs.append(
                    (
                        label,
                        _definition_spec(
                            code="markdown.duplicate-footnote-definition",
                            line_number=line_number,
                            column_start=column_start,
                            column_end=column_end,
                            label=raw_label,
                            first_line=first_line,
                            loss_kind="text",
                            message=(
                                "A duplicate Markdown footnote definition would "
                                "replace or discard note text, so canonical "
                                "recovery was refused."
                            ),
                        ),
                    )
                )
            else:
                seen_footnotes[label] = line_number
                footnote_definitions[label] = (line_number, column_start, column_end)

    footnote_refs = environment.get("footnotes", {}).get("refs", {})
    # A duplicate sighting is only a definition loss when the plugin itself
    # resolved the label as a definition; raw sightings the tokenizer treated
    # as ordinary text must not refuse recovery.
    for label, spec in duplicate_specs:
        if f":{label}" in footnote_refs:
            specs.append(spec)
    for label, (line_number, column_start, column_end) in footnote_definitions.items():
        if label in duplicate_footnotes or footnote_refs.get(f":{label}") != -1:
            continue
        specs.append(
            {
                "code": "markdown.unused-footnote-definition-refused",
                "severity": "error",
                "disposition": "refused",
                "loss_kind": "text",
                "location": DiagnosticLocation(
                    kind="text",
                    line_start=line_number,
                    line_end=line_number,
                    column_start=column_start,
                    column_end=column_end,
                ),
                "message": (
                    "An unreferenced Markdown footnote body is absent from the "
                    "parser token stream, so canonical recovery was refused."
                ),
                "details": {"label": label},
            }
        )

    references = environment.get("references", {})
    duplicate_references: set[str] = set()
    for duplicate in environment.get("duplicate_refs", []):
        label = str(duplicate.get("label", ""))
        line_map = duplicate.get("map") or [0, 1]
        first_map = references.get(label, {}).get("map") or [0, 1]
        duplicate_references.add(label)
        specs.append(
            {
                "code": "markdown.duplicate-reference-definition",
                "severity": "error",
                "disposition": "refused",
                "loss_kind": "metadata",
                "location": DiagnosticLocation(
                    kind="text",
                    line_start=line_map[0] + 1,
                    line_end=max(line_map[0] + 1, line_map[1]),
                ),
                "message": (
                    "A duplicate Markdown reference definition has an ambiguous "
                    "destination, so canonical recovery was refused."
                ),
                "details": {
                    "label": label,
                    "first_definition_line": first_map[0] + 1,
                },
            }
        )

    used_references = _used_reference_labels(tokens)
    for label, reference in references.items():
        if label in used_references or label in duplicate_references:
            continue
        line_map = reference.get("map") or [0, 1]
        specs.append(
            {
                "code": "markdown.unused-reference-definition-omitted",
                "severity": "warning",
                "disposition": "omitted",
                "loss_kind": "metadata",
                "location": DiagnosticLocation(
                    kind="text",
                    line_start=line_map[0] + 1,
                    line_end=max(line_map[0] + 1, line_map[1]),
                ),
                "message": (
                    "An unused Markdown reference definition has no canonical IR "
                    "node and was omitted."
                ),
                "details": {"label": label},
            }
        )
    return specs


def _container_marker_offset(content: str) -> int:
    """Return the offset after leading blockquote and list-item markers."""
    offset = 0
    while True:
        marker = _CONTAINER_MARKER_RE.match(content, offset)
        if marker is None:
            return offset
        offset = marker.end()


def _definition_spec(
    *,
    code: str,
    line_number: int,
    column_start: int,
    column_end: int,
    label: str,
    first_line: int,
    loss_kind: str,
    message: str,
) -> dict:
    return {
        "code": code,
        "severity": "error",
        "disposition": "refused",
        "loss_kind": loss_kind,
        "location": DiagnosticLocation(
            kind="text",
            line_start=line_number,
            line_end=line_number,
            column_start=column_start,
            column_end=column_end,
        ),
        "message": message,
        "details": {"label": label, "first_definition_line": first_line},
    }


def _used_reference_labels(tokens: list[Token]) -> set[str]:
    used: set[str] = set()

    def walk(items: list[Token]) -> None:
        for token in items:
            if token.type in {"image", "link_open"} and (token.meta or {}).get("label"):
                used.add(str(token.meta["label"]))
            if token.children:
                walk(token.children)

    walk(tokens)
    return used


def parse_md(source: str) -> Document:
    """Library entry: parse a markdown string into a Document.

    Blocks carry spans into a canonical stream constructed the same way
    as ``parse_md_file`` (no SourceRef is registered)."""
    doc, _stream, _diagnostics = _parse_with_stream(source)
    return doc


def parse_md_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """File entry: read, parse, register the source, return ParseResult."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    doc, stream, diagnostic_specs = _parse_with_stream(captured.decode("utf-8"))
    source = register_source(
        p,
        "markdown",
        stream,
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    doc.source_id = source.id
    diagnostics = [
        make_diagnostic(
            source_id=source.id,
            parser_name=source.parser,
            parser_version=source.parser_version,
            **spec,
        )
        for spec in diagnostic_specs
    ]
    return ParseResult(
        document=doc,
        source=source,
        diagnostics=make_parse_report(
            source_id=source.id,
            parser_name=source.parser,
            parser_version=source.parser_version,
            diagnostics=diagnostics,
        ),
    )


# ---------------------------------------------------------------------------
# Empty-node cleanup (post-parse)
# ---------------------------------------------------------------------------

# Wrapper inline nodes that are meaningless when they have no children.
_EMPTY_WRAPPERS = (Bold, Italic, Strikethrough, Superscript, Subscript)


def _clean_inlines(inlines: list) -> list:
    """Recursively drop empty emphasis wrappers from an inline list.

    - ``Bold`` / ``Italic`` / ``Strikethrough`` / ``Superscript`` /
      ``Subscript`` with no remaining children are removed (Pandoc leaves
      empty ``****`` emphasis behind when it splits an anchor off a
      heading).
    Wrappers carrying children are cleaned in place and kept.
    """
    out: list = []
    for node in inlines:
        if isinstance(node, Text):
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
            inlines = _inline_children(
                tokens[i + 1 : j],
                allow_trailing_pandoc_attributes=True,
            )
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
            # markdown-it includes one block-terminating newline. Remove only
            # that syntax terminator and preserve any intentional trailing
            # blank lines inside the code block.
            text = tok.content[:-1] if tok.content.endswith("\n") else tok.content
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
                en_id = raw_id[len(ENDNOTE_PREFIX) :]
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


def _inline_children(
    block_tokens: list[Token],
    *,
    allow_trailing_pandoc_attributes: bool = False,
) -> list[Inline]:
    """Given the tokens *inside* a heading/paragraph/cell (which should be
    exactly one `inline` token), return the parsed inline children."""
    for tok in block_tokens:
        if tok.type == "inline":
            return _walk_inline(
                tok.children or [],
                allow_trailing_pandoc_attributes=allow_trailing_pandoc_attributes,
            )
    return []


def _strip_pandoc_cruft(
    value: str,
    *,
    allow_trailing_attributes: bool = False,
) -> str:
    """Remove Pandoc attribute/anchor cruft from a prose Text value.

    Empty anchors are a strong syntactic signal and may occur in prose. Bare
    attribute blocks are removed only at the end of a heading. For each
    removal, at most one newly-adjacent whitespace character is removed;
    unrelated spacing elsewhere in the value is preserved exactly.
    """
    if "{" not in value:
        return value

    for match in reversed(list(_PANDOC_EMPTY_ANCHOR_RE.finditer(value))):
        left = value[: match.start()]
        right = value[match.end() :]
        if left and right and left[-1] in " \t" and right[0] in " \t":
            right = right[1:]
        value = left + right

    if allow_trailing_attributes:
        match = _PANDOC_TRAILING_ATTR_RE.search(value)
        if match is not None:
            start = match.start()
            if start > 0 and value[start - 1] in " \t":
                start -= 1
            value = value[:start] + value[match.end() :]
            if not value.strip():
                return ""
    return value


def _split_sup_sub(
    text_value: str,
    *,
    allow_trailing_pandoc_attributes: bool = False,
) -> list[Inline]:
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
    text_value = _strip_pandoc_cruft(
        text_value,
        allow_trailing_attributes=allow_trailing_pandoc_attributes,
    )
    # First pass: extract citation matches by scanning the whole string
    # for the regex. Citations are unambiguous (opening ``[@``), so we
    # can split around them before doing the character-by-character
    # sup/sub pass on the interstitial text.
    citation_segments: list[
        tuple[str, tuple | None]
    ] = []  # (text, None) or ("", (key, locator))
    last = 0
    for m in _CITATION_RE.finditer(text_value):
        if m.start() > last:
            citation_segments.append((text_value[last : m.start()], None))
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
                result.append(
                    Superscript(children=[Text(value=text_value[i + 1 : end])])
                )
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


def _walk_inline(
    children: list[Token],
    *,
    allow_trailing_pandoc_attributes: bool = False,
) -> list[Inline]:
    out: list[Inline] = []
    stack: list[list[Inline]] = [out]

    def push(node: Inline) -> None:
        stack[-1].append(node)

    def push_text(value: str, *, allow_trailing_attributes: bool = False) -> None:
        """Push text, but first split on Pandoc-style ``^sup^`` / ``~sub~``
        patterns. Strikethrough ``~~...~~`` is already consumed upstream by
        markdown-it-py's GFM plugin, so any ``~`` here is literal or a
        subscript marker."""
        for node in _split_sup_sub(
            value,
            allow_trailing_pandoc_attributes=allow_trailing_attributes,
        ):
            push(node)

    i = 0
    while i < len(children):
        tok = children[i]
        t = tok.type

        if t == "text":
            if tok.content:
                push_text(
                    tok.content,
                    allow_trailing_attributes=(
                        allow_trailing_pandoc_attributes
                        and len(stack) == 1
                        and not _later_inline_content(children, i)
                    ),
                )
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
            alt = tok.content or ""
            src = _attr(tok, "src") or ""
            title = _attr(tok, "title")
            push(Image(alt=alt, src=src, title=title))
        elif t == "footnote_ref":
            label = (tok.meta or {}).get("label")
            raw_id = label if label is not None else str((tok.meta or {}).get("id", ""))
            if raw_id.startswith(ENDNOTE_PREFIX):
                en_id = raw_id[len(ENDNOTE_PREFIX) :]
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
