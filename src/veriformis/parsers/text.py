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
PARSER_VERSION = "1.1.0"


def parse_text(
    path: str | Path,
    *,
    logical_path: str,
    language: str | None = None,
    raw_bytes: bytes | None = None,
) -> ParseResult:
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    text = captured.decode("utf-8")
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
