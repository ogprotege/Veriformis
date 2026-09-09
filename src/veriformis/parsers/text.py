"""Plain-text and source-code parser: blank-line paragraph splitting with spans."""

from __future__ import annotations

import re
from pathlib import Path

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.ir import CodeBlock, Document, Paragraph, Span, Text
from veriformis.sources import ParseResult, register_source

_BLANK = re.compile(r"\n\s*\n")
# 1.2.0 (post-20 defect D-13): invalid UTF-8 refuses with a typed diagnostic
# instead of a bare UnicodeDecodeError, and a leading byte-order mark is
# removed and diagnosed rather than carried into the first paragraph.
PARSER_VERSION = "1.2.0"


def _refuse_text(
    p: Path, *, captured: bytes, logical_path: str, code: str, message: str
) -> ParseResult:
    source = register_source(
        p,
        "text",
        "",
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    return ParseResult(
        document=Document(children=[], source_id=source.id),
        source=source,
        diagnostics=make_parse_report(
            source_id=source.id,
            parser_name="text",
            parser_version=PARSER_VERSION,
            diagnostics=(
                make_diagnostic(
                    source_id=source.id,
                    parser_name="text",
                    parser_version=PARSER_VERSION,
                    code=code,
                    severity="error",
                    disposition="refused",
                    loss_kind="text",
                    location=DiagnosticLocation(kind="source"),
                    message=message,
                ),
            ),
        ),
    )


def _bom_diagnostic(source, *, text: str) -> object:
    return make_diagnostic(
        source_id=source.id,
        parser_name=source.parser,
        parser_version=source.parser_version,
        code="text.bom-removed",
        severity="info",
        disposition="normalized",
        loss_kind="metadata",
        location=DiagnosticLocation(
            kind="text",
            line_start=1,
            line_end=1,
            raw_byte_start=0,
            raw_byte_end=3,
        ),
        message="A UTF-8 byte-order mark preceded the text and was not carried into the canonical stream.",
    )


def parse_text(
    path: str | Path,
    *,
    logical_path: str,
    language: str | None = None,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    try:
        text = captured.decode("utf-8")
    except UnicodeDecodeError as exc:
        return _refuse_text(
            p,
            captured=captured,
            logical_path=logical_path,
            code="text.not-utf8",
            message=f"Text source is not valid UTF-8: {exc}",
        )
    bom_removed = text.startswith("\ufeff")
    if bom_removed:
        text = text[1:]
    if language is not None:
        source = register_source(
            p,
            "text",
            text,
            logical_path=logical_path,
            parser_version=PARSER_VERSION,
            raw_bytes=captured,
        )
        doc = Document(
            children=[
                CodeBlock(
                    text=text, language=language, span=Span(0, len(text)), block_index=0
                )
            ],
            source_id=source.id,
        )
        return ParseResult(
            document=doc,
            source=source,
            diagnostics=make_parse_report(
                source_id=source.id,
                parser_name=source.parser,
                parser_version=source.parser_version,
                diagnostics=(
                    (_bom_diagnostic(source, text=text),) if bom_removed else ()
                ),
            ),
        )
    separators = list(_BLANK.finditer(text))
    raw_chunks = _BLANK.split(text)
    blocks, parts, pos = [], [], 0
    boundary_whitespace_trimmed = bool(separators) and (
        separators[0].start() == 0 or separators[-1].end() == len(text)
    )
    for chunk in raw_chunks:
        stripped = chunk.strip()
        if not stripped:
            boundary_whitespace_trimmed = boundary_whitespace_trimmed or bool(chunk)
            continue
        boundary_whitespace_trimmed = boundary_whitespace_trimmed or stripped != chunk
        # span indexes the canonical extracted stream (stripped blocks joined by
        # "\n\n", built below) — NOT the raw file, whose separators may be
        # irregular; fixed/sliding chunk windows would otherwise drift (final
        # whole-branch review finding).
        blocks.append(
            Paragraph(
                children=[Text(stripped)],
                span=Span(pos, pos + len(stripped)),
                block_index=len(blocks),
            )
        )
        parts.append(stripped)
        pos += len(stripped) + 2
    stream = "\n\n".join(parts)
    source = register_source(
        p,
        "text",
        stream,
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    diagnostics = []
    if bom_removed:
        diagnostics.append(_bom_diagnostic(source, text=text))
    separator_normalized = any(match.group(0) != "\n\n" for match in separators)
    if separator_normalized:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=source.parser,
                parser_version=source.parser_version,
                code="text.paragraph-separator-normalized",
                severity="info",
                disposition="normalized",
                loss_kind="presentation",
                location=DiagnosticLocation(
                    kind="text",
                    line_start=1,
                    line_end=max(1, text.count("\n") + 1),
                    raw_byte_start=0,
                    raw_byte_end=len(text.encode("utf-8")),
                ),
                message="Irregular paragraph separators were normalized to two line feeds in the canonical stream.",
            )
        )
    if boundary_whitespace_trimmed:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=source.parser,
                parser_version=source.parser_version,
                code="text.paragraph-boundary-whitespace-trimmed",
                severity="info",
                disposition="normalized",
                loss_kind="presentation",
                location=DiagnosticLocation(
                    kind="text",
                    line_start=1,
                    line_end=max(1, text.count("\n") + 1),
                    raw_byte_start=0,
                    raw_byte_end=len(text.encode("utf-8")),
                ),
                message="Whitespace at a paragraph boundary was trimmed from canonical text.",
            )
        )
    return ParseResult(
        document=Document(children=blocks, source_id=source.id),
        source=source,
        diagnostics=make_parse_report(
            source_id=source.id,
            parser_name=source.parser,
            parser_version=source.parser_version,
            diagnostics=diagnostics,
        ),
    )
