"""Strict row-source and mapping contracts. No capture or execution."""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)

from veriformis.contracts import (
    MAPPING_CONTRACT_ID,
    MAPPING_CONTRACT_VERSION,
    MAPPING_DISCOVERY_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import MappingError, RowSourceError
from veriformis.goals import goal_catalog
from veriformis.identity import derive_id, sha256_digest, validate_id, validate_sha256

CONTRACT_DATA_NAME = "contracts-v1.json"

ROW_SCHEMA_PAYLOAD_KEYS: dict[str, tuple[str, ...]] = {
    "text": ("text",),
    "prompt_completion": ("prompt", "completion"),
    "instruction_output": ("instruction", "input", "output"),
    "messages": ("messages",),
}
ADMITTED_CONTAINERS: tuple[str, ...] = ("jsonl", "json", "csv", "parquet", "arrow")
RESERVED_CONTAINERS: tuple[str, ...] = ()
CONTAINER_KINDS: tuple[str, ...] = ADMITTED_CONTAINERS + RESERVED_CONTAINERS
CSV_DIALECT: dict[str, object] = {
    "delimiter": ",",
    "encoding": "utf-8",
    "header_required": True,
    "pad": False,
    "trim": False,
}
MEMBERSHIP_POLICIES: tuple[str, ...] = ("authoritative", "advisory", "replaced")
MISSING_VALUE_RULES: tuple[str, ...] = ("refuse",)
INVALID_ROW_RULES: tuple[str, ...] = ("refuse",)
COERCION_RULES: tuple[str, ...] = ("refuse",)
REVIEW_POLICIES: tuple[str, ...] = ("none", "required")
REJECTION_REASON_CODES: tuple[str, ...] = (
    "empty-required-string",
    "invalid-mapped-fields",
    "invalid-messages",
    "invalid-partition",
    "missing-source-path",
    "non-string-value",
    "unmapped-keys",
)
RowSchema = Literal["text", "prompt_completion", "instruction_output", "messages"]
ContainerKind = Literal["jsonl", "json", "csv", "parquet", "arrow"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    @model_validator(mode="before")
    @classmethod
    def _require_exact_fields(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, cls) or not isinstance(value, MappingABC):
            return value
        expected = set(cls.model_fields)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise MappingError(
                f"{cls.__name__} fields do not match its persisted schema; "
                f"missing={missing!r}, extra={extra!r}"
            )
        if info.mode != "json":
            return value
        return dict(value)


class MappedValueEvidence(_StrictModel):
    schema_version: Literal["veriformis.mapped-value-evidence/v1"]
    kind: Literal["mapped_value"]
    evidence_id: str
    source_id: str
    row_index: int
    field_path: str
    original_value_sha256: str
    mapping_rule_id: str
    output_sha256: str

    @model_validator(mode="after")
    def _identity(self) -> MappedValueEvidence:
        if self.schema_version != "veriformis.mapped-value-evidence/v1":
            raise MappingError("mapped-value evidence schema mismatch")
        if self.row_index < 1:
            raise MappingError("mapped-value row_index must be 1-based")
        if not self.field_path.strip():
            raise MappingError("mapped-value field_path must be non-empty")
        validate_id(self.source_id, kind="src")
        validate_id(self.mapping_rule_id, kind="mrl")
        validate_sha256(self.original_value_sha256)
        validate_sha256(self.output_sha256)
        expected = derive_id(
            "mve",
            self.model_dump(mode="json", exclude={"evidence_id"}),
        )
        if self.evidence_id != expected:
            raise MappingError("mapped-value evidence identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        row_index: int,
        field_path: str,
        original_value_sha256: str,
        mapping_rule_id: str,
        output_sha256: str,
    ) -> MappedValueEvidence:
        body = {
            "schema_version": "veriformis.mapped-value-evidence/v1",
            "kind": "mapped_value",
            "source_id": source_id,
            "row_index": row_index,
            "field_path": field_path,
            "original_value_sha256": original_value_sha256,
            "mapping_rule_id": mapping_rule_id,
            "output_sha256": output_sha256,
        }
        return cls(evidence_id=derive_id("mve", body), **body)


class RowSource(_StrictModel):
    schema_version: Literal["veriformis.row-source/v1"]
    row_source_id: str
    logical_path: str
    sha256: str
    size: int
    record_count: int
    container_kind: ContainerKind

    @model_validator(mode="after")
    def _identity(self) -> RowSource:
        if not self.logical_path.strip():
            raise RowSourceError("row source logical_path must be non-empty")
        if self.size < 0:
            raise RowSourceError("row source size cannot be negative")
        if self.record_count < 1:
            raise RowSourceError("row source record_count must be at least 1")
        validate_sha256(self.sha256)
        if self.container_kind not in CONTAINER_KINDS:
            raise RowSourceError(
                f"unknown row-source container {self.container_kind!r}"
            )
        expected = derive_id(
            "rws",
            self.model_dump(mode="json", exclude={"row_source_id"}),
        )
        if self.row_source_id != expected:
            raise RowSourceError("row-source identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        logical_path: str,
        sha256: str,
        size: int,
        record_count: int,
        container_kind: str,
    ) -> RowSource:
        body = {
            "schema_version": "veriformis.row-source/v1",
            "logical_path": logical_path,
            "sha256": sha256,
            "size": size,
            "record_count": record_count,
            "container_kind": container_kind,
        }
        return cls(row_source_id=derive_id("rws", body), **body)


class FieldMapping(_StrictModel):
    schema_version: Literal["veriformis.field-mapping/v1"]
    mapping_rule_id: str
    source_path: str
    target_key: str
    coercion_rule: Literal["refuse"]
    missing_value_rule: Literal["refuse"]
    invalid_row_rule: Literal["refuse"]

    @model_validator(mode="after")
    def _identity(self) -> FieldMapping:
        if not self.source_path.strip():
            raise MappingError("field mapping source_path must be non-empty")
        if not self.target_key.strip():
            raise MappingError("field mapping target_key must be non-empty")
        expected = derive_id(
            "mrl",
            self.model_dump(mode="json", exclude={"mapping_rule_id"}),
        )
        if self.mapping_rule_id != expected:
            raise MappingError("field mapping identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_path: str,
        target_key: str,
        coercion_rule: str = "refuse",
        missing_value_rule: str = "refuse",
        invalid_row_rule: str = "refuse",
    ) -> FieldMapping:
        body = {
            "schema_version": "veriformis.field-mapping/v1",
            "source_path": source_path,
            "target_key": target_key,
            "coercion_rule": coercion_rule,
            "missing_value_rule": missing_value_rule,
            "invalid_row_rule": invalid_row_rule,
        }
        return cls(mapping_rule_id=derive_id("mrl", body), **body)


class MappingPlan(_StrictModel):
    schema_version: Literal["veriformis.mapping-plan/v1"]
    mapping_plan_id: str
    goal_id: str
    representation_id: str
    row_schema: RowSchema
    container_kind: ContainerKind
    membership_policy: Literal["authoritative", "advisory", "replaced"]
    review_policy: Literal["none", "required"]
    confirmation_digest: str
    field_mappings: tuple[FieldMapping, ...]

    @field_validator("field_mappings", mode="before")
    @classmethod
    def _tuple_mappings(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> MappingPlan:
        catalog = goal_catalog()
        try:
            goal = catalog.goal(self.goal_id)
        except Exception as exc:
            raise MappingError(f"unknown mapping goal {self.goal_id!r}") from exc
        if self.representation_id not in goal.compatible_representations:
            raise MappingError(
                f"representation {self.representation_id!r} is incompatible with "
                f"goal {self.goal_id!r}"
            )
        representation = catalog.representation(self.representation_id)
        if representation.row_schema != self.row_schema:
            raise MappingError(
                f"row schema {self.row_schema!r} does not match representation "
                f"{self.representation_id!r}"
            )
        if self.container_kind in RESERVED_CONTAINERS:
            raise MappingError(
                f"container {self.container_kind!r} is reserved"
            )
        if self.container_kind not in ADMITTED_CONTAINERS:
            raise MappingError(
                f"unsupported mapping container {self.container_kind!r}"
            )
        if self.container_kind == "csv" and self.row_schema == "messages":
            raise MappingError(
                "CSV cannot represent nested messages; use split-jsonl-directory or json"
            )
        validate_sha256(self.confirmation_digest)
        if not self.field_mappings:
            raise MappingError("mapping plan requires at least one field mapping")
        expected_keys = ROW_SCHEMA_PAYLOAD_KEYS[self.row_schema]
        actual_keys = tuple(item.target_key for item in self.field_mappings)
        if actual_keys != expected_keys:
            raise MappingError(
                f"{self.row_schema!r} mappings must target {expected_keys!r} in order, "
                f"not {actual_keys!r}"
            )
        rule_ids = tuple(item.mapping_rule_id for item in self.field_mappings)
        if len(rule_ids) != len(set(rule_ids)):
            raise MappingError("mapping plan contains duplicate mapping-rule ids")
        expected = derive_id(
            "mpl",
            self.model_dump(mode="json", exclude={"mapping_plan_id"}),
        )
        if self.mapping_plan_id != expected:
            raise MappingError("mapping-plan identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        goal_id: str,
        representation_id: str,
        row_schema: str,
        container_kind: str,
        confirmation_digest: str,
        field_mappings: tuple[FieldMapping, ...] | list[FieldMapping],
        membership_policy: str = "replaced",
        review_policy: str = "none",
    ) -> MappingPlan:
        mappings = tuple(field_mappings)
        body = {
            "schema_version": "veriformis.mapping-plan/v1",
            "goal_id": goal_id,
            "representation_id": representation_id,
            "row_schema": row_schema,
            "container_kind": container_kind,
            "membership_policy": membership_policy,
            "review_policy": review_policy,
            "confirmation_digest": confirmation_digest,
            "field_mappings": [item.model_dump(mode="json") for item in mappings],
        }
        return cls(mapping_plan_id=derive_id("mpl", body), **body)


class ImportedField(_StrictModel):
    name: str
    value: str
    evidence: MappedValueEvidence

    @model_validator(mode="after")
    def _matches(self) -> ImportedField:
        if not self.name.strip():
            raise MappingError("imported field name must be non-empty")
        if not self.value:
            raise MappingError(f"imported field {self.name!r} value must be non-empty")
        expected = sha256_digest(self.value)
        if self.evidence.output_sha256 != expected:
            raise MappingError(
                f"imported field {self.name!r} value does not match its evidence"
            )
        return self


class ImportedRecord(_StrictModel):
    schema_version: Literal["veriformis.imported-record/v1"]
    record_id: str
    source_id: str
    row_index: int
    mapping_plan_id: str
    goal_id: str
    recipe_id: str
    objective_id: str
    fields: tuple[ImportedField, ...]
    partition_hint: Literal["train", "evaluation"] | None

    @field_validator("fields", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _identity(self) -> ImportedRecord:
        validate_id(self.source_id, kind="src")
        validate_id(self.mapping_plan_id, kind="mpl")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        if self.row_index < 1:
            raise MappingError("imported record row_index must be 1-based")
        if not self.fields:
            raise MappingError("imported record requires at least one field")
        names = tuple(field.name for field in self.fields)
        if len(names) != len(set(names)):
            raise MappingError("imported record contains duplicate field names")
        for field in self.fields:
            if field.evidence.source_id != self.source_id:
                raise MappingError("imported field evidence names another source")
            if field.evidence.row_index != self.row_index:
                raise MappingError("imported field evidence names another row")
        expected = derive_id(
            "irc",
            self.model_dump(mode="json", exclude={"record_id"}),
        )
        if self.record_id != expected:
            raise MappingError("imported-record identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        row_index: int,
        mapping_plan_id: str,
        goal_id: str,
        recipe_id: str,
        objective_id: str,
        fields: tuple[ImportedField, ...] | list[ImportedField],
        partition_hint: str | None = None,
    ) -> ImportedRecord:
        body = {
            "schema_version": "veriformis.imported-record/v1",
            "source_id": source_id,
            "row_index": row_index,
            "mapping_plan_id": mapping_plan_id,
            "goal_id": goal_id,
            "recipe_id": recipe_id,
            "objective_id": objective_id,
            "fields": [field.model_dump(mode="json") for field in fields],
            "partition_hint": partition_hint,
        }
        return cls(record_id=derive_id("irc", body), **body)


def mapping_contract_discovery() -> dict[str, Any]:
    return json.loads(_packaged_contracts()[0])


def mapping_contract_discovery_json() -> str:
    return _packaged_contracts()[0]


@lru_cache(maxsize=1)
def _packaged_contracts() -> tuple[str, dict[str, Any]]:
    raw = (
        resources.files("veriformis.mapping")
        .joinpath(CONTRACT_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise MappingError("mapping contract discovery is not canonical JSON")
    if payload.get("schema_id") != MAPPING_DISCOVERY_SCHEMA_ID:
        raise MappingError("mapping contract discovery schema_id mismatch")
    if payload.get("contract_id") != MAPPING_CONTRACT_ID:
        raise MappingError("mapping contract discovery contract_id mismatch")
    if payload.get("contract_version") != MAPPING_CONTRACT_VERSION:
        raise MappingError("mapping contract discovery contract_version mismatch")
    if tuple(payload.get("admitted_containers") or ()) != ADMITTED_CONTAINERS:
        raise MappingError("mapping contract admitted containers drifted")
    if tuple(payload.get("reserved_containers") or ()) != RESERVED_CONTAINERS:
        raise MappingError("mapping contract reserved containers drifted")
    if tuple(payload.get("row_schemas") or ()) != V1_ROW_SCHEMA_KINDS:
        raise MappingError("mapping contract row schemas drifted")
    if tuple(payload.get("membership_policies") or ()) != MEMBERSHIP_POLICIES:
        raise MappingError("mapping contract membership policies drifted")
    if tuple(payload.get("rejection_reason_codes") or ()) != REJECTION_REASON_CODES:
        raise MappingError("mapping contract rejection reason codes drifted")
    if payload.get("csv_dialect") != CSV_DIALECT:
        raise MappingError("mapping contract csv dialect drifted")
    return canonical, payload
