"""Deterministic HTML recovery into canonical IR.

Uses ``lxml`` only (already a core dependency). Scripts, styles, and non-body
chrome are omitted with explicit diagnostics. No network fetch is performed.
"""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree, html as lxml_html

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.ir import Document, Heading, Paragraph, Span, Text
from veriformis.sources import ParseResult, register_source

PARSER_VERSION = "1.0.0"
_PARSER = "html"
_STRIP_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "iframe",
        "object",
        "embed",
        "link",
        "meta",
    }
)
_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "main",
        "li",
        "td",
        "th",
        "blockquote",
        "pre",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
        "hr",
        "tr",
    }
)
_HEADING_LEVEL = {
    "h1": 1,
    "h2": 2,
    "h3": 3,
    "h4": 4,
    "h5": 5,
    "h6": 6,
}
_WS = re.compile(r"[ \t\f\v]+")
_BLANK = re.compile(r"\n{3,}")


def parse_html_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """Parse one UTF-8 or charset-declared HTML capture into IR."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    diagnostics: list = []
    # provisional source id placeholder after stream is known
    try:
        document_tree = lxml_html.document_fromstring(
            captured,
            parser=lxml_html.HTMLParser(
                encoding=None,
                remove_blank_text=False,
                recover=True,
                no_network=True,
            ),
        )
    except (etree.ParserError, etree.XMLSyntaxError, ValueError, TypeError) as exc:
        # Fall back to empty body with refusal when markup is unusable.
        stream = ""
        source = register_source(
            p,
            _PARSER,
            stream,
            logical_path=logical_path,
            parser_version=PARSER_VERSION,
            raw_bytes=captured,
        )
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=(
                make_diagnostic(
                    source_id=source.id,
                    parser_name=_PARSER,
                    parser_version=PARSER_VERSION,
                    code="html.unparseable",
                    severity="error",
                    disposition="refused",
                    loss_kind="structure",
                    location=DiagnosticLocation(
                        kind="source",
                    ),
                    message=f"HTML markup could not be recovered: {exc}",
                    details={"reason": "unparseable"},
                ),
            ),
        )
        return ParseResult(
            document=Document(children=[], source_id=source.id),
            source=source,
            diagnostics=report,
        )

    omitted_tags: set[str] = set()
    for tag in list(document_tree.iter()):
        if not isinstance(tag.tag, str):
            continue
        name = tag.tag.lower()
        if name in _STRIP_TAGS:
            omitted_tags.add(name)
            parent = tag.getparent()
            if parent is not None:
                parent.remove(tag)

    body = document_tree.find("body")
    root = body if body is not None else document_tree
    if body is None:
        diagnostics.append(
            {
                "code": "html.body-missing",
                "severity": "warning",
                "disposition": "normalized",
                "loss_kind": "structure",
                "message": "HTML had no body element; the document root was used.",
            }
        )

    blocks: list = []
    parts: list[str] = []
    pos = 0

    def append_paragraph(text: str, *, level: int | None = None) -> None:
        nonlocal pos
        cleaned = _WS.sub(" ", text).strip()
        if not cleaned:
            return
        if parts:
            pos += 2
        start = pos
        end = start + len(cleaned)
        if level is None:
            blocks.append(
                Paragraph(
                    children=[Text(cleaned)],
                    span=Span(start, end),
                    block_index=len(blocks),
                )
            )
        else:
            blocks.append(
                Heading(
                    level=level,
                    children=[Text(cleaned)],
                    span=Span(start, end),
                    block_index=len(blocks),
                )
            )
        parts.append(cleaned)
        pos = end

    # Prefer semantic containers when present.
    scope = root
    for candidate in ("main", "article"):
        found = root.find(f".//{candidate}")
        if found is not None:
            scope = found
            diagnostics.append(
                {
                    "code": "html.main-content-selected",
                    "severity": "info",
                    "disposition": "normalized",
                    "loss_kind": "presentation",
                    "message": f"Main content was taken from the first <{candidate}> element.",
                    "details": {"container": candidate},
                }
            )
            break

    for element in scope.iter():
        if not isinstance(element.tag, str):
            continue
        name = element.tag.lower()
        if name in _HEADING_LEVEL:
            append_paragraph(
                "".join(element.itertext()),
                level=_HEADING_LEVEL[name],
            )
            # Prevent nested text from double-counting: clear children text by
            # not walking into them — iter() will still visit children, so mark
            # processed via clearing text of descendants after capture.
            for child in element.iter():
                if child is element:
                    continue
                if isinstance(child.tag, str):
                    child.text = None
                    child.tail = None
            element.text = None
            element.tail = None
            continue
        if name in {"p", "li", "blockquote", "pre", "td", "th"}:
            append_paragraph("".join(element.itertext()))
            for child in element.iter():
                if child is element:
                    continue
                if isinstance(child.tag, str):
                    child.text = None
                    child.tail = None
            element.text = None
            element.tail = None

    # Fallback: residual visible text not captured as block tags.
    residual = _BLANK.sub("\n\n", _WS.sub(" ", " ".join(scope.itertext()))).strip()
    if not blocks and residual:
        for chunk in re.split(r"\n\s*\n", residual):
            append_paragraph(chunk)
        diagnostics.append(
            {
                "code": "html.flat-text-fallback",
                "severity": "warning",
                "disposition": "normalized",
                "loss_kind": "structure",
                "message": "HTML structure was weak; text was recovered as flat paragraphs.",
            }
        )
    elif residual and not parts:
        append_paragraph(residual)

    stream = "\n\n".join(parts)
    source = register_source(
        p,
        _PARSER,
        stream,
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    line_end = max(1, captured.count(b"\n") + 1)
    built = []
    if omitted_tags:
        built.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="html.non-content-tags-omitted",
                severity="info",
                disposition="omitted",
                loss_kind="presentation",
                location=DiagnosticLocation(
                    kind="text",
                    line_start=1,
                    line_end=line_end,
                    raw_byte_start=0,
                    raw_byte_end=len(captured),
                ),
                message=(
                    "Non-content HTML tags were omitted from the canonical stream: "
                    + ", ".join(sorted(omitted_tags))
                ),
                details={"tags": sorted(omitted_tags)},
            )
        )
    for item in diagnostics:
        built.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code=item["code"],
                severity=item["severity"],
                disposition=item["disposition"],
                loss_kind=item["loss_kind"],
                location=DiagnosticLocation(
                    kind="text",
                    line_start=1,
                    line_end=line_end,
                    raw_byte_start=0,
                    raw_byte_end=len(captured),
                ),
                message=item["message"],
                details=item.get("details"),
            )
        )
    if not stream.strip():
        built.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="html.empty-text",
                severity="error",
                disposition="refused",
                loss_kind="text",
                location=DiagnosticLocation(kind="source"),
                message="HTML yielded no recoverable text content.",
            )
        )
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=tuple(built),
        )
    else:
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=tuple(built),
        )
    return ParseResult(
        document=Document(children=blocks, source_id=source.id),
        source=source,
        diagnostics=report,
    )
