"""Objective-preserving lowering from curated records to trainer JSONL.

This module is the only Group 3 boundary that turns immutable ``DatasetRecord``
values into trainer-facing payloads.  It does not reopen construction,
curation, or splitting.  Version 1 always emits exactly one product row for
each curation-included record and keeps all lineage in a separate, aligned
provenance stream.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypeVar, get_origin

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator

from veriformis.construction import (
    ConstructionResult,
    DatasetRecipe,
    DatasetRecord,
    RecordField,
    SourceTextEvidence,
    construction_result_from_dict,
    dataset_recipe_from_dict,
)
from veriformis.errors import (
    ConstructionError,
    CurationError,
    DuplicateIdentityError,
    SerializationError,
    SplitError,
)
from veriformis.identity import (
    canonical_digest,
    derive_id,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

from ._json import canonical_json_object_from_bytes, reject_floats
from .curation import OBJECTIVE_FIELD_ROLES
from .models import CurationResult, curation_result_from_dict
from .splitting import (
    LeakageGroup,
    Partition,
    RecordAssignment,
    SplitResult,
    split_result_from_dict,
)

if TYPE_CHECKING:
    from .plan import FinishedDatasetPlan


RowSchema = Literal[
    "text",
    "prompt_completion",
    "instruction_output",
    "messages",
    "label-classification",
    "preference-pair",
    "tool-call-conversation",
    "stepwise-trace",
]

V1_ROW_SCHEMAS: tuple[RowSchema, ...] = (
    "text",
    "prompt_completion",
    "instruction_output",
    "messages",
)
PRODUCT_ROW_SCHEMAS: tuple[RowSchema, ...] = (
    *V1_ROW_SCHEMAS,
    "label-classification",
    "preference-pair",
    "tool-call-conversation",
    "stepwise-trace",
)
V1_PARTITION_ORDER: tuple[Partition, ...] = ("train", "evaluation")


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        arbitrary_types_allowed=True,
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


def _require_nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_nonnegative_integer(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _require_canonical_ids(
    values: tuple[str, ...],
    *,
    kind: str,
    field_name: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not values and not allow_empty:
        raise ValueError(f"{field_name} cannot be empty")
    checked = tuple(validate_id(value, kind=kind) for value in values)
    if len(checked) != len(set(checked)):
        raise DuplicateIdentityError(f"{field_name} contains duplicate identities")
    if checked != tuple(sorted(checked)):
        raise ValueError(f"{field_name} must be sorted in canonical order")
    return values


def _revalidate_nested(
    value: _StrictModel,
    model_type: type[_StrictModel],
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


def _payload_contract(row_schema: RowSchema, payload: dict[str, Any]) -> None:
    """Validate one exact trainer payload without rewriting its strings."""
    if row_schema == "text":
        if set(payload) != {"text"}:
            raise ValueError("text payload requires exactly the 'text' key")
        _require_nonempty(payload["text"], "text payload target")
        return

    if row_schema == "prompt_completion":
        if set(payload) != {"prompt", "completion"}:
            raise ValueError(
                "prompt_completion payload requires exactly prompt and completion"
            )
        _require_nonempty(payload["prompt"], "prompt payload context")
        _require_nonempty(payload["completion"], "prompt payload target")
        return

    if row_schema == "instruction_output":
        if set(payload) != {"instruction", "input", "output"}:
            raise ValueError(
                "instruction_output payload requires exactly instruction, input, "
                "and output"
            )
        _require_nonempty(payload["instruction"], "instruction payload instruction")
        _require_nonempty(payload["input"], "instruction payload context")
        _require_nonempty(payload["output"], "instruction payload target")
        return

    if row_schema == "label-classification":
        if set(payload) != {"annotator", "context", "label"}:
            raise ValueError(
                "label-classification payload requires exactly annotator, context, "
                "and label"
            )
        _require_nonempty(payload["annotator"], "label-classification annotator")
        _require_nonempty(payload["context"], "label-classification context")
        _require_nonempty(payload["label"], "label-classification label")
        return

    if row_schema == "preference-pair":
        if set(payload) != {"chosen", "prompt", "rejected"}:
            raise ValueError(
                "preference-pair payload requires exactly prompt, chosen, and rejected"
            )
        _require_nonempty(payload["prompt"], "preference-pair prompt")
        _require_nonempty(payload["chosen"], "preference-pair chosen")
        _require_nonempty(payload["rejected"], "preference-pair rejected")
        return

    if row_schema == "tool-call-conversation":
        if set(payload) != {"conversation_id", "turns"}:
            raise ValueError(
                "tool-call-conversation payload requires exactly conversation_id "
                "and turns"
            )
        _require_nonempty(
            payload["conversation_id"], "tool-call-conversation conversation_id"
        )
        from veriformis.families.tool_call import normalize_tool_turns

        normalize_tool_turns(payload["turns"])
        return

    if row_schema == "stepwise-trace":
        if set(payload) != {"prompt", "steps"}:
            raise ValueError(
                "stepwise-trace payload requires exactly prompt and steps"
            )
        _require_nonempty(payload["prompt"], "stepwise-trace prompt")
        from veriformis.families.stepwise import normalize_steps

        normalize_steps(payload["steps"])
        return

    if row_schema != "messages":
        raise ValueError(f"unsupported product row schema {row_schema!r}")
    if set(payload) != {"messages"}:
        raise ValueError("messages payload requires exactly the 'messages' key")
    messages = payload["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError("messages payload requires exactly two ordered turns")
    expected_roles = ("user", "assistant")
    for index, (message, role) in enumerate(zip(messages, expected_roles)):
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise ValueError(f"messages turn {index} has an invalid shape")
        if message["role"] != role:
            raise ValueError(f"messages turn {index} must have role {role!r}")
        _require_nonempty(message["content"], f"messages turn {index} content")


class SerializationPlan(_StrictModel):
    """One exact row-schema selection and any explicit instruction literal."""

    schema_version: Literal["veriformis.serialization-plan/v1"] = (
        "veriformis.serialization-plan/v1"
    )
    serialization_plan_id: str
    row_schema: RowSchema
    instruction_text: str | None

    @model_validator(mode="after")
    def _validate_plan(self) -> SerializationPlan:
        validate_id(self.serialization_plan_id, kind="srp")
        if self.row_schema not in PRODUCT_ROW_SCHEMAS:
            raise ValueError("serialization plan contains an unsupported row schema")
        if self.row_schema == "instruction_output":
            if self.instruction_text is None:
                raise ValueError(
                    "instruction_output serialization requires instruction_text"
                )
            _require_nonempty(self.instruction_text, "serialization instruction_text")
        elif self.instruction_text is not None:
            raise ValueError("instruction_text must be null outside instruction_output")
        expected_id = derive_id(
            "srp",
            self.model_dump(mode="json", exclude={"serialization_plan_id"}),
        )
        if self.serialization_plan_id != expected_id:
            raise ValueError("serialization plan identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        row_schema: RowSchema,
        instruction_text: str | None = None,
    ) -> SerializationPlan:
        payload = {
            "schema_version": "veriformis.serialization-plan/v1",
            "row_schema": row_schema,
            "instruction_text": instruction_text,
        }
        return cls(
            serialization_plan_id=derive_id("srp", payload),
            **payload,
        )


class ProductRow(_StrictModel):
    """One audited trainer payload before metadata is separated to JSONL."""

    schema_version: Literal["veriformis.product-row/v1"] = "veriformis.product-row/v1"
    row_id: str
    record_id: str
    row_schema: RowSchema
    payload: dict[str, Any]
    payload_sha256: str

    @model_validator(mode="after")
    def _validate_row(self) -> ProductRow:
        validate_id(self.row_id, kind="row")
        record_kind = self.record_id.split("-v", 1)[0]
        if record_kind not in {"rec", "irc"}:
            raise ValueError("product row record_id must be a rec or irc identity")
        validate_id(self.record_id, kind=record_kind)
        if self.row_schema not in PRODUCT_ROW_SCHEMAS:
            raise ValueError("product row contains an unsupported row schema")
        reject_floats(self.payload)
        _payload_contract(self.row_schema, self.payload)
        validate_sha256(self.payload_sha256)
        expected_payload_sha256 = sha256_digest(lossless_json_bytes(self.payload))
        if self.payload_sha256 != expected_payload_sha256:
            raise ValueError("product row payload digest mismatch")
        expected_id = derive_id(
            "row",
            self.model_dump(mode="json", exclude={"row_id"}),
        )
        if self.row_id != expected_id:
            raise ValueError("product row identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        row_schema: RowSchema,
        payload: Mapping[str, Any],
    ) -> ProductRow:
        if not isinstance(payload, Mapping):
            raise SerializationError("product row payload must be a mapping")
        checked_payload = dict(payload)
        payload_bytes = lossless_json_bytes(checked_payload)
        body = {
            "schema_version": "veriformis.product-row/v1",
            "record_id": record_id,
            "row_schema": row_schema,
            "payload": checked_payload,
            "payload_sha256": sha256_digest(payload_bytes),
        }
        return cls(row_id=derive_id("row", body), **body)


class RowProvenance(_StrictModel):
    """The exact lineage for one payload line in one authoritative partition."""

    schema_version: Literal["veriformis.row-provenance/v1"] = (
        "veriformis.row-provenance/v1"
    )
    provenance_id: str
    plan_id: str
    serialization_plan_id: str
    construction_result_id: str
    curation_result_id: str
    split_result_id: str
    partition: Partition
    ordinal: int
    row_id: str
    payload_sha256: str
    record_id: str
    promotion_decision_id: str
    curation_decision_id: str
    leakage_group_id: str
    assignment_id: str
    recipe_id: str
    objective_id: str
    pass_id: str
    source_ids: tuple[str, ...]
    chunk_ids: tuple[str, ...]
    transform_ids: tuple[str, ...]
    record_fields: tuple[RecordField, ...]
    field_values_sha256: str
    field_evidence_sha256: str

    @model_validator(mode="after")
    def _validate_provenance(self) -> RowProvenance:
        validate_id(self.provenance_id, kind="prv")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.serialization_plan_id, kind="srp")
        validate_id(self.construction_result_id, kind="run")
        validate_id(self.curation_result_id, kind="cur")
        validate_id(self.split_result_id, kind="spt")
        if self.partition not in V1_PARTITION_ORDER:
            raise ValueError("row provenance contains an unsupported partition")
        _require_nonnegative_integer(self.ordinal, "row provenance ordinal")
        validate_id(self.row_id, kind="row")
        validate_sha256(self.payload_sha256)
        validate_id(self.record_id, kind="rec")
        validate_id(self.promotion_decision_id, kind="dec")
        validate_id(self.curation_decision_id, kind="cud")
        validate_id(self.leakage_group_id, kind="lkg")
        validate_id(self.assignment_id, kind="asg")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.objective_id, kind="obj")
        validate_id(self.pass_id, kind="pas")
        _require_canonical_ids(
            self.source_ids,
            kind="src",
            field_name="row provenance source_ids",
        )
        _require_canonical_ids(
            self.chunk_ids,
            kind="chk",
            field_name="row provenance chunk_ids",
        )
        _require_canonical_ids(
            self.transform_ids,
            kind="trn",
            field_name="row provenance transform_ids",
            allow_empty=True,
        )
        if not self.record_fields:
            raise ValueError("row provenance requires complete record fields")
        field_names = tuple(field.name for field in self.record_fields)
        if len(field_names) != len(set(field_names)):
            raise ValueError("row provenance contains duplicate record field names")
        for field in self.record_fields:
            try:
                checked_field = RecordField.model_validate_json(
                    lossless_json_bytes(field.model_dump(mode="json"))
                )
            except (AttributeError, TypeError, UnicodeError, ValueError) as exc:
                raise ValueError(f"invalid nested record field: {exc}") from exc
            if checked_field != field:
                raise ValueError("nested record field does not round-trip exactly")
            evidence_source_id = (
                checked_field.evidence.evidence.source_id
                if isinstance(checked_field.evidence, SourceTextEvidence)
                else checked_field.evidence.source_id
            )
            if evidence_source_id not in self.source_ids:
                raise ValueError("row provenance field evidence names another source")
        validate_sha256(self.field_values_sha256)
        validate_sha256(self.field_evidence_sha256)
        field_values = tuple(
            {"name": field.name, "value": field.value} for field in self.record_fields
        )
        field_evidence = tuple(
            {
                "name": field.name,
                "evidence": field.evidence.model_dump(mode="json"),
            }
            for field in self.record_fields
        )
        expected_field_values_sha256 = canonical_digest(
            {
                "schema_version": "veriformis.row-field-values/v1",
                "fields": field_values,
            }
        )
        expected_field_evidence_sha256 = canonical_digest(
            {
                "schema_version": "veriformis.row-field-evidence/v1",
                "fields": field_evidence,
            }
        )
        if (
            self.field_values_sha256 != expected_field_values_sha256
            or self.field_evidence_sha256 != expected_field_evidence_sha256
        ):
            raise ValueError("row provenance record field digest mismatch")
        expected_id = derive_id(
            "prv",
            self.model_dump(mode="json", exclude={"provenance_id"}),
        )
        if self.provenance_id != expected_id:
            raise ValueError("row provenance identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        serialization_plan_id: str,
        construction_result_id: str,
        curation_result_id: str,
        split_result_id: str,
        partition: Partition,
        ordinal: int,
        row: ProductRow,
        record: DatasetRecord,
        curation_decision_id: str,
        assignment: RecordAssignment,
        leakage_group: LeakageGroup,
    ) -> RowProvenance:
        if row.record_id != record.record_id:
            raise SerializationError("product row names another dataset record")
        if assignment.record_id != record.record_id:
            raise SerializationError("split assignment names another dataset record")
        if assignment.group_id != leakage_group.group_id:
            raise SerializationError("split assignment names another leakage group")
        if partition != assignment.partition:
            raise SerializationError("row partition differs from split assignment")
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
            "schema_version": "veriformis.row-provenance/v1",
            "plan_id": plan_id,
            "serialization_plan_id": serialization_plan_id,
            "construction_result_id": construction_result_id,
            "curation_result_id": curation_result_id,
            "split_result_id": split_result_id,
            "partition": partition,
            "ordinal": ordinal,
            "row_id": row.row_id,
            "payload_sha256": row.payload_sha256,
            "record_id": record.record_id,
            "promotion_decision_id": record.decision_id,
            "curation_decision_id": curation_decision_id,
            "leakage_group_id": leakage_group.group_id,
            "assignment_id": assignment.assignment_id,
            "recipe_id": record.recipe_id,
            "objective_id": record.objective_id,
            "pass_id": record.pass_id,
            "source_ids": record.source_ids,
            "chunk_ids": record.chunk_ids,
            "transform_ids": record.transform_ids,
            "record_fields": record.fields,
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


def _canonical_payload_jsonl(rows: Sequence[ProductRow]) -> bytes:
    return b"".join(lossless_json_bytes(row.payload) + b"\n" for row in rows)


def _canonical_provenance_jsonl(
    provenance: Sequence[RowProvenance],
) -> bytes:
    return b"".join(
        lossless_json_bytes(item.model_dump(mode="json")) + b"\n" for item in provenance
    )


class RowSet(_StrictModel):
    """Complete ordered row/provenance state and exact emitted-byte bindings."""

    schema_version: Literal["veriformis.row-set/v1"] = "veriformis.row-set/v1"
    row_set_id: str
    plan_id: str
    serialization_plan_id: str
    recipe_id: str
    construction_result_id: str
    curation_result_id: str
    split_result_id: str
    row_schema: RowSchema
    train_rows: tuple[ProductRow, ...]
    evaluation_rows: tuple[ProductRow, ...]
    provenance: tuple[RowProvenance, ...]
    train_jsonl_sha256: str
    train_jsonl_byte_size: int
    evaluation_jsonl_sha256: str
    evaluation_jsonl_byte_size: int
    provenance_jsonl_sha256: str
    provenance_jsonl_byte_size: int
    train_row_count: int
    evaluation_row_count: int
    total_row_count: int

    @model_validator(mode="after")
    def _validate_row_set(self) -> RowSet:
        validate_id(self.row_set_id, kind="rws")
        validate_id(self.plan_id, kind="fdp")
        validate_id(self.serialization_plan_id, kind="srp")
        validate_id(self.recipe_id, kind="rcp")
        validate_id(self.construction_result_id, kind="run")
        validate_id(self.curation_result_id, kind="cur")
        validate_id(self.split_result_id, kind="spt")
        if self.row_schema not in PRODUCT_ROW_SCHEMAS:
            raise ValueError("row set contains an unsupported row schema")

        for row in (*self.train_rows, *self.evaluation_rows):
            _revalidate_nested(row, ProductRow, label="product row")
            if row.row_schema != self.row_schema:
                raise ValueError("product row schema differs from row set schema")
        for item in self.provenance:
            _revalidate_nested(item, RowProvenance, label="row provenance")

        if not self.train_rows:
            raise ValueError("row set requires a non-empty train partition")
        train_record_ids = tuple(row.record_id for row in self.train_rows)
        evaluation_record_ids = tuple(row.record_id for row in self.evaluation_rows)
        if train_record_ids != tuple(sorted(train_record_ids)):
            raise ValueError("train rows must be ordered by record_id")
        if evaluation_record_ids != tuple(sorted(evaluation_record_ids)):
            raise ValueError("evaluation rows must be ordered by record_id")
        combined_record_ids = (*train_record_ids, *evaluation_record_ids)
        if len(combined_record_ids) != len(set(combined_record_ids)):
            raise DuplicateIdentityError(
                "row set contains duplicate or cross-partition records"
            )
        combined_rows = (*self.train_rows, *self.evaluation_rows)
        if len({row.row_id for row in combined_rows}) != len(combined_rows):
            raise DuplicateIdentityError("row set contains duplicate product rows")
        if len({item.provenance_id for item in self.provenance}) != len(
            self.provenance
        ):
            raise DuplicateIdentityError("row set contains duplicate provenance")
        if len(self.provenance) != len(combined_rows):
            raise ValueError("row set requires one provenance value per product row")

        train_count = len(self.train_rows)
        for index, (row, item) in enumerate(zip(combined_rows, self.provenance)):
            partition: Partition = "train" if index < train_count else "evaluation"
            ordinal = index if partition == "train" else index - train_count
            if (
                item.plan_id != self.plan_id
                or item.serialization_plan_id != self.serialization_plan_id
                or item.construction_result_id != self.construction_result_id
                or item.curation_result_id != self.curation_result_id
                or item.split_result_id != self.split_result_id
                or item.partition != partition
                or item.ordinal != ordinal
                or item.row_id != row.row_id
                or item.record_id != row.record_id
                or item.payload_sha256 != row.payload_sha256
                or item.recipe_id != self.recipe_id
            ):
                raise ValueError("row provenance is not aligned with its product row")

        train_bytes = _canonical_payload_jsonl(self.train_rows)
        evaluation_bytes = _canonical_payload_jsonl(self.evaluation_rows)
        provenance_bytes = _canonical_provenance_jsonl(self.provenance)
        expected_metadata = (
            sha256_digest(train_bytes),
            len(train_bytes),
            sha256_digest(evaluation_bytes),
            len(evaluation_bytes),
            sha256_digest(provenance_bytes),
            len(provenance_bytes),
            len(self.train_rows),
            len(self.evaluation_rows),
            len(combined_rows),
        )
        actual_metadata = (
            self.train_jsonl_sha256,
            self.train_jsonl_byte_size,
            self.evaluation_jsonl_sha256,
            self.evaluation_jsonl_byte_size,
            self.provenance_jsonl_sha256,
            self.provenance_jsonl_byte_size,
            self.train_row_count,
            self.evaluation_row_count,
            self.total_row_count,
        )
        for digest in (
            self.train_jsonl_sha256,
            self.evaluation_jsonl_sha256,
            self.provenance_jsonl_sha256,
        ):
            validate_sha256(digest)
        for field_name in (
            "train_jsonl_byte_size",
            "evaluation_jsonl_byte_size",
            "provenance_jsonl_byte_size",
            "train_row_count",
            "evaluation_row_count",
            "total_row_count",
        ):
            _require_nonnegative_integer(getattr(self, field_name), field_name)
        if actual_metadata != expected_metadata:
            raise ValueError("row set byte bindings or counts do not close")

        expected_id = derive_id(
            "rws",
            self.model_dump(mode="json", exclude={"row_set_id"}),
        )
        if self.row_set_id != expected_id:
            raise ValueError("row set identity mismatch")
        return self

    @classmethod
    def create(
        cls,
        *,
        plan_id: str,
        serialization_plan_id: str,
        recipe_id: str,
        construction_result_id: str,
        curation_result_id: str,
        split_result_id: str,
        row_schema: RowSchema,
        train_rows: Sequence[ProductRow],
        evaluation_rows: Sequence[ProductRow],
        provenance: Sequence[RowProvenance],
    ) -> RowSet:
        checked_train = tuple(train_rows)
        checked_evaluation = tuple(evaluation_rows)
        checked_provenance = tuple(provenance)
        train_bytes = _canonical_payload_jsonl(checked_train)
        evaluation_bytes = _canonical_payload_jsonl(checked_evaluation)
        provenance_bytes = _canonical_provenance_jsonl(checked_provenance)
        body = {
            "schema_version": "veriformis.row-set/v1",
            "plan_id": plan_id,
            "serialization_plan_id": serialization_plan_id,
            "recipe_id": recipe_id,
            "construction_result_id": construction_result_id,
            "curation_result_id": curation_result_id,
            "split_result_id": split_result_id,
            "row_schema": row_schema,
            "train_rows": checked_train,
            "evaluation_rows": checked_evaluation,
            "provenance": checked_provenance,
            "train_jsonl_sha256": sha256_digest(train_bytes),
            "train_jsonl_byte_size": len(train_bytes),
            "evaluation_jsonl_sha256": sha256_digest(evaluation_bytes),
            "evaluation_jsonl_byte_size": len(evaluation_bytes),
            "provenance_jsonl_sha256": sha256_digest(provenance_bytes),
            "provenance_jsonl_byte_size": len(provenance_bytes),
            "train_row_count": len(checked_train),
            "evaluation_row_count": len(checked_evaluation),
            "total_row_count": len(checked_train) + len(checked_evaluation),
        }
        return cls(row_set_id=derive_id("rws", body), **body)


class SerializationOutput(NamedTuple):
    """The exact semantic row set plus the three bytes artifacts it binds."""

    row_set: RowSet
    train_jsonl: bytes
    evaluation_jsonl: bytes
    provenance_jsonl: bytes


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
        raise SerializationError(f"invalid {label}: {exc}") from exc
    if checked != value:
        raise SerializationError(f"{label} does not round-trip exactly")
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
        raise SerializationError(f"invalid {label}: {exc}") from exc


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
    except (DuplicateIdentityError, SerializationError):
        raise
    except (TypeError, UnicodeError, ValueError) as exc:
        raise SerializationError(f"invalid {label}: {exc}") from exc


def serialization_plan_to_dict(value: SerializationPlan) -> dict[str, Any]:
    return _model_to_dict(value, SerializationPlan, label="serialization plan")


def serialization_plan_from_json_bytes(data: bytes) -> SerializationPlan:
    return _model_from_json_bytes(data, SerializationPlan, label="serialization plan")


def serialization_plan_from_dict(value: dict[str, Any]) -> SerializationPlan:
    return _model_from_dict(value, SerializationPlan, label="serialization plan")


def product_row_to_dict(value: ProductRow) -> dict[str, Any]:
    return _model_to_dict(value, ProductRow, label="product row")


def product_row_from_json_bytes(data: bytes) -> ProductRow:
    return _model_from_json_bytes(data, ProductRow, label="product row")


def product_row_from_dict(value: dict[str, Any]) -> ProductRow:
    return _model_from_dict(value, ProductRow, label="product row")


def row_provenance_to_dict(value: RowProvenance) -> dict[str, Any]:
    return _model_to_dict(value, RowProvenance, label="row provenance")


def row_provenance_from_json_bytes(data: bytes) -> RowProvenance:
    return _model_from_json_bytes(data, RowProvenance, label="row provenance")


def row_provenance_from_dict(value: dict[str, Any]) -> RowProvenance:
    return _model_from_dict(value, RowProvenance, label="row provenance")


def row_set_to_dict(value: RowSet) -> dict[str, Any]:
    return _model_to_dict(value, RowSet, label="row set")


def row_set_from_json_bytes(data: bytes) -> RowSet:
    return _model_from_json_bytes(data, RowSet, label="row set")


def row_set_from_dict(value: dict[str, Any]) -> RowSet:
    return _model_from_dict(value, RowSet, label="row set")


def _checked_inputs(
    finished_plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    split_result: SplitResult,
) -> tuple[
    FinishedDatasetPlan,
    DatasetRecipe,
    ConstructionResult,
    CurationResult,
    SplitResult,
]:
    from .plan import finished_dataset_plan_from_dict

    try:
        checked_plan = finished_dataset_plan_from_dict(
            finished_plan.model_dump(mode="json")
        )
        checked_recipe = dataset_recipe_from_dict(recipe.model_dump(mode="json"))
        checked_construction = construction_result_from_dict(
            construction_result.model_dump(mode="json")
        )
        checked_curation = curation_result_from_dict(
            curation_result.model_dump(mode="json")
        )
        checked_split = split_result_from_dict(split_result.model_dump(mode="json"))
    except DuplicateIdentityError:
        raise
    except (
        AttributeError,
        ConstructionError,
        CurationError,
        SerializationError,
        SplitError,
        TypeError,
        ValueError,
    ) as exc:
        raise SerializationError(f"invalid serialization input: {exc}") from exc
    return (
        checked_plan,
        checked_recipe,
        checked_construction,
        checked_curation,
        checked_split,
    )


def _validate_input_relationships(
    finished_plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction: ConstructionResult,
    curation: CurationResult,
    split: SplitResult,
) -> None:
    plan_id = finished_plan.plan_id
    serialization_plan = finished_plan.serialization_plan
    if serialization_plan.row_schema != recipe.target_row_schema:
        raise SerializationError(
            "serialization row schema differs from the construction recipe"
        )
    if construction.recipe_id != recipe.recipe_id:
        raise SerializationError("construction result names another recipe")
    if (
        finished_plan.recipe_id != recipe.recipe_id
        or finished_plan.construction_result_id != construction.result_id
    ):
        raise SerializationError(
            "finished dataset plan names another recipe or construction result"
        )
    if curation.plan_id != plan_id:
        raise SerializationError("curation result names another finished dataset plan")
    if curation.recipe_id != recipe.recipe_id:
        raise SerializationError("curation result names another recipe")
    if curation.construction_result_id != construction.result_id:
        raise SerializationError("curation result names another construction result")
    construction_record_ids = tuple(
        sorted(record.record_id for record in construction.records)
    )
    if curation.input_record_ids != construction_record_ids:
        raise SerializationError(
            "curation records do not exactly match construction records"
        )
    if split.construction_result_id != construction.result_id:
        raise SerializationError("split result names another construction result")
    if split.plan_id != plan_id:
        raise SerializationError("split result names another finished dataset plan")
    if split.curation_result_id != curation.result_id:
        raise SerializationError("split result names another curation result")
    if split.plan_id != plan_id:
        raise SerializationError("split result names another finished dataset plan")
    if split.policy_id != finished_plan.split_policy.policy_id:
        raise SerializationError("split result names another split policy")
    if curation.policy_id != finished_plan.curation_policy.policy_id:
        raise SerializationError("curation result names another curation policy")
    if split.input_record_ids != curation.included_record_ids:
        raise SerializationError(
            "split assignments do not exactly match curation-included records"
        )

    records_by_id = {record.record_id: record for record in construction.records}
    decisions_by_record = {
        decision.record_id: decision for decision in curation.decisions
    }
    if set(decisions_by_record) != set(records_by_id):
        raise SerializationError("curation decisions do not cover records exactly once")
    for record_id in curation.included_record_ids:
        record = records_by_id.get(record_id)
        if record is None:
            raise SerializationError("curation includes an unknown record")
        decision = decisions_by_record[record_id]
        if decision.status != "included":
            raise SerializationError("curation inclusion contradicts its decision")
        if (
            record.recipe_id != recipe.recipe_id
            or record.objective_id != recipe.objective.objective_id
            or tuple(field.name for field in record.fields)
            != recipe.objective.field_names
        ):
            raise SerializationError(
                "record fields or objective differ from the construction recipe"
            )

    assignments_by_record = {
        assignment.record_id: assignment for assignment in split.assignments
    }
    if len(assignments_by_record) != len(split.assignments):
        raise DuplicateIdentityError(
            "split result contains duplicate record assignments"
        )
    if tuple(sorted(assignments_by_record)) != curation.included_record_ids:
        raise SerializationError(
            "split result has missing, duplicate, or unknown record assignments"
        )
    groups_by_id = {group.group_id: group for group in split.groups}
    if len(groups_by_id) != len(split.groups):
        raise DuplicateIdentityError("split result contains duplicate leakage groups")
    for record_id, assignment in assignments_by_record.items():
        group = groups_by_id.get(assignment.group_id)
        if group is None or record_id not in group.record_ids:
            raise SerializationError(
                "record assignment does not bind its authoritative leakage group"
            )


def render_record_payload(
    serialization_plan: SerializationPlan,
    recipe: DatasetRecipe,
    record: DatasetRecord,
) -> dict[str, Any]:
    """Render one accepted record exactly as `format` lowers it (read-only)."""
    return _record_payload(serialization_plan, recipe, record)


def _record_payload(
    serialization_plan: SerializationPlan,
    recipe: DatasetRecipe,
    record: DatasetRecord,
) -> dict[str, Any]:
    fields = {field.name: field.value for field in record.fields}
    context_names, target_names = OBJECTIVE_FIELD_ROLES[recipe.objective.kind]
    if len(target_names) != 1:
        raise SerializationError("v1 serialization requires one target field")
    try:
        target = fields[target_names[0]]
    except KeyError as exc:
        raise SerializationError(
            f"record is missing objective target field {exc.args[0]!r}"
        ) from exc

    row_schema = serialization_plan.row_schema
    if row_schema == "text":
        if recipe.objective.kind != "full_text":
            raise SerializationError("text rows are valid only for full_text")
        return {"text": target}
    if recipe.objective.kind == "full_text":
        raise SerializationError("full_text is valid only for text rows")
    if len(context_names) != 1:
        raise SerializationError(
            "v1 supervised serialization requires one context field"
        )
    try:
        context = fields[context_names[0]]
    except KeyError as exc:
        raise SerializationError(
            f"record is missing objective context field {exc.args[0]!r}"
        ) from exc

    if row_schema == "prompt_completion":
        return {"prompt": context, "completion": target}
    if row_schema == "instruction_output":
        instruction = serialization_plan.instruction_text
        if instruction is None:
            raise SerializationError("instruction_output requires instruction_text")
        return {"instruction": instruction, "input": context, "output": target}
    if row_schema == "messages":
        return {
            "messages": [
                {"role": "user", "content": context},
                {"role": "assistant", "content": target},
            ]
        }
    if row_schema == "label-classification":
        try:
            annotator = fields["annotator"]
        except KeyError as exc:
            raise SerializationError(
                "record is missing objective annotator field 'annotator'"
            ) from exc
        return {"annotator": annotator, "context": context, "label": target}
    if row_schema == "preference-pair":
        try:
            rejected = fields["rejected"]
        except KeyError as exc:
            raise SerializationError(
                "record is missing objective rejected field 'rejected'"
            ) from exc
        return {"prompt": context, "chosen": target, "rejected": rejected}
    if row_schema == "tool-call-conversation":
        return {"conversation_id": context, "turns": json.loads(target)}
    if row_schema == "stepwise-trace":
        return {"prompt": context, "steps": json.loads(target)}
    raise SerializationError(f"unsupported product row schema {row_schema!r}")


def serialize_dataset(
    finished_plan: FinishedDatasetPlan,
    recipe: DatasetRecipe,
    construction_result: ConstructionResult,
    curation_result: CurationResult,
    split_result: SplitResult,
) -> SerializationOutput:
    """Lower each included record once under its authoritative assignment."""
    (
        checked_finished_plan,
        checked_recipe,
        checked_construction,
        checked_curation,
        checked_split,
    ) = _checked_inputs(
        finished_plan,
        recipe,
        construction_result,
        curation_result,
        split_result,
    )
    _validate_input_relationships(
        checked_finished_plan,
        checked_recipe,
        checked_construction,
        checked_curation,
        checked_split,
    )
    checked_plan = checked_finished_plan.serialization_plan
    plan_id = checked_finished_plan.plan_id

    records_by_id = {
        record.record_id: record for record in checked_construction.records
    }
    decisions_by_record = {
        decision.record_id: decision for decision in checked_curation.decisions
    }
    assignments_by_record = {
        assignment.record_id: assignment for assignment in checked_split.assignments
    }
    groups_by_id = {group.group_id: group for group in checked_split.groups}

    rows_by_record = {
        record_id: ProductRow.create(
            record_id=record_id,
            row_schema=checked_plan.row_schema,
            payload=_record_payload(
                checked_plan,
                checked_recipe,
                records_by_id[record_id],
            ),
        )
        for record_id in checked_curation.included_record_ids
    }
    train_rows = tuple(
        rows_by_record[record_id]
        for record_id in sorted(rows_by_record)
        if assignments_by_record[record_id].partition == "train"
    )
    evaluation_rows = tuple(
        rows_by_record[record_id]
        for record_id in sorted(rows_by_record)
        if assignments_by_record[record_id].partition == "evaluation"
    )
    provenance: list[RowProvenance] = []
    for partition, rows in (
        ("train", train_rows),
        ("evaluation", evaluation_rows),
    ):
        for ordinal, row in enumerate(rows):
            record = records_by_id[row.record_id]
            assignment = assignments_by_record[row.record_id]
            provenance.append(
                RowProvenance.create(
                    plan_id=plan_id,
                    serialization_plan_id=checked_plan.serialization_plan_id,
                    construction_result_id=checked_construction.result_id,
                    curation_result_id=checked_curation.result_id,
                    split_result_id=checked_split.result_id,
                    partition=partition,
                    ordinal=ordinal,
                    row=row,
                    record=record,
                    curation_decision_id=(
                        decisions_by_record[row.record_id].decision_id
                    ),
                    assignment=assignment,
                    leakage_group=groups_by_id[assignment.group_id],
                )
            )

    row_set = RowSet.create(
        plan_id=plan_id,
        serialization_plan_id=checked_plan.serialization_plan_id,
        recipe_id=checked_recipe.recipe_id,
        construction_result_id=checked_construction.result_id,
        curation_result_id=checked_curation.result_id,
        split_result_id=checked_split.result_id,
        row_schema=checked_plan.row_schema,
        train_rows=train_rows,
        evaluation_rows=evaluation_rows,
        provenance=tuple(provenance),
    )
    train_jsonl = _canonical_payload_jsonl(row_set.train_rows)
    evaluation_jsonl = _canonical_payload_jsonl(row_set.evaluation_rows)
    provenance_jsonl = _canonical_provenance_jsonl(row_set.provenance)
    if (
        sha256_digest(train_jsonl) != row_set.train_jsonl_sha256
        or sha256_digest(evaluation_jsonl) != row_set.evaluation_jsonl_sha256
        or sha256_digest(provenance_jsonl) != row_set.provenance_jsonl_sha256
    ):
        raise SerializationError("emitted bytes do not match the row set")
    return SerializationOutput(
        row_set=row_set,
        train_jsonl=train_jsonl,
        evaluation_jsonl=evaluation_jsonl,
        provenance_jsonl=provenance_jsonl,
    )


__all__ = [
    "render_record_payload",
    "V1_PARTITION_ORDER",
    "PRODUCT_ROW_SCHEMAS",
    "V1_ROW_SCHEMAS",
    "ProductRow",
    "RowProvenance",
    "RowSchema",
    "RowSet",
    "SerializationOutput",
    "SerializationPlan",
    "product_row_from_dict",
    "product_row_from_json_bytes",
    "product_row_to_dict",
    "row_provenance_from_dict",
    "row_provenance_from_json_bytes",
    "row_provenance_to_dict",
    "row_set_from_dict",
    "row_set_from_json_bytes",
    "row_set_to_dict",
    "serialization_plan_from_dict",
    "serialization_plan_from_json_bytes",
    "serialization_plan_to_dict",
    "serialize_dataset",
]
