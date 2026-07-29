# src/veriformis/chunkers/base.py
"""Chunk model + shared helpers."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Mapping

from veriformis.evidence import (
    DerivationStep, EvidenceComponent, EvidenceError, SourceEvidence,
    join_derivation, make_evidence, replay_derivations, source_evidence_from_dict,
    source_evidence_to_dict, source_range,
)
from veriformis.identity import canonical_digest, derive_id, sha256_digest, validate_id
from veriformis.ir import Block, Heading, Span, block_text
from veriformis.sources import SourceRef


CHUNK_SCHEMA_VERSION = "veriformis.chunk/v1"


@dataclass(frozen=True)
class Chunk:
    id: str
    source_id: str
    block_index: int
    span: Span | None
    heading_path: list[str]
    text: str
    tokens_est: int
    transformed: bool = False
    evidence: SourceEvidence | None = None
    artifact_id: str = ""
    schema_version: str = CHUNK_SCHEMA_VERSION
    sequence: int = 0
    block_indexes: tuple[int, ...] = ()
    identity_context: dict = field(default_factory=dict)


def exact_span_from_evidence(evidence: SourceEvidence | None) -> Span | None:
    """Return a canonical-source span only when the evidence proves one.

    A single untouched source range is exact. Joined ranges and any derived
    value are not represented as one canonical range, even when their outer
    offsets happen to form a broad interval.
    """
    if evidence is None or len(evidence.components) != 1:
        return None
    component = evidence.components[0]
    item = component.source_range
    if component.derivations or evidence.join_derivation is not None or evidence.derivations:
        return None
    if item.range_kind != "text" or item.start >= item.end:
        return None
    if item.text_sha256 != evidence.output_sha256:
        return None
    return Span(start=item.start, end=item.end)


def _span_value(span: Span | None) -> dict | None:
    if span is None:
        return None
    return {"start": span.start, "end": span.end, "page": span.page}


def _chunk_identity_payload(chunk: Chunk) -> dict:
    """Return the complete semantic payload bound by a v1 chunk ID."""
    return {
        "schema_version": chunk.schema_version,
        "source_id": chunk.source_id,
        "sequence": chunk.sequence,
        "block_index": chunk.block_index,
        "block_indexes": list(chunk.block_indexes),
        "span": _span_value(chunk.span),
        "heading_path": list(chunk.heading_path),
        "text_sha256": sha256_digest(chunk.text),
        "tokens_est": chunk.tokens_est,
        "transformed": chunk.transformed,
        "evidence_id": chunk.evidence.evidence_id if chunk.evidence else None,
        "artifact_id": chunk.artifact_id,
        "identity_context": chunk.identity_context,
    }


def derive_chunk_id(chunk: Chunk) -> str:
    """Derive a chunk ID from every persisted semantic field."""
    return derive_id("chk", _chunk_identity_payload(chunk))


def refresh_chunk_id(chunk: Chunk) -> Chunk:
    """Recompute an ID after an intentional in-memory chunk transformation."""
    return replace(chunk, id=derive_chunk_id(chunk))


def chunk_to_dict(chunk: Chunk) -> dict:
    """Serialize a chunk using the exact persisted workspace schema."""
    evidence = source_evidence_to_dict(chunk.evidence) if chunk.evidence is not None else None
    _validate_chunk(chunk)
    return {
        "schema_version": chunk.schema_version,
        "id": chunk.id,
        "source_id": chunk.source_id,
        "sequence": chunk.sequence,
        "block_index": chunk.block_index,
        "block_indexes": list(chunk.block_indexes),
        "span": _span_value(chunk.span),
        "heading_path": list(chunk.heading_path),
        "text": chunk.text,
        "tokens_est": chunk.tokens_est,
        "transformed": chunk.transformed,
        "evidence": evidence,
        "artifact_id": chunk.artifact_id,
        "identity_context": dict(chunk.identity_context),
    }


def chunk_from_dict(value: dict) -> Chunk:
    """Load a chunk from the exact persisted workspace schema."""
    expected = {
        "schema_version", "id", "source_id", "sequence", "block_index",
        "block_indexes", "span", "heading_path", "text", "tokens_est",
        "transformed", "evidence", "artifact_id", "identity_context",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidenceError("chunk keys do not match the v1 schema")
    span_value = value["span"]
    if span_value is not None:
        if not isinstance(span_value, dict) or set(span_value) != {"start", "end", "page"}:
            raise EvidenceError("chunk span keys do not match the v1 schema")
        try:
            span = Span(**span_value)
        except TypeError as exc:
            raise EvidenceError(f"invalid chunk span: {exc}") from exc
    else:
        span = None
    if not isinstance(value["heading_path"], list) \
            or not all(isinstance(item, str) for item in value["heading_path"]):
        raise EvidenceError("chunk heading_path must be a list of strings")
    if not isinstance(value["block_indexes"], list):
        raise EvidenceError("chunk block_indexes must be a list")
    if not isinstance(value["identity_context"], dict):
        raise EvidenceError("chunk identity_context must be an object")
    evidence_value = value["evidence"]
    if evidence_value is not None and not isinstance(evidence_value, dict):
        raise EvidenceError("chunk evidence must be an object or null")
    evidence = source_evidence_from_dict(evidence_value) if evidence_value is not None else None
    chunk = Chunk(
        id=value["id"],
        source_id=value["source_id"],
        block_index=value["block_index"],
        span=span,
        heading_path=list(value["heading_path"]),
        text=value["text"],
        tokens_est=value["tokens_est"],
        transformed=value["transformed"],
        evidence=evidence,
        artifact_id=value["artifact_id"],
        schema_version=value["schema_version"],
        sequence=value["sequence"],
        block_indexes=tuple(value["block_indexes"]),
        identity_context=dict(value["identity_context"]),
    )
    _validate_chunk(chunk)
    return chunk


def _validate_chunk(chunk: Chunk) -> None:
    """Validate v1 shape, evidence relationships, and content identity."""
    try:
        if chunk.schema_version != CHUNK_SCHEMA_VERSION:
            raise EvidenceError(f"unsupported chunk schema {chunk.schema_version!r}")
        validate_id(chunk.id, kind="chk")
        validate_id(chunk.source_id, kind="src")
        if chunk.artifact_id:
            validate_id(chunk.artifact_id, kind="art")
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid chunk identity: {exc}") from exc
    if type(chunk.sequence) is not int or chunk.sequence < 1:
        raise EvidenceError("chunk sequence must be a positive integer")
    if type(chunk.block_index) is not int:
        raise EvidenceError("chunk block_index must be an integer")
    if not chunk.block_indexes or not all(type(item) is int for item in chunk.block_indexes):
        raise EvidenceError("chunk block_indexes must contain integers")
    if any(item < 0 for item in chunk.block_indexes) \
            or tuple(sorted(chunk.block_indexes)) != chunk.block_indexes:
        raise EvidenceError("chunk block_indexes must be non-negative and ordered")
    if chunk.block_index != chunk.block_indexes[0]:
        raise EvidenceError("chunk block_index must equal its first block index")
    if len(set(chunk.block_indexes)) != len(chunk.block_indexes):
        raise EvidenceError("chunk block_indexes contain duplicates")
    if not isinstance(chunk.text, str) or not chunk.text:
        raise EvidenceError("chunk text must be a non-empty string")
    if not isinstance(chunk.heading_path, list) \
            or not all(isinstance(item, str) for item in chunk.heading_path):
        raise EvidenceError("chunk heading_path must be a list of strings")
    if type(chunk.tokens_est) is not int or chunk.tokens_est != est_tokens(chunk.text):
        raise EvidenceError("chunk token estimate does not match its text")
    if type(chunk.transformed) is not bool:
        raise EvidenceError("chunk transformed must be a boolean")
    if not isinstance(chunk.identity_context, dict):
        raise EvidenceError("chunk identity_context must be an object")
    if chunk.span is not None:
        if type(chunk.span.start) is not int or type(chunk.span.end) is not int \
                or not (0 <= chunk.span.start < chunk.span.end):
            raise EvidenceError("chunk span is invalid")
        if chunk.span.page is not None \
                and (type(chunk.span.page) is not int or chunk.span.page < 0):
            raise EvidenceError("chunk span page is invalid")
    if chunk.evidence is None:
        raise EvidenceError("persisted chunks require source evidence")
    if not chunk.evidence.components:
        raise EvidenceError("chunk evidence requires at least one component")
    if chunk.evidence.source_id != chunk.source_id:
        raise EvidenceError("chunk and evidence source identities differ")
    if chunk.evidence.output_sha256 != sha256_digest(chunk.text):
        raise EvidenceError("chunk text does not match its source evidence")
    if chunk.evidence.context_digest != canonical_digest(chunk.identity_context):
        raise EvidenceError("chunk evidence context does not match its identity context")
    evidence_artifact = chunk.evidence.components[0].source_range.artifact_id
    if chunk.artifact_id != evidence_artifact:
        raise EvidenceError("chunk and evidence artifact identities differ")
    evidence_region = chunk.evidence.components[0].source_range.region_id
    _validate_chunk_context(chunk, evidence_region)
    if chunk.span != exact_span_from_evidence(chunk.evidence):
        raise EvidenceError("chunk span is not the exact range proved by its evidence")
    try:
        expected_id = derive_chunk_id(chunk)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid chunk identity context: {exc}") from exc
    if expected_id != chunk.id:
        raise EvidenceError("chunk identity mismatch")


def _validate_chunk_context(chunk: Chunk, evidence_region: str) -> None:
    context = chunk.identity_context
    strategy = context.get("strategy")
    common = {"strategy", "sequence", "region_id"}
    overlap = None
    if strategy in ("paragraph", "sentence", "structure"):
        expected = common | {"max_size"}
        size_value = context.get("max_size")
    elif strategy in ("fixed", "sliding"):
        expected = common | {"size", "overlap"}
        size_value = context.get("size")
        overlap = context.get("overlap")
    else:
        raise EvidenceError(f"unsupported chunk strategy {strategy!r}")
    if set(context) != expected:
        raise EvidenceError("chunk identity context keys do not match its strategy")
    if type(size_value) is not int or size_value < 1:
        raise EvidenceError("chunk size must be a positive integer")
    if strategy in ("fixed", "sliding") \
            and (type(overlap) is not int or not (0 <= overlap < size_value)):
        raise EvidenceError("chunk overlap must be smaller than its size")
    if context.get("sequence") != chunk.sequence:
        raise EvidenceError("chunk context sequence does not match the chunk sequence")
    if context.get("region_id") != evidence_region:
        raise EvidenceError("chunk identity context does not match its evidence region")


def est_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def heading_paths(blocks: list[Block]) -> list[list[str]]:
    """Heading path in effect at each block index (headings included, path = self)."""
    stack: list[tuple[int, str]] = []
    paths: list[list[str]] = []
    for block in blocks:
        if isinstance(block, Heading):
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block_text(block)))
        paths.append([title for _, title in stack])
    return paths


def make_chunk(
    seq: int, blocks: list[Block], text: str, *, source_id: str,
    heading_path: list[str], transformed_blocks: set[int],
    evidence: SourceEvidence | None = None, identity_context: dict | None = None,
) -> Chunk:
    chunk = Chunk(
        id="",
        source_id=source_id,
        block_index=blocks[0].block_index if blocks else -1,
        span=exact_span_from_evidence(evidence),
        heading_path=heading_path,
        text=text,
        tokens_est=est_tokens(text),
        transformed=any(b.block_index in transformed_blocks for b in blocks),
        evidence=evidence,
        artifact_id=(
            evidence.components[0].source_range.artifact_id
            if evidence and evidence.components else ""
        ),
        sequence=seq,
        block_indexes=tuple(block.block_index for block in blocks),
        identity_context=dict(identity_context or {}),
    )
    return refresh_chunk_id(chunk)


def flatten(blocks: list[Block]) -> str:
    """The canonical extracted stream (must equal parser-built streams)."""
    return "\n\n".join(block_text(b) for b in blocks)


def evidence_component_for_block(
    source: SourceRef,
    block: Block,
    block_derivations: Mapping[int, tuple[DerivationStep, ...]],
    *,
    region_id: str = "body",
) -> EvidenceComponent:
    if block.span is None:
        raise EvidenceError(f"block {block.block_index} has no immutable source range")
    item = source_range(source, block.span.start, block.span.end, region_id=region_id)
    steps = tuple(block_derivations.get(block.block_index, ()))
    resolved = replay_derivations(source.extracted_text[item.start:item.end], steps)
    if resolved != block_text(block):
        raise EvidenceError(f"block {block.block_index} derivations do not reconstruct its text")
    return EvidenceComponent(source_range=item, derivations=steps)


def evidence_for_blocks(
    *,
    source: SourceRef | None,
    blocks: list[Block],
    block_derivations: Mapping[int, tuple[DerivationStep, ...]] | None,
    output_text: str,
    context: dict,
    selection: tuple[int, int] | None = None,
    region_id: str = "body",
) -> SourceEvidence | None:
    if source is None or not blocks:
        return None
    derivations_by_block = block_derivations or {}
    components = [
        evidence_component_for_block(
            source,
            block,
            derivations_by_block,
            region_id=region_id,
        )
        for block in blocks
    ]
    values = [
        replay_derivations(
            source.extracted_text[item.source_range.start:item.source_range.end],
            item.derivations,
        )
        for item in components
    ]
    join = join_derivation(values, "\n\n", context={**context, "operation": "block-join"}) \
        if len(values) > 1 else None
    joined = "\n\n".join(values)
    tail: tuple[DerivationStep, ...] = ()
    if selection is not None:
        from veriformis.evidence import slice_derivation

        start, end = selection
        step = slice_derivation(joined, start, end, context={**context, "operation": "slice"})
        tail = (step,)
        joined = joined[start:end]
    if joined != output_text:
        raise EvidenceError("chunk evidence does not reconstruct chunk text")
    return make_evidence(
        source_id=source.id,
        components=components,
        output_text=output_text,
        join=join,
        derivations=tail,
        context=context,
    )
