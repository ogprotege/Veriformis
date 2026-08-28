"""Strict v1 contracts for receipt-bound derivatives of verified bundles."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Literal, Self, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.bundle.finished import VerificationResult
from veriformis.contracts import PRODUCT_ROW_SCHEMA_KINDS, V1_ROW_SCHEMA_KINDS
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports._json import canonical_export_object_from_bytes
from veriformis.exports.paths import (
    validate_export_path_set,
    validate_export_relative_path,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)
from veriformis.taxonomy import loss_policy_for_row

EXPORT_RECEIPT_PATH = "export-receipt.json"

EXPORT_CONTAINER_PROFILE_SCHEMA = "veriformis.export-container-profile/v1"
EXPORT_CONSUMER_PROFILE_SCHEMA = "veriformis.export-consumer-profile/v1"
EXPORT_DEPENDENCY_BINDING_SCHEMA = "veriformis.export-dependency-binding/v1"
EXPORT_FILE_PLAN_SCHEMA = "veriformis.export-file-plan/v1"
EXPORT_DESTINATION_FILE_BINDING_SCHEMA = (
    "veriformis.export-destination-file-binding/v1"
)
EXPORT_MEMBERSHIP_ENTRY_SCHEMA = "veriformis.export-membership-entry/v1"
EXPORT_MEMBERSHIP_PROJECTION_SCHEMA = (
    "veriformis.export-membership-projection/v1"
)
EXPORT_PLAN_SCHEMA = "veriformis.export-plan/v1"
EXPORT_RECEIPT_SCHEMA = "veriformis.export-receipt/v1"
EXPORT_VERIFICATION_SCHEMA = "veriformis.export-verification/v1"

_ASSIGNMENT_PROJECTION_SCHEMA = "veriformis.export-assignment-projection/v1"
_OUTPUT_CONTENT_ROOT_SCHEMA = "veriformis.export-content-root/v1"
_MINIMAL_V1_PAYLOAD_FILE_COUNT = 4
_EMPTY_SHA256 = sha256_digest(b"")
_LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")

SourceTrustPolicy = Literal["require_external_digest", "allow_self_consistent"]
SourceTrustGrade = Literal["external_digest", "self_consistent"]
DeterminismClaim = Literal["portable_exact_bytes", "semantic_content_only"]
MembershipScope = Literal["none", "train", "evaluation", "all"]
DatasetPartition = Literal["train", "evaluation"]


def _validate_label(value: str, *, label: str) -> str:
    if not _LABEL.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase canonical identifier")
    return value


def _validate_id_kinds(value: str, kinds: tuple[str, ...]) -> str:
    prefix = value.split("-v", 1)[0]
    if prefix not in kinds:
        raise ValueError(f"identity must use one of {kinds!r}")
    return validate_id(value, kind=prefix)


def _validate_exact_text(value: str, *, label: str) -> str:
    if not value or value != value.strip() or "\x00" in value:
        raise ValueError(f"{label} must be a non-empty exact string")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"{label} must contain valid Unicode") from exc
    if any(
        unicodedata.category(character) in {"Cc", "Cf"} for character in value
    ):
        raise ValueError(f"{label} cannot contain control or format characters")
    return value


def _validate_nonnegative(value: int, *, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_positive(value: int, *, label: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _assignment_projection_digest(
    entries: Sequence[ExportMembershipEntry],
) -> str:
    return canonical_digest(
        {
            "schema_version": _ASSIGNMENT_PROJECTION_SCHEMA,
            "entries": tuple(
                {
                    "record_id": entry.record_id,
                    "assignment_id": entry.assignment_id,
                    "leakage_group_id": entry.leakage_group_id,
                    "partition": entry.partition,
                    "ordinal": entry.ordinal,
                }
                for entry in entries
            ),
        }
    )


def _output_content_root(files: Sequence[ExportDestinationFileBinding]) -> str:
    return canonical_digest(
        {
            "schema_version": _OUTPUT_CONTENT_ROOT_SCHEMA,
            "files": tuple(file.model_dump(mode="json") for file in files),
        }
    )


class _StrictExportModel(BaseModel):
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
        """Return the unique canonical bytes after a fresh strict boundary."""
        try:
            data = lossless_json_bytes(self.model_dump(mode="json"))
            checked = type(self).model_validate_json(data)
        except (TypeError, UnicodeError, ValueError) as exc:
            raise ExportContractError(
                f"invalid {type(self).__name__}: {exc}"
            ) from exc
        if checked != self:
            raise ExportContractError(
                f"{type(self).__name__} does not round-trip exactly"
            )
        return data

    @classmethod
    def from_json_bytes(cls, data: bytes) -> Self:
        """Load only the unique canonical representation of this exact model."""
        canonical_export_object_from_bytes(data, label=cls.__name__)
        try:
            checked = cls.model_validate_json(data)
        except (TypeError, ValueError) as exc:
            raise ExportVerificationError(f"invalid {cls.__name__}: {exc}") from exc
        if checked.canonical_bytes() != data:
            raise ExportVerificationError(
                f"{cls.__name__} does not round-trip exactly"
            )
        return checked


class _IdentifiedExportModel(_StrictExportModel):
    _identity_field: ClassVar[str]
    _identity_kind: ClassVar[str]

    @model_validator(mode="after")
    def _consistent_identity(self) -> Self:
        value = getattr(self, self._identity_field)
        validate_id(value, kind=self._identity_kind)
        payload = self.model_dump(mode="json", exclude={self._identity_field})
        if value != derive_id(self._identity_kind, payload):
            raise ValueError(f"{type(self).__name__} identity mismatch")
        return self

    @classmethod
    def _create(cls, **body: Any) -> Self:
        identity = derive_id(cls._identity_kind, body)
        return cls.model_validate({cls._identity_field: identity, **body})


class ExportContainerProfile(_IdentifiedExportModel):
    """One versioned physical-container behavior contract."""

    _identity_field = "container_profile_id"
    _identity_kind = "export-container"

    schema_version: Literal["veriformis.export-container-profile/v1"]
    container_profile_id: str
    container_id: str
    container_version: int
    determinism_claim: DeterminismClaim

    @field_validator("container_id")
    @classmethod
    def _valid_container_id(cls, value: str) -> str:
        return _validate_label(value, label="container_id")

    @field_validator("container_version")
    @classmethod
    def _valid_container_version(cls, value: int) -> int:
        return _validate_positive(value, label="container_version")

    @classmethod
    def create(
        cls,
        *,
        container_id: str,
        container_version: int,
        determinism_claim: DeterminismClaim,
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_CONTAINER_PROFILE_SCHEMA,
            container_id=container_id,
            container_version=container_version,
            determinism_claim=determinism_claim,
        )


class ExportConsumerProfile(_IdentifiedExportModel):
    """One optional versioned destination-consumer restriction."""

    _identity_field = "consumer_profile_id"
    _identity_kind = "export-consumer"

    schema_version: Literal["veriformis.export-consumer-profile/v1"]
    consumer_profile_id: str
    consumer_id: str
    profile_version: int
    accepted_row_schemas: tuple[str, ...]

    @field_validator("consumer_id")
    @classmethod
    def _valid_consumer_id(cls, value: str) -> str:
        return _validate_label(value, label="consumer_id")

    @field_validator("profile_version")
    @classmethod
    def _valid_profile_version(cls, value: int) -> int:
        return _validate_positive(value, label="profile_version")

    @field_validator("accepted_row_schemas")
    @classmethod
    def _valid_row_schemas(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("consumer profile must accept at least one row schema")
        if value != tuple(sorted(value)) or len(value) != len(set(value)):
            raise ValueError("accepted_row_schemas must be sorted and unique")
        if any(item not in V1_ROW_SCHEMA_KINDS for item in value):
            raise ValueError("consumer profile names an unsupported row schema")
        return value

    @classmethod
    def create(
        cls,
        *,
        consumer_id: str,
        profile_version: int,
        accepted_row_schemas: Sequence[str],
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_CONSUMER_PROFILE_SCHEMA,
            consumer_id=consumer_id,
            profile_version=profile_version,
            accepted_row_schemas=tuple(sorted(accepted_row_schemas)),
        )


class ExportDependencyBinding(_IdentifiedExportModel):
    """One exact dependency name/version/role used by an export plan."""

    _identity_field = "dependency_id"
    _identity_kind = "export-dependency"

    schema_version: Literal["veriformis.export-dependency-binding/v1"]
    dependency_id: str
    dependency_name: str
    dependency_version: str
    dependency_role: str

    @field_validator("dependency_name", "dependency_role")
    @classmethod
    def _valid_labels(cls, value: str, info: ValidationInfo) -> str:
        return _validate_label(value, label=info.field_name)

    @field_validator("dependency_version")
    @classmethod
    def _valid_version(cls, value: str) -> str:
        return _validate_exact_text(value, label="dependency_version")

    @classmethod
    def create(
        cls,
        *,
        dependency_name: str,
        dependency_version: str,
        dependency_role: str,
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_DEPENDENCY_BINDING_SCHEMA,
            dependency_name=dependency_name,
            dependency_version=dependency_version,
            dependency_role=dependency_role,
        )


class ExportFilePlan(_IdentifiedExportModel):
    """One exact output path and its expected evidence boundary."""

    _identity_field = "file_plan_id"
    _identity_kind = "export-file-plan"

    schema_version: Literal["veriformis.export-file-plan/v1"]
    file_plan_id: str
    path: str
    role: str
    media_type: str
    membership_scope: MembershipScope
    record_count: int | None
    semantic_content_sha256: str | None
    expected_sha256: str | None
    expected_byte_size: int | None

    @field_validator("path")
    @classmethod
    def _valid_path(cls, value: str) -> str:
        return validate_export_relative_path(value)

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        return _validate_label(value, label="file plan role")

    @field_validator("media_type")
    @classmethod
    def _valid_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE.fullmatch(value):
            raise ValueError("media_type must be a lowercase canonical MIME type")
        return value

    @field_validator("record_count")
    @classmethod
    def _valid_record_count(cls, value: int | None) -> int | None:
        if value is not None:
            _validate_nonnegative(value, label="record_count")
        return value

    @field_validator("semantic_content_sha256", "expected_sha256")
    @classmethod
    def _valid_optional_digest(cls, value: str | None) -> str | None:
        return validate_sha256(value) if value is not None else None

    @field_validator("expected_byte_size")
    @classmethod
    def _valid_expected_size(cls, value: int | None) -> int | None:
        if value is not None:
            _validate_nonnegative(value, label="expected_byte_size")
        return value

    @model_validator(mode="after")
    def _consistent_expectations(self) -> Self:
        if (self.expected_sha256 is None) != (self.expected_byte_size is None):
            raise ValueError(
                "expected_sha256 and expected_byte_size must be present together"
            )
        if self.membership_scope != "none" and self.record_count is None:
            raise ValueError("membership-bearing file plans require record_count")
        if self.expected_byte_size == 0 and self.expected_sha256 != _EMPTY_SHA256:
            raise ValueError("a zero-byte file must bind the SHA-256 of empty bytes")
        if self.record_count not in (None, 0) and self.expected_byte_size == 0:
            raise ValueError("a non-empty record set cannot occupy zero bytes")
        return self

    @classmethod
    def create(
        cls,
        *,
        path: str,
        role: str,
        media_type: str,
        membership_scope: MembershipScope,
        record_count: int | None,
        semantic_content_sha256: str | None,
        expected_sha256: str | None,
        expected_byte_size: int | None,
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_FILE_PLAN_SCHEMA,
            path=path,
            role=role,
            media_type=media_type,
            membership_scope=membership_scope,
            record_count=record_count,
            semantic_content_sha256=semantic_content_sha256,
            expected_sha256=expected_sha256,
            expected_byte_size=expected_byte_size,
        )


class ExportDestinationFileBinding(_IdentifiedExportModel):
    """One exact file observed in a published derivative."""

    _identity_field = "destination_file_id"
    _identity_kind = "export-file"

    schema_version: Literal["veriformis.export-destination-file-binding/v1"]
    destination_file_id: str
    file_plan_id: str
    path: str
    role: str
    media_type: str
    membership_scope: MembershipScope
    record_count: int | None
    semantic_content_sha256: str | None
    sha256: str
    byte_size: int

    @field_validator("file_plan_id")
    @classmethod
    def _valid_file_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-file-plan")

    @field_validator("path")
    @classmethod
    def _valid_path(cls, value: str) -> str:
        return validate_export_relative_path(value)

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        return _validate_label(value, label="destination file role")

    @field_validator("media_type")
    @classmethod
    def _valid_media_type(cls, value: str) -> str:
        if not _MEDIA_TYPE.fullmatch(value):
            raise ValueError("media_type must be a lowercase canonical MIME type")
        return value

    @field_validator("record_count")
    @classmethod
    def _valid_record_count(cls, value: int | None) -> int | None:
        if value is not None:
            _validate_nonnegative(value, label="record_count")
        return value

    @field_validator("semantic_content_sha256")
    @classmethod
    def _valid_semantic_digest(cls, value: str | None) -> str | None:
        return validate_sha256(value) if value is not None else None

    @field_validator("sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("byte_size")
    @classmethod
    def _valid_byte_size(cls, value: int) -> int:
        return _validate_nonnegative(value, label="byte_size")

    @model_validator(mode="after")
    def _consistent_count(self) -> Self:
        if self.membership_scope != "none" and self.record_count is None:
            raise ValueError("membership-bearing destination files require record_count")
        if self.byte_size == 0 and self.sha256 != _EMPTY_SHA256:
            raise ValueError("a zero-byte file must bind the SHA-256 of empty bytes")
        if self.record_count not in (None, 0) and self.byte_size == 0:
            raise ValueError("a non-empty record set cannot occupy zero bytes")
        return self

    @classmethod
    def create(
        cls,
        *,
        file_plan_id: str,
        path: str,
        role: str,
        media_type: str,
        membership_scope: MembershipScope,
        record_count: int | None,
        semantic_content_sha256: str | None,
        sha256: str,
        byte_size: int,
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_DESTINATION_FILE_BINDING_SCHEMA,
            file_plan_id=file_plan_id,
            path=path,
            role=role,
            media_type=media_type,
            membership_scope=membership_scope,
            record_count=record_count,
            semantic_content_sha256=semantic_content_sha256,
            sha256=sha256,
            byte_size=byte_size,
        )


class ExportMembershipEntry(_IdentifiedExportModel):
    """One immutable row/member assignment in authoritative source order."""

    _identity_field = "membership_entry_id"
    _identity_kind = "export-membership-entry"

    schema_version: Literal["veriformis.export-membership-entry/v1"]
    membership_entry_id: str
    record_id: str
    row_id: str
    provenance_id: str
    assignment_id: str
    leakage_group_id: str
    partition: DatasetPartition
    ordinal: int
    payload_sha256: str

    @field_validator("record_id")
    @classmethod
    def _valid_record_id(cls, value: str) -> str:
        return _validate_id_kinds(value, ("rec", "irc"))

    @field_validator("row_id")
    @classmethod
    def _valid_row_id(cls, value: str) -> str:
        return validate_id(value, kind="row")

    @field_validator("provenance_id")
    @classmethod
    def _valid_provenance_id(cls, value: str) -> str:
        return validate_id(value, kind="prv")

    @field_validator("assignment_id")
    @classmethod
    def _valid_assignment_id(cls, value: str) -> str:
        return validate_id(value, kind="asg")

    @field_validator("leakage_group_id")
    @classmethod
    def _valid_group_id(cls, value: str) -> str:
        return validate_id(value, kind="lkg")

    @field_validator("ordinal")
    @classmethod
    def _valid_ordinal(cls, value: int) -> int:
        return _validate_nonnegative(value, label="membership ordinal")

    @field_validator("payload_sha256")
    @classmethod
    def _valid_payload_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        row_id: str,
        provenance_id: str,
        assignment_id: str,
        leakage_group_id: str,
        partition: DatasetPartition,
        ordinal: int,
        payload_sha256: str,
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_MEMBERSHIP_ENTRY_SCHEMA,
            record_id=record_id,
            row_id=row_id,
            provenance_id=provenance_id,
            assignment_id=assignment_id,
            leakage_group_id=leakage_group_id,
            partition=partition,
            ordinal=ordinal,
            payload_sha256=payload_sha256,
        )


class ExportMembershipProjection(_IdentifiedExportModel):
    """Complete ordered source membership and partition projection."""

    _identity_field = "membership_projection_id"
    _identity_kind = "export-membership"

    schema_version: Literal["veriformis.export-membership-projection/v1"]
    membership_projection_id: str
    split_result_id: str
    row_set_id: str
    row_schema: str
    assignment_projection_sha256: str
    entries: tuple[ExportMembershipEntry, ...]

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in PRODUCT_ROW_SCHEMA_KINDS:
            raise ValueError("membership projection uses an unsupported row schema")
        return value

    @field_validator("assignment_projection_sha256")
    @classmethod
    def _valid_assignment_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _complete_ordered_membership(self) -> Self:
        if not self.entries:
            raise ValueError("membership projection cannot be empty")
        unique_fields = (
            "membership_entry_id",
            "record_id",
            "row_id",
            "provenance_id",
            "assignment_id",
        )
        for field_name in unique_fields:
            values = tuple(getattr(entry, field_name) for entry in self.entries)
            if len(values) != len(set(values)):
                raise ValueError(
                    f"membership projection contains duplicate {field_name}"
                )

        seen_evaluation = False
        next_ordinal = {"train": 0, "evaluation": 0}
        group_partitions: dict[str, DatasetPartition] = {}
        for entry in self.entries:
            if entry.partition == "evaluation":
                seen_evaluation = True
            elif seen_evaluation:
                raise ValueError("train membership cannot follow evaluation membership")
            expected = next_ordinal[entry.partition]
            if entry.ordinal != expected:
                raise ValueError(
                    f"{entry.partition} membership ordinals must be contiguous from zero"
                )
            next_ordinal[entry.partition] += 1
            prior_partition = group_partitions.setdefault(
                entry.leakage_group_id,
                entry.partition,
            )
            if prior_partition != entry.partition:
                raise ValueError(
                    "a leakage group cannot cross export membership partitions"
                )
        if next_ordinal["train"] < 1:
            raise ValueError("membership projection requires a non-empty train partition")
        expected_digest = _assignment_projection_digest(self.entries)
        if self.assignment_projection_sha256 != expected_digest:
            raise ValueError("assignment projection digest mismatch")
        return self

    @property
    def train_record_count(self) -> int:
        return sum(entry.partition == "train" for entry in self.entries)

    @property
    def evaluation_record_count(self) -> int:
        return sum(entry.partition == "evaluation" for entry in self.entries)

    @property
    def total_record_count(self) -> int:
        return len(self.entries)

    @classmethod
    def create(
        cls,
        *,
        split_result_id: str,
        row_set_id: str,
        row_schema: str,
        entries: Sequence[ExportMembershipEntry],
    ) -> Self:
        checked_entries = tuple(entries)
        return cls._create(
            schema_version=EXPORT_MEMBERSHIP_PROJECTION_SCHEMA,
            split_result_id=split_result_id,
            row_set_id=row_set_id,
            row_schema=row_schema,
            assignment_projection_sha256=_assignment_projection_digest(
                checked_entries
            ),
            entries=checked_entries,
        )


class ExportPlan(_IdentifiedExportModel):
    """Complete portable plan for a derivative of one verified bundle."""

    _identity_field = "export_plan_id"
    _identity_kind = "export-plan"

    schema_version: Literal["veriformis.export-plan/v1"]
    export_plan_id: str
    source_bundle_id: str
    source_manifest_sha256: str
    source_content_root_sha256: str
    source_verification_id: str
    source_trust_policy: SourceTrustPolicy
    source_trust_grade: SourceTrustGrade
    dataset_snapshot_id: str
    validation_report_id: str
    finished_dataset_plan_id: str
    recipe_id: str
    objective_id: str
    construction_result_id: str
    curation_result_id: str
    serialization_plan_id: str
    split_result_id: str
    row_set_id: str
    source_ids: tuple[str, ...]
    row_schema: str
    loss_policy: str
    derivative_policy: Literal["preserve_membership_and_semantics"]
    container_profile: ExportContainerProfile
    consumer_profile: ExportConsumerProfile | None
    dependencies: tuple[ExportDependencyBinding, ...]
    membership_projection: ExportMembershipProjection
    file_plans: tuple[ExportFilePlan, ...]
    overwrite_policy: Literal["refuse"]

    @field_validator("source_bundle_id")
    @classmethod
    def _valid_bundle_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle")

    @field_validator("source_manifest_sha256", "source_content_root_sha256")
    @classmethod
    def _valid_source_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("source_verification_id")
    @classmethod
    def _valid_source_verification_id(cls, value: str) -> str:
        return validate_id(value, kind="verification")

    @field_validator("dataset_snapshot_id")
    @classmethod
    def _valid_snapshot_id(cls, value: str) -> str:
        return validate_id(value, kind="dss")

    @field_validator("validation_report_id")
    @classmethod
    def _valid_validation_id(cls, value: str) -> str:
        return validate_id(value, kind="dvr")

    @field_validator("finished_dataset_plan_id")
    @classmethod
    def _valid_finished_plan_id(cls, value: str) -> str:
        return _validate_id_kinds(value, ("fdp", "fip"))

    @field_validator("recipe_id")
    @classmethod
    def _valid_recipe_id(cls, value: str) -> str:
        return validate_id(value, kind="rcp")

    @field_validator("objective_id")
    @classmethod
    def _valid_objective_id(cls, value: str) -> str:
        return validate_id(value, kind="obj")

    @field_validator("construction_result_id")
    @classmethod
    def _valid_construction_id(cls, value: str) -> str:
        return _validate_id_kinds(value, ("run", "imr"))

    @field_validator("curation_result_id")
    @classmethod
    def _valid_curation_id(cls, value: str) -> str:
        return validate_id(value, kind="cur")

    @field_validator("serialization_plan_id")
    @classmethod
    def _valid_serialization_id(cls, value: str) -> str:
        return validate_id(value, kind="srp")

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("source_ids")
    @classmethod
    def _valid_source_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or value != tuple(sorted(value)) or len(value) != len(set(value)):
            raise ValueError("source_ids must be non-empty, sorted, and unique")
        for source_id in value:
            validate_id(source_id, kind="src")
        return value

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in PRODUCT_ROW_SCHEMA_KINDS:
            raise ValueError("export plan uses an unsupported row schema")
        return value

    @field_validator("loss_policy")
    @classmethod
    def _valid_loss_policy_label(cls, value: str) -> str:
        return _validate_label(value, label="loss_policy")

    @model_validator(mode="after")
    def _closed_derivative_plan(self) -> Self:
        if (
            self.source_trust_policy == "require_external_digest"
            and self.source_trust_grade != "external_digest"
        ):
            raise ValueError(
                "require_external_digest plans need external_digest source trust"
            )
        if self.loss_policy != loss_policy_for_row(self.row_schema):
            raise ValueError("export plan loss policy differs from its row schema")

        expected_source_verification = VerificationResult.create(
            bundle_id=self.source_bundle_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            validation_report_id=self.validation_report_id,
            manifest_sha256=self.source_manifest_sha256,
            content_root_sha256=self.source_content_root_sha256,
            trust_grade=self.source_trust_grade,
            payload_file_count=_MINIMAL_V1_PAYLOAD_FILE_COUNT,
            declared_record_count=self.membership_projection.total_record_count,
        )
        if self.source_verification_id != expected_source_verification.verification_id:
            raise ValueError(
                "source verification identity differs from the bound source facts"
            )
        if self.consumer_profile is not None and (
            self.row_schema not in self.consumer_profile.accepted_row_schemas
        ):
            raise ValueError("consumer profile refuses the export row schema")

        projection = self.membership_projection
        if (
            projection.split_result_id != self.split_result_id
            or projection.row_set_id != self.row_set_id
            or projection.row_schema != self.row_schema
        ):
            raise ValueError("membership projection names another source row set")

        dependency_ids = tuple(item.dependency_id for item in self.dependencies)
        if not dependency_ids:
            raise ValueError("export plan requires at least one dependency binding")
        if dependency_ids != tuple(sorted(dependency_ids)):
            raise ValueError("export dependencies must be sorted by dependency_id")
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError("export plan contains duplicate dependencies")
        dependency_names = tuple(item.dependency_name for item in self.dependencies)
        if len(dependency_names) != len(set(dependency_names)):
            raise ValueError("export plan contains duplicate dependency names")

        paths = tuple(item.path for item in self.file_plans)
        validate_export_path_set(paths, label="export file plans")
        validate_export_path_set(
            (*paths, EXPORT_RECEIPT_PATH),
            label="export tree paths",
            require_sorted=False,
        )
        if not self.file_plans:
            raise ValueError("export plan must declare at least one output file")
        plan_ids = tuple(item.file_plan_id for item in self.file_plans)
        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("export plan contains duplicate file-plan identities")

        scopes = tuple(
            item.membership_scope
            for item in self.file_plans
            if item.membership_scope != "none"
        )
        if scopes == ("all",):
            pass
        elif sorted(scopes) == ["evaluation", "train"] and len(scopes) == 2:
            pass
        else:
            raise ValueError(
                "membership output must be one all file or one train and one "
                "evaluation file"
            )
        expected_counts = {
            "train": projection.train_record_count,
            "evaluation": projection.evaluation_record_count,
            "all": projection.total_record_count,
        }
        for file_plan in self.file_plans:
            if file_plan.membership_scope != "none" and (
                file_plan.record_count
                != expected_counts[file_plan.membership_scope]
            ):
                raise ValueError("file-plan record count differs from membership")
            if self.container_profile.determinism_claim == "portable_exact_bytes":
                if (
                    file_plan.expected_sha256 is None
                    or file_plan.expected_byte_size is None
                    or file_plan.semantic_content_sha256 is not None
                ):
                    raise ValueError(
                        "portable exact plans require byte expectations only"
                    )
            elif (
                file_plan.expected_sha256 is not None
                or file_plan.expected_byte_size is not None
                or file_plan.semantic_content_sha256 is None
            ):
                raise ValueError(
                    "semantic-only plans require semantic evidence only"
                )
        return self

    @classmethod
    def create(
        cls,
        *,
        source_bundle_id: str,
        source_manifest_sha256: str,
        source_content_root_sha256: str,
        source_verification_id: str,
        source_trust_policy: SourceTrustPolicy,
        source_trust_grade: SourceTrustGrade,
        dataset_snapshot_id: str,
        validation_report_id: str,
        finished_dataset_plan_id: str,
        recipe_id: str,
        objective_id: str,
        construction_result_id: str,
        curation_result_id: str,
        serialization_plan_id: str,
        split_result_id: str,
        row_set_id: str,
        source_ids: Sequence[str],
        row_schema: str,
        container_profile: ExportContainerProfile,
        consumer_profile: ExportConsumerProfile | None,
        dependencies: Sequence[ExportDependencyBinding],
        membership_projection: ExportMembershipProjection,
        file_plans: Sequence[ExportFilePlan],
    ) -> Self:
        return cls._create(
            schema_version=EXPORT_PLAN_SCHEMA,
            source_bundle_id=source_bundle_id,
            source_manifest_sha256=source_manifest_sha256,
            source_content_root_sha256=source_content_root_sha256,
            source_verification_id=source_verification_id,
            source_trust_policy=source_trust_policy,
            source_trust_grade=source_trust_grade,
            dataset_snapshot_id=dataset_snapshot_id,
            validation_report_id=validation_report_id,
            finished_dataset_plan_id=finished_dataset_plan_id,
            recipe_id=recipe_id,
            objective_id=objective_id,
            construction_result_id=construction_result_id,
            curation_result_id=curation_result_id,
            serialization_plan_id=serialization_plan_id,
            split_result_id=split_result_id,
            row_set_id=row_set_id,
            source_ids=tuple(sorted(source_ids)),
            row_schema=row_schema,
            loss_policy=loss_policy_for_row(row_schema),
            derivative_policy="preserve_membership_and_semantics",
            container_profile=container_profile,
            consumer_profile=consumer_profile,
            dependencies=tuple(
                sorted(dependencies, key=lambda item: item.dependency_id)
            ),
            membership_projection=membership_projection,
            file_plans=tuple(sorted(file_plans, key=lambda item: item.path)),
            overwrite_policy="refuse",
        )


class ExportReceipt(_IdentifiedExportModel):
    """Self-describing binding from one plan to one closed derivative tree."""

    _identity_field = "export_receipt_id"
    _identity_kind = "export-receipt"

    schema_version: Literal["veriformis.export-receipt/v1"]
    export_receipt_id: str
    export_plan_id: str
    export_plan: ExportPlan
    output_content_root_sha256: str
    files: tuple[ExportDestinationFileBinding, ...]

    @field_validator("export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")

    @field_validator("output_content_root_sha256")
    @classmethod
    def _valid_content_root(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _closed_receipt(self) -> Self:
        if self.export_plan_id != self.export_plan.export_plan_id:
            raise ValueError("export receipt embeds another export plan")
        paths = tuple(item.path for item in self.files)
        validate_export_path_set(paths, label="export receipt files")
        validate_export_path_set(
            (*paths, EXPORT_RECEIPT_PATH),
            label="export receipt tree",
            require_sorted=False,
        )
        if not self.files:
            raise ValueError("export receipt requires at least one bound file")
        destination_ids = tuple(item.destination_file_id for item in self.files)
        if len(destination_ids) != len(set(destination_ids)):
            raise ValueError("export receipt contains duplicate destination bindings")

        plans_by_path = {item.path: item for item in self.export_plan.file_plans}
        files_by_path = {item.path: item for item in self.files}
        if set(plans_by_path) != set(files_by_path):
            raise ValueError("receipt files do not match the complete planned file set")
        exact = (
            self.export_plan.container_profile.determinism_claim
            == "portable_exact_bytes"
        )
        for path in sorted(plans_by_path):
            planned = plans_by_path[path]
            observed = files_by_path[path]
            if (
                observed.file_plan_id != planned.file_plan_id
                or observed.role != planned.role
                or observed.media_type != planned.media_type
                or observed.membership_scope != planned.membership_scope
                or observed.record_count != planned.record_count
            ):
                raise ValueError(f"destination binding differs from plan for {path!r}")
            if exact:
                if (
                    observed.sha256 != planned.expected_sha256
                    or observed.byte_size != planned.expected_byte_size
                    or observed.semantic_content_sha256 is not None
                ):
                    raise ValueError(
                        f"exact destination bytes differ from plan for {path!r}"
                    )
            elif (
                observed.semantic_content_sha256
                != planned.semantic_content_sha256
            ):
                raise ValueError(
                    f"destination semantics differ from plan for {path!r}"
                )
        if self.output_content_root_sha256 != _output_content_root(self.files):
            raise ValueError("export output content root mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        export_plan: ExportPlan,
        files: Sequence[ExportDestinationFileBinding],
    ) -> Self:
        checked_files = tuple(sorted(files, key=lambda item: item.path))
        return cls._create(
            schema_version=EXPORT_RECEIPT_SCHEMA,
            export_plan_id=export_plan.export_plan_id,
            export_plan=export_plan,
            output_content_root_sha256=_output_content_root(checked_files),
            files=checked_files,
        )


class ExportVerification(_IdentifiedExportModel):
    """Successful verification evidence; invalid exports raise instead."""

    _identity_field = "export_verification_id"
    _identity_kind = "export-verification"

    schema_version: Literal["veriformis.export-verification/v1"]
    export_verification_id: str
    export_receipt_id: str
    export_plan_id: str
    source_bundle_id: str
    source_manifest_sha256: str
    source_content_root_sha256: str
    source_verification_id: str
    source_trust_grade: SourceTrustGrade
    dataset_snapshot_id: str
    validation_report_id: str
    split_result_id: str
    row_set_id: str
    row_schema: str
    container_profile_id: str
    consumer_profile_id: str | None
    membership_projection_id: str
    determinism_claim: DeterminismClaim
    output_content_root_sha256: str
    output_file_count: int
    declared_record_count: int

    @field_validator("export_receipt_id")
    @classmethod
    def _valid_receipt_id(cls, value: str) -> str:
        return validate_id(value, kind="export-receipt")

    @field_validator("export_plan_id")
    @classmethod
    def _valid_plan_id(cls, value: str) -> str:
        return validate_id(value, kind="export-plan")

    @field_validator("source_bundle_id")
    @classmethod
    def _valid_bundle_id(cls, value: str) -> str:
        return validate_id(value, kind="bundle")

    @field_validator(
        "source_manifest_sha256",
        "source_content_root_sha256",
        "output_content_root_sha256",
    )
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("source_verification_id")
    @classmethod
    def _valid_source_verification_id(cls, value: str) -> str:
        return validate_id(value, kind="verification")

    @field_validator("dataset_snapshot_id")
    @classmethod
    def _valid_snapshot_id(cls, value: str) -> str:
        return validate_id(value, kind="dss")

    @field_validator("validation_report_id")
    @classmethod
    def _valid_validation_id(cls, value: str) -> str:
        return validate_id(value, kind="dvr")

    @field_validator("split_result_id")
    @classmethod
    def _valid_split_id(cls, value: str) -> str:
        return validate_id(value, kind="spt")

    @field_validator("row_set_id")
    @classmethod
    def _valid_row_set_id(cls, value: str) -> str:
        return validate_id(value, kind="rws")

    @field_validator("row_schema")
    @classmethod
    def _valid_row_schema(cls, value: str) -> str:
        if value not in PRODUCT_ROW_SCHEMA_KINDS:
            raise ValueError("export verification uses an unsupported row schema")
        return value

    @field_validator("container_profile_id")
    @classmethod
    def _valid_container_profile_id(cls, value: str) -> str:
        return validate_id(value, kind="export-container")

    @field_validator("consumer_profile_id")
    @classmethod
    def _valid_consumer_profile_id(cls, value: str | None) -> str | None:
        return (
            validate_id(value, kind="export-consumer")
            if value is not None
            else None
        )

    @field_validator("membership_projection_id")
    @classmethod
    def _valid_membership_id(cls, value: str) -> str:
        return validate_id(value, kind="export-membership")

    @field_validator("output_file_count", "declared_record_count")
    @classmethod
    def _valid_count(cls, value: int, info: ValidationInfo) -> int:
        return _validate_positive(value, label=info.field_name)

    @model_validator(mode="after")
    def _closed_source_verification(self) -> Self:
        expected = VerificationResult.create(
            bundle_id=self.source_bundle_id,
            dataset_snapshot_id=self.dataset_snapshot_id,
            validation_report_id=self.validation_report_id,
            manifest_sha256=self.source_manifest_sha256,
            content_root_sha256=self.source_content_root_sha256,
            trust_grade=self.source_trust_grade,
            payload_file_count=_MINIMAL_V1_PAYLOAD_FILE_COUNT,
            declared_record_count=self.declared_record_count,
        )
        if self.source_verification_id != expected.verification_id:
            raise ValueError(
                "source verification identity differs from the bound source facts"
            )
        return self

    @classmethod
    def create(cls, *, receipt: ExportReceipt) -> Self:
        checked_receipt = ExportReceipt.from_json_bytes(receipt.canonical_bytes())
        plan = checked_receipt.export_plan
        consumer_id = (
            plan.consumer_profile.consumer_profile_id
            if plan.consumer_profile is not None
            else None
        )
        return cls._create(
            schema_version=EXPORT_VERIFICATION_SCHEMA,
            export_receipt_id=checked_receipt.export_receipt_id,
            export_plan_id=plan.export_plan_id,
            source_bundle_id=plan.source_bundle_id,
            source_manifest_sha256=plan.source_manifest_sha256,
            source_content_root_sha256=plan.source_content_root_sha256,
            source_verification_id=plan.source_verification_id,
            source_trust_grade=plan.source_trust_grade,
            dataset_snapshot_id=plan.dataset_snapshot_id,
            validation_report_id=plan.validation_report_id,
            split_result_id=plan.split_result_id,
            row_set_id=plan.row_set_id,
            row_schema=plan.row_schema,
            container_profile_id=plan.container_profile.container_profile_id,
            consumer_profile_id=consumer_id,
            membership_projection_id=(
                plan.membership_projection.membership_projection_id
            ),
            determinism_claim=plan.container_profile.determinism_claim,
            output_content_root_sha256=checked_receipt.output_content_root_sha256,
            output_file_count=len(checked_receipt.files),
            declared_record_count=plan.membership_projection.total_record_count,
        )


__all__ = [
    "EXPORT_CONTAINER_PROFILE_SCHEMA",
    "EXPORT_CONSUMER_PROFILE_SCHEMA",
    "EXPORT_DEPENDENCY_BINDING_SCHEMA",
    "EXPORT_DESTINATION_FILE_BINDING_SCHEMA",
    "EXPORT_FILE_PLAN_SCHEMA",
    "EXPORT_MEMBERSHIP_ENTRY_SCHEMA",
    "EXPORT_MEMBERSHIP_PROJECTION_SCHEMA",
    "EXPORT_PLAN_SCHEMA",
    "EXPORT_RECEIPT_PATH",
    "EXPORT_RECEIPT_SCHEMA",
    "EXPORT_VERIFICATION_SCHEMA",
    "DatasetPartition",
    "DeterminismClaim",
    "ExportConsumerProfile",
    "ExportContainerProfile",
    "ExportDependencyBinding",
    "ExportDestinationFileBinding",
    "ExportFilePlan",
    "ExportMembershipEntry",
    "ExportMembershipProjection",
    "ExportPlan",
    "ExportReceipt",
    "ExportVerification",
    "MembershipScope",
    "SourceTrustGrade",
    "SourceTrustPolicy",
]
