# src/veriformis/chunkers/strategies.py
"""Chunking strategies. Coverage invariant: no source text is silently orphaned."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Mapping

from veriformis.chunkers.base import (
    Chunk, evidence_component_for_block, evidence_for_blocks, flatten,
    heading_paths, make_chunk,
)
from veriformis.evidence import (
    DerivationStep, EvidenceComponent, EvidenceError, join_derivation,
    make_evidence, replay_derivations, slice_derivation,
)
from veriformis.ir import Block, Heading, block_text
from veriformis.sources import SourceRef

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


def chunk_paragraph(
    blocks, *, max_size=1000, source_id="", transformed=(),
    source: SourceRef | None = None,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None = None,
    region_id: str = "body",
) -> list[Chunk]:
    if source is not None:
        source_id = source.id
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    group: list[Block] = []

    def flush() -> None:
        nonlocal seq
        if not flatten(group):
            return  # never emit empty chunks (e.g. a lone horizontal rule): the
                    # gate rejects zero-length spans and empty records are noise
        seq += 1
        text = flatten(group)
        context = {
            "strategy": "paragraph",
            "max_size": max_size,
            "sequence": seq,
            "region_id": region_id,
        }
        evidence = evidence_for_blocks(
            source=source,
            blocks=group,
            block_derivations=block_derivations,
            output_text=text,
            context=context,
            region_id=region_id,
        )
        chunks.append(make_chunk(
            seq, group, text, source_id=source_id,
            heading_path=paths.get(group[0].block_index, []),
            transformed_blocks=tb,
            evidence=evidence,
            identity_context=context,
        ))

    for block in blocks:
        if group and block_text(block) and len(flatten(group + [block])) > max_size:
            flush()
            group = [block]
        else:
            group = group + [block]
    if group:
        flush()
    return chunks


def _block_ranges(blocks) -> list[tuple[int, int]]:
    """[start, end) offset of each block's region (text plus its following
    separator) within the flattened stream."""
    ranges, pos = [], 0
    for i, block in enumerate(blocks):
        end = pos + len(block_text(block)) + (0 if i == len(blocks) - 1 else 2)
        ranges.append((pos, end))
        pos = end
    return ranges


def _blocks_intersecting(blocks, ranges, start, end) -> list[Block]:
    return [b for b, (s, e) in zip(blocks, ranges, strict=True) if start < e and end > s]


def _evidence_window(
    blocks: list[Block],
    ranges: list[tuple[int, int]],
    start: int,
    end: int,
) -> tuple[list[Block], tuple[int, int]]:
    """Return the smallest contiguous block stream that proves one window.

    A window may end inside the separator after its last contributing block.
    In that case the following block is required to reproduce the separator,
    even though it is not attributed as chunk content.
    """
    first = next(
        (
            index
            for index, (range_start, range_end) in enumerate(ranges)
            if start < range_end and end > range_start
        ),
        None,
    )
    if first is None:
        raise EvidenceError("chunk window does not intersect a source block")
    group_start = ranges[first][0]
    last = first
    proof = blocks[first : last + 1]
    while group_start + len(flatten(proof)) < end:
        last += 1
        if last >= len(blocks):
            raise EvidenceError("chunk window exceeds its block stream")
        proof = blocks[first : last + 1]
    return proof, (start - group_start, end - group_start)


def _stream_chunks(
    blocks, size, overlap, *, source_id, transformed, source=None,
    block_derivations=None, strategy="fixed", region_id="body",
):
    """Shared engine for fixed/sliding: `fixed` is boundary splitting with optional
    overlap; `sliding` is the same engine with overlap as a first-class parameter.
    A document shorter than `size` always yields exactly one chunk."""
    tb, stream, chunks, seq = _norm(transformed), flatten(blocks), [], 0
    ranges = _block_ranges(blocks)
    if len(stream) <= size:
        if stream:
            context = {
                "strategy": strategy,
                "size": size,
                "overlap": overlap,
                "sequence": 1,
                "region_id": region_id,
            }
            evidence = evidence_for_blocks(
                source=source,
                blocks=blocks,
                block_derivations=block_derivations,
                output_text=stream,
                context=context,
                region_id=region_id,
            )
            chunks.append(make_chunk(1, blocks, stream, source_id=source_id,
                                     heading_path=_path_map(blocks).get(blocks[0].block_index, []) if blocks else [],
                                     transformed_blocks=tb, evidence=evidence,
                                     identity_context=context))
        return chunks
    step = max(1, size - overlap)
    pos = 0
    while pos < len(stream):
        end = min(pos + size, len(stream))
        seq += 1
        contributing = _blocks_intersecting(blocks, ranges, pos, end)
        evidence_blocks, selection = _evidence_window(blocks, ranges, pos, end)
        context = {
            "strategy": strategy,
            "size": size,
            "overlap": overlap,
            "sequence": seq,
            "region_id": region_id,
        }
        evidence = evidence_for_blocks(
            source=source,
            blocks=evidence_blocks,
            block_derivations=block_derivations,
            output_text=stream[pos:end],
            context=context,
            selection=selection,
            region_id=region_id,
        )
        chunks.append(make_chunk(seq, contributing,
                                 stream[pos:end], source_id=source_id,
                                 heading_path=[], transformed_blocks=tb,
                                 evidence=evidence, identity_context=context))
        if end == len(stream):
            break
        pos += step
    return chunks


def chunk_fixed(
    blocks, *, size=1000, overlap=100, source_id="", transformed=(),
    source: SourceRef | None = None,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None = None,
    region_id: str = "body",
) -> list[Chunk]:
    if source is not None:
        source_id = source.id
    return _stream_chunks(
        blocks, size, overlap, source_id=source_id, transformed=transformed,
        source=source, block_derivations=block_derivations, strategy="fixed",
        region_id=region_id,
    )


def chunk_sliding(
    blocks, *, size=1000, overlap=100, source_id="", transformed=(),
    source: SourceRef | None = None,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None = None,
    region_id: str = "body",
) -> list[Chunk]:
    if source is not None:
        source_id = source.id
    return _stream_chunks(
        blocks, size, overlap, source_id=source_id, transformed=transformed,
        source=source, block_derivations=block_derivations, strategy="sliding",
        region_id=region_id,
    )


def _sentences(text: str) -> list[str]:
    return [text[start:end] for start, end in _sentence_spans(text)]


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENT_SPLIT.finditer(text):
        candidate = text[start:match.start()]
        if any(candidate.lower().endswith(abbrev) for abbrev in _ABBREVS):
            continue
        spans.append((start, match.start()))
        start = match.end()
    spans.append((start, len(text)))
    # Exclude leading/trailing whitespace from every span: cleaning can leave
    # edge whitespace inside a block (e.g. the urls rule deleting a trailing
    # token), and buffered chunk text must equal the exact " ".join of its
    # evidence slices by construction.
    trimmed: list[tuple[int, int]] = []
    for begin, end in spans:
        while begin < end and text[begin].isspace():
            begin += 1
        while end > begin and text[end - 1].isspace():
            end -= 1
        if begin < end:
            trimmed.append((begin, end))
    return trimmed


def chunk_sentence(
    blocks, *, max_size=1000, source_id="", transformed=(),
    source: SourceRef | None = None,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None = None,
    region_id: str = "body",
) -> list[Chunk]:
    if source is not None:
        source_id = source.id
    tb, paths, chunks, seq = _norm(transformed), _path_map(blocks), [], 0
    buf, buf_blocks, buf_components = "", [], []

    def emit() -> None:
        nonlocal seq
        if not buf:
            return
        seq += 1
        context = {
            "strategy": "sentence",
            "max_size": max_size,
            "sequence": seq,
            "region_id": region_id,
        }
        evidence = _sentence_evidence(source, buf_components, buf, context)
        chunks.append(make_chunk(
            seq, buf_blocks, buf, source_id=source_id,
            heading_path=paths.get(buf_blocks[0].block_index, []) if buf_blocks else [],
            transformed_blocks=tb, evidence=evidence,
            identity_context=context,
        ))

    for block in blocks:
        text = block_text(block)
        for begin, end in _sentence_spans(text):
            sent = text[begin:end]
            component = _sentence_component(
                source,
                block,
                begin,
                end,
                block_derivations,
                region_id,
            )
            candidate = buf + " " + sent if buf else sent
            if buf and len(candidate) > max_size:
                emit()
                buf, buf_blocks = sent, [block]
                buf_components = [component] if component else []
            else:
                buf = candidate
                if not any(b is block for b in buf_blocks):
                    buf_blocks.append(block)
                if component is not None:
                    buf_components.append(component)
    if buf:
        emit()
    return chunks


def _sentence_component(source, block, begin, end, block_derivations, region_id):
    if source is None:
        return None
    component = evidence_component_for_block(
        source,
        block,
        block_derivations or {},
        region_id=region_id,
    )
    resolved = replay_derivations(
        source.extracted_text[component.source_range.start:component.source_range.end],
        component.derivations,
    )
    select = slice_derivation(
        resolved, begin, end,
        context={
            "strategy": "sentence",
            "block_index": block.block_index,
            "region_id": region_id,
        },
    )
    return EvidenceComponent(
        source_range=component.source_range,
        derivations=component.derivations + (select,),
    )


def _sentence_evidence(source, components, output_text, context):
    if source is None:
        return None
    if not components:
        raise EvidenceError("sentence chunk has no reconstructible source components")
    values = [
        replay_derivations(
            source.extracted_text[item.source_range.start:item.source_range.end],
            item.derivations,
        )
        for item in components
    ]
    join = join_derivation(values, " ", context={**context, "operation": "sentence-join"}) \
        if len(values) > 1 else None
    if " ".join(values) != output_text:
        raise EvidenceError("sentence evidence does not reconstruct chunk text")
    return make_evidence(
        source_id=source.id,
        components=components,
        output_text=output_text,
        join=join,
        context=context,
    )


def chunk_structure(
    blocks, *, max_size=2000, source_id="", transformed=(),
    source: SourceRef | None = None,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None = None,
    region_id: str = "body",
) -> list[Chunk]:
    if source is not None:
        source_id = source.id
    transformed_blocks = _norm(transformed)
    global_paths = _path_map(blocks)
    blocks_by_index = {block.block_index: block for block in blocks}
    sections: list[list[Block]] = [[]]
    for block in blocks:
        if isinstance(block, Heading) and sections[-1]:
            sections.append([])
        sections[-1].append(block)
    chunks: list[Chunk] = []
    for section in sections:
        chunks.extend(chunk_paragraph(
            section, max_size=max_size, source_id=source_id,
            transformed=transformed_blocks,
            source=source, block_derivations=block_derivations, region_id=region_id,
        ))
    for index, chunk in enumerate(chunks):
        sequence = index + 1
        context = {
            "strategy": "structure",
            "max_size": max_size,
            "sequence": sequence,
            "region_id": region_id,
        }
        chunk_blocks = [blocks_by_index[item] for item in chunk.block_indexes]
        evidence = evidence_for_blocks(
            source=source,
            blocks=chunk_blocks,
            block_derivations=block_derivations,
            output_text=chunk.text,
            context=context,
            region_id=region_id,
        )
        # heading_path must reflect the document-wide context of the chunk's first
        # block, not just its section — re-attach from the global map
        chunks[index] = make_chunk(
            sequence,
            chunk_blocks,
            chunk.text,
            source_id=source_id,
            heading_path=global_paths.get(chunk.block_index, chunk.heading_path),
            transformed_blocks=transformed_blocks,
            evidence=evidence,
            identity_context=context,
        )
    return chunks
