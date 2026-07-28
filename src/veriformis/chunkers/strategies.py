# src/veriformis/chunkers/strategies.py
"""Chunking strategies. Coverage invariant: no source text is silently orphaned."""
from __future__ import annotations

import re
from collections.abc import Iterable

from veriformis.chunkers.base import Chunk, Span, flatten, heading_paths, make_chunk
from veriformis.ir import Block, Heading, block_text

_ABBREVS = ("mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "vs.", "etc.", "e.g.", "i.e.",
            "p.m.", "a.m.", "u.s.", "u.k.", "no.", "fig.", "approx.", "dept.", "est.")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def _norm(transformed: Iterable[int]) -> set[int]:
    return set(transformed)


def _path_map(blocks: list[Block]) -> dict[int, list[str]]:
    """heading_path per block_index (robust when `blocks` is a sub-list whose
    block_index values are not 0-based positions)."""
    paths = heading_paths(blocks)
    return {block.block_index: paths[i] for i, block in enumerate(blocks)}


def chunk_paragraph(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]:
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    group: list[Block] = []

    def flush() -> None:
        nonlocal seq
        seq += 1
        chunks.append(make_chunk(
            seq, group, flatten(group), source_id=source_id,
            heading_path=paths.get(group[0].block_index, []),
            span=Span(group[0].span.start, group[-1].span.end)
            if group[0].span and group[-1].span else None,
            transformed_blocks=tb,
        ))

    for block in blocks:
        if group and len(flatten(group + [block])) > max_size:
            flush()
            group = [block]
        else:
            group = group + [block]
    if group:
        flush()
    return chunks


def _stream_chunks(blocks, size, overlap, *, source_id, transformed):
    """Shared engine for fixed/sliding: `fixed` is boundary splitting with optional
    overlap; `sliding` is the same engine with overlap as a first-class parameter.
    A document shorter than `size` always yields exactly one chunk."""
    tb, stream, chunks, seq = _norm(transformed), flatten(blocks), [], 0
    if len(stream) <= size:
        if stream:
            chunks.append(make_chunk(1, blocks, stream, source_id=source_id,
                                     heading_path=_path_map(blocks).get(blocks[0].block_index, []) if blocks else [],
                                     span=Span(0, len(stream)) if blocks and blocks[0].span else None,
                                     transformed_blocks=tb))
        return chunks
    step = max(1, size - overlap)
    pos = 0
    while pos < len(stream):
        end = min(pos + size, len(stream))
        seq += 1
        chunks.append(make_chunk(seq, blocks, stream[pos:end], source_id=source_id,
                                 heading_path=[], span=Span(pos, end), transformed_blocks=tb))
        if end == len(stream):
            break
        pos += step
    return chunks


def chunk_fixed(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]:
    return _stream_chunks(blocks, size, overlap, source_id=source_id, transformed=transformed)


def chunk_sliding(blocks, *, size=1000, overlap=100, source_id="", transformed=()) -> list[Chunk]:
    return _stream_chunks(blocks, size, overlap, source_id=source_id, transformed=transformed)


def _sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT.split(text)
    merged: list[str] = []
    for part in parts:
        if merged and any(merged[-1].lower().endswith(a) for a in _ABBREVS):
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    return merged


def chunk_sentence(blocks, *, max_size=1000, source_id="", transformed=()) -> list[Chunk]:
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    buf, buf_blocks = "", []
    for block in blocks:
        for sent in _sentences(block_text(block)):
            candidate = (buf + " " + sent).strip() if buf else sent
            if buf and len(candidate) > max_size:
                seq += 1
                chunks.append(make_chunk(seq, buf_blocks, buf, source_id=source_id,
                                         heading_path=paths.get(buf_blocks[0].block_index, []) if buf_blocks else [],
                                         span=None, transformed_blocks=tb))
                buf, buf_blocks = sent, [block]
            else:
                buf, buf_blocks = candidate, (buf_blocks or [block])
    if buf:
        seq += 1
        chunks.append(make_chunk(seq, buf_blocks, buf, source_id=source_id,
                                 heading_path=paths.get(buf_blocks[0].block_index, []) if buf_blocks else [],
                                 span=None, transformed_blocks=tb))
    return chunks


def chunk_structure(blocks, *, max_size=2000, source_id="", transformed=()) -> list[Chunk]:
    global_paths = _path_map(blocks)
    sections: list[list[Block]] = [[]]
    for block in blocks:
        if isinstance(block, Heading) and sections[-1]:
            sections.append([])
        sections[-1].append(block)
    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(chunk_paragraph(section, max_size=max_size, source_id=source_id, transformed=transformed))
    for i, chunk in enumerate(chunks, 1):
        chunk.id = f"chk-{i:04d}"
        # heading_path must reflect the document-wide context of the chunk's first
        # block, not just its section — re-attach from the global map
        chunk.heading_path = global_paths.get(chunk.block_index, chunk.heading_path)
    return chunks
