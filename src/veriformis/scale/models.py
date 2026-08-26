"""Versioned scale-corpus spec and materialized corpus identities."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    SCALE_CORPUS_SCHEMA_ID,
    SCALE_CORPUS_SPEC_SCHEMA_ID,
)
from veriformis.errors import ScaleError
from veriformis.identity import derive_id, validate_id, validate_sha256
from veriformis.taxonomy import IMPLEMENTED_PHYSICAL_CONTAINERS


_TOKEN = re.compile(r"^[a-z][a-z0-9-]*$")
PPM_DENOMINATOR = 1_000_000
GENERIC_SCALE_CONTAINERS: tuple[str, ...] = tuple(
    container
    for container in IMPLEMENTED_PHYSICAL_CONTAINERS
    if container
    not in {
        "deterministic-export-pack-zip-v1",
        "deterministic-vfbundle-zip-v1",
        "minimal-v1",
    }
)
ScaleInputMode = Literal["dataset-row", "document-source"]
ScaleContainer = Literal[
    "arrow",
    "constrained-csv",
    "hugging-face-dataset",
    "json",
    "parquet",
    "split-jsonl-directory",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def _require_token(value: str, label: str) -> str:
    if not value or value.strip() != value or _TOKEN.fullmatch(value) is None:
        raise ScaleError(f"{label} must be a lowercase hyphenated token")
    return value


def _require_non_negative(value: int, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ScaleError(f"{label} must be a non-negative integer")
    return value


def _require_positive(value: int, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ScaleError(f"{label} must be a positive integer")
    return value


def record_payload(*, seed: str, index: int, row_length: int) -> str:
    """Build a deterministic Unicode payload of exact ``row_length`` characters."""
    _require_token(seed, "seed")
    _require_non_negative(index, "index")
    _require_positive(row_length, "row_length")
    digest = hmac.new(
        seed.encode("utf-8"),
        f"record:{index}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    unit = f"café-{index}-{digest}-"
    body = (unit * ((row_length // len(unit)) + 1))[:row_length]
    if len(body) != row_length:
        raise ScaleError("record payload length mismatch")
    return body


class ScaleCorpusSpec(_StrictModel):
    container: ScaleContainer
    corpus_id: str
    duplicate_rate_ppm: int
    file_count: int
    input_mode: ScaleInputMode
    nesting_depth: int
    pdf_pages: int
    record_count: int
    row_length: int
    schema_id: Literal["veriformis.scale-corpus-spec/v1"] = SCALE_CORPUS_SPEC_SCHEMA_ID
    seed: str
    spec_id: str

    @model_validator(mode="after")
    def _closed(self) -> ScaleCorpusSpec:
        _require_token(self.corpus_id, "corpus_id")
        _require_token(self.seed, "seed")
        _require_positive(self.file_count, "file_count")
        _require_positive(self.record_count, "record_count")
        _require_positive(self.row_length, "row_length")
        _require_non_negative(self.nesting_depth, "nesting_depth")
        _require_non_negative(self.pdf_pages, "pdf_pages")
        _require_non_negative(self.duplicate_rate_ppm, "duplicate_rate_ppm")
        if self.duplicate_rate_ppm > PPM_DENOMINATOR:
            raise ScaleError("duplicate_rate_ppm cannot exceed 1000000")
        if self.record_count < self.file_count:
            raise ScaleError("record_count must be at least file_count")
        if self.container not in GENERIC_SCALE_CONTAINERS:
            raise ScaleError("container is not a generic scale export")
        if self.container == "constrained-csv" and self.nesting_depth != 0:
            raise ScaleError("constrained-csv admits only flat rows")
        if self.input_mode == "dataset-row":
            if self.pdf_pages != 0:
                raise ScaleError("dataset-row corpora cannot include PDF pages")
        elif self.pdf_pages > 0:
            if self.nesting_depth != 0:
                raise ScaleError("PDF corpora cannot nest records")
            expected = self.file_count * self.pdf_pages
            if self.record_count != expected:
                raise ScaleError(
                    "PDF record_count must equal file_count times pdf_pages"
                )
        elif self.pdf_pages == 0 and self.input_mode == "document-source":
            if self.nesting_depth != 0:
                raise ScaleError("markdown corpora cannot nest records")
        if self.duplicate_rate_ppm > 0:
            if self.record_count < 2:
                raise ScaleError("duplicates require at least two records")
            copies = (self.record_count * self.duplicate_rate_ppm) // PPM_DENOMINATOR
            if copies < 1:
                raise ScaleError("duplicate_rate_ppm is too small to copy a record")
        validate_id(self.spec_id, kind="scs")
        expected_id = derive_id(
            "scs",
            self.model_dump(mode="json", exclude={"spec_id"}),
        )
        if self.spec_id != expected_id:
            raise ScaleError("scale corpus spec identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        corpus_id: str,
        input_mode: ScaleInputMode,
        file_count: int,
        record_count: int,
        row_length: int,
        nesting_depth: int,
        pdf_pages: int,
        duplicate_rate_ppm: int,
        container: ScaleContainer,
        seed: str,
    ) -> ScaleCorpusSpec:
        payload = {
            "container": container,
            "corpus_id": corpus_id,
            "duplicate_rate_ppm": duplicate_rate_ppm,
            "file_count": file_count,
            "input_mode": input_mode,
            "nesting_depth": nesting_depth,
            "pdf_pages": pdf_pages,
            "record_count": record_count,
            "row_length": row_length,
            "schema_id": SCALE_CORPUS_SPEC_SCHEMA_ID,
            "seed": seed,
        }
        return cls(spec_id=derive_id("scs", payload), **payload)


class ScaleCorpusFile(_StrictModel):
    digest: str
    path: str
    size: int

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        if not value or value.strip() != value or "/" in value or "\\" in value:
            raise ScaleError("corpus file path must be a single relative name")
        if value in {".", ".."} or value.startswith("."):
            raise ScaleError("corpus file path must be a visible relative name")
        return value

    @model_validator(mode="after")
    def _closed(self) -> ScaleCorpusFile:
        validate_sha256(self.digest)
        _require_non_negative(self.size, "size")
        return self


class ScaleCorpus(_StrictModel):
    container: ScaleContainer
    corpus_id: str
    duplicate_rate_ppm: int
    file_count: int
    files: tuple[ScaleCorpusFile, ...]
    input_mode: ScaleInputMode
    nesting_depth: int
    pdf_pages: int
    record_count: int
    row_length: int
    schema_id: Literal["veriformis.scale-corpus/v1"] = SCALE_CORPUS_SCHEMA_ID
    seed: str
    spec_id: str
    total_bytes: int

    @field_validator("files", mode="before")
    @classmethod
    def _files(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ScaleCorpus:
        validate_id(self.corpus_id, kind="scb")
        validate_id(self.spec_id, kind="scs")
        _require_token(self.seed, "seed")
        if len(self.files) != self.file_count:
            raise ScaleError("corpus file_count must equal the file tuple")
        if tuple(item.path for item in self.files) != tuple(
            sorted(item.path for item in self.files)
        ):
            raise ScaleError("corpus files must be sorted by path")
        measured = sum(item.size for item in self.files)
        if measured != self.total_bytes:
            raise ScaleError("corpus total_bytes must equal measured file sizes")
        expected = derive_id(
            "scb",
            self.model_dump(mode="json", exclude={"corpus_id"}),
        )
        if self.corpus_id != expected:
            raise ScaleError("scale corpus identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        spec: ScaleCorpusSpec,
        files: tuple[ScaleCorpusFile, ...],
        total_bytes: int,
    ) -> ScaleCorpus:
        payload = {
            "container": spec.container,
            "duplicate_rate_ppm": spec.duplicate_rate_ppm,
            "file_count": spec.file_count,
            "files": [item.model_dump(mode="json") for item in files],
            "input_mode": spec.input_mode,
            "nesting_depth": spec.nesting_depth,
            "pdf_pages": spec.pdf_pages,
            "record_count": spec.record_count,
            "row_length": spec.row_length,
            "schema_id": SCALE_CORPUS_SCHEMA_ID,
            "seed": spec.seed,
            "spec_id": spec.spec_id,
            "total_bytes": total_bytes,
        }
        return cls(corpus_id=derive_id("scb", payload), **payload)


def duplicate_indexes(*, record_count: int, duplicate_rate_ppm: int) -> frozenset[int]:
    """Return indexes after zero that copy record zero under the ppm rate."""
    _require_positive(record_count, "record_count")
    _require_non_negative(duplicate_rate_ppm, "duplicate_rate_ppm")
    if duplicate_rate_ppm == 0:
        return frozenset()
    copies = (record_count * duplicate_rate_ppm) // PPM_DENOMINATOR
    if copies < 1:
        raise ScaleError("duplicate_rate_ppm is too small to copy a record")
    if copies >= record_count:
        copies = record_count - 1
    return frozenset(range(record_count - copies, record_count))


def encode_record(
    *,
    spec: ScaleCorpusSpec,
    payload: str,
) -> str:
    """Encode one record for the spec's input mode and nesting."""
    if spec.input_mode == "dataset-row":
        if spec.nesting_depth == 0:
            return json.dumps({"text": payload}, ensure_ascii=False, separators=(",", ":"))
        messages = []
        roles = ("system", "user", "assistant")
        for turn in range(spec.nesting_depth):
            messages.append(
                {
                    "role": roles[turn % 3],
                    "content": payload if turn == spec.nesting_depth - 1 else f"turn-{turn}",
                }
            )
        return json.dumps(
            {"messages": messages},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    if spec.pdf_pages > 0:
        return payload
    return payload
