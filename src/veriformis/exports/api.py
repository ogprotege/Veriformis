"""Typed, non-persisted surface protocol for verified exports.

The ten models in :mod:`veriformis.exports.models` remain the durable evidence
contract.  This module defines bounded request/response shapes used by Python,
CLI, MCP, and the CLI-backed Mac bridge; surface envelopes are transport API,
not additional persisted export evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import PRODUCT_ROW_SCHEMA_KINDS
from veriformis.datasets import RowSet, row_set_from_json_bytes
from veriformis.errors import (
    ExportContractError,
    ExportVerificationError,
    VeriformisError,
)
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports._publication import (
    CancellationCheck,
    ExportPartialPublicationError,
    ExportPublicationOutcome,
    _MAX_EXPORT_TREE_DEPTH,
)
from veriformis.exports.models import (
    EXPORT_RECEIPT_PATH,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportDestinationFileBinding,
    ExportPlan,
    ExportReceipt,
    ExportVerification,
    SourceTrustPolicy,
)
from veriformis.identity import lossless_json_bytes, sha256_digest, validate_id

EXPORT_SURFACE_REQUEST_SCHEMA = "veriformis.export-surface-request/v1"
EXPORT_SURFACE_REQUEST_SCHEMA_V2 = "veriformis.export-surface-request/v2"
EXPORT_SURFACE_RESPONSE_SCHEMA = "veriformis.export-surface-response/v1"
EXPORT_SURFACE_RESPONSE_SCHEMA_V2 = "veriformis.export-surface-response/v2"
EXPORT_DISCOVERY_SCHEMA = "veriformis.export-discovery/v1"
EXPORT_DRY_RUN_PREVIEW_SCHEMA = "veriformis.export-dry-run-preview/v1"

ExportOperation = Literal["discover", "dry_run", "inspect", "execute", "verify"]
ExportResponseStatus = Literal[
    "ok",
    "error",
    "cancelled",
    "visible_partial",
]

_SELECTOR_LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MAX_SURFACE_REQUEST_BYTES = 1024 * 1024
_MAX_SURFACE_RESPONSE_BYTES = 1024 * 1024
_MAX_RUNTIME_PATH_BYTES = 32 * 1024
_MAX_EXECUTABLE_PLAN_RESPONSE_BYTES = 256 * 1024
_MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES = 256 * 1024
_MAX_ERROR_MESSAGE_BYTES = 4096
_MAX_SAMPLE_PAYLOAD_BYTES = 64 * 1024
_SAMPLE_POLICY = "first-row-per-non-empty-partition"
_PREVIEW_LIMIT_OMISSION = "exact-payload-exceeds-preview-limit"
_RESPONSE_BUDGET_OMISSION = "exact-payload-exceeds-response-budget"


def _selector_sort_key(
    selector: tuple[str, int, str | None, int | None],
) -> tuple[str, int, str, int]:
    return (
        selector[0],
        selector[1],
        "" if selector[2] is None else selector[2],
        0 if selector[3] is None else selector[3],
    )


def _bounded_request_bytes(data: bytes, *, label: str) -> bytes:
    if type(data) is not bytes:
        raise ExportContractError(f"{label} must be loaded from exact bytes")
    if len(data) > _MAX_SURFACE_REQUEST_BYTES:
        raise ExportContractError(f"{label} exceeds the export surface request limit")
    return data


def _runtime_path(value: str, *, label: str) -> str:
    if type(value) is not str or not value or "\x00" in value:
        raise ValueError(f"{label} must be a non-empty exact path string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"{label} must contain valid Unicode") from exc
    if len(encoded) > _MAX_RUNTIME_PATH_BYTES:
        raise ValueError(f"{label} exceeds the export surface path limit")
    return value


def _bounded_message(message: str) -> str:
    """Keep runtime text small even when a dependency raises huge detail."""
    encoded = message.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_ERROR_MESSAGE_BYTES:
        return encoded.decode("utf-8")
    prefix = encoded[:_MAX_ERROR_MESSAGE_BYTES].decode("utf-8", errors="ignore")
    return f"{prefix}… [truncated]"


def _bounded_error_message(exc: BaseException) -> str:
    try:
        message = str(exc)
    except Exception:
        message = f"{type(exc).__name__}: message unavailable"
    return _bounded_message(message)


class _ExportSurfaceRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    schema_version: Literal[
        "veriformis.export-surface-request/v1",
        "veriformis.export-surface-request/v2",
    ]
    operation: ExportOperation

    @classmethod
    def from_json_bytes(cls, data: bytes) -> Self:
        try:
            _bounded_request_bytes(data, label=cls.__name__)
            canonical_export_object_from_bytes(data, label=cls.__name__)
            request = cls.model_validate_json(data)
        except (TypeError, ValueError, VeriformisError) as exc:
            raise ExportContractError(f"invalid {cls.__name__}: {exc}") from exc
        if lossless_json_bytes(request.model_dump(mode="json")) != data:
            raise ExportContractError(f"{cls.__name__} does not round-trip exactly")
        return request

    def canonical_bytes(self) -> bytes:
        data = lossless_json_bytes(self.model_dump(mode="json"))
        checked = type(self).from_json_bytes(data)
        if checked != self:
            raise ExportContractError(
                f"{type(self).__name__} does not round-trip exactly"
            )
        return data


class _SelectedExportRequest(_ExportSurfaceRequest):
    schema_version: Literal["veriformis.export-surface-request/v1"]
    bundle: str
    container_id: str
    container_version: int
    consumer_id: str | None
    consumer_profile_version: int | None
    source_trust_policy: SourceTrustPolicy
    expected_manifest_sha256: str | None
    overwrite_policy: Literal["refuse"]

    @field_validator("bundle")
    @classmethod
    def _valid_bundle(cls, value: str) -> str:
        return _runtime_path(value, label="bundle")

    @field_validator("container_id")
    @classmethod
    def _valid_container_id(cls, value: str) -> str:
        if type(value) is not str or _SELECTOR_LABEL.fullmatch(value) is None:
            raise ValueError("container_id must be a lowercase canonical identifier")
        return value

    @field_validator("container_version", "consumer_profile_version")
    @classmethod
    def _valid_versions(cls, value: int | None) -> int | None:
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError("profile versions must be positive exact integers")
        return value

    @field_validator("consumer_id")
    @classmethod
    def _valid_consumer_id(cls, value: str | None) -> str | None:
        if value is not None and (
            type(value) is not str or _SELECTOR_LABEL.fullmatch(value) is None
        ):
            raise ValueError(
                "consumer_id must be null or a lowercase canonical identifier"
            )
        return value

    @field_validator("expected_manifest_sha256")
    @classmethod
    def _valid_manifest_digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError("expected_manifest_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def _closed_selector_and_trust(self) -> Self:
        if (self.consumer_id is None) != (self.consumer_profile_version is None):
            raise ValueError(
                "consumer_id and consumer_profile_version must be present together"
            )
        if (
            self.source_trust_policy == "require_external_digest"
            and self.expected_manifest_sha256 is None
        ):
            raise ValueError(
                "require_external_digest needs expected_manifest_sha256"
            )
        return self


class _SelectedExportRequestV2(_SelectedExportRequest):
    """Selected request with versioned, implementation-validated options."""

    schema_version: Literal["veriformis.export-surface-request/v2"]
    container_options: dict[str, str | bool | int | None]

    @field_validator("container_options")
    @classmethod
    def _valid_container_options(
        cls,
        value: dict[str, str | bool | int | None],
    ) -> dict[str, str | bool | int | None]:
        if type(value) is not dict:
            raise ValueError("container_options must be an exact JSON object")
        for key, item in value.items():
            if type(key) is not str or _SELECTOR_LABEL.fullmatch(key) is None:
                raise ValueError(
                    "container_options keys must be lowercase canonical identifiers"
                )
            if item is not None and type(item) not in {str, bool, int}:
                raise ValueError(
                    "container_options values must be exact strings, booleans, "
                    "integers, or null"
                )
        return dict(value)


class ExportDryRunRequest(_SelectedExportRequest):
    operation: Literal["dry_run"]


class ExportDryRunRequestV2(_SelectedExportRequestV2):
    operation: Literal["dry_run"]


class ExportExecuteRequest(_SelectedExportRequest):
    operation: Literal["execute"]
    destination_root: str
    expected_export_plan_id: str

    @field_validator("destination_root")
    @classmethod
    def _valid_destination(cls, value: str) -> str:
        return _runtime_path(value, label="destination_root")

    @field_validator("expected_export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")


class ExportExecuteRequestV2(_SelectedExportRequestV2):
    operation: Literal["execute"]
    destination_root: str
    expected_export_plan_id: str

    @field_validator("destination_root")
    @classmethod
    def _valid_destination(cls, value: str) -> str:
        return _runtime_path(value, label="destination_root")

    @field_validator("expected_export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")


class ExportVerifyRequest(_SelectedExportRequest):
    operation: Literal["verify"]
    destination_root: str
    expected_export_plan_id: str

    @field_validator("destination_root")
    @classmethod
    def _valid_destination(cls, value: str) -> str:
        return _runtime_path(value, label="destination_root")

    @field_validator("expected_export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")


class ExportVerifyRequestV2(_SelectedExportRequestV2):
    operation: Literal["verify"]
    destination_root: str
    expected_export_plan_id: str

    @field_validator("destination_root")
    @classmethod
    def _valid_destination(cls, value: str) -> str:
        return _runtime_path(value, label="destination_root")

    @field_validator("expected_export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")


class ExportInspectRequest(_ExportSurfaceRequest):
    schema_version: Literal["veriformis.export-surface-request/v1"]
    operation: Literal["inspect"]
    destination_root: str

    @field_validator("destination_root")
    @classmethod
    def _valid_destination(cls, value: str) -> str:
        return _runtime_path(value, label="destination_root")


ExportActionRequest = (
    ExportDryRunRequest
    | ExportDryRunRequestV2
    | ExportInspectRequest
    | ExportExecuteRequest
    | ExportExecuteRequestV2
    | ExportVerifyRequest
    | ExportVerifyRequestV2
)


def export_request_from_json_bytes(
    data: bytes,
    *,
    expected_operation: Literal["dry_run", "inspect", "execute", "verify"],
) -> ExportActionRequest:
    """Strict-load one canonical operation-specific surface request."""
    _bounded_request_bytes(data, label="export surface request")
    try:
        value = canonical_export_object_from_bytes(data, label="export surface request")
    except ExportVerificationError as exc:
        raise ExportContractError(str(exc)) from exc
    observed = value.get("operation")
    if observed != expected_operation:
        raise ExportContractError(
            f"export request operation must be {expected_operation!r}"
        )
    schema_version = value.get("schema_version")
    request_types: dict[
        tuple[str, str],
        type[_ExportSurfaceRequest],
    ] = {
        (EXPORT_SURFACE_REQUEST_SCHEMA, "dry_run"): ExportDryRunRequest,
        (EXPORT_SURFACE_REQUEST_SCHEMA, "inspect"): ExportInspectRequest,
        (EXPORT_SURFACE_REQUEST_SCHEMA, "execute"): ExportExecuteRequest,
        (EXPORT_SURFACE_REQUEST_SCHEMA, "verify"): ExportVerifyRequest,
        (EXPORT_SURFACE_REQUEST_SCHEMA_V2, "dry_run"): ExportDryRunRequestV2,
        (EXPORT_SURFACE_REQUEST_SCHEMA_V2, "execute"): ExportExecuteRequestV2,
        (EXPORT_SURFACE_REQUEST_SCHEMA_V2, "verify"): ExportVerifyRequestV2,
    }
    request_type = request_types.get((str(schema_version), expected_operation))
    if request_type is None:
        raise ExportContractError(
            "unsupported export request schema and operation combination"
        )
    request = request_type.from_json_bytes(data)
    assert isinstance(
        request,
        (
            ExportDryRunRequest,
            ExportDryRunRequestV2,
            ExportInspectRequest,
            ExportExecuteRequest,
            ExportExecuteRequestV2,
            ExportVerifyRequest,
            ExportVerifyRequestV2,
        ),
    )
    return request


@dataclass(frozen=True, slots=True)
class ExportProfileDescriptor:
    """One discoverable internal implementation, without executable hooks."""

    container_profile: ExportContainerProfile
    consumer_profile: ExportConsumerProfile | None
    dependencies: tuple[ExportDependencyBinding, ...]
    supported_row_schemas: tuple[str, ...]
    overwrite_policies: tuple[Literal["refuse"], ...] = ("refuse",)

    def __post_init__(self) -> None:
        try:
            container = ExportContainerProfile.from_json_bytes(
                self.container_profile.canonical_bytes()
            )
            consumer = (
                ExportConsumerProfile.from_json_bytes(
                    self.consumer_profile.canonical_bytes()
                )
                if self.consumer_profile is not None
                else None
            )
            dependencies = tuple(
                ExportDependencyBinding.from_json_bytes(item.canonical_bytes())
                for item in self.dependencies
            )
        except (AttributeError, TypeError, ValueError, VeriformisError) as exc:
            raise ExportContractError(f"invalid export profile descriptor: {exc}") from exc
        if not dependencies:
            raise ExportContractError("export implementation requires dependencies")
        if tuple(item.dependency_id for item in dependencies) != tuple(
            sorted(item.dependency_id for item in dependencies)
        ):
            raise ExportContractError("export implementation dependencies must be sorted")
        if len({item.dependency_id for item in dependencies}) != len(dependencies):
            raise ExportContractError("export implementation dependencies must be unique")
        if len({item.dependency_name for item in dependencies}) != len(dependencies):
            raise ExportContractError(
                "export implementation dependency names must be unique"
            )
        schemas = tuple(self.supported_row_schemas)
        if (
            not schemas
            or schemas != tuple(sorted(schemas))
            or len(schemas) != len(set(schemas))
            or any(item not in PRODUCT_ROW_SCHEMA_KINDS for item in schemas)
        ):
            raise ExportContractError(
                "supported_row_schemas must be non-empty, sorted, unique v1 rows"
            )
        if consumer is not None and not set(schemas).issubset(
            consumer.accepted_row_schemas
        ):
            raise ExportContractError(
                "implementation rows must be accepted by its consumer profile"
            )
        if self.overwrite_policies != ("refuse",):
            raise ExportContractError("verified export overwrite policy is refuse only")
        object.__setattr__(self, "container_profile", container)
        object.__setattr__(self, "consumer_profile", consumer)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(self, "supported_row_schemas", schemas)

    @property
    def selector(self) -> tuple[str, int, str | None, int | None]:
        consumer = self.consumer_profile
        return (
            self.container_profile.container_id,
            self.container_profile.container_version,
            consumer.consumer_id if consumer is not None else None,
            consumer.profile_version if consumer is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "container_profile": self.container_profile.model_dump(mode="json"),
            "consumer_profile": (
                self.consumer_profile.model_dump(mode="json")
                if self.consumer_profile is not None
                else None
            ),
            "dependencies": [
                item.model_dump(mode="json") for item in self.dependencies
            ],
            "overwrite_policies": list(self.overwrite_policies),
            "supported_row_schemas": list(self.supported_row_schemas),
        }


@dataclass(frozen=True, slots=True)
class ExportDiscovery:
    schema_version: Literal["veriformis.export-discovery/v1"]
    profiles: tuple[ExportProfileDescriptor, ...]

    @classmethod
    def create(cls, profiles: tuple[ExportProfileDescriptor, ...]) -> Self:
        ordered = tuple(
            sorted(profiles, key=lambda item: _selector_sort_key(item.selector))
        )
        if len({item.selector for item in ordered}) != len(ordered):
            raise ExportContractError("export discovery contains duplicate selectors")
        return cls(schema_version=EXPORT_DISCOVERY_SCHEMA, profiles=ordered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profiles": [item.to_dict() for item in self.profiles],
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class ExportInspection:
    destination_root: Path
    inspection_scope: Literal["self_described_physical"]
    receipt: ExportReceipt


@dataclass(frozen=True, slots=True)
class ExportVerifiedOutcome:
    destination_root: Path
    receipt: ExportReceipt
    verification: ExportVerification


PreviewOmissionReason = Literal[
    "exact-payload-exceeds-preview-limit",
    "exact-payload-exceeds-response-budget",
]


@dataclass(frozen=True, slots=True)
class _ExportDryRunSample:
    """One immutable exact semantic payload or one whole-row omission."""

    partition: Literal["train", "evaluation"]
    ordinal: int
    payload_sha256: str
    payload_byte_size: int
    canonical_payload_bytes: bytes | None
    omission_reason: PreviewOmissionReason | None

    def __post_init__(self) -> None:
        if type(self.partition) is not str or self.partition not in {
            "train",
            "evaluation",
        }:
            raise ExportContractError("preview sample partition is invalid")
        if type(self.ordinal) is not int or self.ordinal != 0:
            raise ExportContractError(
                "preview samples must use authoritative partition ordinal zero"
            )
        if (
            type(self.payload_sha256) is not str
            or len(self.payload_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.payload_sha256
            )
        ):
            raise ExportContractError("preview sample payload digest is invalid")
        if type(self.payload_byte_size) is not int or self.payload_byte_size < 0:
            raise ExportContractError("preview sample payload size is invalid")

        payload_bytes = self.canonical_payload_bytes
        if payload_bytes is not None:
            if type(payload_bytes) is not bytes:
                raise ExportContractError(
                    "preview sample payload must be immutable canonical bytes"
                )
            try:
                canonical_export_object_from_bytes(
                    payload_bytes,
                    label="export dry-run preview sample",
                )
            except ExportVerificationError as exc:
                raise ExportContractError(str(exc)) from exc
            if (
                len(payload_bytes) != self.payload_byte_size
                or sha256_digest(payload_bytes) != self.payload_sha256
            ):
                raise ExportContractError(
                    "preview sample payload bytes differ from their binding"
                )
            if self.omission_reason is not None:
                raise ExportContractError(
                    "an emitted preview payload cannot have an omission reason"
                )
            return

        if self.omission_reason not in {
            _PREVIEW_LIMIT_OMISSION,
            _RESPONSE_BUDGET_OMISSION,
        }:
            raise ExportContractError(
                "an omitted preview payload requires an exact omission reason"
            )
        if (
            self.omission_reason == _PREVIEW_LIMIT_OMISSION
            and self.payload_byte_size <= _MAX_SAMPLE_PAYLOAD_BYTES
        ):
            raise ExportContractError(
                "preview-limit omission requires a payload above the exact limit"
            )
        if (
            self.omission_reason == _RESPONSE_BUDGET_OMISSION
            and self.payload_byte_size > _MAX_SAMPLE_PAYLOAD_BYTES
        ):
            raise ExportContractError(
                "an over-limit payload must use the preview-limit omission reason"
            )

    def to_dict(self) -> dict[str, Any]:
        payload = (
            canonical_export_object_from_bytes(
                self.canonical_payload_bytes,
                label="export dry-run preview sample",
            )
            if self.canonical_payload_bytes is not None
            else None
        )
        return {
            "omission_reason": self.omission_reason,
            "ordinal": self.ordinal,
            "partition": self.partition,
            "payload": payload,
            "payload_byte_size": self.payload_byte_size,
            "payload_sha256": self.payload_sha256,
        }


def _sample_omitted_for_response_budget(
    sample: _ExportDryRunSample,
) -> _ExportDryRunSample:
    if sample.canonical_payload_bytes is None:
        return sample
    return _ExportDryRunSample(
        partition=sample.partition,
        ordinal=sample.ordinal,
        payload_sha256=sample.payload_sha256,
        payload_byte_size=sample.payload_byte_size,
        canonical_payload_bytes=None,
        omission_reason=_RESPONSE_BUDGET_OMISSION,
    )


@dataclass(frozen=True, slots=True, init=False)
class _ExportDryRunSampleEvidence:
    """Bounded canonical evidence retained for one selected source payload."""

    partition: Literal["train", "evaluation"]
    payload_sha256: str
    payload_byte_size: int
    canonical_payload_bytes: bytes | None

    def __init__(self) -> None:
        raise TypeError(
            "dry-run sample evidence must be derived from canonical payload bytes"
        )

    @classmethod
    def _from_payload_bytes(
        cls,
        *,
        partition: Literal["train", "evaluation"],
        payload_bytes: bytes,
    ) -> Self:
        if type(partition) is not str or partition not in {"train", "evaluation"}:
            raise ExportContractError("preview sample evidence partition is invalid")
        if type(payload_bytes) is not bytes:
            raise ExportContractError(
                "preview sample evidence requires immutable canonical bytes"
            )
        try:
            canonical_export_object_from_bytes(
                payload_bytes,
                label="export dry-run preview sample evidence",
            )
        except ExportVerificationError as exc:
            raise ExportContractError(str(exc)) from exc
        evidence = object.__new__(cls)
        object.__setattr__(evidence, "partition", partition)
        object.__setattr__(
            evidence,
            "payload_sha256",
            sha256_digest(payload_bytes),
        )
        object.__setattr__(evidence, "payload_byte_size", len(payload_bytes))
        object.__setattr__(
            evidence,
            "canonical_payload_bytes",
            (
                bytes(payload_bytes)
                if len(payload_bytes) <= _MAX_SAMPLE_PAYLOAD_BYTES
                else None
            ),
        )
        return evidence


@dataclass(frozen=True, slots=True, init=False)
class ExportDryRunPreview:
    """One non-persisted preview bound to one exact export plan."""

    plan: ExportPlan
    sample_rows: tuple[_ExportDryRunSample, ...]
    _sample_evidence: tuple[_ExportDryRunSampleEvidence, ...]

    def __init__(self) -> None:
        raise TypeError(
            "ExportDryRunPreview must be created from exact plan-bound row evidence"
        )

    @classmethod
    def _from_samples(
        cls,
        *,
        plan: ExportPlan,
        sample_rows: tuple[_ExportDryRunSample, ...],
        sample_evidence: tuple[_ExportDryRunSampleEvidence, ...],
    ) -> Self:
        """Construct only inside the service-owned preview derivation path."""
        preview = object.__new__(cls)
        object.__setattr__(preview, "plan", plan)
        object.__setattr__(preview, "sample_rows", sample_rows)
        object.__setattr__(preview, "_sample_evidence", sample_evidence)
        preview.__post_init__()
        return preview

    def __post_init__(self) -> None:
        try:
            checked_plan = ExportPlan.from_json_bytes(self.plan.canonical_bytes())
        except (
            AttributeError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ) as exc:
            raise ExportContractError(f"invalid dry-run preview plan: {exc}") from exc
        samples = tuple(self.sample_rows)
        evidence = tuple(self._sample_evidence)
        expected_partitions: tuple[str, ...] = (
            ("train", "evaluation")
            if checked_plan.membership_projection.evaluation_record_count
            else ("train",)
        )
        if (
            tuple(sample.partition for sample in samples) != expected_partitions
            or tuple(item.partition for item in evidence) != expected_partitions
            or len(samples) != len(evidence)
        ):
            raise ExportContractError(
                "preview samples must contain ordinal zero for every non-empty "
                "partition in train-then-evaluation order"
            )
        entries = {
            (entry.partition, entry.ordinal): entry
            for entry in checked_plan.membership_projection.entries
        }
        for sample, source in zip(samples, evidence, strict=True):
            if type(sample) is not _ExportDryRunSample:
                raise ExportContractError("preview sample has the wrong runtime type")
            if type(source) is not _ExportDryRunSampleEvidence:
                raise ExportContractError(
                    "preview sample evidence has the wrong runtime type"
                )
            entry = entries.get((sample.partition, sample.ordinal))
            if (
                entry is None
                or entry.payload_sha256 != sample.payload_sha256
                or source.payload_sha256 != sample.payload_sha256
                or source.payload_byte_size != sample.payload_byte_size
            ):
                raise ExportContractError(
                    "preview sample differs from the export plan membership binding"
                )
            candidate = source.canonical_payload_bytes
            if candidate is None:
                if (
                    sample.canonical_payload_bytes is not None
                    or sample.omission_reason != _PREVIEW_LIMIT_OMISSION
                ):
                    raise ExportContractError(
                        "preview-limit omission differs from exact source evidence"
                    )
            elif sample.canonical_payload_bytes is not None:
                if sample.canonical_payload_bytes != candidate:
                    raise ExportContractError(
                        "included preview payload differs from exact source evidence"
                    )
            elif sample.omission_reason != _RESPONSE_BUDGET_OMISSION:
                raise ExportContractError(
                    "within-limit preview omission has an invalid reason"
                )
        object.__setattr__(self, "plan", checked_plan)
        object.__setattr__(self, "sample_rows", samples)
        object.__setattr__(self, "_sample_evidence", evidence)

    @classmethod
    def create(cls, *, plan: ExportPlan, row_set: RowSet) -> Self:
        """Freeze ordinal-zero payloads from the exact row set used by planning."""
        try:
            checked_plan = ExportPlan.from_json_bytes(plan.canonical_bytes())
            dumped = lossless_json_bytes(row_set.model_dump(mode="json"))
            payload = json.loads(dumped.decode("utf-8"))
            if (
                isinstance(payload, dict)
                and payload.get("schema_version")
                == "veriformis.imported-bundle-row-set/v1"
            ):
                from veriformis.bundle.verifier import ImportedBundleRowSet

                checked_row_set = ImportedBundleRowSet.from_dump(payload)
            else:
                checked_row_set = row_set_from_json_bytes(dumped)
        except (AttributeError, TypeError, UnicodeError, ValueError, VeriformisError) as exc:
            raise ExportContractError(
                f"invalid dry-run preview source evidence: {exc}"
            ) from exc
        if (
            checked_row_set.row_set_id != checked_plan.row_set_id
            or checked_row_set.row_schema != checked_plan.row_schema
            or checked_row_set.train_row_count
            != checked_plan.membership_projection.train_record_count
            or checked_row_set.evaluation_row_count
            != checked_plan.membership_projection.evaluation_record_count
        ):
            raise ExportContractError(
                "dry-run preview row set differs from its exact export plan"
            )

        selected = [("train", checked_row_set.train_rows[0])]
        if checked_row_set.evaluation_rows:
            selected.append(("evaluation", checked_row_set.evaluation_rows[0]))
        evidence: list[_ExportDryRunSampleEvidence] = []
        for partition, row in selected:
            payload_bytes = lossless_json_bytes(row.payload)
            evidence.append(
                _ExportDryRunSampleEvidence._from_payload_bytes(
                    partition=partition,  # type: ignore[arg-type]
                    payload_bytes=payload_bytes,
                )
            )
        return _derive_dry_run_preview_from_evidence(
            plan=checked_plan,
            evidence=tuple(evidence),
        )

    @property
    def destination_files(self) -> tuple[str, ...]:
        return tuple(
            sorted((*[item.path for item in self.plan.file_plans], EXPORT_RECEIPT_PATH))
        )

    @property
    def destination_directories(self) -> tuple[str, ...]:
        directories: set[str] = set()
        for path in self.destination_files:
            parts = path.split("/")
            directories.update(
                "/".join(parts[:index]) for index in range(1, len(parts))
            )
        return tuple(sorted(directories))

    def strict_copy(self) -> Self:
        checked = _derive_dry_run_preview_from_evidence(
            plan=ExportPlan.from_json_bytes(self.plan.canonical_bytes()),
            evidence=tuple(self._sample_evidence),
        )
        if self.sample_rows != checked.sample_rows:
            raise ExportContractError(
                "dry-run preview omission state differs from its exact source evidence"
            )
        return checked

    def to_dict(self) -> dict[str, Any]:
        return _dry_run_preview_dict_from_validated(self.strict_copy())


def _derive_dry_run_preview_from_evidence(
    *,
    plan: ExportPlan,
    evidence: tuple[_ExportDryRunSampleEvidence, ...],
) -> ExportDryRunPreview:
    samples = tuple(
        _ExportDryRunSample(
            partition=item.partition,
            ordinal=0,
            payload_sha256=item.payload_sha256,
            payload_byte_size=item.payload_byte_size,
            canonical_payload_bytes=item.canonical_payload_bytes,
            omission_reason=(
                _PREVIEW_LIMIT_OMISSION
                if item.canonical_payload_bytes is None
                else None
            ),
        )
        for item in evidence
    )
    preview = ExportDryRunPreview._from_samples(
        plan=plan,
        sample_rows=samples,
        sample_evidence=evidence,
    )
    return _fit_dry_run_preview_response_budget(preview)


def _dry_run_preview_dict_from_validated(
    preview: ExportDryRunPreview,
) -> dict[str, Any]:
    return {
        "container_profile_id": preview.plan.container_profile.container_profile_id,
        "destination_tree": {
            "directories": list(preview.destination_directories),
            "files": list(preview.destination_files),
        },
        "export_plan_id": preview.plan.export_plan_id,
        "maximum_sample_payload_bytes": _MAX_SAMPLE_PAYLOAD_BYTES,
        "row_schema": preview.plan.row_schema,
        "row_set_id": preview.plan.row_set_id,
        "sample_policy": _SAMPLE_POLICY,
        "sample_rows": [sample.to_dict() for sample in preview.sample_rows],
        "schema_version": EXPORT_DRY_RUN_PREVIEW_SCHEMA,
    }


class ExportOperationCancelled(Exception):
    """A cooperative surface cancellation observed before publication."""


_EXPORT_SURFACE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ExportPartialPublicationError,
    ExportOperationCancelled,
    VeriformisError,
    OSError,
    RecursionError,
    UnicodeError,
    ValueError,
    TypeError,
)


def _file_plan_summary(plan: ExportPlan) -> list[dict[str, Any]]:
    return [
        {
            "expected_byte_size": item.expected_byte_size,
            "expected_sha256": item.expected_sha256,
            "file_plan_id": item.file_plan_id,
            "media_type": item.media_type,
            "membership_scope": item.membership_scope,
            "path": item.path,
            "record_count": item.record_count,
            "role": item.role,
            "semantic_content_sha256": item.semantic_content_sha256,
        }
        for item in plan.file_plans
    ]


def _canonical_model_sha256(model: BaseModel) -> str:
    """Hash one already-validated model without invoking its strict loader."""
    return sha256_digest(lossless_json_bytes(model.model_dump(mode="json")))


def _export_plan_summary_from_validated(plan: ExportPlan) -> dict[str, Any]:
    """Project one validated plan into the bounded transport summary."""
    projection = plan.membership_projection
    return {
        "canonical_sha256": _canonical_model_sha256(plan),
        "consumer_profile_id": (
            plan.consumer_profile.consumer_profile_id
            if plan.consumer_profile is not None
            else None
        ),
        "container_profile_id": plan.container_profile.container_profile_id,
        "evaluation_record_count": projection.evaluation_record_count,
        "export_plan_id": plan.export_plan_id,
        "files": _file_plan_summary(plan),
        "membership_projection_id": projection.membership_projection_id,
        "overwrite_policy": plan.overwrite_policy,
        "row_schema": plan.row_schema,
        "row_set_id": plan.row_set_id,
        "source_bundle_id": plan.source_bundle_id,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "source_trust_grade": plan.source_trust_grade,
        "source_trust_policy": plan.source_trust_policy,
        "total_record_count": projection.total_record_count,
        "train_record_count": projection.train_record_count,
    }


def export_plan_summary(plan: ExportPlan) -> dict[str, Any]:
    checked = ExportPlan.from_json_bytes(plan.canonical_bytes())
    return _export_plan_summary_from_validated(checked)


def _export_receipt_summary_from_validated(
    receipt: ExportReceipt,
) -> dict[str, Any]:
    """Project one validated receipt without a second strict reload."""
    return {
        "canonical_sha256": _canonical_model_sha256(receipt),
        "export_plan_id": receipt.export_plan_id,
        "export_receipt_id": receipt.export_receipt_id,
        "files": [item.model_dump(mode="json") for item in receipt.files],
        "output_content_root_sha256": receipt.output_content_root_sha256,
    }


def export_receipt_summary(receipt: ExportReceipt) -> dict[str, Any]:
    checked = ExportReceipt.from_json_bytes(receipt.canonical_bytes())
    return _export_receipt_summary_from_validated(checked)


def _export_verification_summary_from_validated(
    verification: ExportVerification,
) -> dict[str, Any]:
    """Project one validated verification without a second strict reload."""
    return {
        **verification.model_dump(mode="json"),
        "canonical_sha256": _canonical_model_sha256(verification),
    }


def export_verification_summary(
    verification: ExportVerification,
) -> dict[str, Any]:
    checked = ExportVerification.from_json_bytes(verification.canonical_bytes())
    return _export_verification_summary_from_validated(checked)


def export_discovery_response(discovery: ExportDiscovery) -> dict[str, Any]:
    return _response("discover", result=discovery.to_dict())


def export_dry_run_response(plan: ExportPlan) -> dict[str, Any]:
    """Return the legacy v1 plan-only response."""
    return _response("dry_run", result={"plan": export_plan_summary(plan)})


def export_dry_run_preview_response(
    preview: ExportDryRunPreview,
) -> dict[str, Any]:
    """Return the v2 dry-run response with one plan-bound exact preview."""
    if type(preview) is not ExportDryRunPreview:
        raise ExportContractError("dry-run preview has the wrong runtime type")
    checked = preview.strict_copy()
    return _export_dry_run_preview_response_from_validated(checked)


def _export_dry_run_preview_response_from_validated(
    preview: ExportDryRunPreview,
) -> dict[str, Any]:
    """Project one already validated, response-budgeted preview."""
    return _response(
        "dry_run",
        result={
            "plan": export_plan_summary(preview.plan),
            "preview": _dry_run_preview_dict_from_validated(preview),
        },
        schema_version=EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    )


def _dry_run_preview_response_size(preview: ExportDryRunPreview) -> int:
    response = _export_dry_run_preview_response_from_validated(preview)
    return len(export_response_json(response).encode("ascii"))


def _fit_dry_run_preview_response_budget(
    preview: ExportDryRunPreview,
) -> ExportDryRunPreview:
    """Omit whole candidate payloads until the exact v2 response is bounded."""
    checked = preview
    if _dry_run_preview_response_size(checked) <= _MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES:
        return checked

    samples = list(checked.sample_rows)
    # Keep deterministic train-then-evaluation ordering while preferring the
    # train sample when only one complete payload fits.
    for partition in ("evaluation", "train"):
        for index, sample in enumerate(samples):
            if (
                sample.partition == partition
                and sample.canonical_payload_bytes is not None
            ):
                samples[index] = _sample_omitted_for_response_budget(sample)
                break
        checked = ExportDryRunPreview._from_samples(
            plan=checked.plan,
            sample_rows=tuple(samples),
            sample_evidence=checked._sample_evidence,
        )
        if (
            _dry_run_preview_response_size(checked)
            <= _MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES
        ):
            return checked

    raise ExportContractError(
        "export dry-run plan and preview metadata exceed the 256 KiB response budget"
    )


def export_inspection_response(inspection: ExportInspection) -> dict[str, Any]:
    return _response(
        "inspect",
        result={
            "destination_root": str(inspection.destination_root),
            "inspection_scope": inspection.inspection_scope,
            "plan": export_plan_summary(inspection.receipt.export_plan),
            "receipt": export_receipt_summary(inspection.receipt),
        },
    )


def export_execution_response(
    publication: ExportPublicationOutcome,
) -> dict[str, Any]:
    return _response(
        "execute",
        result=_export_execution_result(publication, revalidate=True),
    )


def _export_execution_result(
    publication: ExportPublicationOutcome,
    *,
    revalidate: bool,
) -> dict[str, Any]:
    """Build one execution result, optionally reloading persisted evidence."""
    if revalidate:
        plan_summary = export_plan_summary(publication.receipt.export_plan)
        receipt_summary = export_receipt_summary(publication.receipt)
        verification_summary = export_verification_summary(publication.verification)
    else:
        # A partial-publication exception is raised only after publication has
        # created these frozen, validated evidence models. Avoid strict reloads
        # while reporting that exception: reporting must not mask the visible
        # destination if a loader itself is the failing dependency.
        plan_summary = _export_plan_summary_from_validated(
            publication.receipt.export_plan
        )
        receipt_summary = _export_receipt_summary_from_validated(
            publication.receipt
        )
        verification_summary = _export_verification_summary_from_validated(
            publication.verification
        )
    return {
        "destination_root": str(publication.destination_root),
        "durability_warning": (
            _bounded_message(publication.durability_warning)
            if publication.durability_warning is not None
            else None
        ),
        "plan": plan_summary,
        "receipt": receipt_summary,
        "verification": verification_summary,
    }


def export_verify_response(verified: ExportVerifiedOutcome) -> dict[str, Any]:
    return _response(
        "verify",
        result={
            "destination_root": str(verified.destination_root),
            "plan": export_plan_summary(verified.receipt.export_plan),
            "receipt": export_receipt_summary(verified.receipt),
            "verification": export_verification_summary(verified.verification),
        },
    )


def export_error_response(
    operation: ExportOperation,
    exc: BaseException,
    *,
    response_schema: str | None = None,
) -> dict[str, Any]:
    if response_schema is None:
        response_schema = (
            EXPORT_SURFACE_RESPONSE_SCHEMA_V2
            if operation == "dry_run"
            else EXPORT_SURFACE_RESPONSE_SCHEMA
        )
    if response_schema not in {
        EXPORT_SURFACE_RESPONSE_SCHEMA,
        EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    }:
        raise ExportContractError("unsupported export error response schema")
    if (
        response_schema == EXPORT_SURFACE_RESPONSE_SCHEMA_V2
        and operation != "dry_run"
    ):
        raise ExportContractError(
            "export response v2 is reserved for the dry-run preview operation"
        )
    if isinstance(exc, ExportPartialPublicationError):
        if response_schema != EXPORT_SURFACE_RESPONSE_SCHEMA:
            raise ExportContractError(
                "visible partial publication uses export response v1"
            )
        publication = exc.publication
        response = _response(
            "execute",
            result=_export_execution_result(publication, revalidate=False),
        )
        response["status"] = "visible_partial"
        response["error"] = {
            "code": "export-partial-publication",
            "message": _bounded_error_message(exc.cause),
        }
        return response
    if isinstance(exc, ExportOperationCancelled):
        status: ExportResponseStatus = "cancelled"
        code = "export-cancelled"
    else:
        status = "error"
        code = getattr(exc, "code", "invalid-data")
    return _response(
        operation,
        status=status,
        result=None,
        error={"code": code, "message": _bounded_error_message(exc)},
        schema_version=response_schema,
    )


def export_response_json(payload: dict[str, Any]) -> str:
    """Return one bounded canonical response, without a trailing LF."""
    if payload.get("schema_version") == EXPORT_SURFACE_RESPONSE_SCHEMA_V2:
        try:
            data = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
        except (RecursionError, TypeError, UnicodeError, ValueError) as exc:
            raise ExportContractError(
                f"invalid export response v2 payload: {exc}"
            ) from exc
    else:
        # Preserve the historical response-v1 bytes exactly.
        data = lossless_json_bytes(payload)
    if len(data) > _MAX_SURFACE_RESPONSE_BYTES:
        raise ExportContractError("export surface response exceeds the 1 MiB limit")
    return data.decode("utf-8")


def _validate_executable_plan_response_budget(plan: ExportPlan) -> None:
    """Reserve room for receipt/verification summaries before publication."""
    if any(
        item.path.count("/") > _MAX_EXPORT_TREE_DEPTH
        for item in plan.file_plans
    ):
        raise ExportContractError(
            "export plan exceeds the maximum destination directory depth"
        )
    data = lossless_json_bytes(export_dry_run_response(plan))
    if len(data) > _MAX_EXECUTABLE_PLAN_RESPONSE_BYTES:
        raise ExportContractError(
            "export plan exceeds the executable surface response budget"
        )
    exact = plan.container_profile.determinism_claim == "portable_exact_bytes"
    if exact and any(
        item.expected_sha256 is None or item.expected_byte_size is None
        for item in plan.file_plans
    ):
        raise ExportContractError("exact export plan lacks complete byte evidence")
    files = tuple(
        ExportDestinationFileBinding.create(
            file_plan_id=item.file_plan_id,
            path=item.path,
            role=item.role,
            media_type=item.media_type,
            membership_scope=item.membership_scope,
            record_count=item.record_count,
            semantic_content_sha256=(
                None if exact else item.semantic_content_sha256
            ),
            sha256=(
                item.expected_sha256 if exact else "f" * 64
            ),
            byte_size=(
                item.expected_byte_size if exact else (2**63 - 1)
            ),
        )
        for item in plan.file_plans
    )
    receipt = ExportReceipt.create(export_plan=plan, files=files)
    synthetic = ExportPublicationOutcome(
        destination_root=Path("/" + "\x01" * (_MAX_RUNTIME_PATH_BYTES - 1)),
        receipt=receipt,
        verification=ExportVerification.create(receipt=receipt),
        durability_warning="\x01" * _MAX_ERROR_MESSAGE_BYTES,
    )
    try:
        export_response_json(export_execution_response(synthetic))
    except ExportContractError as exc:
        raise ExportContractError(
            "export plan cannot produce a bounded execute response"
        ) from exc


def _response(
    operation: ExportOperation,
    *,
    status: ExportResponseStatus = "ok",
    result: dict[str, Any] | None,
    error: dict[str, Any] | None = None,
    schema_version: str = EXPORT_SURFACE_RESPONSE_SCHEMA,
) -> dict[str, Any]:
    if schema_version not in {
        EXPORT_SURFACE_RESPONSE_SCHEMA,
        EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    }:
        raise ExportContractError("unsupported export surface response schema")
    if schema_version == EXPORT_SURFACE_RESPONSE_SCHEMA_V2 and operation != "dry_run":
        raise ExportContractError(
            "export surface response v2 is reserved for dry-run preview"
        )
    return {
        "error": error,
        "operation": operation,
        "result": result,
        "schema_version": schema_version,
        "status": status,
    }


__all__ = [
    "CancellationCheck",
    "EXPORT_DISCOVERY_SCHEMA",
    "EXPORT_DRY_RUN_PREVIEW_SCHEMA",
    "EXPORT_SURFACE_REQUEST_SCHEMA",
    "EXPORT_SURFACE_REQUEST_SCHEMA_V2",
    "EXPORT_SURFACE_RESPONSE_SCHEMA",
    "EXPORT_SURFACE_RESPONSE_SCHEMA_V2",
    "ExportDiscovery",
    "ExportDryRunPreview",
    "ExportDryRunRequest",
    "ExportDryRunRequestV2",
    "ExportExecuteRequest",
    "ExportExecuteRequestV2",
    "ExportInspectRequest",
    "ExportInspection",
    "ExportOperationCancelled",
    "ExportPartialPublicationError",
    "ExportProfileDescriptor",
    "ExportPublicationOutcome",
    "ExportVerifiedOutcome",
    "ExportVerifyRequest",
    "ExportVerifyRequestV2",
    "export_discovery_response",
    "export_dry_run_preview_response",
    "export_dry_run_response",
    "export_error_response",
    "export_execution_response",
    "export_inspection_response",
    "export_request_from_json_bytes",
    "export_response_json",
    "export_verify_response",
]
