"""Deterministic, atomic finished-dataset bundles.

This module is intentionally additive.  The legacy bundle writer remains
available for compatibility, while this API provides the fail-closed contract
for integrity-bearing finished datasets.
"""

from __future__ import annotations

import ctypes
import errno
import io
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.errors import (
    BundleVerificationError,
    SealError,
    VeriformisError,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

MANIFEST_NAME = "manifest.json"
ATTESTATION_NAME = "attestation.json"
TRAIN_PATH = "data/train.jsonl"
EVALUATION_PATH = "data/evaluation.jsonl"
PROVENANCE_PATH = "metadata/row-provenance.jsonl"
VALIDATION_PATH = "validation.json"

_MINIMAL_PAYLOAD_CONTRACT: dict[str, tuple[str, str]] = {
    TRAIN_PATH: ("training-partition", "application/jsonl"),
    EVALUATION_PATH: ("evaluation-partition", "application/jsonl"),
    PROVENANCE_PATH: ("row-provenance", "application/jsonl"),
    VALIDATION_PATH: ("dataset-validation-report", "application/json"),
}
_MINIMAL_PAYLOAD_PATHS = tuple(sorted(_MINIMAL_PAYLOAD_CONTRACT))
_MINIMAL_JSONL_PATHS = frozenset({TRAIN_PATH, EVALUATION_PATH, PROVENANCE_PATH})

_MANIFEST_SCHEMA = "veriformis.finished-bundle-manifest/v1"
_FILE_SCHEMA = "veriformis.finished-bundle-file/v1"
_ATTESTATION_SCHEMA = "veriformis.bundle-attestation/v1"
_VERIFICATION_SCHEMA = "veriformis.bundle-verification/v1"
_CONTENT_ROOT_SCHEMA = "veriformis.bundle-content-root/v1"
_JSONL_MEDIA_TYPES = frozenset(
    {
        "application/jsonl",
        "application/ndjson",
        "application/x-ndjson",
    }
)
_MEDIA_TYPE = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_WINDOWS_RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
)
_RESERVED_BUNDLE_PATHS = frozenset({MANIFEST_NAME, ATTESTATION_NAME})


class FinishedBundleError(SealError):
    """A finished bundle cannot be constructed without weakening integrity."""


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BundleVerificationError(
                f"canonical JSON contains duplicate key {key!r}"
            )
        result[key] = value
    return result


def _reject_json_float(value: str) -> None:
    raise BundleVerificationError(
        f"floating-point JSON number is not allowed: {value!r}"
    )


def _reject_json_constant(value: str) -> None:
    raise BundleVerificationError(f"non-finite JSON number is not allowed: {value!r}")


def _canonical_json_object_from_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    """Decode one exact canonical object without normalizing string content."""
    if type(data) is not bytes:
        raise BundleVerificationError(f"{label} must be loaded from exact bytes")
    try:
        decoded = data.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except BundleVerificationError:
        raise
    except RecursionError as exc:
        raise BundleVerificationError(
            f"invalid {label} JSON: nesting too deep"
        ) from exc
    except (UnicodeError, ValueError) as exc:
        raise BundleVerificationError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleVerificationError(f"{label} JSON root must be an object")
    try:
        canonical = lossless_json_bytes(value)
    except RecursionError as exc:
        raise BundleVerificationError(
            f"invalid {label} JSON: nesting too deep"
        ) from exc
    except (TypeError, UnicodeError, ValueError) as exc:
        raise BundleVerificationError(f"invalid {label} JSON: {exc}") from exc
    if canonical != data:
        raise BundleVerificationError(f"{label} JSON bytes are not canonical")
    return value


def _canonical_jsonl_record_count(data: bytes, *, label: str) -> int:
    """Validate exact canonical JSONL bytes and return their record count."""
    if type(data) is not bytes:
        raise FinishedBundleError(f"{label} must be exact bytes")
    count = 0
    with io.BytesIO(data) as handle:
        while True:
            line = handle.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                raise FinishedBundleError(
                    f"JSONL payload {label!r} must end every record with LF"
                )
            record = line[:-1]
            if not record:
                raise FinishedBundleError(
                    f"JSONL payload {label!r} contains a blank record"
                )
            try:
                _canonical_json_object_from_bytes(
                    record,
                    label=f"{label} record {count + 1}",
                )
            except BundleVerificationError as exc:
                raise FinishedBundleError(str(exc)) from exc
            count += 1
    return count


def _require_passing_validation_report(
    data: bytes,
    *,
    dataset_snapshot_id: str,
    validation_report_id: str,
    payload_bindings: Mapping[
        str,
        tuple[str, int, int, str, str],
    ],
    error_type: type[VeriformisError],
) -> Any:
    """Strict-load and bind the exact passing report retained in the bundle."""
    try:
        from veriformis.datasets.validation import (
            dataset_validation_report_from_json_bytes,
            dataset_validation_report_json_bytes,
        )

        report = dataset_validation_report_from_json_bytes(data)
        canonical = dataset_validation_report_json_bytes(report)
    except (
        ImportError,
        AttributeError,
        TypeError,
        UnicodeError,
        ValueError,
        VeriformisError,
    ) as exc:
        raise error_type(f"invalid validation.json: {exc}") from exc
    if canonical != data:
        raise error_type("validation.json bytes do not round-trip exactly")
    if report.status != "passed":
        raise error_type("validation.json must contain a passing validation report")
    if report.report_id != validation_report_id:
        raise error_type(
            "validation.json report_id does not match the finished manifest"
        )
    if report.snapshot_id != dataset_snapshot_id:
        raise error_type(
            "validation.json snapshot_id does not match the finished manifest"
        )
    snapshot_bindings = {item.path: item for item in report.snapshot.file_bindings}
    if set(snapshot_bindings) != _MINIMAL_JSONL_PATHS:
        raise error_type(
            "validation.json snapshot does not bind the exact emitted files"
        )
    for path in sorted(_MINIMAL_JSONL_PATHS):
        sha256, size, record_count, role, media_type = payload_bindings[path]
        binding = snapshot_bindings[path]
        if (
            binding.sha256 != sha256
            or binding.byte_size != size
            or binding.record_count != record_count
            or binding.role != role
            or binding.media_type != media_type
        ):
            raise error_type(
                f"validation.json snapshot binding differs from payload {path!r}"
            )
    return report


