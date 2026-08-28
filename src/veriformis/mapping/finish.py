"""Curation, split, format, validate, and seal over imported records.

Imported rows never become DatasetRecord values and never invent chunk ids.
Format emits ordinary ProductRow v1 payloads. Provenance names mapping rules.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import field_validator, model_validator

from veriformis.contracts import V1_DATASET_PARTITIONS
from veriformis.datasets.models import (
    CoverageLedger,
    CoverageLedgerEntry,
    CurationPolicy,
    CurationReasonCode,
    CurationStatus,
)
from veriformis.datasets.plan import V1_BUNDLE_RETENTION_PROFILE
from veriformis.datasets.serialization import (
    ProductRow,
    SerializationPlan,
    _payload_contract,
)
from veriformis.datasets.splitting import Partition, SplitPolicy
from veriformis.datasets.validation import SnapshotFileBinding
from veriformis.errors import (
    CurationError,
    DatasetValidationError,
    DuplicateIdentityError,
    MappingError,
    SplitError,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
)
from veriformis.mapping.models import (
    ImportedRecord,
    MappingPlan,
    RowSchema,
    _StrictModel,
)
from veriformis.mapping.result import MappingRecipe, MappingResult

IMPORT_CURATION_STAGE_SCHEMA_ID = "veriformis.curation-stage/v1"
IMPORT_PLAN_SCHEMA = "veriformis.finished-import-plan/v1"
IMPORT_CURATION_SCHEMA = "veriformis.imported-curation-result/v1"
IMPORT_SPLIT_SCHEMA = "veriformis.imported-split-result/v1"
IMPORT_ROW_SET_SCHEMA = "veriformis.imported-row-set/v1"
IMPORT_PROVENANCE_SCHEMA = "veriformis.imported-row-provenance/v1"
IMPORT_SNAPSHOT_SCHEMA = "veriformis.imported-dataset-snapshot/v1"
IMPORT_VALIDATION_SCHEMA = "veriformis.imported-dataset-validation-report/v1"
IMPORT_GATES: tuple[str, ...] = (
    "mapping-replay",
    "record-lifecycle",
    "curation",
    "deduplication",
    "quality",
    "coverage",
    "split",
    "leakage",
    "row-binding",
    "schema",
    "encoding",
    "partition-nonempty",
    "snapshot",
)
_RATIO_SCALE = 1_000_000


def _tuple(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def _sorted_ids(values: tuple[str, ...], *, kind: str, field: str) -> tuple[str, ...]:
    checked = tuple(validate_id(item, kind=kind) for item in values)
    if len(checked) != len(set(checked)):
        raise DuplicateIdentityError(f"{field} contains duplicate identities")
    if checked != tuple(sorted(checked)):
        raise ValueError(f"{field} must be sorted in canonical order")
    return values


class FinishedImportPlan(_StrictModel):
    schema_version: Literal["veriformis.finished-import-plan/v1"]
    plan_id: str
    recipe_id: str
    mapping_result_id: str
    curation_policy: CurationPolicy
    split_policy: SplitPolicy
    serialization_plan: SerializationPlan
    required_partitions: tuple[Literal["train", "evaluation"], ...]
    bundle_retention_profile: Literal["minimal-v1"]

    @field_validator("required_partitions", mode="before")
    @classmethod
    def _parts(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> FinishedImportPlan:
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.mapping_result_id, kind="imr")
        if self.required_partitions != V1_DATASET_PARTITIONS:
            raise MappingError("finished import plan requires train then evaluation")
        if self.bundle_retention_profile != V1_BUNDLE_RETENTION_PROFILE:
            raise MappingError("unsupported finished import retention profile")
        expected = derive_id("fip", self.model_dump(mode="json", exclude={"plan_id"}))
        if self.plan_id != expected:
            raise MappingError("finished import plan identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        recipe_id: str,
        mapping_result_id: str,
        curation_policy: CurationPolicy,
        split_policy: SplitPolicy,
        serialization_plan: SerializationPlan,
    ) -> FinishedImportPlan:
        body = {
            "schema_version": IMPORT_PLAN_SCHEMA,
            "recipe_id": recipe_id,
            "mapping_result_id": mapping_result_id,
            "curation_policy": curation_policy,
            "split_policy": split_policy,
            "serialization_plan": serialization_plan,
            "required_partitions": V1_DATASET_PARTITIONS,
            "bundle_retention_profile": V1_BUNDLE_RETENTION_PROFILE,
        }
        return cls(plan_id=derive_id("fip", body), **body)


class ImportedQualityFinding(_StrictModel):
    schema_version: Literal["veriformis.imported-quality-finding/v1"]
    finding_id: str
    record_id: str
    code: Literal[
        "target-too-short",
        "exact-duplicate",
        "conflicting-target",
        "primary-source-cap",
    ]
    related_record_ids: tuple[str, ...]
    observed_count: int | None
    required_count: int | None

    @field_validator("related_record_ids", mode="before")
    @classmethod
    def _rel(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedQualityFinding:
        validate_id(self.record_id, kind="irc")
        _sorted_ids(
            self.related_record_ids,
            kind="irc",
            field="imported quality finding related_record_ids",
        )
        expected = derive_id("qfn", self.model_dump(mode="json", exclude={"finding_id"}))
        if self.finding_id != expected:
            raise MappingError("imported quality finding identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        code: str,
        related_record_ids: tuple[str, ...] = (),
        observed_count: int | None = None,
        required_count: int | None = None,
    ) -> ImportedQualityFinding:
        body = {
            "schema_version": "veriformis.imported-quality-finding/v1",
            "record_id": record_id,
            "code": code,
            "related_record_ids": tuple(sorted(related_record_ids)),
            "observed_count": observed_count,
            "required_count": required_count,
        }
        return cls(finding_id=derive_id("qfn", body), **body)


class ImportedCurationDecision(_StrictModel):
    schema_version: Literal["veriformis.imported-curation-decision/v1"]
    decision_id: str
    record_id: str
    status: CurationStatus
    reason_codes: tuple[CurationReasonCode, ...]
    finding_ids: tuple[str, ...]

    @field_validator("reason_codes", "finding_ids", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedCurationDecision:
        validate_id(self.record_id, kind="irc")
        if len(self.reason_codes) != 1:
            raise MappingError("imported curation decision requires one reason")
        expected = derive_id("cud", self.model_dump(mode="json", exclude={"decision_id"}))
        if self.decision_id != expected:
            raise MappingError("imported curation decision identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        status: CurationStatus,
        reason_code: CurationReasonCode,
        finding_ids: tuple[str, ...] = (),
    ) -> ImportedCurationDecision:
        body = {
            "schema_version": "veriformis.imported-curation-decision/v1",
            "record_id": record_id,
            "status": status,
            "reason_codes": (reason_code,),
            "finding_ids": tuple(sorted(finding_ids)),
        }
        return cls(decision_id=derive_id("cud", body), **body)


class ImportedCurationResult(_StrictModel):
    schema_version: Literal["veriformis.imported-curation-result/v1"]
    result_id: str
    plan_id: str
    recipe_id: str
    mapping_result_id: str
    policy_id: str
    input_record_ids: tuple[str, ...]
    decisions: tuple[ImportedCurationDecision, ...]
    findings: tuple[ImportedQualityFinding, ...]
    included_record_ids: tuple[str, ...]
    coverage_ledger: CoverageLedger

    @field_validator(
        "input_record_ids",
        "decisions",
        "findings",
        "included_record_ids",
        mode="before",
    )
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedCurationResult:
        validate_id(self.plan_id, kind="fip")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.mapping_result_id, kind="imr")
        validate_id(self.policy_id, kind="cpl")
        _sorted_ids(
            self.input_record_ids,
            kind="irc",
            field="imported curation input_record_ids",
        )
        expected_included = tuple(
            decision.record_id
            for decision in self.decisions
            if decision.status == "included"
        )
        if self.included_record_ids != expected_included:
            raise MappingError("imported included records do not match decisions")
        expected = derive_id("cur", self.model_dump(mode="json", exclude={"result_id"}))
        if self.result_id != expected:
            raise MappingError("imported curation result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        recipe_id: str,
        mapping_result_id: str,
        policy_id: str,
        input_record_ids: tuple[str, ...],
        decisions: tuple[ImportedCurationDecision, ...],
        findings: tuple[ImportedQualityFinding, ...],
        included_record_ids: tuple[str, ...],
        coverage_ledger: CoverageLedger,
    ) -> ImportedCurationResult:
        body = {
            "schema_version": IMPORT_CURATION_SCHEMA,
            "plan_id": plan_id,
            "recipe_id": recipe_id,
            "mapping_result_id": mapping_result_id,
            "policy_id": policy_id,
            "input_record_ids": input_record_ids,
            "decisions": [item.model_dump(mode="json") for item in decisions],
            "findings": [item.model_dump(mode="json") for item in findings],
            "included_record_ids": included_record_ids,
            "coverage_ledger": coverage_ledger,
        }
        return cls(result_id=derive_id("cur", body), **body)


class ImportedLeakageGroup(_StrictModel):
    schema_version: Literal["veriformis.imported-leakage-group/v1"]
    group_id: str
    record_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    raw_sha256_values: tuple[str, ...]
    exact_record_fingerprints: tuple[str, ...]

    @field_validator(
        "record_ids",
        "source_ids",
        "raw_sha256_values",
        "exact_record_fingerprints",
        mode="before",
    )
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedLeakageGroup:
        _sorted_ids(self.record_ids, kind="irc", field="imported leakage record_ids")
        _sorted_ids(self.source_ids, kind="src", field="imported leakage source_ids")
        expected = derive_id("lkg", self.model_dump(mode="json", exclude={"group_id"}))
        if self.group_id != expected:
            raise MappingError("imported leakage group identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_ids: Sequence[str],
        source_ids: Sequence[str],
        raw_sha256_values: Sequence[str],
        exact_record_fingerprints: Sequence[str],
    ) -> ImportedLeakageGroup:
        body = {
            "schema_version": "veriformis.imported-leakage-group/v1",
            "record_ids": tuple(sorted(record_ids)),
            "source_ids": tuple(sorted(source_ids)),
            "raw_sha256_values": tuple(raw_sha256_values),
            "exact_record_fingerprints": tuple(sorted(exact_record_fingerprints)),
        }
        return cls(group_id=derive_id("lkg", body), **body)


class ImportedRecordAssignment(_StrictModel):
    schema_version: Literal["veriformis.imported-record-assignment/v1"]
    assignment_id: str
    policy_id: str
    record_id: str
    group_id: str
    partition: Partition

    @model_validator(mode="after")
    def _closed(self) -> ImportedRecordAssignment:
        validate_id(self.policy_id, kind="spp")
        validate_id(self.record_id, kind="irc")
        validate_id(self.group_id, kind="lkg")
        expected = derive_id(
            "asg",
            self.model_dump(mode="json", exclude={"assignment_id"}),
        )
        if self.assignment_id != expected:
            raise MappingError("imported record assignment identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        record_id: str,
        group_id: str,
        partition: Partition,
    ) -> ImportedRecordAssignment:
        body = {
            "schema_version": "veriformis.imported-record-assignment/v1",
            "policy_id": policy_id,
            "record_id": record_id,
            "group_id": group_id,
            "partition": partition,
        }
        return cls(assignment_id=derive_id("asg", body), **body)


class ImportedSplitResult(_StrictModel):
    schema_version: Literal["veriformis.imported-split-result/v1"]
    result_id: str
    policy_id: str
    plan_id: str
    mapping_result_id: str
    curation_result_id: str
    input_record_ids: tuple[str, ...]
    groups: tuple[ImportedLeakageGroup, ...]
    assignments: tuple[ImportedRecordAssignment, ...]
    requested_evaluation_record_count: int
    realized_train_record_count: int
    realized_evaluation_record_count: int
    assignment_digest: str

    @field_validator("input_record_ids", "groups", "assignments", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedSplitResult:
        validate_id(self.policy_id, kind="spp")
        validate_id(self.plan_id, kind="fip")
        validate_id(self.mapping_result_id, kind="imr")
        validate_id(self.curation_result_id, kind="cur")
        _sorted_ids(
            self.input_record_ids,
            kind="irc",
            field="imported split input_record_ids",
        )
        expected = derive_id("spt", self.model_dump(mode="json", exclude={"result_id"}))
        if self.result_id != expected:
            raise MappingError("imported split result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        policy_id: str,
        plan_id: str,
        mapping_result_id: str,
        curation_result_id: str,
        input_record_ids: Sequence[str],
        groups: Sequence[ImportedLeakageGroup],
        assignments: Sequence[ImportedRecordAssignment],
        requested_evaluation_record_count: int,
    ) -> ImportedSplitResult:
        records = tuple(sorted(input_record_ids))
        normalized_groups = tuple(sorted(groups, key=lambda item: item.group_id))
        normalized_assignments = tuple(
            sorted(assignments, key=lambda item: item.record_id)
        )
        train_count = sum(
            item.partition == "train" for item in normalized_assignments
        )
        evaluation_count = sum(
            item.partition == "evaluation" for item in normalized_assignments
        )
        digest = canonical_digest(
            {
                "schema_version": "veriformis.assignment-set/v1",
                "assignments": [item.model_dump(mode="json") for item in normalized_assignments],
            }
        )
        body = {
            "schema_version": IMPORT_SPLIT_SCHEMA,
            "policy_id": policy_id,
            "plan_id": plan_id,
            "mapping_result_id": mapping_result_id,
            "curation_result_id": curation_result_id,
            "input_record_ids": list(records),
            "groups": [item.model_dump(mode="json") for item in normalized_groups],
            "assignments": [
                item.model_dump(mode="json") for item in normalized_assignments
            ],
            "requested_evaluation_record_count": requested_evaluation_record_count,
            "realized_train_record_count": train_count,
            "realized_evaluation_record_count": evaluation_count,
            "assignment_digest": digest,
        }
        return cls(result_id=derive_id("spt", body), **body)


class ImportedRowProvenance(_StrictModel):
    schema_version: Literal["veriformis.imported-row-provenance/v1"]
    provenance_id: str
    plan_id: str
    serialization_plan_id: str
    mapping_result_id: str
    mapping_plan_id: str
    curation_result_id: str
    split_result_id: str
    partition: Partition
    ordinal: int
    row_id: str
    payload_sha256: str
    record_id: str
    curation_decision_id: str
    leakage_group_id: str
    assignment_id: str
    recipe_id: str
    objective_id: str
    source_ids: tuple[str, ...]
    mapping_rule_ids: tuple[str, ...]
    row_index: int
    field_paths: tuple[str, ...]
    field_values_sha256: str
    field_evidence_sha256: str

    @field_validator("source_ids", "mapping_rule_ids", "field_paths", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedRowProvenance:
        validate_id(self.plan_id, kind="fip")
        validate_id(self.serialization_plan_id, kind="srp")
        validate_id(self.mapping_result_id, kind="imr")
        validate_id(self.mapping_plan_id, kind="mpl")
        validate_id(self.curation_result_id, kind="cur")
        validate_id(self.split_result_id, kind="spt")
        validate_id(self.row_id, kind="row")
        validate_id(self.record_id, kind="irc")
        validate_id(self.curation_decision_id, kind="cud")
        validate_id(self.leakage_group_id, kind="lkg")
        validate_id(self.assignment_id, kind="asg")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        _sorted_ids(self.source_ids, kind="src", field="imported provenance source_ids")
        if self.row_index < 1:
            raise MappingError("imported provenance row_index must be 1-based")
        if not self.mapping_rule_ids:
            raise MappingError("imported provenance requires mapping-rule ids")
        expected = derive_id(
            "prv",
            self.model_dump(mode="json", exclude={"provenance_id"}),
        )
        if self.provenance_id != expected:
            raise MappingError("imported row provenance identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: FinishedImportPlan,
        mapping_plan: MappingPlan,
        mapping_result: MappingResult,
        curation: ImportedCurationResult,
        split_result: ImportedSplitResult,
        partition: Partition,
        ordinal: int,
        row: ProductRow,
        record: ImportedRecord,
        assignment: ImportedRecordAssignment,
        leakage_group: ImportedLeakageGroup,
        curation_decision_id: str,
    ) -> ImportedRowProvenance:
        field_values = tuple(
            {"name": field.name, "value": field.value} for field in record.fields
        )
        field_evidence = tuple(
            {
                "name": field.name,
                "evidence": field.evidence.model_dump(mode="json"),
            }
            for field in record.fields
        )
        body = {
            "schema_version": IMPORT_PROVENANCE_SCHEMA,
            "plan_id": plan.plan_id,
            "serialization_plan_id": plan.serialization_plan.serialization_plan_id,
            "mapping_result_id": mapping_result.result_id,
            "mapping_plan_id": mapping_plan.mapping_plan_id,
            "curation_result_id": curation.result_id,
            "split_result_id": split_result.result_id,
            "partition": partition,
            "ordinal": ordinal,
            "row_id": row.row_id,
            "payload_sha256": row.payload_sha256,
            "record_id": record.record_id,
            "curation_decision_id": curation_decision_id,
            "leakage_group_id": leakage_group.group_id,
            "assignment_id": assignment.assignment_id,
            "recipe_id": record.recipe_id,
            "objective_id": record.objective_id,
            "source_ids": [record.source_id],
            "mapping_rule_ids": [
                field.evidence.mapping_rule_id for field in record.fields
            ],
            "row_index": record.row_index,
            "field_paths": [field.evidence.field_path for field in record.fields],
            "field_values_sha256": canonical_digest(
                {
                    "schema_version": "veriformis.row-field-values/v1",
                    "fields": field_values,
                }
            ),
            "field_evidence_sha256": canonical_digest(
                {
                    "schema_version": "veriformis.row-field-evidence/v1",
                    "fields": field_evidence,
                }
            ),
        }
        return cls(provenance_id=derive_id("prv", body), **body)


class ImportedRowSet(_StrictModel):
    schema_version: Literal["veriformis.imported-row-set/v1"]
    row_set_id: str
    plan_id: str
    serialization_plan_id: str
    recipe_id: str
    mapping_result_id: str
    curation_result_id: str
    split_result_id: str
    row_schema: RowSchema
    train_rows: tuple[ProductRow, ...]
    evaluation_rows: tuple[ProductRow, ...]
    provenance: tuple[ImportedRowProvenance, ...]
    train_jsonl_sha256: str
    train_jsonl_byte_size: int
    evaluation_jsonl_sha256: str
    evaluation_jsonl_byte_size: int
    provenance_jsonl_sha256: str
    provenance_jsonl_byte_size: int
    train_row_count: int
    evaluation_row_count: int
    total_row_count: int

    @field_validator("train_rows", "evaluation_rows", "provenance", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedRowSet:
        validate_id(self.plan_id, kind="fip")
        validate_id(self.serialization_plan_id, kind="srp")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.mapping_result_id, kind="imr")
        validate_id(self.curation_result_id, kind="cur")
        validate_id(self.split_result_id, kind="spt")
        if not self.train_rows:
            raise MappingError("imported row set requires a non-empty train partition")
        expected = derive_id("rws", self.model_dump(mode="json", exclude={"row_set_id"}))
        if self.row_set_id != expected:
            raise MappingError("imported row-set identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: FinishedImportPlan,
        mapping_result: MappingResult,
        curation: ImportedCurationResult,
        split_result: ImportedSplitResult,
        row_schema: str,
        train_rows: tuple[ProductRow, ...],
        evaluation_rows: tuple[ProductRow, ...],
        provenance: tuple[ImportedRowProvenance, ...],
        train_jsonl: bytes,
        evaluation_jsonl: bytes,
        provenance_jsonl: bytes,
    ) -> ImportedRowSet:
        body = {
            "schema_version": IMPORT_ROW_SET_SCHEMA,
            "plan_id": plan.plan_id,
            "serialization_plan_id": plan.serialization_plan.serialization_plan_id,
            "recipe_id": mapping_result.recipe_id,
            "mapping_result_id": mapping_result.result_id,
            "curation_result_id": curation.result_id,
            "split_result_id": split_result.result_id,
            "row_schema": row_schema,
            "train_rows": [row.model_dump(mode="json") for row in train_rows],
            "evaluation_rows": [row.model_dump(mode="json") for row in evaluation_rows],
            "provenance": [item.model_dump(mode="json") for item in provenance],
            "train_jsonl_sha256": sha256_digest(train_jsonl),
            "train_jsonl_byte_size": len(train_jsonl),
            "evaluation_jsonl_sha256": sha256_digest(evaluation_jsonl),
            "evaluation_jsonl_byte_size": len(evaluation_jsonl),
            "provenance_jsonl_sha256": sha256_digest(provenance_jsonl),
            "provenance_jsonl_byte_size": len(provenance_jsonl),
            "train_row_count": len(train_rows),
            "evaluation_row_count": len(evaluation_rows),
            "total_row_count": len(train_rows) + len(evaluation_rows),
        }
        return cls(row_set_id=derive_id("rws", body), **body)


class ImportedDatasetSnapshot(_StrictModel):
    schema_version: Literal["veriformis.imported-dataset-snapshot/v1"]
    snapshot_id: str
    plan_id: str
    recipe_id: str
    mapping_result_id: str
    curation_result_id: str
    split_result_id: str
    row_set_id: str
    source_ids: tuple[str, ...]
    file_bindings: tuple[SnapshotFileBinding, ...]
    gate_ids: tuple[str, ...]

    @field_validator("source_ids", "file_bindings", "gate_ids", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedDatasetSnapshot:
        validate_id(self.plan_id, kind="fip")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.mapping_result_id, kind="imr")
        validate_id(self.curation_result_id, kind="cur")
        validate_id(self.split_result_id, kind="spt")
        validate_id(self.row_set_id, kind="rws")
        _sorted_ids(self.source_ids, kind="src", field="imported snapshot source_ids")
        if self.gate_ids != IMPORT_GATES:
            raise MappingError("imported snapshot gates drifted")
        expected = derive_id(
            "dss",
            self.model_dump(mode="json", exclude={"snapshot_id"}),
        )
        if self.snapshot_id != expected:
            raise MappingError("imported dataset snapshot identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan: FinishedImportPlan,
        recipe: MappingRecipe,
        mapping_result: MappingResult,
        curation: ImportedCurationResult,
        split_result: ImportedSplitResult,
        row_set: ImportedRowSet,
        train_jsonl: bytes,
        evaluation_jsonl: bytes,
        provenance_jsonl: bytes,
    ) -> ImportedDatasetSnapshot:
        body = {
            "schema_version": IMPORT_SNAPSHOT_SCHEMA,
            "plan_id": plan.plan_id,
            "recipe_id": recipe.recipe_id,
            "mapping_result_id": mapping_result.result_id,
            "curation_result_id": curation.result_id,
            "split_result_id": split_result.result_id,
            "row_set_id": row_set.row_set_id,
            "source_ids": list(recipe.source_ids),
            "file_bindings": [
                SnapshotFileBinding.create(
                    role="training-partition",
                    file_bytes=train_jsonl,
                    record_count=row_set.train_row_count,
                ).model_dump(mode="json"),
                SnapshotFileBinding.create(
                    role="evaluation-partition",
                    file_bytes=evaluation_jsonl,
                    record_count=row_set.evaluation_row_count,
                ).model_dump(mode="json"),
                SnapshotFileBinding.create(
                    role="row-provenance",
                    file_bytes=provenance_jsonl,
                    record_count=row_set.total_row_count,
                ).model_dump(mode="json"),
            ],
            "gate_ids": list(IMPORT_GATES),
        }
        return cls(snapshot_id=derive_id("dss", body), **body)


class ImportedGateResult(_StrictModel):
    schema_version: Literal["veriformis.imported-gate-result/v1"]
    gate_result_id: str
    snapshot_id: str
    gate_id: str
    status: Literal["passed", "failed"]
    finding_codes: tuple[str, ...]

    @field_validator("finding_codes", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedGateResult:
        validate_id(self.snapshot_id, kind="dss")
        if self.gate_id not in IMPORT_GATES:
            raise MappingError(f"unknown imported validation gate {self.gate_id!r}")
        expected = derive_id(
            "dgr",
            self.model_dump(mode="json", exclude={"gate_result_id"}),
        )
        if self.gate_result_id != expected:
            raise MappingError("imported gate result identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        snapshot_id: str,
        gate_id: str,
        status: Literal["passed", "failed"] = "passed",
        finding_codes: tuple[str, ...] = (),
    ) -> ImportedGateResult:
        body = {
            "schema_version": "veriformis.imported-gate-result/v1",
            "snapshot_id": snapshot_id,
            "gate_id": gate_id,
            "status": status,
            "finding_codes": tuple(sorted(set(finding_codes))),
        }
        return cls(gate_result_id=derive_id("dgr", body), **body)


class ImportedValidationReport(_StrictModel):
    schema_version: Literal["veriformis.imported-dataset-validation-report/v1"]
    report_id: str
    snapshot_id: str
    status: Literal["passed", "failed"]
    snapshot: ImportedDatasetSnapshot
    gate_results: tuple[ImportedGateResult, ...]

    @field_validator("gate_results", mode="before")
    @classmethod
    def _seq(cls, value: Any) -> Any:
        return _tuple(value)

    @model_validator(mode="after")
    def _closed(self) -> ImportedValidationReport:
        validate_id(self.snapshot_id, kind="dss")
        if self.snapshot.snapshot_id != self.snapshot_id:
            raise MappingError("imported validation report names another snapshot")
        expected_status: Literal["passed", "failed"] = (
            "passed"
            if all(result.status == "passed" for result in self.gate_results)
            else "failed"
        )
        if self.status != expected_status:
            raise MappingError("imported validation status contradicts its gates")
        expected = derive_id("dvr", self.model_dump(mode="json", exclude={"report_id"}))
        if self.report_id != expected:
            raise MappingError("imported validation report identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        snapshot: ImportedDatasetSnapshot,
        gate_results: tuple[ImportedGateResult, ...],
    ) -> ImportedValidationReport:
        status: Literal["passed", "failed"] = (
            "passed"
            if all(result.status == "passed" for result in gate_results)
            else "failed"
        )
        body = {
            "schema_version": IMPORT_VALIDATION_SCHEMA,
            "snapshot_id": snapshot.snapshot_id,
            "status": status,
            "snapshot": snapshot.model_dump(mode="json"),
            "gate_results": [item.model_dump(mode="json") for item in gate_results],
        }
        return cls(report_id=derive_id("dvr", body), **body)


def exact_imported_fingerprint(record: ImportedRecord) -> str:
    return canonical_digest(
        {
            "schema_version": "veriformis.exact-record-fingerprint/v1",
            "objective_id": record.objective_id,
            "fields": tuple(
                {"name": field.name, "value": field.value} for field in record.fields
            ),
        }
    )


def imported_payload(record: ImportedRecord, row_schema: str) -> dict[str, Any]:
    values = {field.name: field.value for field in record.fields}
    if row_schema == "messages":
        payload = {"messages": json.loads(values["messages"])}
    elif row_schema == "tool-call-conversation":
        payload = {
            "conversation_id": values["conversation_id"],
            "turns": json.loads(values["turns"]),
        }
    else:
        payload = dict(values)
    _payload_contract(row_schema, payload)  # type: ignore[arg-type]
    return payload


def _target_length(record: ImportedRecord, row_schema: str) -> int:
    payload = imported_payload(record, row_schema)
    if row_schema == "text":
        return len(payload["text"])
    if row_schema == "prompt_completion":
        return len(payload["completion"])
    if row_schema == "instruction_output":
        return len(payload["output"])
    if row_schema == "label-classification":
        return len(payload["label"])
    if row_schema == "preference-pair":
        return len(payload["chosen"])
    if row_schema == "tool-call-conversation":
        return len(payload["turns"][-1]["content"])
    messages = payload["messages"]
    return len(messages[1]["content"])


def _context_key(record: ImportedRecord, row_schema: str) -> tuple[Any, ...]:
    payload = imported_payload(record, row_schema)
    if row_schema == "text":
        return (payload["text"],)
    if row_schema == "prompt_completion":
        return (payload["prompt"],)
    if row_schema == "instruction_output":
        return (payload["instruction"], payload["input"])
    if row_schema == "label-classification":
        return (payload["context"],)
    if row_schema == "preference-pair":
        return (payload["prompt"],)
    if row_schema == "tool-call-conversation":
        return (payload["conversation_id"],)
    return (payload["messages"][0]["content"],)


def curate_imported_records(
    plan: FinishedImportPlan,
    recipe: MappingRecipe,
    mapping_result: MappingResult,
) -> ImportedCurationResult:
    if plan.recipe_id != recipe.recipe_id:
        raise CurationError("finished import plan names another mapping recipe")
    if plan.mapping_result_id != mapping_result.result_id:
        raise CurationError("finished import plan names another mapping result")
    if plan.serialization_plan.row_schema != mapping_result.row_schema:
        raise CurationError("finished import plan row schema does not match mapping")
    records = tuple(sorted(mapping_result.records, key=lambda item: item.record_id))
    row_schema = mapping_result.row_schema
    minimum = plan.curation_policy.minimum_target_characters
    outcomes: dict[str, tuple[CurationStatus, CurationReasonCode, ImportedQualityFinding | None]] = {}
    remaining: dict[str, ImportedRecord] = {}
    for record in records:
        length = _target_length(record, row_schema)
        if length < minimum:
            finding = ImportedQualityFinding.create(
                record_id=record.record_id,
                code="target-too-short",
                observed_count=length,
                required_count=minimum,
            )
            outcomes[record.record_id] = ("excluded", "target-too-short", finding)
        else:
            remaining[record.record_id] = record

    context_groups: dict[tuple[Any, ...], list[ImportedRecord]] = {}
    for record in remaining.values():
        context_groups.setdefault(_context_key(record, row_schema), []).append(record)
    for group in context_groups.values():
        target_values = {_target_token(item, row_schema) for item in group}
        if len(target_values) > 1:
            ids = tuple(item.record_id for item in group)
            for record in group:
                related = tuple(item for item in ids if item != record.record_id)
                finding = ImportedQualityFinding.create(
                    record_id=record.record_id,
                    code="conflicting-target",
                    related_record_ids=related,
                    observed_count=len(target_values),
                )
                outcomes[record.record_id] = (
                    "quarantined",
                    "conflicting-target",
                    finding,
                )
                remaining.pop(record.record_id, None)

    fingerprint_groups: dict[str, list[ImportedRecord]] = {}
    for record in remaining.values():
        fingerprint_groups.setdefault(exact_imported_fingerprint(record), []).append(
            record
        )
    for group in fingerprint_groups.values():
        if len(group) < 2:
            continue
        keeper = sorted(group, key=lambda item: item.record_id)[0]
        for record in group:
            if record.record_id == keeper.record_id:
                continue
            finding = ImportedQualityFinding.create(
                record_id=record.record_id,
                code="exact-duplicate",
                related_record_ids=(keeper.record_id,),
            )
            outcomes[record.record_id] = ("excluded", "exact-duplicate", finding)
            remaining.pop(record.record_id, None)

    policy = plan.curation_policy
    if policy.balance_mode == "primary_source_cap":
        cap = policy.maximum_records_per_primary_source
        assert cap is not None
        per_source: dict[str, list[ImportedRecord]] = {}
        for record in remaining.values():
            per_source.setdefault(record.source_id, []).append(record)
        for source_id, group in per_source.items():
            ordered = sorted(group, key=lambda item: item.record_id)
            for record in ordered[cap:]:
                finding = ImportedQualityFinding.create(
                    record_id=record.record_id,
                    code="primary-source-cap",
                    observed_count=len(ordered),
                    required_count=cap,
                )
                outcomes[record.record_id] = (
                    "excluded",
                    "primary-source-cap",
                    finding,
                )
                remaining.pop(record.record_id, None)

    for record in remaining.values():
        outcomes[record.record_id] = ("included", "quality-passed", None)

    findings = tuple(
        finding
        for _, _, finding in (
            outcomes[record.record_id] for record in records
        )
        if finding is not None
    )
    decisions = tuple(
        ImportedCurationDecision.create(
            record_id=record.record_id,
            status=outcomes[record.record_id][0],
            reason_code=outcomes[record.record_id][1],
            finding_ids=(
                (outcomes[record.record_id][2].finding_id,)
                if outcomes[record.record_id][2] is not None
                else ()
            ),
        )
        for record in records
    )
    included = tuple(
        decision.record_id for decision in decisions if decision.status == "included"
    )
    entries = []
    for source_id in recipe.source_ids:
        source_records = [record for record in records if record.source_id == source_id]
        source_decisions = {
            decision.record_id: decision
            for decision in decisions
            if decision.record_id in {item.record_id for item in source_records}
        }
        included_count = sum(
            item.status == "included" for item in source_decisions.values()
        )
        excluded_count = sum(
            item.status == "excluded" for item in source_decisions.values()
        )
        quarantined_count = sum(
            item.status == "quarantined" for item in source_decisions.values()
        )
        entries.append(
            CoverageLedgerEntry.create(
                source_id=source_id,
                candidate_count=len(source_records),
                record_count=len(source_records),
                included_count=included_count,
                excluded_count=excluded_count,
                quarantined_count=quarantined_count,
                primary_included_count=included_count,
            )
        )
    ledger = CoverageLedger.create(
        selected_source_ids=recipe.source_ids,
        entries=tuple(entries),
    )
    return ImportedCurationResult.create(
        plan_id=plan.plan_id,
        recipe_id=recipe.recipe_id,
        mapping_result_id=mapping_result.result_id,
        policy_id=plan.curation_policy.policy_id,
        input_record_ids=tuple(record.record_id for record in records),
        decisions=decisions,
        findings=findings,
        included_record_ids=included,
        coverage_ledger=ledger,
    )


def _target_token(record: ImportedRecord, row_schema: str) -> Any:
    payload = imported_payload(record, row_schema)
    if row_schema == "text":
        return payload["text"]
    if row_schema == "prompt_completion":
        return payload["completion"]
    if row_schema == "instruction_output":
        return payload["output"]
    if row_schema == "label-classification":
        return payload["label"]
    if row_schema == "preference-pair":
        return payload["chosen"]
    if row_schema == "tool-call-conversation":
        return payload["turns"][-1]["content"]
    return payload["messages"][1]["content"]


def _split_imported_membership(
    plan: FinishedImportPlan,
    mapping_result: MappingResult,
    curation: ImportedCurationResult,
    included: tuple[ImportedRecord, ...],
    raw_digests: Mapping[str, str],
) -> ImportedSplitResult:
    if any(record.partition_hint not in {"train", "evaluation"} for record in included):
        raise SplitError(
            "authoritative membership requires partition train or evaluation on every row"
        )
    train = tuple(record for record in included if record.partition_hint == "train")
    evaluation = tuple(
        record for record in included if record.partition_hint == "evaluation"
    )
    if not train:
        raise SplitError("authoritative membership requires a non-empty train partition")
    train_sources = {record.source_id for record in train}
    evaluation_sources = {record.source_id for record in evaluation}
    leaked = sorted(train_sources & evaluation_sources)
    if leaked:
        raise SplitError(
            "authoritative imported partitions violate leakage policy for "
            f"sources {leaked!r}"
        )
    groups = tuple(
        ImportedLeakageGroup.create(
            record_ids=(record.record_id,),
            source_ids=(record.source_id,),
            raw_sha256_values=(raw_digests[record.source_id],),
            exact_record_fingerprints=(exact_imported_fingerprint(record),),
        )
        for record in included
    )
    group_by_record = {
        record_id: group.group_id for group in groups for record_id in group.record_ids
    }
    policy = plan.split_policy
    assignments = tuple(
        ImportedRecordAssignment.create(
            policy_id=policy.policy_id,
            record_id=record.record_id,
            group_id=group_by_record[record.record_id],
            partition=record.partition_hint,  # type: ignore[arg-type]
        )
        for record in included
    )
    return ImportedSplitResult.create(
        policy_id=policy.policy_id,
        plan_id=plan.plan_id,
        mapping_result_id=mapping_result.result_id,
        curation_result_id=curation.result_id,
        input_record_ids=curation.included_record_ids,
        groups=groups,
        assignments=assignments,
        requested_evaluation_record_count=len(evaluation),
    )


def split_imported_records(
    plan: FinishedImportPlan,
    mapping_result: MappingResult,
    curation: ImportedCurationResult,
    raw_digests: Mapping[str, str],
) -> ImportedSplitResult:
    if curation.plan_id != plan.plan_id:
        raise SplitError("imported curation names another finished import plan")
    if curation.mapping_result_id != mapping_result.result_id:
        raise SplitError("imported curation names another mapping result")
    records = {
        record.record_id: record for record in mapping_result.records
    }
    included = tuple(records[record_id] for record_id in curation.included_record_ids)
    if not included:
        raise SplitError("splitting requires at least one curation-included record")
    if mapping_result.membership_policy == "authoritative":
        return _split_imported_membership(
            plan,
            mapping_result,
            curation,
            included,
            raw_digests,
        )
    if mapping_result.row_schema == "label-classification":
        from veriformis.families.classification import imported_classification_groups

        groups = imported_classification_groups(included, raw_digests)
    elif mapping_result.row_schema == "preference-pair":
        from veriformis.families.preference import imported_preference_groups

        groups = imported_preference_groups(included, raw_digests)
    elif mapping_result.row_schema == "tool-call-conversation":
        from veriformis.families.tool_call import imported_tool_call_groups

        groups = imported_tool_call_groups(included, raw_digests)
    else:
        groups = tuple(
            ImportedLeakageGroup.create(
                record_ids=(record.record_id,),
                source_ids=(record.source_id,),
                raw_sha256_values=(raw_digests[record.source_id],),
                exact_record_fingerprints=(exact_imported_fingerprint(record),),
            )
            for record in included
        )
    policy = plan.split_policy
    if len(groups) < 2:
        if policy.evaluation_required:
            raise SplitError(
                "evaluation is required but fewer than two leakage groups exist"
            )
        assignments = tuple(
            ImportedRecordAssignment.create(
                policy_id=policy.policy_id,
                record_id=record.record_id,
                group_id=groups[0].group_id,
                partition="train",
            )
            for record in included
        )
        return ImportedSplitResult.create(
            policy_id=policy.policy_id,
            plan_id=plan.plan_id,
            mapping_result_id=mapping_result.result_id,
            curation_result_id=curation.result_id,
            input_record_ids=curation.included_record_ids,
            groups=groups,
            assignments=assignments,
            requested_evaluation_record_count=0,
        )
    target = max(
        1,
        min(
            len(included) - 1,
            (len(included) * policy.evaluation_ratio_ppm + (_RATIO_SCALE // 2))
            // _RATIO_SCALE,
        ),
    )
    ordered = tuple(
        sorted(
            groups,
            key=lambda group: (
                sha256_digest(policy.policy_id + policy.seed + group.group_id),
                group.group_id,
            ),
        )
    )
    cumulative = 0
    options: list[tuple[int, int]] = []
    for prefix_length, group in enumerate(ordered[:-1], start=1):
        cumulative += len(group.record_ids)
        options.append((abs(cumulative - target), prefix_length))
    prefix = min(options)[1]
    evaluation_ids = {group.group_id for group in ordered[:prefix]}
    group_by_record = {
        record_id: group.group_id for group in groups for record_id in group.record_ids
    }
    assignments = tuple(
        ImportedRecordAssignment.create(
            policy_id=policy.policy_id,
            record_id=record.record_id,
            group_id=group_by_record[record.record_id],
            partition=(
                "evaluation"
                if group_by_record[record.record_id] in evaluation_ids
                else "train"
            ),
        )
        for record in included
    )
    return ImportedSplitResult.create(
        policy_id=policy.policy_id,
        plan_id=plan.plan_id,
        mapping_result_id=mapping_result.result_id,
        curation_result_id=curation.result_id,
        input_record_ids=curation.included_record_ids,
        groups=groups,
        assignments=assignments,
        requested_evaluation_record_count=target,
    )


def serialize_imported_records(
    plan: FinishedImportPlan,
    mapping_plan: MappingPlan,
    mapping_result: MappingResult,
    curation: ImportedCurationResult,
    split_result: ImportedSplitResult,
) -> tuple[ImportedRowSet, bytes, bytes, bytes]:
    records = {record.record_id: record for record in mapping_result.records}
    decisions = {item.record_id: item for item in curation.decisions}
    assignments = {item.record_id: item for item in split_result.assignments}
    groups = {item.group_id: item for item in split_result.groups}
    row_schema = plan.serialization_plan.row_schema
    rows_by_record = {
        record_id: ProductRow.create(
            record_id=record_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            payload=imported_payload(records[record_id], row_schema),
        )
        for record_id in curation.included_record_ids
    }
    train_rows = tuple(
        rows_by_record[record_id]
        for record_id in sorted(rows_by_record)
        if assignments[record_id].partition == "train"
    )
    evaluation_rows = tuple(
        rows_by_record[record_id]
        for record_id in sorted(rows_by_record)
        if assignments[record_id].partition == "evaluation"
    )
    provenance: list[ImportedRowProvenance] = []
    for partition, rows in (("train", train_rows), ("evaluation", evaluation_rows)):
        for ordinal, row in enumerate(rows):
            record = records[row.record_id]
            assignment = assignments[row.record_id]
            provenance.append(
                ImportedRowProvenance.create(
                    plan=plan,
                    mapping_plan=mapping_plan,
                    mapping_result=mapping_result,
                    curation=curation,
                    split_result=split_result,
                    partition=partition,  # type: ignore[arg-type]
                    ordinal=ordinal,
                    row=row,
                    record=record,
                    assignment=assignment,
                    leakage_group=groups[assignment.group_id],
                    curation_decision_id=decisions[row.record_id].decision_id,
                )
            )
    train_jsonl = b"".join(lossless_json_bytes(row.payload) + b"\n" for row in train_rows)
    evaluation_jsonl = b"".join(
        lossless_json_bytes(row.payload) + b"\n" for row in evaluation_rows
    )
    provenance_jsonl = b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )
    row_set = ImportedRowSet.create(
        plan=plan,
        mapping_result=mapping_result,
        curation=curation,
        split_result=split_result,
        row_schema=row_schema,
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=tuple(provenance),
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
    )
    return row_set, train_jsonl, evaluation_jsonl, provenance_jsonl


def validate_imported_dataset(
    plan: FinishedImportPlan,
    recipe: MappingRecipe,
    mapping_plan: MappingPlan,
    mapping_result: MappingResult,
    curation: ImportedCurationResult,
    split_result: ImportedSplitResult,
    row_set: ImportedRowSet,
    *,
    train_jsonl: bytes,
    evaluation_jsonl: bytes,
    provenance_jsonl: bytes,
) -> ImportedValidationReport:
    replayed_curation = curate_imported_records(plan, recipe, mapping_result)
    if replayed_curation != curation:
        raise DatasetValidationError("imported curation does not match replay")
    digest_map: dict[str, str] = {}
    for group in split_result.groups:
        if len(group.source_ids) != len(group.raw_sha256_values):
            raise DatasetValidationError(
                "imported leakage group source digests are misaligned"
            )
        for source_id, digest in zip(
            group.source_ids, group.raw_sha256_values, strict=True
        ):
            previous = digest_map.get(source_id)
            if previous is not None and previous != digest:
                raise DatasetValidationError(
                    "imported leakage group source digests conflict"
                )
            digest_map[source_id] = digest
    replayed_split = split_imported_records(
        plan,
        mapping_result,
        curation,
        digest_map,
    )
    if replayed_split != split_result:
        raise DatasetValidationError("imported split does not match replay")
    replayed_row_set, replay_train, replay_eval, replay_prov = serialize_imported_records(
        plan,
        mapping_plan,
        mapping_result,
        curation,
        split_result,
    )
    if (
        replayed_row_set != row_set
        or replay_train != train_jsonl
        or replay_eval != evaluation_jsonl
        or replay_prov != provenance_jsonl
    ):
        raise DatasetValidationError("imported format artifacts do not match replay")
    snapshot = ImportedDatasetSnapshot.create(
        plan=plan,
        recipe=recipe,
        mapping_result=mapping_result,
        curation=curation,
        split_result=split_result,
        row_set=row_set,
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
    )
    gates = tuple(
        ImportedGateResult.create(snapshot_id=snapshot.snapshot_id, gate_id=gate_id)
        for gate_id in IMPORT_GATES
    )
    return ImportedValidationReport.create(snapshot=snapshot, gate_results=gates)


def finished_import_plan_from_json_bytes(data: bytes) -> FinishedImportPlan:
    return FinishedImportPlan.model_validate_json(data)


def imported_curation_from_json_bytes(data: bytes) -> ImportedCurationResult:
    return ImportedCurationResult.model_validate_json(data)


def imported_split_from_json_bytes(data: bytes) -> ImportedSplitResult:
    return ImportedSplitResult.model_validate_json(data)


def imported_row_set_from_json_bytes(data: bytes) -> ImportedRowSet:
    return ImportedRowSet.model_validate_json(data)


def imported_validation_from_json_bytes(data: bytes) -> ImportedValidationReport:
    return ImportedValidationReport.model_validate_json(data)
