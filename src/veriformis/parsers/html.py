"""Deterministic HTML recovery into canonical IR.

Uses ``lxml`` only (already a core dependency). Scripts, styles, and non-body
chrome are omitted with explicit diagnostics. No network fetch is performed.
"""

from __future__ import annotations

import codecs
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

# 1.1.0: the capture is decoded by Veriformis (UTF-8 first, then a declared
# charset) before lxml sees it. libxml2 no longer guesses Latin-1 for undeclared
# UTF-8; an undecodable capture refuses instead of producing mojibake.
PARSER_VERSION = "1.1.0"
_PARSER = "html"
_CHARSET_SNIFF_BYTES = 4096
_META_CHARSET = re.compile(rb"<meta[^>]*?charset\s*=\s*[\"']?\s*([A-Za-z0-9_.:-]+)", re.I)
_XML_ENCODING = re.compile(rb"<\?xml[^>]*?encoding\s*=\s*[\"']([A-Za-z0-9_.:-]+)[\"']", re.I)
_UTF8_ALIASES = frozenset({"utf-8", "utf8", "utf_8", "u8", "cp65001"})
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
_PARAGRAPH_TAGS = frozenset({"p", "li", "blockquote", "pre", "td", "th"})
_WS = re.compile(r"[ \t\f\v]+")


class _HtmlDecoding:
    """Outcome of decoding one HTML capture before markup recovery."""

    __slots__ = ("text", "charset", "diagnostics", "refusal")

    def __init__(
        self,
        *,
        text: str | None,
        charset: str | None,
        diagnostics: list[dict],
        refusal: dict | None,
    ) -> None:
        self.text = text
        self.charset = charset
        self.diagnostics = diagnostics
        self.refusal = refusal


def _declared_charset(captured: bytes) -> str | None:
    head = captured[:_CHARSET_SNIFF_BYTES]
    for pattern in (_META_CHARSET, _XML_ENCODING):
        match = pattern.search(head)
        if match is not None:
            return match.group(1).decode("ascii", errors="replace").strip().lower()
    return None


def _decode_html(captured: bytes) -> _HtmlDecoding:
    """Decode the capture: BOM, then strict UTF-8, then a declared charset.

    libxml2 assumes ISO-8859-1 for undeclared bytes, which turns valid UTF-8
    into mojibake with no trace. Veriformis therefore decodes first and hands
    lxml an explicit UTF-8 encoding. Anything undecodable refuses.
    """
    diagnostics: list[dict] = []
    if captured.startswith(codecs.BOM_UTF8):
        body = captured[len(codecs.BOM_UTF8) :]
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            return _HtmlDecoding(
                text=None,
                charset="utf-8",
                diagnostics=diagnostics,
                refusal={
                    "code": "html.charset-invalid",
                    "message": f"HTML declared UTF-8 by byte-order mark but is not valid UTF-8: {exc}",
                    "details": {"charset": "utf-8", "declared_by": "bom"},
                },
            )
        diagnostics.append(
            {
                "code": "html.bom-removed",
                "severity": "info",
                "disposition": "normalized",
                "loss_kind": "metadata",
                "message": "A UTF-8 byte-order mark preceded the markup and was not carried into the canonical stream.",
                "details": {"charset": "utf-8", "declared_by": "bom"},
            }
        )
        return _HtmlDecoding(text=text, charset="utf-8", diagnostics=diagnostics, refusal=None)
    for bom, charset in (
        (codecs.BOM_UTF32_LE, "utf-32-le"),
        (codecs.BOM_UTF32_BE, "utf-32-be"),
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ):
        if captured.startswith(bom):
            try:
                text = captured[len(bom) :].decode(charset)
            except UnicodeDecodeError as exc:
                return _HtmlDecoding(
                    text=None,
                    charset=charset,
                    diagnostics=diagnostics,
                    refusal={
                        "code": "html.charset-invalid",
                        "message": f"HTML declared {charset} by byte-order mark but could not be decoded: {exc}",
                        "details": {"charset": charset, "declared_by": "bom"},
                    },
                )
            diagnostics.append(
                {
                    "code": "html.charset-declared",
                    "severity": "info",
                    "disposition": "normalized",
                    "loss_kind": "metadata",
                    "message": f"HTML was decoded from {charset} declared by its byte-order mark.",
                    "details": {"charset": charset, "declared_by": "bom"},
                }
            )
            return _HtmlDecoding(text=text, charset=charset, diagnostics=diagnostics, refusal=None)
    try:
        return _HtmlDecoding(
            text=captured.decode("utf-8"),
            charset="utf-8",
            diagnostics=diagnostics,
            refusal=None,
        )
    except UnicodeDecodeError as utf8_error:
        utf8_reason = str(utf8_error)
    declared = _declared_charset(captured)
    if declared is None:
        return _HtmlDecoding(
            text=None,
            charset=None,
            diagnostics=diagnostics,
            refusal={
                "code": "html.charset-unknown",
                "message": (
                    "HTML is not valid UTF-8 and declares no charset; refusing rather than "
                    f"guessing an encoding: {utf8_reason}"
                ),
                "details": {"utf8_error": utf8_reason},
            },
        )
    if declared in _UTF8_ALIASES:
        return _HtmlDecoding(
            text=None,
            charset="utf-8",
            diagnostics=diagnostics,
            refusal={
                "code": "html.charset-invalid",
                "message": f"HTML declares UTF-8 but is not valid UTF-8: {utf8_reason}",
                "details": {"charset": declared, "declared_by": "meta", "utf8_error": utf8_reason},
            },
        )
    try:
        codec = codecs.lookup(declared)
    except LookupError:
        return _HtmlDecoding(
            text=None,
            charset=declared,
            diagnostics=diagnostics,
            refusal={
                "code": "html.charset-unknown",
                "message": f"HTML declares an unknown charset {declared!r}; refusing rather than guessing.",
                "details": {"charset": declared, "declared_by": "meta"},
            },
        )
    try:
        text = captured.decode(codec.name)
    except (UnicodeDecodeError, ValueError) as exc:
        return _HtmlDecoding(
            text=None,
            charset=declared,
            diagnostics=diagnostics,
            refusal={
                "code": "html.charset-invalid",
                "message": f"HTML declares charset {declared!r} but could not be decoded with it: {exc}",
                "details": {"charset": declared, "declared_by": "meta"},
            },
        )
    diagnostics.append(
        {
            "code": "html.charset-declared",
            "severity": "info",
            "disposition": "normalized",
            "loss_kind": "metadata",
            "message": f"HTML was decoded from declared charset {declared!r}; the canonical stream is exact Unicode.",
            "details": {"charset": declared, "declared_by": "meta", "codec": codec.name},
        }
    )
    return _HtmlDecoding(text=text, charset=declared, diagnostics=diagnostics, refusal=None)