def _validate_path_syntax(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("bundle paths must be non-empty strings")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("bundle paths must contain valid Unicode") from exc
    if value != unicodedata.normalize("NFC", value):
        raise ValueError("bundle paths must use canonical NFC Unicode")
    if "\x00" in value:
        raise ValueError("bundle paths cannot contain NUL")
    if "\\" in value:
        raise ValueError("bundle paths must use POSIX separators")
    if value.startswith("/") or _WINDOWS_DRIVE.match(value):
        raise ValueError("bundle paths must be relative POSIX paths")

    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("bundle paths cannot contain empty, dot, or parent segments")
    for part in parts:
        if ":" in part or part.endswith((" ", ".")):
            raise ValueError("bundle paths cannot contain Windows path aliases")
        if any(unicodedata.category(character) == "Cc" for character in part):
            raise ValueError("bundle paths cannot contain control characters")
        device_name = part.split(".", 1)[0].casefold()
        if device_name in _WINDOWS_RESERVED:
            raise ValueError("bundle paths cannot use Windows device names")
    return value


def _validate_payload_path(value: str) -> str:
    value = _validate_path_syntax(value)
    first = value.split("/", 1)[0]
    if _portable_path_key(first) in {
        _portable_path_key(path) for path in _RESERVED_BUNDLE_PATHS
    }:
        raise ValueError(f"payload path conflicts with reserved bundle file {first!r}")
    return value


def _portable_path_key(path: str) -> str:
    """Return the conservative key used by case/Unicode-insensitive systems."""
    return unicodedata.normalize("NFKC", path).casefold()


def _uses_jsonl_contract(
    *, path: str, media_type: str, record_count: int | None
) -> bool:
    return (
        path.casefold().endswith(".jsonl")
        or media_type in _JSONL_MEDIA_TYPES
        or record_count is not None
    )


def _file_identity_payload(
    *,
    path: str,
    role: str,
    media_type: str,
    size: int,
    sha256: str,
    record_count: int | None,
) -> dict[str, Any]:
    return {
        "schema_version": _FILE_SCHEMA,
        "path": path,
        "role": role,
        "media_type": media_type,
        "size": size,
        "sha256": sha256,
        "record_count": record_count,
    }


class _StrictFinishedModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, cls) or not isinstance(value, Mapping):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(
                f"{cls.__name__} fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if info.mode != "json":
            return value
        normalized = dict(value)
        for name, field in cls.model_fields.items():
            if get_origin(field.annotation) is tuple and isinstance(
                normalized[name], list
            ):
                normalized[name] = tuple(normalized[name])
        return normalized

    def canonical_bytes(self) -> bytes:
        """Return exact canonical JSON after a fresh validation boundary."""
        try:
            data = lossless_json_bytes(self.model_dump(mode="json"))
            checked = type(self).model_validate_json(data)
        except (TypeError, UnicodeError, ValueError) as exc:
            raise FinishedBundleError(f"invalid {type(self).__name__}: {exc}") from exc
        if checked != self:
            raise FinishedBundleError(
                f"{type(self).__name__} does not round-trip exactly"
            )
        return data

    @classmethod
    def from_json_bytes(cls, data: bytes) -> Self:
        """Load only the unique canonical byte representation of this model."""
        _canonical_json_object_from_bytes(data, label=cls.__name__)
        try:
            checked = cls.model_validate_json(data)
        except (TypeError, ValueError) as exc:
            raise BundleVerificationError(f"invalid {cls.__name__}: {exc}") from exc
        if checked.canonical_bytes() != data:
            raise BundleVerificationError(f"{cls.__name__} does not round-trip exactly")
        return checked


class BundleFile(_StrictFinishedModel):
    """One exact payload in a finished bundle."""

    schema_version: Literal["veriformis.finished-bundle-file/v1"]
    file_id: str
    path: str
    role: str
    media_type: str
    size: int
    sha256: str
    record_count: int | None

    @field_validator("file_id")
    @classmethod
    def _valid_file_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle-file")

    @field_validator("path")
    @classmethod
    def _valid_path(cls, value: str) -> str:
        return _validate_payload_path(value)

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        if not value or value != value.strip() or "\x00" in value:
            raise ValueError("bundle file roles must be non-empty canonical labels")
        try:
            value.encode("utf-8")
        except UnicodeError as exc:
            raise ValueError("bundle file roles must contain valid Unicode") from exc
        return value

    @field_validator("media_type")
    @classmethod
    def _valid_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE.fullmatch(value):
            raise ValueError(
                "bundle media types must be lowercase canonical MIME types"
            )
        return value

    @field_validator("size")
    @classmethod
    def _valid_size(cls, value: int) -> int:
        if value < 0:
            raise ValueError("bundle file size cannot be negative")
        return value

    @field_validator("sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("record_count")
    @classmethod
    def _valid_record_count(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("bundle record count cannot be negative")
        return value

    @model_validator(mode="after")
    def _consistent_identity(self) -> Self:
        uses_jsonl = _uses_jsonl_contract(
            path=self.path,
            media_type=self.media_type,
            record_count=self.record_count,
        )
        if uses_jsonl and self.record_count is None:
            raise ValueError("JSONL payloads require an exact record_count")
        payload = _file_identity_payload(
            path=self.path,
            role=self.role,
            media_type=self.media_type,
            size=self.size,
            sha256=self.sha256,
            record_count=self.record_count,
        )
        if self.file_id != derive_id("bundle-file", payload):
            raise ValueError("bundle file identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        path: str,
        data: bytes,
        role: str,
        media_type: str,
        record_count: int | None,
    ) -> Self:
        if type(data) is not bytes:
            raise TypeError("finished bundle payloads must be exact bytes")
        payload = _file_identity_payload(
            path=path,
            role=role,
            media_type=media_type,
            size=len(data),
            sha256=sha256_digest(data),
            record_count=record_count,
        )
        return cls(file_id=derive_id("bundle-file", payload), **payload)


def _validated_file_tuple(files: Sequence[BundleFile]) -> tuple[BundleFile, ...]:
    checked = tuple(
        BundleFile.from_json_bytes(file.canonical_bytes()) for file in files
    )
    paths = tuple(file.path for file in checked)
    if paths != tuple(sorted(paths)):
        raise ValueError("bundle files must be sorted by exact path")
    if paths != _MINIMAL_PAYLOAD_PATHS:
        raise ValueError(
            "minimal-v1 requires exactly the four declared payload paths; "
            f"expected={list(_MINIMAL_PAYLOAD_PATHS)!r}, actual={list(paths)!r}"
        )

    exact_paths: set[str] = set()
    portable_paths: dict[str, str] = {}
    for file in checked:
        if file.path in exact_paths:
            raise ValueError(f"duplicate bundle path {file.path!r}")
        exact_paths.add(file.path)
        parts = file.path.split("/")
        for index in range(1, len(parts) + 1):
            entry = "/".join(parts[:index])
            portable = _portable_path_key(entry)
            previous = portable_paths.get(portable)
            if previous is not None and previous != entry:
                raise ValueError(
                    f"bundle paths collide by case or Unicode: "
                    f"{previous!r} and {entry!r}"
                )
            portable_paths[portable] = entry

    for path in exact_paths:
        parts = path.split("/")
        for index in range(1, len(parts)):
            parent = "/".join(parts[:index])
            if parent in exact_paths:
                raise ValueError(
                    f"bundle path {parent!r} is both a file and a directory"
                )
    by_path = {file.path: file for file in checked}
    for path, (role, media_type) in _MINIMAL_PAYLOAD_CONTRACT.items():
        file = by_path[path]
        if file.role != role or file.media_type != media_type:
            raise ValueError(
                f"minimal-v1 descriptor mismatch for {path!r}: "
                f"expected role={role!r}, media_type={media_type!r}"
            )
        expected_count_presence = path in _MINIMAL_JSONL_PATHS
        if (file.record_count is not None) != expected_count_presence:
            raise ValueError(f"minimal-v1 record_count presence mismatch for {path!r}")

    train_count = by_path[TRAIN_PATH].record_count
    evaluation_count = by_path[EVALUATION_PATH].record_count
    provenance_count = by_path[PROVENANCE_PATH].record_count
    if train_count is None or train_count <= 0:
        raise ValueError("finished bundle training partition cannot be empty")
    if evaluation_count is None or provenance_count is None:
        raise ValueError("minimal-v1 JSONL descriptors require record counts")
    if provenance_count != train_count + evaluation_count:
        raise ValueError(
            "row provenance count must equal train plus evaluation row counts"
        )
    return checked


def _derive_content_root(files: Sequence[BundleFile]) -> str:
    return canonical_digest(
        {
            "schema_version": _CONTENT_ROOT_SCHEMA,
            "files": [file.model_dump(mode="json") for file in files],
        }
    )


def _manifest_identity_payload(
    *,
    dataset_snapshot_id: str,
    validation_report_id: str,
    content_root_sha256: str,
    files: Sequence[BundleFile],
) -> dict[str, Any]:
    return {
        "schema_version": _MANIFEST_SCHEMA,
        "dataset_snapshot_id": dataset_snapshot_id,
        "validation_report_id": validation_report_id,
        "content_root_sha256": content_root_sha256,
        "files": tuple(files),
    }


class FinishedBundleManifest(_StrictFinishedModel):
    """The deterministic inventory and semantic identity of a finished bundle."""

    schema_version: Literal["veriformis.finished-bundle-manifest/v1"]
    bundle_id: str
    dataset_snapshot_id: str
    validation_report_id: str
    content_root_sha256: str
    files: tuple[BundleFile, ...]

    @field_validator("bundle_id")
    @classmethod
    def _valid_bundle_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle")

    @field_validator("dataset_snapshot_id", "validation_report_id")
    @classmethod
    def _valid_bound_identity(cls, value: str) -> str:
        return validate_id(value)

    @field_validator("content_root_sha256")
    @classmethod
    def _valid_content_root(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _consistent_identity(self) -> Self:
        checked_files = _validated_file_tuple(self.files)
        if checked_files != self.files:
            raise ValueError("bundle manifest files do not round-trip exactly")
        expected_root = _derive_content_root(checked_files)
        if self.content_root_sha256 != expected_root:
            raise ValueError("bundle content root mismatch")
        payload = _manifest_identity_payload(
            dataset_snapshot_id=self.dataset_snapshot_id,
            validation_report_id=self.validation_report_id,
            content_root_sha256=self.content_root_sha256,
            files=checked_files,
        )
        if self.bundle_id != derive_id("bundle", payload):
            raise ValueError("finished bundle identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        dataset_snapshot_id: str,
        validation_report_id: str,
        files: Sequence[BundleFile],
    ) -> Self:
        checked_files = _validated_file_tuple(tuple(files))
        content_root = _derive_content_root(checked_files)
        payload = _manifest_identity_payload(
            dataset_snapshot_id=dataset_snapshot_id,
            validation_report_id=validation_report_id,
            content_root_sha256=content_root,
            files=checked_files,
        )
        return cls(bundle_id=derive_id("bundle", payload), **payload)


def _attestation_identity_payload(
    *,
    bundle_id: str,
    dataset_snapshot_id: str,
    validation_report_id: str,
    manifest_sha256: str,
    content_root_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": _ATTESTATION_SCHEMA,
        "bundle_id": bundle_id,
        "dataset_snapshot_id": dataset_snapshot_id,
        "validation_report_id": validation_report_id,
        "manifest_sha256": manifest_sha256,
        "content_root_sha256": content_root_sha256,
    }


class BundleAttestation(_StrictFinishedModel):
    """Detached binding between exact manifest bytes and their content root."""

    schema_version: Literal["veriformis.bundle-attestation/v1"]
    attestation_id: str
    bundle_id: str
    dataset_snapshot_id: str
    validation_report_id: str
    manifest_sha256: str
    content_root_sha256: str

    @field_validator("attestation_id")
    @classmethod
    def _valid_attestation_id(cls, value: str) -> str:
        return validate_id(value, kind="attestation")

    @field_validator("bundle_id")
    @classmethod
    def _valid_bundle_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle")

    @field_validator("dataset_snapshot_id", "validation_report_id")
    @classmethod
    def _valid_bound_identity(cls, value: str) -> str:
        return validate_id(value)

    @field_validator("manifest_sha256", "content_root_sha256")
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _consistent_identity(self) -> Self:
        payload = _attestation_identity_payload(
            bundle_id=self.bundle_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            validation_report_id=self.validation_report_id,
            manifest_sha256=self.manifest_sha256,
            content_root_sha256=self.content_root_sha256,
        )
        if self.attestation_id != derive_id("attestation", payload):
            raise ValueError("bundle attestation identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        manifest: FinishedBundleManifest,
        manifest_sha256: str,
    ) -> Self:
        checked_manifest = FinishedBundleManifest.from_json_bytes(
            manifest.canonical_bytes()
        )
        payload = _attestation_identity_payload(
            bundle_id=checked_manifest.bundle_id,
            dataset_snapshot_id=checked_manifest.dataset_snapshot_id,
            validation_report_id=checked_manifest.validation_report_id,
            manifest_sha256=manifest_sha256,
            content_root_sha256=checked_manifest.content_root_sha256,
        )
        return cls(attestation_id=derive_id("attestation", payload), **payload)


def _verification_identity_payload(
    *,
    bundle_id: str,
    dataset_snapshot_id: str,
    validation_report_id: str,
    manifest_sha256: str,
    content_root_sha256: str,
    trust_grade: Literal["self_consistent", "external_digest"],
    payload_file_count: int,
    declared_record_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": _VERIFICATION_SCHEMA,
        "bundle_id": bundle_id,
        "dataset_snapshot_id": dataset_snapshot_id,
        "validation_report_id": validation_report_id,
        "manifest_sha256": manifest_sha256,
        "content_root_sha256": content_root_sha256,
        "trust_grade": trust_grade,
        "payload_file_count": payload_file_count,
        "declared_record_count": declared_record_count,
    }


class VerificationResult(_StrictFinishedModel):
    """Successful verification evidence.  Invalid bundles raise instead."""

    schema_version: Literal["veriformis.bundle-verification/v1"]
    verification_id: str
    bundle_id: str
    dataset_snapshot_id: str
    validation_report_id: str
    manifest_sha256: str
    content_root_sha256: str
    trust_grade: Literal["self_consistent", "external_digest"]
    payload_file_count: int
    declared_record_count: int

    @field_validator("verification_id")
    @classmethod
    def _valid_verification_id(cls, value: str) -> str:
        return validate_id(value, kind="verification")

    @field_validator("bundle_id")
    @classmethod
    def _valid_bundle_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle")

    @field_validator("dataset_snapshot_id", "validation_report_id")
    @classmethod
    def _valid_bound_identity(cls, value: str) -> str:
        return validate_id(value)

    @field_validator("manifest_sha256", "content_root_sha256")
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("payload_file_count", "declared_record_count")
    @classmethod
    def _valid_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("verification counts cannot be negative")
        return value

    @model_validator(mode="after")
    def _consistent_identity(self) -> Self:
        payload = _verification_identity_payload(
            bundle_id=self.bundle_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            validation_report_id=self.validation_report_id,
            manifest_sha256=self.manifest_sha256,
            content_root_sha256=self.content_root_sha256,
            trust_grade=self.trust_grade,
            payload_file_count=self.payload_file_count,
            declared_record_count=self.declared_record_count,
        )
        if self.verification_id != derive_id("verification", payload):
            raise ValueError("bundle verification identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        bundle_id: str,
        dataset_snapshot_id: str,
        validation_report_id: str,
        manifest_sha256: str,
        content_root_sha256: str,
        trust_grade: Literal["self_consistent", "external_digest"],
        payload_file_count: int,
        declared_record_count: int,
    ) -> Self:
        payload = _verification_identity_payload(
            bundle_id=bundle_id,
            dataset_snapshot_id=dataset_snapshot_id,
            validation_report_id=validation_report_id,
            manifest_sha256=manifest_sha256,
            content_root_sha256=content_root_sha256,
            trust_grade=trust_grade,
            payload_file_count=payload_file_count,
            declared_record_count=declared_record_count,
        )
        return cls(verification_id=derive_id("verification", payload), **payload)


@dataclass(frozen=True, slots=True)
class BundlePublicationReceipt:
    """Local receipt for one visible bundle and its exact workspace artifacts."""

    bundle_path: Path
    manifest: FinishedBundleManifest
    attestation: BundleAttestation
    manifest_bytes: bytes
    attestation_bytes: bytes
    manifest_sha256: str
    verification: VerificationResult
    durability_warning: str | None

    @property
    def bundle_id(self) -> str:
        return self.verification.bundle_id

    @property
    def trust_grade(self) -> Literal["self_consistent", "external_digest"]:
        return self.verification.trust_grade

    @property
    def payload_file_count(self) -> int:
        return self.verification.payload_file_count

    @property
    def declared_record_count(self) -> int:
        return self.verification.declared_record_count


def _copy_payload_inputs(
    files: Mapping[str, bytes],
    *,
    roles: Mapping[str, str],
    media_types: Mapping[str, str],
    record_counts: Mapping[str, int] | None,
    dataset_snapshot_id: str,
    validation_report_id: str,
) -> tuple[dict[str, bytes], tuple[BundleFile, ...]]:
    if not isinstance(files, Mapping):
        raise TypeError("files must be a mapping of relative paths to exact bytes")
    if not isinstance(roles, Mapping) or not isinstance(media_types, Mapping):
        raise TypeError("roles and media_types must be mappings")
    if record_counts is not None and not isinstance(record_counts, Mapping):
        raise TypeError("record_counts must be a mapping when provided")

    paths = tuple(files.keys())
    if any(not isinstance(path, str) for path in paths):
        raise TypeError("finished bundle paths must be strings")
    path_set = set(paths)
    expected_paths = set(_MINIMAL_PAYLOAD_PATHS)
    if path_set != expected_paths:
        raise FinishedBundleError(
            "minimal-v1 requires exactly the four declared payload paths; "
            f"missing={sorted(expected_paths - path_set)!r}, "
            f"extra={sorted(path_set - expected_paths)!r}"
        )
    expected_roles = {
        path: contract[0] for path, contract in _MINIMAL_PAYLOAD_CONTRACT.items()
    }
    expected_media_types = {
        path: contract[1] for path, contract in _MINIMAL_PAYLOAD_CONTRACT.items()
    }
    if dict(roles) != expected_roles:
        raise FinishedBundleError(
            "minimal-v1 roles must match the exact declared payload mapping"
        )
    if dict(media_types) != expected_media_types:
        raise FinishedBundleError(
            "minimal-v1 media types must match the exact declared payload mapping"
        )
    if record_counts is None:
        raise FinishedBundleError(
            "minimal-v1 requires exact record counts for every JSONL payload"
        )
    counts = dict(record_counts)
    if set(counts) != _MINIMAL_JSONL_PATHS:
        raise FinishedBundleError(
            "record_counts must describe exactly train, evaluation, and provenance"
        )

    copied: dict[str, bytes] = {}
    descriptors: list[BundleFile] = []
    for path in sorted(paths):
        data = files[path]
        if type(data) is not bytes:
            raise TypeError("finished bundle payloads must be exact bytes")
        if path in _MINIMAL_JSONL_PATHS:
            observed_count = _canonical_jsonl_record_count(data, label=path)
            if type(counts[path]) is not int or counts[path] != observed_count:
                raise FinishedBundleError(
                    f"record count mismatch for {path!r}: "
                    f"declared {counts[path]!r}, found {observed_count}"
                )
        copied[path] = data
        descriptors.append(
            BundleFile.create(
                path=path,
                data=data,
                role=roles[path],
                media_type=media_types[path],
                record_count=counts.get(path),
            )
        )
    checked_descriptors = _validated_file_tuple(tuple(descriptors))
    _require_passing_validation_report(
        copied[VALIDATION_PATH],
        dataset_snapshot_id=dataset_snapshot_id,
        validation_report_id=validation_report_id,
        payload_bindings={
            descriptor.path: (
                descriptor.sha256,
                descriptor.size,
                descriptor.record_count,
                descriptor.role,
                descriptor.media_type,
            )
            for descriptor in checked_descriptors
            if descriptor.path in _MINIMAL_JSONL_PATHS
            and descriptor.record_count is not None
        },
        error_type=FinishedBundleError,
    )
    return copied, checked_descriptors


def _prepare_finished_bundle(
    files: Mapping[str, bytes],
    *,
    roles: Mapping[str, str],
    media_types: Mapping[str, str],
    record_counts: Mapping[str, int] | None,
    dataset_snapshot_id: str,
    validation_report_id: str,
) -> tuple[
    dict[str, bytes],
    FinishedBundleManifest,
    BundleAttestation,
    bytes,
    bytes,
]:
    copied, descriptors = _copy_payload_inputs(
        files,
        roles=roles,
        media_types=media_types,
        record_counts=record_counts,
        dataset_snapshot_id=dataset_snapshot_id,
        validation_report_id=validation_report_id,
    )
    manifest = FinishedBundleManifest.create(
        dataset_snapshot_id=dataset_snapshot_id,
        validation_report_id=validation_report_id,
        files=descriptors,
    )
    manifest_bytes = manifest.canonical_bytes()
    attestation = BundleAttestation.create(
        manifest=manifest,
        manifest_sha256=sha256_digest(manifest_bytes),
    )
    attestation_bytes = attestation.canonical_bytes()
    return copied, manifest, attestation, manifest_bytes, attestation_bytes


def build_finished_bundle(
    files: Mapping[str, bytes],
    *,
    roles: Mapping[str, str],
    media_types: Mapping[str, str],
    record_counts: Mapping[str, int] | None = None,
    dataset_snapshot_id: str,
    validation_report_id: str,
) -> tuple[FinishedBundleManifest, BundleAttestation]:
    """Build deterministic metadata for one validated minimal-v1 payload set."""
    try:
        _, manifest, attestation, _, _ = _prepare_finished_bundle(
            files,
            roles=roles,
            media_types=media_types,
            record_counts=record_counts,
            dataset_snapshot_id=dataset_snapshot_id,
            validation_report_id=validation_report_id,
        )
        return manifest, attestation
    except FinishedBundleError:
        raise
    except VeriformisError as exc:
        raise FinishedBundleError(str(exc)) from exc
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        raise FinishedBundleError(f"finished bundle preparation failed: {exc}") from exc


def _write_fsync_at(directory_descriptor: int, name: str, data: bytes) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_descriptor)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while sealing finished bundle")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory_descriptor(descriptor: int) -> None:
    os.fsync(descriptor)


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _directory_identity(descriptor: int) -> tuple[int, int]:
    status = os.fstat(descriptor)
    if not stat.S_ISDIR(status.st_mode):
        raise FinishedBundleError("staging descriptor is not a directory")
    return status.st_dev, status.st_ino


def _path_matches_directory_descriptor(path: Path, descriptor: int) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    return (
        stat.S_ISDIR(status.st_mode)
        and not stat.S_ISLNK(status.st_mode)
        and (status.st_dev, status.st_ino) == _directory_identity(descriptor)
    )


def _require_staging_path_identity(path: Path, descriptor: int) -> None:
    if not _path_matches_directory_descriptor(path, descriptor):
        raise FinishedBundleError(
            "finished bundle staging path changed identity during publication"
        )


def _name_matches_directory_descriptor(
    parent_descriptor: int,
    name: str,
    descriptor: int,
) -> bool:
    try:
        status = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return False
    return (
        stat.S_ISDIR(status.st_mode)
        and not stat.S_ISLNK(status.st_mode)
        and (status.st_dev, status.st_ino) == _directory_identity(descriptor)
    )


def _remove_directory_contents_anchored(descriptor: int) -> None:
    """Remove only entries reached through an already verified directory fd."""
    for name in os.listdir(descriptor):
        try:
            status = os.stat(
                name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        if stat.S_ISDIR(status.st_mode) and not stat.S_ISLNK(status.st_mode):
            child_descriptor = os.open(name, _directory_flags(), dir_fd=descriptor)
            try:
                _remove_directory_contents_anchored(child_descriptor)
            finally:
                os.close(child_descriptor)
            try:
                os.rmdir(name, dir_fd=descriptor)
            except FileNotFoundError:
                continue
        else:
            try:
                os.unlink(name, dir_fd=descriptor)
            except FileNotFoundError:
                continue


def _cleanup_staging_directory(path: Path, descriptor: int) -> None:
    """Clean the opened staging tree without following a replaced path name."""
    if not _path_matches_directory_descriptor(path, descriptor):
        _emit_runtime_warning(
            "refused to clean a replaced or moved finished-bundle staging path",
            stacklevel=3,
        )
        return
    try:
        _remove_directory_contents_anchored(descriptor)
    except OSError as exc:
        _emit_runtime_warning(
            f"could not clean finished-bundle staging directory contents: {exc}",
            stacklevel=3,
        )
        return

    try:
        parent_descriptor = os.open(path.parent, _directory_flags())
    except OSError as exc:
        _emit_runtime_warning(
            f"could not open finished-bundle staging parent for cleanup: {exc}",
            stacklevel=3,
        )
        return
    try:
        if not _name_matches_directory_descriptor(
            parent_descriptor,
            path.name,
            descriptor,
        ):
            _emit_runtime_warning(
                "refused to remove a replaced or moved finished-bundle staging path",
                stacklevel=3,
            )
            return
        try:
            os.rmdir(path.name, dir_fd=parent_descriptor)
        except FileNotFoundError:
            return
    except OSError as exc:
        _emit_runtime_warning(
            f"could not remove finished-bundle staging directory: {exc}",
            stacklevel=3,
        )
    finally:
        os.close(parent_descriptor)


def _payload_parent_descriptors(
    staging_descriptor: int,
    paths: Sequence[str],
) -> dict[str, int]:
    """Create and retain anchored descriptors for every payload directory."""
    descriptors: dict[str, int] = {"": os.dup(staging_descriptor)}
    try:
        for path in paths:
            parts = path.split("/")[:-1]
            parent_key = ""
            for part in parts:
                child_key = f"{parent_key}/{part}" if parent_key else part
                if child_key in descriptors:
                    parent_key = child_key
                    continue
                parent_descriptor = descriptors[parent_key]
                try:
                    os.mkdir(part, 0o700, dir_fd=parent_descriptor)
                except FileExistsError:
                    pass
                child_descriptor = os.open(
                    part,
                    _directory_flags(),
                    dir_fd=parent_descriptor,
                )
                status = os.fstat(child_descriptor)
                if not stat.S_ISDIR(status.st_mode):
                    os.close(child_descriptor)
                    raise FinishedBundleError(
                        f"payload parent {child_key!r} is not a directory"
                    )
                descriptors[child_key] = child_descriptor
                parent_key = child_key
        return descriptors
    except BaseException:
        for descriptor in descriptors.values():
            os.close(descriptor)
        raise


def _rename_no_replace(
    source: Path,
    target: Path,
    *,
    source_descriptor: int,
) -> None:
    """Atomically publish one directory while refusing an existing target."""
    if source.parent != target.parent:
        raise FinishedBundleError(
            "finished bundle staging and target must share one parent"
        )
    parent_descriptor = os.open(source.parent, _directory_flags())
    try:
        if not _name_matches_directory_descriptor(
            parent_descriptor,
            source.name,
            source_descriptor,
        ):
            raise FinishedBundleError(
                "finished bundle staging path changed identity during publication"
            )

        if sys.platform == "darwin":
            libc = ctypes.CDLL(None, use_errno=True)
            renameatx = libc.renameatx_np
            renameatx.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            renameatx.restype = ctypes.c_int
            result = renameatx(
                parent_descriptor,
                os.fsencode(source.name),
                parent_descriptor,
                os.fsencode(target.name),
                0x00000004,  # RENAME_EXCL
            )
        elif sys.platform.startswith("linux"):
            libc = ctypes.CDLL(None, use_errno=True)
            renameat2 = getattr(libc, "renameat2", None)
            if renameat2 is None:
                raise OSError(
                    errno.ENOTSUP,
                    "atomic no-replace directory rename is unavailable",
                    os.fspath(target),
                )
            renameat2.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            renameat2.restype = ctypes.c_int
            result = renameat2(
                parent_descriptor,
                os.fsencode(source.name),
                parent_descriptor,
                os.fsencode(target.name),
                1,
            )
        elif sys.platform == "win32":
            move_file = ctypes.windll.kernel32.MoveFileExW
            move_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
            move_file.restype = ctypes.c_int
            result = move_file(os.fspath(source), os.fspath(target), 0)
            if result == 0:
                win_error = ctypes.get_last_error()
                if win_error in (80, 183):
                    raise FileExistsError(
                        errno.EEXIST,
                        "finished bundle target already exists",
                        os.fspath(target),
                    )
                raise OSError(
                    win_error,
                    "finished bundle rename failed",
                    os.fspath(target),
                )
            result = 0
        else:
            raise OSError(
                errno.ENOTSUP,
                "atomic no-replace directory rename is unavailable",
                os.fspath(target),
            )

        if result != 0:
            error_number = ctypes.get_errno()
            if error_number in (errno.EEXIST, errno.ENOTEMPTY):
                raise FileExistsError(
                    error_number,
                    "finished bundle target already exists",
                    os.fspath(target),
                )
            raise OSError(error_number, os.strerror(error_number), os.fspath(target))
        if not _name_matches_directory_descriptor(
            parent_descriptor,
            target.name,
            source_descriptor,
        ):
            raise FinishedBundleError(
                "published bundle does not match the verified staging directory"
            )
    finally:
        os.close(parent_descriptor)


def _inject(
    failure_injector: Callable[[str], None] | None,
    point: str,
) -> None:
    if failure_injector is not None:
        failure_injector(point)


def _emit_runtime_warning(message: str, *, stacklevel: int = 2) -> None:
    """Emit a warning without allowing warning filters to change control flow."""
    with warnings.catch_warnings():
        warnings.simplefilter("always", RuntimeWarning)
        warnings.warn(
            message,
            RuntimeWarning,
            stacklevel=stacklevel,
        )


def write_finished_bundle(
    target_dir: str | os.PathLike[str],
    files: Mapping[str, bytes],
    *,
    roles: Mapping[str, str],
    media_types: Mapping[str, str],
    record_counts: Mapping[str, int] | None = None,
    dataset_snapshot_id: str,
    validation_report_id: str,
    failure_injector: Callable[[str], None] | None = None,
    pre_publish_guard: Callable[[], None] | None = None,
) -> BundlePublicationReceipt:
    """Seal, independently verify, and atomically publish a finished bundle.

    The target must not exist.  Every failure before the exclusive rename leaves
    it absent.  The only semantic bytes are the caller's payloads and the two
    deterministic canonical metadata documents.
    """
    try:
        if failure_injector is not None and not callable(failure_injector):
            raise TypeError("failure_injector must be callable")
        if pre_publish_guard is not None and not callable(pre_publish_guard):
            raise TypeError("pre_publish_guard must be callable")
        copied, manifest, attestation, manifest_bytes, attestation_bytes = (
            _prepare_finished_bundle(
                files,
                roles=roles,
                media_types=media_types,
                record_counts=record_counts,
                dataset_snapshot_id=dataset_snapshot_id,
                validation_report_id=validation_report_id,
            )
        )

        target = Path(os.path.abspath(os.fspath(target_dir)))
        if not target.name:
            raise ValueError("finished bundle target must name a directory")
        parent = target.parent
        try:
            parent_status = parent.lstat()
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                errno.ENOENT,
                "finished bundle parent directory does not exist",
                os.fspath(parent),
            ) from exc
        if not stat.S_ISDIR(parent_status.st_mode) or stat.S_ISLNK(
            parent_status.st_mode
        ):
            raise ValueError("finished bundle parent must be a real directory")
        if os.path.lexists(target):
            raise FileExistsError(
                errno.EEXIST,
                "finished bundle target already exists",
                os.fspath(target),
            )

        staged = Path(
            tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=os.fspath(parent))
        )
        created_status = staged.lstat()
        try:
            staging_descriptor = os.open(staged, _directory_flags())
        except BaseException:
            try:
                cleanup_descriptor = os.open(staged, _directory_flags())
            except OSError as cleanup_error:
                _emit_runtime_warning(
                    "could not safely reopen finished-bundle staging directory "
                    f"after open failure: {cleanup_error}",
                    stacklevel=2,
                )
            else:
                try:
                    if _directory_identity(cleanup_descriptor) == (
                        created_status.st_dev,
                        created_status.st_ino,
                    ):
                        _cleanup_staging_directory(staged, cleanup_descriptor)
                    else:
                        _emit_runtime_warning(
                            "refused to clean a replaced finished-bundle staging "
                            "path after open failure",
                            stacklevel=2,
                        )
                finally:
                    os.close(cleanup_descriptor)
            raise
        directory_descriptors: dict[str, int] = {}
        published = False
        try:
            os.fchmod(staging_descriptor, 0o700)
            _require_staging_path_identity(staged, staging_descriptor)
            _inject(failure_injector, "before-write")
            directory_descriptors = _payload_parent_descriptors(
                staging_descriptor,
                tuple(copied),
            )
            for relative_path, data in copied.items():
                parent_path, name = (
                    relative_path.rsplit("/", 1)
                    if "/" in relative_path
                    else ("", relative_path)
                )
                _write_fsync_at(directory_descriptors[parent_path], name, data)
            _inject(failure_injector, "after-payloads")

            _write_fsync_at(staging_descriptor, MANIFEST_NAME, manifest_bytes)
            _inject(failure_injector, "after-manifest")
            _write_fsync_at(staging_descriptor, ATTESTATION_NAME, attestation_bytes)
            _inject(failure_injector, "after-attestation")
            for key in sorted(
                directory_descriptors,
                key=lambda value: 0 if not value else value.count("/") + 1,
                reverse=True,
            ):
                _fsync_directory_descriptor(directory_descriptors[key])

            _require_staging_path_identity(staged, staging_descriptor)
            _inject(failure_injector, "before-verify")
            from veriformis.bundle.verifier import verify_finished_bundle

            try:
                verification = verify_finished_bundle(staged)
            except BundleVerificationError as exc:
                raise FinishedBundleError(
                    f"temporary finished bundle failed verification: {exc}"
                ) from exc
            expected_manifest_sha256 = sha256_digest(manifest_bytes)
            if (
                verification.bundle_id != manifest.bundle_id
                or verification.manifest_sha256 != expected_manifest_sha256
            ):
                raise FinishedBundleError(
                    "independent verification returned the wrong bundle binding"
                )
            if verification.trust_grade != "self_consistent":
                raise FinishedBundleError(
                    "internal seal verification overstated its trust grade"
                )
            _require_staging_path_identity(staged, staging_descriptor)
            _inject(failure_injector, "after-verify")
            if pre_publish_guard is not None:
                pre_publish_guard()
            _inject(failure_injector, "before-rename")
            _rename_no_replace(
                staged,
                target,
                source_descriptor=staging_descriptor,
            )
            published = True
        finally:
            for descriptor in directory_descriptors.values():
                os.close(descriptor)
            if not published:
                _cleanup_staging_directory(staged, staging_descriptor)
            os.close(staging_descriptor)

        durability_warning: str | None = None
        try:
            _fsync_directory(parent)
        except OSError as exc:
            durability_warning = (
                f"finished bundle {target} is visible, but its parent directory "
                f"could not be synced: {exc}"
            )
            _emit_runtime_warning(
                durability_warning,
                stacklevel=2,
            )
        return BundlePublicationReceipt(
            bundle_path=target,
            manifest=manifest,
            attestation=attestation,
            manifest_bytes=manifest_bytes,
            attestation_bytes=attestation_bytes,
            manifest_sha256=sha256_digest(manifest_bytes),
            verification=verification,
            durability_warning=durability_warning,
        )
    except FinishedBundleError:
        raise
    except VeriformisError:
        raise
    except (OSError, TypeError, UnicodeError, ValueError) as exc:
        raise FinishedBundleError(f"finished bundle publication failed: {exc}") from exc


__all__ = [
    "ATTESTATION_NAME",
    "EVALUATION_PATH",
    "MANIFEST_NAME",
    "PROVENANCE_PATH",
    "TRAIN_PATH",
    "VALIDATION_PATH",
    "BundleAttestation",
    "BundleFile",
    "BundlePublicationReceipt",
    "BundleVerificationError",
    "FinishedBundleError",
    "FinishedBundleManifest",
    "VerificationResult",
    "build_finished_bundle",
    "write_finished_bundle",
]
