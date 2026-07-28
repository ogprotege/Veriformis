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


class TransformEntry(BaseModel):
    rule: str
    params: dict
    block_index: int
    edits: int
    bytes_removed: int
    warned: bool


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