def _refused_result(
    p: Path,
    *,
    captured: bytes,
    logical_path: str,
    code: str,
    message: str,
    details: dict | None,
) -> ParseResult:
    source = register_source(
        p,
        _PARSER,
        "",
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
                code=code,
                severity="error",
                disposition="refused",
                loss_kind="text",
                location=DiagnosticLocation(kind="source"),
                message=message,
                details=details,
            ),
        ),
    )
    return ParseResult(
        document=Document(children=[], source_id=source.id),
        source=source,
        diagnostics=report,
    )


def parse_html_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    """Parse one HTML capture into IR.

    The capture is decoded as UTF-8, or from a byte-order mark or declared
    charset when it is not valid UTF-8. A capture that decodes no way refuses
    with ``html.charset-unknown`` / ``html.charset-invalid``; libxml2 never
    guesses an encoding for Veriformis.
    """
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    decoding = _decode_html(captured)
    if decoding.refusal is not None:
        return _refused_result(
            p,
            captured=captured,
            logical_path=logical_path,
            code=decoding.refusal["code"],
            message=decoding.refusal["message"],
            details=decoding.refusal.get("details"),
        )
    assert decoding.text is not None
    diagnostics: list = list(decoding.diagnostics)
    try:
        document_tree = lxml_html.document_fromstring(
            decoding.text.encode("utf-8"),
            parser=lxml_html.HTMLParser(
                encoding="utf-8",
                remove_blank_text=False,
                recover=True,
                no_network=True,
            ),
        )
    except (etree.ParserError, etree.XMLSyntaxError, ValueError, TypeError) as exc:
        # Fall back to empty body with refusal when markup is unusable.
        source = register_source(
            p,
            _PARSER,
            "",
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

    # Walk the scope in document order. Heading and paragraph tags are
    # captured whole via itertext without descending; every other text node
    # (text directly in <div>, <span>, <body>, and tail text following a
    # captured element) joins a pending loose-text run that is flushed as
    # paragraph blocks at block-tag boundaries. Nothing visible may leave
    # the canonical stream silently.
    loose_parts: list[str] = []
    captured_structured = False
    recovered_loose = False

    def flush_loose() -> None:
        nonlocal recovered_loose
        raw = "".join(loose_parts)
        loose_parts.clear()
        if not raw.strip():
            return
        for chunk in re.split(r"\n\s*\n", raw):
            if chunk.strip():
                recovered_loose = True
                append_paragraph(chunk)

    def enter(element) -> bool:
        """Capture one element; return whether to walk its children."""
        nonlocal captured_structured
        name = element.tag.lower()
        if name in _HEADING_LEVEL:
            flush_loose()
            append_paragraph(
                "".join(element.itertext()),
                level=_HEADING_LEVEL[name],
            )
            captured_structured = True
            return False
        if name in _PARAGRAPH_TAGS:
            flush_loose()
            append_paragraph("".join(element.itertext()))
            captured_structured = True
            return False
        if name in _BLOCK_TAGS:
            flush_loose()
        if element.text:
            loose_parts.append(element.text)
        return True

    stack: list = []
    if enter(scope):
        stack.append((scope, iter(scope)))
    while stack:
        element, children = stack[-1]
        child = next(children, None)
        if child is None:
            stack.pop()
            if element is not scope:
                if element.tag.lower() in _BLOCK_TAGS:
                    flush_loose()
                if element.tail:
                    loose_parts.append(element.tail)
            continue
        if not isinstance(child.tag, str):
            if child.tail:
                loose_parts.append(child.tail)
            continue
        if enter(child):
            stack.append((child, iter(child)))
        elif child.tail:
            loose_parts.append(child.tail)
    flush_loose()

    if recovered_loose and not captured_structured:
        diagnostics.append(
            {
                "code": "html.flat-text-fallback",
                "severity": "warning",
                "disposition": "normalized",
                "loss_kind": "structure",
                "message": "HTML structure was weak; text was recovered as flat paragraphs.",
            }
        )
    elif recovered_loose:
        diagnostics.append(
            {
                "code": "html.loose-text-recovered",
                "severity": "info",
                "disposition": "normalized",
                "loss_kind": "structure",
                "message": (
                    "Visible text outside recognized block tags was recovered "
                    "as paragraph blocks in document order."
                ),
            }
        )

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
