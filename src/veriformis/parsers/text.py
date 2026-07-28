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
    source = register_source(p, "text", text)
    if language is not None:
        doc = Document(
            children=[CodeBlock(text=text, language=language, span=Span(0, len(text)), block_index=0)],
            source_id=source.id,
        )
        return ParseResult(document=doc, source=source)
    blocks = []
    pos = 0
    for chunk in _BLANK.split(text):
        stripped = chunk.strip()
        if not stripped:
            continue
        chunk_start = text.index(chunk, pos)
        start = chunk_start + (len(chunk) - len(chunk.lstrip()))
        pos = chunk_start + len(chunk)
        # span covers the stripped range, so stream[start:end] == block_text(block)
        blocks.append(
            Paragraph(children=[Text(stripped)], span=Span(start, start + len(stripped)),
                      block_index=len(blocks))
        )
    return ParseResult(document=Document(children=blocks, source_id=source.id), source=source)
