# src/veriformis/bundle/writer.py
"""Bundle writing and sealing. Fail-closed: a failed gate means no bundle."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import veriformis
from veriformis.bundle.manifest import (
    ChunkEntry,
    DatasetInfo,
    Manifest,
    SourceEntry,
    SpanEntry,
    TransformEntry,
    ValidationEntry,
)
from veriformis.chunkers.base import Chunk, chunk_to_dict
from veriformis.contracts import CANONICAL_STREAM_CONTRACT_VERSION
from veriformis.errors import EvidenceError, GateFailure, RuleError
from veriformis.evidence import resolve_evidence
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_source_id,
    normalize_logical_path,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.rules.engine import (
    TransformRecord,
    transform_record_to_dict,
)
from veriformis.sources import SourceRef


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_source(source: SourceRef) -> None:
    if not isinstance(source, SourceRef):
        raise EvidenceError("bundle sources must be SourceRef values")
    if not isinstance(source.path, str) or not source.path:
        raise EvidenceError("bundle source path must be a non-empty string")
    if not isinstance(source.logical_path, str):
        raise EvidenceError("bundle source logical path must be a string")
    if type(source.size) is not int or source.size < 0:
        raise EvidenceError("bundle source size must be a non-negative integer")
    if not isinstance(source.extracted_text, str):
        raise EvidenceError("bundle source canonical stream must be text")
    if not isinstance(source.parser, str) or not source.parser:
        raise EvidenceError("bundle source parser must be a non-empty string")
    if not isinstance(source.parser_version, str) or not source.parser_version:
        raise EvidenceError("bundle source parser version must be a non-empty string")
    if (
        type(source.canonical_stream_contract_version) is not int
        or source.canonical_stream_contract_version != CANONICAL_STREAM_CONTRACT_VERSION
    ):
        raise EvidenceError(
            "bundle source uses an unsupported canonical stream contract"
        )
    try:
        logical_path = normalize_logical_path(source.logical_path)
        validate_sha256(source.sha256)
        validate_sha256(source.stream_sha256)
        validate_id(source.id, kind="src")
        validate_id(source.artifact_id, kind="art")
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"invalid bundle source identity or digest: {exc}") from exc
    if source.id != derive_source_id(logical_path, source.sha256):
        raise EvidenceError(
            "bundle source identity does not match its locator and digest"
        )
    stream_sha256 = sha256_digest(source.extracted_text)
    if source.stream_sha256 != stream_sha256:
        raise EvidenceError("bundle source canonical stream digest mismatch")
    config_digest = canonical_digest(
        {
            "parser": source.parser,
            "parser_version": source.parser_version,
            "canonical_stream_contract_version": (
                source.canonical_stream_contract_version
            ),
        }
    )
    expected_artifact_id = derive_artifact_id(
        kind="canonical-source-text",
        content_sha256=stream_sha256,
        source_ids=(source.id,),
        producer_id=f"veriformis.parser.{source.parser}",
        producer_version=source.parser_version,
        config_digest=config_digest,
    )
    if source.artifact_id != expected_artifact_id:
        raise EvidenceError("bundle source canonical artifact identity mismatch")


def _validate_integrity_inputs(
    sources: list[SourceRef],
    transforms: list[TransformRecord],
    chunks: list[Chunk],
) -> None:
    source_map: dict[str, SourceRef] = {}
    for source in sources:
        _validate_source(source)
        if source.id in source_map:
            raise EvidenceError(f"bundle contains duplicate source {source.id!r}")
        source_map[source.id] = source

    transform_ids: set[str] = set()
    for transform in transforms:
        if not isinstance(transform, TransformRecord):
            raise RuleError("bundle transforms must be TransformRecord values")
        transform_record_to_dict(transform)
        if transform.id in transform_ids:
            raise RuleError(f"bundle contains duplicate transform {transform.id!r}")
        transform_ids.add(transform.id)
        if transform.source_id not in source_map:
            raise RuleError(
                f"transform {transform.id!r} refers to an unregistered source"
            )

    chunk_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, Chunk):
            raise EvidenceError("bundle chunks must be Chunk values")
        # The strict serializer validates every field, the content-derived
        # chunk ID, and the complete embedded evidence graph.
        chunk_to_dict(chunk)
        if chunk.id in chunk_ids:
            raise EvidenceError(f"bundle contains duplicate chunk {chunk.id!r}")
        chunk_ids.add(chunk.id)
        source = source_map.get(chunk.source_id)
        if source is None:
            raise EvidenceError(f"chunk {chunk.id!r} refers to an unregistered source")
        if chunk.artifact_id != source.artifact_id:
            raise EvidenceError("bundle chunk and source artifact identities differ")
        if chunk.evidence is None:
            raise EvidenceError("bundle chunks require source evidence")
        if resolve_evidence(chunk.evidence, source_map) != chunk.text:
            raise EvidenceError("bundle chunk evidence does not reconstruct its text")


def write_bundle(
    out_dir,
    *,
    records: list[dict],
    chunks,
    sources,
    transforms,
    validations,
    format: str,
    template: str | None,
) -> Path:
    failed = [v for v in validations if not v.passed]
    if failed:
        raise GateFailure(
            "bundle refused: failed gates: " + ", ".join(v.gate for v in failed)
        )
    _validate_integrity_inputs(sources, transforms, chunks)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)

    dataset_path = out / "dataset.jsonl"
    with dataset_path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = Manifest(
        bundle_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC).isoformat(),
        veriformis_version=veriformis.__version__,
        sources=[
            SourceEntry(
                id=s.id,
                # Host filesystem paths are capture-time facts, not portable
                # bundle identity. Keep the legacy field workspace-relative.
                path=s.logical_path,
                sha256=s.sha256,
                size=s.size,
                parser=s.parser,
                logical_path=s.logical_path,
                parser_version=s.parser_version,
                canonical_stream_contract_version=(s.canonical_stream_contract_version),
                stream_sha256=s.stream_sha256,
                artifact_id=s.artifact_id,
            )
            for s in sources
        ],
        transforms=[
            TransformEntry(
                schema_version=t.schema_version,
                rule=t.rule,
                params=t.params,
                block_index=t.block_index,
                edits=t.edits,
                bytes_removed=t.bytes_removed,
                warned=t.warned,
                id=t.id,
                source_id=t.source_id,
                chars_removed=t.chars_removed,
                operation_ids=t.operation_ids,
                input_sha256=t.input_sha256,
                output_sha256=t.output_sha256,
                rule_index=t.rule_index,
            )
            for t in transforms
        ],
        chunks=[
            ChunkEntry(
                id=c.id,
                source_id=c.source_id,
                block_index=c.block_index,
                span=SpanEntry(start=c.span.start, end=c.span.end, page=c.span.page)
                if c.span
                else None,
                heading_path=c.heading_path,
                tokens_est=c.tokens_est,
                transformed=c.transformed,
                artifact_id=c.artifact_id,
                evidence_id=c.evidence.evidence_id if c.evidence else None,
                evidence_output_sha256=c.evidence.output_sha256 if c.evidence else None,
            )
            for c in chunks
        ],
        dataset=DatasetInfo(
            format=format,
            template=template,
            record_count=len(records),
            total_chars=sum(len(r.get("text") or r.get("output", "")) for r in records),
            total_tokens_est=sum(c.tokens_est for c in chunks),
        ),
        validations=[
            ValidationEntry(gate=v.gate, passed=v.passed, messages=v.messages)
            for v in validations
        ],
        files={"dataset.jsonl": _sha256(dataset_path)},
    )
    manifest_path = out / "manifest.json"
    manifest.files["manifest.json"] = "pending"  # placeholder replaced below
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    manifest.files["manifest.json"] = _sha256(manifest_path)
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out


def verify_bundle(bundle_dir) -> bool:
    out = Path(bundle_dir)
    manifest = Manifest.model_validate_json(
        (out / "manifest.json").read_text(encoding="utf-8")
    )
    for rel, digest in manifest.files.items():
        path = out / rel
        if not path.exists():
            return False
        if rel == "manifest.json":
            continue  # self-hash is informational only
        if _sha256(path) != digest:
            return False
    return True
