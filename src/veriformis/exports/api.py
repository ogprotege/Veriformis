"""Typed, non-persisted surface protocol for verified exports.

The ten models in :mod:`veriformis.exports.models` remain the durable evidence
contract.  This module defines bounded request/response shapes used by Python,
CLI, MCP, and the CLI-backed Mac bridge; surface envelopes are transport API,
not additional persisted export evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import V1_ROW_SCHEMA_KINDS
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
EXPORT_DISCOVERY_SCHEMA = "veriformis.export-discovery/v1"

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
_MAX_ERROR_MESSAGE_BYTES = 4096


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
            or any(item not in V1_ROW_SCHEMA_KINDS for item in schemas)
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
    return _response("dry_run", result={"plan": export_plan_summary(plan)})


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
) -> dict[str, Any]:
    if isinstance(exc, ExportPartialPublicationError):
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
    )


def export_response_json(payload: dict[str, Any]) -> str:
    """Return one bounded canonical response, without a trailing LF."""
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
) -> dict[str, Any]:
    return {
        "error": error,
        "operation": operation,
        "result": result,
        "schema_version": EXPORT_SURFACE_RESPONSE_SCHEMA,
        "status": status,
    }


__all__ = [
    "CancellationCheck",
    "EXPORT_DISCOVERY_SCHEMA",
    "EXPORT_SURFACE_REQUEST_SCHEMA",
    "EXPORT_SURFACE_REQUEST_SCHEMA_V2",
    "EXPORT_SURFACE_RESPONSE_SCHEMA",
    "ExportDiscovery",
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
    "export_dry_run_response",
    "export_error_response",
    "export_execution_response",
    "export_inspection_response",
    "export_request_from_json_bytes",
    "export_response_json",
    "export_verify_response",
]
