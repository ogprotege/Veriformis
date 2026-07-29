"""Deterministic chunk-stage projection from validated clean artifacts."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from veriformis.chunkers.base import Chunk
from veriformis.chunkers.strategies import (
    chunk_fixed,
    chunk_paragraph,
    chunk_sentence,
    chunk_sliding,
    chunk_structure,
)
from veriformis.errors import EvidenceError
from veriformis.evidence import DerivationStep
from veriformis.ir import Document, block_text, iter_document_regions
from veriformis.rules.engine import TransformRecord
from veriformis.sources import SourceRef


_STRATEGIES = {
    "paragraph": chunk_paragraph,
    "fixed": chunk_fixed,
    "sliding": chunk_sliding,
    "sentence": chunk_sentence,
    "structure": chunk_structure,
}


def build_chunks(
    documents: Mapping[str, Document],
    sources: Mapping[str, SourceRef],
    transforms: Sequence[TransformRecord],
    block_derivations: Mapping[
        str, Mapping[int, tuple[DerivationStep, ...]]
    ],
    *,
    strategy: str,
    size: int,
    overlap: int,
) -> list[Chunk]:
    """Return the one exact chunk list implied by clean state and config."""
    if strategy not in _STRATEGIES:
        raise EvidenceError(f"unsupported chunk strategy {strategy!r}")
    if type(size) is not int or size < 1:
        raise EvidenceError("chunk size must be a positive integer")
    if type(overlap) is not int or not 0 <= overlap < size:
        raise EvidenceError("chunk overlap must be smaller than its size")
    if set(documents) != set(sources) or set(block_derivations) != set(sources):
        raise EvidenceError("chunk inputs do not cover the exact source set")

    transformed: dict[str, set[int]] = {source_id: set() for source_id in sources}
    for record in transforms:
        if record.source_id not in transformed:
            raise EvidenceError("transform names an unregistered chunk source")
        if record.edits and not record.warned:
            transformed[record.source_id].add(record.block_index)

    chunks: list[Chunk] = []
    chunker = _STRATEGIES[strategy]
    for source_id, document in sorted(documents.items()):
        for region_id, region_blocks in iter_document_regions(document):
            common = {
                "source": sources[source_id],
                "transformed": transformed[source_id],
                "block_derivations": block_derivations[source_id],
                "region_id": region_id,
            }
            if strategy in {"paragraph", "sentence", "structure"}:
                made = chunker(region_blocks, max_size=size, **common)
            else:
                made = chunker(
                    region_blocks,
                    size=size,
                    overlap=overlap,
                    **common,
                )
            expected_indexes = {
                block.block_index for block in region_blocks if block_text(block)
            }
            covered_indexes = {
                block_index
                for chunk in made
                for block_index in chunk.block_indexes
            }
            if not expected_indexes <= covered_indexes:
                missing = sorted(expected_indexes - covered_indexes)
                raise EvidenceError(
                    f"chunking orphaned {region_id} blocks {missing}"
                )
            chunks.extend(made)

    chunk_ids = [chunk.id for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise EvidenceError("chunk identities are not globally unique")
    return chunks
