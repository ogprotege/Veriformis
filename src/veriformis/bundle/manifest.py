# src/veriformis/bundle/manifest.py
"""The sealed manifest: provenance, transforms, validations, and file hashes."""

from __future__ import annotations

from pydantic import BaseModel


class SourceEntry(BaseModel):
    id: str
    path: str
    sha256: str
    size: int
    parser: str
    logical_path: str = ""
    parser_version: str = "1"
    canonical_stream_contract_version: int = 1
    stream_sha256: str = ""
    artifact_id: str = ""


class TransformEntry(BaseModel):
    schema_version: str
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool
    id: str = ""
    source_id: str = ""
    chars_removed: int = 0
    operation_ids: tuple[str, ...] = ()
    input_sha256: str = ""
    output_sha256: str = ""
    rule_index: int = 0


class SpanEntry(BaseModel):
    start: int
    end: int
    page: int | None = None


class ChunkEntry(BaseModel):
    id: str
    source_id: str
    block_index: int
    span: SpanEntry | None
    heading_path: list[str]
    tokens_est: int
    transformed: bool
    artifact_id: str = ""
    evidence_id: str | None = None
    evidence_output_sha256: str | None = None


class DatasetInfo(BaseModel):
    format: str
    template: str | None
    record_count: int
    total_chars: int
    total_tokens_est: int


class ValidationEntry(BaseModel):
    gate: str
    passed: bool
    messages: list[str]


class Manifest(BaseModel):
    bundle_id: str
    created_at: str
    veriformis_version: str
    sources: list[SourceEntry]
    transforms: list[TransformEntry]
    chunks: list[ChunkEntry]
    dataset: DatasetInfo
    validations: list[ValidationEntry]
    files: dict[str, str]
