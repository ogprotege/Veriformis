"""Plain-text and source-code parser: blank-line paragraph splitting with spans."""
from __future__ import annotations

import re
from pathlib import Path

from veriformis.ir import CodeBlock, Document, Paragraph, Span, Text
from veriformis.sources import ParseResult, register_source

_BLANK = re.compile(r"\n\s*\n")


def parse_text(path: str | Path, *, language: str | None = None) -> ParseResult:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if language is not None:
        source = register_source(p, "text", text)
        doc = Document(
            children=[CodeBlock(text=text, language=language, span=Span(0, len(text)), block_index=0)],
            source_id=source.id,
        )
        return ParseResult(document=doc, source=source)
    blocks, parts, pos = [], [], 0
    for chunk in _BLANK.split(text):
        stripped = chunk.strip()
        if not stripped:
            continue
        # span indexes the canonical extracted stream (stripped blocks joined by
        # "\n\n", built below) — NOT the raw file, whose separators may be
        # irregular; fixed/sliding chunk windows would otherwise drift (final
        # whole-branch review finding).
        blocks.append(
            Paragraph(children=[Text(stripped)], span=Span(pos, pos + len(stripped)),
                      block_index=len(blocks))
        )
        parts.append(stripped)
        pos += len(stripped) + 2
    stream = "\n\n".join(parts)
    source = register_source(p, "text", stream)
    return ParseResult(document=Document(children=blocks, source_id=source.id), source=source)
