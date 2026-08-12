"""Exact replay validation for one immutable finished-dataset snapshot.

The validator keeps two concerns separate. ``DatasetSnapshot`` binds the exact
semantic artifacts and emitted files intended for sealing. Validation then
reloads those artifacts, replays every deterministic stage, and reports every
required v1 gate. A failed report remains a canonical, content-addressed audit
artifact, but only a report whose seventeen gates pass can be sealed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypeVar, get_origin

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from veriformis.construction import (
    ConstructionInputs,
    ConstructionResult,
    DatasetRecipe,
    construction_result_from_json_bytes,
    dataset_recipe_from_json_bytes,
    validate_construction_result,
)
from veriformis.contracts import V1_FINISHED_DATASET_GATES
from veriformis.errors import (
    DatasetValidationError,
    DuplicateIdentityError,
    VeriformisError,
)
from veriformis.identity import (
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

from ._json import canonical_json_object_from_bytes, reject_floats
from .curation import curate_dataset
from .models import CurationResult, curation_result_from_json_bytes
from .plan import FinishedDatasetPlan, finished_dataset_plan_from_json_bytes
from .serialization import (
    RowSet,
    SerializationOutput,
    row_set_from_json_bytes,
    serialize_dataset,
)
from .splitting import (
    SplitResult,
    split_result_from_json_bytes,
    validate_split_result,
)


GateStatus = Literal["passed", "failed", "blocked"]
ValidationStatus = Literal["passed", "failed"]
ArtifactRole = Literal[
    "plan",
    "recipe",
    "construction-result",
    "curation-result",
    "split-result",
    "row-set",
]
FileRole = Literal[
    "training-partition",
    "evaluation-partition",
    "row-provenance",
]

V1_VALIDATOR_VERSION = "1"
V1_ARTIFACT_ROLES: tuple[ArtifactRole, ...] = (
    "plan",
    "recipe",
    "construction-result",
    "curation-result",
    "split-result",
    "row-set",
)
V1_FILE_ROLES: tuple[FileRole, ...] = (
    "training-partition",
    "evaluation-partition",
    "row-provenance",
)
V1_FILE_PATHS: tuple[str, ...] = (
    "data/train.jsonl",
    "data/evaluation.jsonl",
    "metadata/row-provenance.jsonl",
)

_ARTIFACT_CONTRACTS: Mapping[ArtifactRole, tuple[str, str]] = {
    "plan": ("veriformis.finished-dataset-plan/v1", "fdp"),
    "recipe": ("veriformis.dataset-recipe/v1", "rcp"),
    "construction-result": ("veriformis.construction-result/v1", "run"),
    "curation-result": ("veriformis.curation-result/v1", "cur"),
    "split-result": ("veriformis.split-result/v1", "spt"),
    "row-set": ("veriformis.row-set/v1", "rws"),
}
_FILE_CONTRACTS: Mapping[FileRole, tuple[str, str]] = {
    "training-partition": ("data/train.jsonl", "application/jsonl"),
    "evaluation-partition": ("data/evaluation.jsonl", "application/jsonl"),
    "row-provenance": (
        "metadata/row-provenance.jsonl",
        "application/jsonl",
    ),
}
_FINDING_CODE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        reject_floats(value)
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


def _require_nonnegative_integer(value: int, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _revalidate_nested(
    value: BaseModel,
    model_type: type[BaseModel],
    *,
    label: str,
) -> None:
    try:
        checked = model_type.model_validate_json(
            lossless_json_bytes(value.model_dump(mode="json"))
        )
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid nested {label}: {exc}") from exc
    if checked != value:
        raise ValueError(f"nested {label} does not round-trip exactly")


class SnapshotArtifactBinding(_StrictModel):
    """Identity and byte binding for one semantic snapshot artifact."""

    schema_version: Literal["veriformis.snapshot-artifact-binding/v1"] = (
        "veriformis.snapshot-artifact-binding/v1"
    )
    role: ArtifactRole
    artifact_id: str
    artifact_schema_version: str
    sha256: str
    byte_size: int

    @model_validator(mode="after")
    def _validate_binding(self) -> SnapshotArtifactBinding:
        expected_schema, identity_kind = _ARTIFACT_CONTRACTS[self.role]
        validate_id(self.artifact_id, kind=identity_kind)
        if self.artifact_schema_version != expected_schema:
            raise ValueError("snapshot artifact schema differs from its role")
        validate_sha256(self.sha256)
        _require_nonnegative_integer(self.byte_size, "artifact byte_size")
        if self.byte_size == 0:
            raise ValueError("snapshot semantic artifact cannot be empty")
        return self

    @classmethod
    def create(
        cls,
        *,
        role: ArtifactRole,
        artifact_id: str,
        artifact_bytes: bytes,
    ) -> SnapshotArtifactBinding:
        if not isinstance(artifact_bytes, bytes):
            raise DatasetValidationError("snapshot artifact bytes must be exact bytes")
        return cls(
            schema_version="veriformis.snapshot-artifact-binding/v1",
            role=role,
            artifact_id=artifact_id,
            artifact_schema_version=_ARTIFACT_CONTRACTS[role][0],
            sha256=sha256_digest(artifact_bytes),
            byte_size=len(artifact_bytes),
        )


class SnapshotFileBinding(_StrictModel):
    """Canonical path and exact byte binding for one emitted JSONL file."""

    schema_version: Literal["veriformis.snapshot-file-binding/v1"] = (
        "veriformis.snapshot-file-binding/v1"
    )
    path: str
    role: FileRole
    media_type: Literal["application/jsonl"] = "application/jsonl"
    sha256: str
    byte_size: int
    record_count: int

    @model_validator(mode="after")
    def _validate_binding(self) -> SnapshotFileBinding:
        expected_path, expected_media_type = _FILE_CONTRACTS[self.role]
        if self.path != expected_path or self.media_type != expected_media_type:
            raise ValueError("snapshot file path or media type differs from its role")
        validate_sha256(self.sha256)
        _require_nonnegative_integer(self.byte_size, "file byte_size")
        _require_nonnegative_integer(self.record_count, "file record_count")
        return self

    @classmethod
    def create(
        cls,
        *,
        role: FileRole,
        file_bytes: bytes,
        record_count: int,
    ) -> SnapshotFileBinding:
        if not isinstance(file_bytes, bytes):
            raise DatasetValidationError("snapshot file bytes must be exact bytes")
        path, media_type = _FILE_CONTRACTS[role]
        return cls(
            schema_version="veriformis.snapshot-file-binding/v1",
            path=path,
            role=role,
            media_type=media_type,
            sha256=sha256_digest(file_bytes),
            byte_size=len(file_bytes),
            record_count=record_count,
        )


class SnapshotValidatorBinding(_StrictModel):
    """The validator implementation version selected for one required gate."""

    schema_version: Literal["veriformis.snapshot-validator-binding/v1"] = (
        "veriformis.snapshot-validator-binding/v1"
    )
    gate_id: str
    validator_version: Literal["1"] = V1_VALIDATOR_VERSION

    @model_validator(mode="after")
    def _validate_binding(self) -> SnapshotValidatorBinding:
        if self.gate_id not in V1_FINISHED_DATASET_GATES:
            raise ValueError("snapshot validator names an unsupported gate")
        return self


class DatasetSnapshot(_StrictModel):
    """Portable identity of all semantic values and files intended for seal."""

    schema_version: Literal["veriformis.dataset-snapshot/v1"] = (
        "veriformis.dataset-snapshot/v1"
    )
    snapshot_id: str
    plan_id: str
    recipe_id: str
    construction_result_id: str
    curation_result_id: str
    split_result_id: str
    row_set_id: str
    source_ids: tuple[str, ...]
    artifact_bindings: tuple[SnapshotArtifactBinding, ...]
    file_bindings: tuple[SnapshotFileBinding, ...]
    validator_bindings: tuple[SnapshotValidatorBinding, ...]

    @model_validator(mode="after")
    def _validate_snapshot(self) -> DatasetSnapshot:
        validate_id(self.snapshot_id, kind="dss")
        explicit_ids = (
            validate_id(self.plan_id, kind="fdp"),
            validate_id(self.recipe_id, kind="rcp"),
            validate_id(self.construction_result_id, kind="run"),
            validate_id(self.curation_result_id, kind="cur"),
            validate_id(self.split_result_id, kind="spt"),
            validate_id(self.row_set_id, kind="rws"),
        )
        checked_sources = tuple(
            validate_id(value, kind="src") for value in self.source_ids
        )
        if not checked_sources:
            raise ValueError("dataset snapshot requires at least one source")
        if checked_sources != tuple(sorted(set(checked_sources))):
            raise ValueError("snapshot source_ids must be sorted and unique")

        for item in self.artifact_bindings:
            _revalidate_nested(
                item,
                SnapshotArtifactBinding,
                label="snapshot artifact binding",
            )
        if tuple(item.role for item in self.artifact_bindings) != V1_ARTIFACT_ROLES:
            raise ValueError("snapshot requires the exact ordered artifact registry")
        if tuple(item.artifact_id for item in self.artifact_bindings) != explicit_ids:
            raise ValueError("snapshot artifact bindings disagree with explicit IDs")

        for item in self.file_bindings:
            _revalidate_nested(item, SnapshotFileBinding, label="snapshot file binding")
        if tuple(item.role for item in self.file_bindings) != V1_FILE_ROLES:
            raise ValueError(
                "snapshot requires the exact ordered emitted-file registry"
            )
        if tuple(item.path for item in self.file_bindings) != V1_FILE_PATHS:
            raise ValueError("snapshot emitted paths are not canonical")
        train_binding, evaluation_binding, provenance_binding = self.file_bindings
        if train_binding.record_count < 1 or train_binding.byte_size < 1:
            raise ValueError("snapshot requires a non-empty train file")
        if (evaluation_binding.record_count == 0) != (
            evaluation_binding.byte_size == 0
        ):
            raise ValueError(
                "snapshot zero-record evaluation must be exactly zero bytes"
            )
        if (
            provenance_binding.record_count
            != train_binding.record_count + evaluation_binding.record_count
            or provenance_binding.byte_size < 1
        ):
            raise ValueError(
                "snapshot provenance count must equal all emitted dataset rows"
            )

        for item in self.validator_bindings:
            _revalidate_nested(
                item,
                SnapshotValidatorBinding,
                label="snapshot validator binding",
            )
        if tuple(item.gate_id for item in self.validator_bindings) != (
            V1_FINISHED_DATASET_GATES
        ):
            raise ValueError("snapshot requires the exact ordered validator registry")

        expected_id = derive_id(
            "dss",
            self.model_dump(mode="json", exclude={"snapshot_id"}),
        )
        if self.snapshot_id != expected_id:
            raise ValueError("dataset snapshot identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: FinishedDatasetPlan,
        recipe: DatasetRecipe,
        construction_result: ConstructionResult,
        curation_result: CurationResult,
        split_result: SplitResult,
        row_set: RowSet,
        train_jsonl: bytes,
        evaluation_jsonl: bytes,
        provenance_jsonl: bytes,
    ) -> DatasetSnapshot:
        plan = finished_dataset_plan_from_json_bytes(
            _value_bytes(plan, label="finished dataset plan")
        )
        recipe = dataset_recipe_from_json_bytes(
            _value_bytes(recipe, label="dataset recipe")
        )
        construction_result = construction_result_from_json_bytes(
            _value_bytes(construction_result, label="construction result")
        )
        curation_result = curation_result_from_json_bytes(
            _value_bytes(curation_result, label="curation result")
        )
        split_result = split_result_from_json_bytes(
            _value_bytes(split_result, label="split result")
        )
        row_set = row_set_from_json_bytes(_value_bytes(row_set, label="row set"))
        artifacts = _canonical_artifact_bytes(
            plan,
            recipe,
            construction_result,
            curation_result,
            split_result,
            row_set,
        )
        body = {
            "schema_version": "veriformis.dataset-snapshot/v1",
            "plan_id": plan.plan_id,
            "recipe_id": recipe.recipe_id,
            "construction_result_id": construction_result.result_id,
            "curation_result_id": curation_result.result_id,
            "split_result_id": split_result.result_id,
            "row_set_id": row_set.row_set_id,
            "source_ids": recipe.source_ids,
            "artifact_bindings": tuple(
                SnapshotArtifactBinding.create(
                    role=role,
                    artifact_id=artifact_id,
                    artifact_bytes=artifacts[role],
                )
                for role, artifact_id in zip(
                    V1_ARTIFACT_ROLES,
                    (
                        plan.plan_id,
                        recipe.recipe_id,
                        construction_result.result_id,
                        curation_result.result_id,
                        split_result.result_id,
                        row_set.row_set_id,
                    ),
                )
            ),
            "file_bindings": (
                SnapshotFileBinding.create(
                    role="training-partition",
                    file_bytes=train_jsonl,
                    record_count=row_set.train_row_count,
                ),
                SnapshotFileBinding.create(
                    role="evaluation-partition",
                    file_bytes=evaluation_jsonl,
                    record_count=row_set.evaluation_row_count,
                ),
                SnapshotFileBinding.create(
                    role="row-provenance",
                    file_bytes=provenance_jsonl,
                    record_count=row_set.total_row_count,
                ),
            ),
            "validator_bindings": tuple(
                SnapshotValidatorBinding(
                    schema_version="veriformis.snapshot-validator-binding/v1",
                    gate_id=gate_id,
                    validator_version=V1_VALIDATOR_VERSION,
                )
                for gate_id in V1_FINISHED_DATASET_GATES
            ),
        }
        return cls(snapshot_id=derive_id("dss", body), **body)


class DatasetGateResult(_StrictModel):
    """One deterministic gate disposition for one exact snapshot."""

    schema_version: Literal["veriformis.dataset-gate-result/v1"] = (
        "veriformis.dataset-gate-result/v1"
    )
    gate_result_id: str
    snapshot_id: str
    gate_id: str
    validator_version: Literal["1"] = V1_VALIDATOR_VERSION
    status: GateStatus
    finding_codes: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_result(self) -> DatasetGateResult:
        validate_id(self.gate_result_id, kind="dgr")
        validate_id(self.snapshot_id, kind="dss")
        if self.gate_id not in V1_FINISHED_DATASET_GATES:
            raise ValueError("dataset gate result names an unsupported gate")
        if any(_FINDING_CODE.fullmatch(code) is None for code in self.finding_codes):
            raise ValueError("dataset gate finding code is malformed")
        if self.finding_codes != tuple(sorted(set(self.finding_codes))):
            raise ValueError("dataset gate finding codes must be sorted and unique")
        if self.status == "passed" and self.finding_codes:
            raise ValueError("a passing dataset gate cannot contain findings")
        if self.status != "passed" and not self.finding_codes:
            raise ValueError("a failed or blocked dataset gate requires a finding")
        expected_id = derive_id(
            "dgr",
            self.model_dump(mode="json", exclude={"gate_result_id"}),
        )
        if self.gate_result_id != expected_id:
            raise ValueError("dataset gate result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: str,
        gate_id: str,
        status: GateStatus,
        finding_codes: Sequence[str] = (),
    ) -> DatasetGateResult:
        body = {
            "schema_version": "veriformis.dataset-gate-result/v1",
            "snapshot_id": snapshot_id,
            "gate_id": gate_id,
            "validator_version": V1_VALIDATOR_VERSION,
            "status": status,
            "finding_codes": tuple(sorted(finding_codes)),
        }
        return cls(gate_result_id=derive_id("dgr", body), **body)


class DatasetValidationReport(_StrictModel):
    """Complete ordered gate report, including its independently loadable snapshot."""

    schema_version: Literal["veriformis.dataset-validation-report/v1"] = (
        "veriformis.dataset-validation-report/v1"
    )
    report_id: str
    snapshot_id: str
    snapshot: DatasetSnapshot
    status: ValidationStatus
    gate_results: tuple[DatasetGateResult, ...]

    @model_validator(mode="after")
    def _validate_report(self) -> DatasetValidationReport:
        validate_id(self.report_id, kind="dvr")
        validate_id(self.snapshot_id, kind="dss")
        _revalidate_nested(self.snapshot, DatasetSnapshot, label="dataset snapshot")
        if self.snapshot.snapshot_id != self.snapshot_id:
            raise ValueError("validation report snapshot identity disagrees")
        for result in self.gate_results:
            _revalidate_nested(result, DatasetGateResult, label="dataset gate result")
        if tuple(result.gate_id for result in self.gate_results) != (
            V1_FINISHED_DATASET_GATES
        ):
            raise ValueError("validation report requires every ordered v1 gate")
        if any(result.snapshot_id != self.snapshot_id for result in self.gate_results):
            raise ValueError("validation gate result names another snapshot")
        expected_status: ValidationStatus = (
            "passed"
            if all(result.status == "passed" for result in self.gate_results)
            else "failed"
        )
        if self.status != expected_status:
            raise ValueError("validation report status contradicts its gate results")
        expected_id = derive_id(
            "dvr",
            self.model_dump(mode="json", exclude={"report_id"}),
        )
        if self.report_id != expected_id:
            raise ValueError("dataset validation report identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        snapshot: DatasetSnapshot,
        gate_results: Sequence[DatasetGateResult],
    ) -> DatasetValidationReport:
        checked_results = tuple(gate_results)
        status: ValidationStatus = (
            "passed"
            if all(result.status == "passed" for result in checked_results)
            else "failed"
        )
        body = {
            "schema_version": "veriformis.dataset-validation-report/v1",
            "snapshot_id": snapshot.snapshot_id,
            "snapshot": snapshot,
            "status": status,
            "gate_results": checked_results,
        }
        return cls(report_id=derive_id("dvr", body), **body)


ModelT = TypeVar("ModelT", bound=_StrictModel)


def _model_to_dict(
    value: ModelT,
    model_type: type[ModelT],
    *,
    label: str,
) -> dict[str, Any]:
    try:
        payload = value.model_dump(mode="json")
        reject_floats(payload)
        checked = model_type.model_validate_json(lossless_json_bytes(payload))
    except DuplicateIdentityError:
        raise
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise DatasetValidationError(f"invalid {label}: {exc}") from exc
    if checked != value:
        raise DatasetValidationError(f"{label} does not round-trip exactly")
    return payload


def _model_from_json_bytes(
    data: bytes,
    model_type: type[ModelT],
    *,
    label: str,
) -> ModelT:
    try:
        canonical_json_object_from_bytes(data, label=label)
        return model_type.model_validate_json(data)
    except DuplicateIdentityError:
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise DatasetValidationError(f"invalid {label}: {exc}") from exc


def _model_from_dict(
    value: dict[str, Any],
    model_type: type[ModelT],
    *,
    label: str,
) -> ModelT:
    try:
        return _model_from_json_bytes(
            lossless_json_bytes(value),
            model_type,
            label=label,
        )
    except (DuplicateIdentityError, DatasetValidationError):
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise DatasetValidationError(f"invalid {label}: {exc}") from exc


def dataset_snapshot_to_dict(value: DatasetSnapshot) -> dict[str, Any]:
    return _model_to_dict(value, DatasetSnapshot, label="dataset snapshot")


def dataset_snapshot_from_json_bytes(data: bytes) -> DatasetSnapshot:
    return _model_from_json_bytes(data, DatasetSnapshot, label="dataset snapshot")


def dataset_snapshot_from_dict(value: dict[str, Any]) -> DatasetSnapshot:
    return _model_from_dict(value, DatasetSnapshot, label="dataset snapshot")


def dataset_snapshot_json_bytes(value: DatasetSnapshot) -> bytes:
    return lossless_json_bytes(dataset_snapshot_to_dict(value))


def dataset_gate_result_to_dict(value: DatasetGateResult) -> dict[str, Any]:
    return _model_to_dict(value, DatasetGateResult, label="dataset gate result")


def dataset_gate_result_from_json_bytes(data: bytes) -> DatasetGateResult:
    return _model_from_json_bytes(data, DatasetGateResult, label="dataset gate result")


def dataset_gate_result_from_dict(value: dict[str, Any]) -> DatasetGateResult:
    return _model_from_dict(value, DatasetGateResult, label="dataset gate result")


def dataset_validation_report_to_dict(
    value: DatasetValidationReport,
) -> dict[str, Any]:
    return _model_to_dict(
        value,
        DatasetValidationReport,
        label="dataset validation report",
    )


def dataset_validation_report_from_json_bytes(
    data: bytes,
) -> DatasetValidationReport:
    return _model_from_json_bytes(
        data,
        DatasetValidationReport,
        label="dataset validation report",
    )


def dataset_validation_report_from_dict(
    value: dict[str, Any],
) -> DatasetValidationReport:
    return _model_from_dict(
        value,
        DatasetValidationReport,
        label="dataset validation report",
    )


def dataset_validation_report_json_bytes(
    value: DatasetValidationReport,
) -> bytes:
    """Return the canonical validation.json bytes used by the bundle contract."""
    return lossless_json_bytes(dataset_validation_report_to_dict(value))


def _value_bytes(value: BaseModel | bytes, *, label: str) -> bytes:
    if isinstance(value, bytes):
        return value
    try:
        return lossless_json_bytes(value.model_dump(mode="json"))
    except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
        raise DatasetValidationError(f"cannot serialize {label}: {exc}") from exc


def _canonical_artifact_bytes(
    plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    split_result: SplitResult,
    row_set: RowSet,
) -> dict[ArtifactRole, bytes]:
    return {
        "plan": _value_bytes(plan, label="finished dataset plan"),
        "recipe": _value_bytes(recipe, label="dataset recipe"),
        "construction-result": _value_bytes(
            construction_result,
            label="construction result",
        ),
        "curation-result": _value_bytes(curation_result, label="curation result"),
        "split-result": _value_bytes(split_result, label="split result"),
        "row-set": _value_bytes(row_set, label="row set"),
    }


def create_dataset_snapshot(
    plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    split_result: SplitResult,
    row_set: RowSet,
    *,
    train_jsonl: bytes,
    evaluation_jsonl: bytes,
    provenance_jsonl: bytes,
) -> DatasetSnapshot:
    """Create a snapshot over exact persisted artifacts and emitted bytes."""
    try:
        checked_plan = finished_dataset_plan_from_json_bytes(
            _value_bytes(plan, label="finished dataset plan")
        )
        checked_recipe = dataset_recipe_from_json_bytes(
            _value_bytes(recipe, label="dataset recipe")
        )
        checked_construction = construction_result_from_json_bytes(
            _value_bytes(construction_result, label="construction result")
        )
        checked_curation = curation_result_from_json_bytes(
            _value_bytes(curation_result, label="curation result")
        )
        checked_split = split_result_from_json_bytes(
            _value_bytes(split_result, label="split result")
        )
        checked_row_set = row_set_from_json_bytes(
            _value_bytes(row_set, label="row set")
        )
        return DatasetSnapshot.create(
            plan=checked_plan,
            recipe=checked_recipe,
            construction_result=checked_construction,
            curation_result=checked_curation,
            split_result=checked_split,
            row_set=checked_row_set,
            train_jsonl=train_jsonl,
            evaluation_jsonl=evaluation_jsonl,
            provenance_jsonl=provenance_jsonl,
        )
    except DuplicateIdentityError:
        raise
    except DatasetValidationError:
        raise
    except (
        AttributeError,
        TypeError,
        UnicodeError,
        ValueError,
        VeriformisError,
    ) as exc:
        raise DatasetValidationError(f"cannot create dataset snapshot: {exc}") from exc


def _gate(
    snapshot_id: str,
    gate_id: str,
    status: GateStatus,
    *finding_codes: str,
) -> DatasetGateResult:
    return DatasetGateResult.create(
        snapshot_id=snapshot_id,
        gate_id=gate_id,
        status=status,
        finding_codes=finding_codes,
    )


def _snapshot_findings(
    snapshot: DatasetSnapshot,
    *,
    artifacts: Mapping[ArtifactRole, bytes],
    train_jsonl: bytes,
    evaluation_jsonl: bytes,
    provenance_jsonl: bytes,
    row_set: RowSet | None,
) -> tuple[str, ...]:
    findings: set[str] = set()
    for binding in snapshot.artifact_bindings:
        value = artifacts.get(binding.role)
        if value is None:
            findings.add("snapshot-artifact-unavailable")
        elif binding.sha256 != sha256_digest(value) or binding.byte_size != len(value):
            findings.add("snapshot-artifact-digest-mismatch")

    file_values = {
        "training-partition": train_jsonl,
        "evaluation-partition": evaluation_jsonl,
        "row-provenance": provenance_jsonl,
    }
    for binding in snapshot.file_bindings:
        value = file_values[binding.role]
        if binding.sha256 != sha256_digest(value) or binding.byte_size != len(value):
            findings.add("snapshot-file-digest-mismatch")

    if row_set is None:
        findings.add("snapshot-row-set-unavailable")
    else:
        expected_counts = (
            row_set.train_row_count,
            row_set.evaluation_row_count,
            row_set.total_row_count,
        )
        if (
            tuple(item.record_count for item in snapshot.file_bindings)
            != expected_counts
        ):
            findings.add("snapshot-record-count-mismatch")
        expected_file_metadata = (
            (
                row_set.train_jsonl_sha256,
                row_set.train_jsonl_byte_size,
            ),
            (
                row_set.evaluation_jsonl_sha256,
                row_set.evaluation_jsonl_byte_size,
            ),
            (
                row_set.provenance_jsonl_sha256,
                row_set.provenance_jsonl_byte_size,
            ),
        )
        actual_file_metadata = tuple(
            (item.sha256, item.byte_size) for item in snapshot.file_bindings
        )
        if actual_file_metadata != expected_file_metadata:
            findings.add("snapshot-row-set-file-mismatch")
    return tuple(sorted(findings))


def _blocked(
    results: dict[str, DatasetGateResult],
    snapshot_id: str,
    gate_ids: Sequence[str],
    finding_code: str,
) -> None:
    for gate_id in gate_ids:
        results.setdefault(
            gate_id,
            _gate(snapshot_id, gate_id, "blocked", finding_code),
        )


def _raw_digest_mapping(inputs: ConstructionInputs) -> dict[str, str]:
    return {source.id: source.sha256 for source in inputs.sources}


def validate_dataset_snapshot(
    snapshot: DatasetSnapshot,
    *,
    plan: FinishedDatasetPlan | bytes,
    recipe: DatasetRecipe | bytes,
    construction_inputs: ConstructionInputs,
    construction_result: ConstructionResult | bytes,
    curation_result: CurationResult | bytes,
    split_result: SplitResult | bytes,
    row_set: RowSet | bytes,
    train_jsonl: bytes,
    evaluation_jsonl: bytes,
    provenance_jsonl: bytes,
) -> DatasetValidationReport:
    """Replay all stages and report every gate for the supplied snapshot.

    The six semantic artifacts may be supplied as exact canonical bytes. This
    lets validation preserve a failed report when a persisted critical input is
    unreadable. Gates that depend on that input are explicitly blocked.
    """
    checked_snapshot = dataset_snapshot_from_json_bytes(
        dataset_snapshot_json_bytes(snapshot)
    )
    snapshot_id = checked_snapshot.snapshot_id
    results: dict[str, DatasetGateResult] = {}
    artifact_bytes: dict[ArtifactRole, bytes] = {}
    for role, value in (
        ("plan", plan),
        ("recipe", recipe),
        ("construction-result", construction_result),
        ("curation-result", curation_result),
        ("split-result", split_result),
        ("row-set", row_set),
    ):
        try:
            artifact_bytes[role] = _value_bytes(value, label=role)
        except DatasetValidationError:
            artifact_bytes[role] = b""

    checked_plan: FinishedDatasetPlan | None = None
    checked_recipe: DatasetRecipe | None = None
    checked_construction: ConstructionResult | None = None
    checked_curation: CurationResult | None = None
    checked_split: SplitResult | None = None
    checked_row_set: RowSet | None = None
    replay_output: SerializationOutput | None = None

    try:
        checked_plan = finished_dataset_plan_from_json_bytes(artifact_bytes["plan"])
        checked_recipe = dataset_recipe_from_json_bytes(artifact_bytes["recipe"])
        checked_construction = construction_result_from_json_bytes(
            artifact_bytes["construction-result"]
        )
        checked_inputs = ConstructionInputs.model_validate_json(
            lossless_json_bytes(construction_inputs.model_dump(mode="json"))
        )
    except (
        AttributeError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
        VeriformisError,
    ):
        results["construction-replay"] = _gate(
            snapshot_id,
            "construction-replay",
            "failed",
            "critical-input-load-failed",
        )
        _blocked(
            results,
            snapshot_id,
            V1_FINISHED_DATASET_GATES[1:16],
            "construction-replay-unavailable",
        )
    else:
        try:
            validate_construction_result(
                checked_recipe,
                checked_inputs,
                checked_construction,
            )
            if (
                checked_plan.recipe_id != checked_recipe.recipe_id
                or checked_plan.construction_result_id != checked_construction.result_id
                or checked_snapshot.plan_id != checked_plan.plan_id
                or checked_snapshot.recipe_id != checked_recipe.recipe_id
                or checked_snapshot.construction_result_id
                != checked_construction.result_id
                or checked_snapshot.source_ids != checked_recipe.source_ids
            ):
                raise ValueError("construction identities differ from the snapshot")
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ):
            results["construction-replay"] = _gate(
                snapshot_id,
                "construction-replay",
                "failed",
                "construction-replay-mismatch",
            )
            _blocked(
                results,
                snapshot_id,
                V1_FINISHED_DATASET_GATES[1:16],
                "construction-replay-unavailable",
            )
        else:
            results["construction-replay"] = _gate(
                snapshot_id,
                "construction-replay",
                "passed",
            )
            results["record-lifecycle"] = _gate(
                snapshot_id,
                "record-lifecycle",
                "passed",
            )

    if results["construction-replay"].status == "passed":
        assert checked_plan is not None
        assert checked_recipe is not None
        assert checked_construction is not None
        try:
            checked_curation = curation_result_from_json_bytes(
                artifact_bytes["curation-result"]
            )
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ):
            results["curation"] = _gate(
                snapshot_id,
                "curation",
                "failed",
                "critical-input-load-failed",
            )
        else:
            try:
                replayed_curation = curate_dataset(
                    checked_plan,
                    checked_recipe,
                    construction_inputs,
                    checked_construction,
                )
                if checked_curation != replayed_curation:
                    raise ValueError("curation result differs from replay")
                if checked_snapshot.curation_result_id != checked_curation.result_id:
                    raise ValueError("curation identity differs from snapshot")
            except (
                AttributeError,
                RecursionError,
                TypeError,
                UnicodeError,
                ValueError,
                VeriformisError,
            ):
                results["curation"] = _gate(
                    snapshot_id,
                    "curation",
                    "failed",
                    "curation-replay-mismatch",
                )
        if results.get("curation", None) is not None and (
            results["curation"].status == "failed"
        ):
            _blocked(
                results,
                snapshot_id,
                ("deduplication", "quality", "balance", "coverage"),
                "curation-unavailable",
            )
            _blocked(
                results,
                snapshot_id,
                V1_FINISHED_DATASET_GATES[7:16],
                "curation-unavailable",
            )
        else:
            assert checked_curation is not None
            for gate_id in ("curation", "deduplication", "quality", "balance"):
                results[gate_id] = _gate(snapshot_id, gate_id, "passed")
            blockers = tuple(
                blocker
                for entry in checked_curation.coverage_ledger.entries
                for blocker in entry.blocker_codes
            )
            results["coverage"] = (
                _gate(snapshot_id, "coverage", "passed")
                if not blockers
                else _gate(
                    snapshot_id,
                    "coverage",
                    "failed",
                    "coverage-blocker-present",
                )
            )

    if results.get("curation", None) is not None and (
        results["curation"].status == "passed"
    ):
        assert checked_plan is not None
        assert checked_construction is not None
        assert checked_curation is not None
        try:
            checked_split = split_result_from_json_bytes(artifact_bytes["split-result"])
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ):
            results["split"] = _gate(
                snapshot_id,
                "split",
                "failed",
                "critical-input-load-failed",
            )
        else:
            try:
                validate_split_result(
                    checked_plan,
                    checked_construction,
                    checked_curation,
                    _raw_digest_mapping(construction_inputs),
                    checked_split,
                )
                if checked_snapshot.split_result_id != checked_split.result_id:
                    raise ValueError("split identity differs from snapshot")
            except (
                AttributeError,
                RecursionError,
                TypeError,
                UnicodeError,
                ValueError,
                VeriformisError,
            ):
                results["split"] = _gate(
                    snapshot_id,
                    "split",
                    "failed",
                    "split-replay-mismatch",
                )
        if results.get("split", None) is not None and (
            results["split"].status == "failed"
        ):
            results["leakage"] = _gate(
                snapshot_id,
                "leakage",
                "blocked",
                "split-unavailable",
            )
            _blocked(
                results,
                snapshot_id,
                V1_FINISHED_DATASET_GATES[9:16],
                "split-unavailable",
            )
        else:
            assert checked_split is not None
            results["split"] = _gate(snapshot_id, "split", "passed")
            results["leakage"] = _gate(snapshot_id, "leakage", "passed")

    if results.get("split", None) is not None and results["split"].status == "passed":
        assert checked_plan is not None
        assert checked_recipe is not None
        assert checked_construction is not None
        assert checked_curation is not None
        assert checked_split is not None
        try:
            checked_row_set = row_set_from_json_bytes(artifact_bytes["row-set"])
        except (
            AttributeError,
            RecursionError,
            TypeError,
            UnicodeError,
            ValueError,
            VeriformisError,
        ):
            results["row-binding"] = _gate(
                snapshot_id,
                "row-binding",
                "failed",
                "critical-input-load-failed",
            )
        else:
            try:
                replay_output = serialize_dataset(
                    checked_plan,
                    checked_recipe,
                    checked_construction,
                    checked_curation,
                    checked_split,
                )
                if checked_row_set != replay_output.row_set:
                    raise ValueError("row set differs from serialization replay")
                if checked_snapshot.row_set_id != checked_row_set.row_set_id:
                    raise ValueError("row-set identity differs from snapshot")
            except (
                AttributeError,
                RecursionError,
                TypeError,
                UnicodeError,
                ValueError,
                VeriformisError,
            ):
                results["row-binding"] = _gate(
                    snapshot_id,
                    "row-binding",
                    "failed",
                    "row-set-replay-mismatch",
                )
        if results.get("row-binding", None) is not None and (
            results["row-binding"].status == "failed"
        ):
            _blocked(
                results,
                snapshot_id,
                ("objective", "schema", "encoding", "masking"),
                "row-set-unavailable",
            )
            _blocked(
                results,
                snapshot_id,
                ("partition-nonempty", "aptus-row-shape"),
                "row-set-unavailable",
            )
        else:
            assert checked_row_set is not None
            assert replay_output is not None
            for gate_id in ("row-binding", "objective", "schema", "masking"):
                results[gate_id] = _gate(snapshot_id, gate_id, "passed")
            exact_bytes = (
                replay_output.train_jsonl == train_jsonl
                and replay_output.evaluation_jsonl == evaluation_jsonl
                and replay_output.provenance_jsonl == provenance_jsonl
            )
            results["encoding"] = (
                _gate(snapshot_id, "encoding", "passed")
                if exact_bytes
                else _gate(
                    snapshot_id,
                    "encoding",
                    "failed",
                    "emitted-bytes-mismatch",
                )
            )
            partition_ok = bool(checked_row_set.train_rows) and (
                bool(checked_row_set.evaluation_rows)
                or not checked_plan.split_policy.evaluation_required
            )
            results["partition-nonempty"] = (
                _gate(snapshot_id, "partition-nonempty", "passed")
                if partition_ok
                else _gate(
                    snapshot_id,
                    "partition-nonempty",
                    "failed",
                    "required-partition-empty",
                )
            )
            results["aptus-row-shape"] = _gate(
                snapshot_id,
                "aptus-row-shape",
                "passed",
            )

    snapshot_findings = _snapshot_findings(
        checked_snapshot,
        artifacts=artifact_bytes,
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
        row_set=checked_row_set,
    )
    results["snapshot"] = (
        _gate(snapshot_id, "snapshot", "passed")
        if not snapshot_findings
        else _gate(snapshot_id, "snapshot", "failed", *snapshot_findings)
    )

    _blocked(
        results,
        snapshot_id,
        V1_FINISHED_DATASET_GATES[:-1],
        "required-input-unavailable",
    )
    ordered_results = tuple(results[gate_id] for gate_id in V1_FINISHED_DATASET_GATES)
    return DatasetValidationReport.create(
        snapshot=checked_snapshot,
        gate_results=ordered_results,
    )


def validate_finished_dataset(
    plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction_inputs: ConstructionInputs,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    split_result: SplitResult,
    row_set: RowSet,
    *,
    train_jsonl: bytes,
    evaluation_jsonl: bytes,
    provenance_jsonl: bytes,
) -> DatasetValidationReport:
    """Snapshot and validate one in-memory finished dataset in one call."""
    snapshot = create_dataset_snapshot(
        plan,
        recipe,
        construction_result,
        curation_result,
        split_result,
        row_set,
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
    )
    return validate_dataset_snapshot(
        snapshot,
        plan=plan,
        recipe=recipe,
        construction_inputs=construction_inputs,
        construction_result=construction_result,
        curation_result=curation_result,
        split_result=split_result,
        row_set=row_set,
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
    )


__all__ = [
    "V1_ARTIFACT_ROLES",
    "V1_FILE_PATHS",
    "V1_FILE_ROLES",
    "V1_VALIDATOR_VERSION",
    "DatasetGateResult",
    "DatasetSnapshot",
    "DatasetValidationReport",
    "SnapshotArtifactBinding",
    "SnapshotFileBinding",
    "SnapshotValidatorBinding",
    "create_dataset_snapshot",
    "dataset_gate_result_from_dict",
    "dataset_gate_result_from_json_bytes",
    "dataset_gate_result_to_dict",
    "dataset_snapshot_from_dict",
    "dataset_snapshot_from_json_bytes",
    "dataset_snapshot_json_bytes",
    "dataset_snapshot_to_dict",
    "dataset_validation_report_from_dict",
    "dataset_validation_report_from_json_bytes",
    "dataset_validation_report_json_bytes",
    "dataset_validation_report_to_dict",
    "validate_dataset_snapshot",
    "validate_finished_dataset",
]
