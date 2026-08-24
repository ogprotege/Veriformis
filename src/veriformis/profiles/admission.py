"""Section-5 admission pins for implemented export consumer profiles."""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    PROFILE_ADMISSION_CONTRACT_ID,
    PROFILE_ADMISSION_CONTRACT_VERSION,
    PROFILE_ADMISSION_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import ExportContractError
from veriformis.identity import sha256_digest
from veriformis.taxonomy import (
    EXPORT_CONSUMER_PROFILE_ITEMS,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
    OBJECTIVE_ROW_COMPATIBILITY,
)

ADMISSION_DATA_NAME = "admission-v1.json"
RowSchema = Literal["instruction_output", "messages", "prompt_completion", "text"]
MappingKind = Literal["identity", "assemble-prompt", "remap"]
PartitionName = Literal["evaluation", "train"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class RowMappingPin(_StrictModel):
    destination_format: str
    destination_keys: tuple[str, ...]
    mapping_kind: MappingKind
    notes: str
    source_row_schema: RowSchema

    @field_validator("destination_keys", mode="before")
    @classmethod
    def _tuple_keys(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> RowMappingPin:
        if self.source_row_schema not in V1_ROW_SCHEMA_KINDS:
            raise ExportContractError("admission names an unsupported row schema")
        if not self.destination_format.strip() or not self.notes.strip():
            raise ExportContractError("admission mapping notes must be nonempty")
        if self.destination_keys != tuple(sorted(self.destination_keys)):
            raise ExportContractError("destination_keys must be sorted")
        if len(self.destination_keys) != len(set(self.destination_keys)):
            raise ExportContractError("destination_keys must be unique")
        return self


class ProfileAdmission(_StrictModel):
    accepted_goals: tuple[str, ...]
    admitted_row_schemas: tuple[RowSchema, ...]
    deprecation_policy: str
    docs_reviewed_on: str
    executable_item: str
    extra: str
    license: str
    loader: str
    loss_notes: str
    package: str
    partition_mapping: dict[str, str]
    primary_docs_url: str
    profile_id: str
    refused_dataset_types: tuple[str, ...]
    rejected_goals: tuple[str, ...]
    round_trip: bool
    row_mappings: tuple[RowMappingPin, ...]
    state: Literal["implemented"]
    transformed_row_schemas: tuple[RowSchema, ...]
    version_range: str
    workflow: str

    @field_validator(
        "accepted_goals",
        "admitted_row_schemas",
        "refused_dataset_types",
        "rejected_goals",
        "row_mappings",
        "transformed_row_schemas",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ProfileAdmission:
        if self.profile_id not in IMPLEMENTED_EXPORT_CONSUMER_PROFILES:
            raise ExportContractError(
                f"admission profile {self.profile_id!r} is not an implemented export profile"
            )
        expected_item = EXPORT_CONSUMER_PROFILE_ITEMS[self.profile_id]
        if self.executable_item != expected_item:
            raise ExportContractError(
                f"admission {self.profile_id!r} must name item {expected_item}"
            )
        if self.profile_id == "aptus":
            if self.extra != "":
                raise ExportContractError("aptus pin extra must be empty")
        elif self.extra != self.profile_id:
            raise ExportContractError("admission extra must equal profile_id")
        if self.admitted_row_schemas != tuple(sorted(self.admitted_row_schemas)):
            raise ExportContractError("admitted_row_schemas must be sorted")
        if self.refused_dataset_types != tuple(sorted(self.refused_dataset_types)):
            raise ExportContractError("refused_dataset_types must be sorted")
        mapped = tuple(item.source_row_schema for item in self.row_mappings)
        if mapped != self.admitted_row_schemas:
            raise ExportContractError("row_mappings must cover admitted schemas in order")
        transformed = tuple(
            item.source_row_schema
            for item in self.row_mappings
            if item.mapping_kind in {"assemble-prompt", "remap"}
        )
        if self.transformed_row_schemas != transformed:
            raise ExportContractError(
                "transformed_row_schemas must match assemble-prompt and remap mappings"
            )
        expected_goals = tuple(
            sorted(
                objective
                for objective in DETERMINISTIC_V1_OBJECTIVE_KINDS
                if set(OBJECTIVE_ROW_COMPATIBILITY[objective]) & set(self.admitted_row_schemas)
            )
        )
        if self.accepted_goals != expected_goals:
            raise ExportContractError("accepted_goals must match admitted row schemas")
        expected_rejected = tuple(
            objective
            for objective in DETERMINISTIC_V1_OBJECTIVE_KINDS
            if objective not in self.accepted_goals
        )
        if self.rejected_goals != expected_rejected:
            raise ExportContractError("rejected_goals must be the remaining v1 objectives")
        expected_partitions = ("evaluation", "train")
        if tuple(sorted(self.partition_mapping)) != expected_partitions:
            raise ExportContractError("partition_mapping must name train and evaluation")
        if self.round_trip is not False:
            raise ExportContractError("admission pins do not claim round-trip yet")
        for field in (
            "deprecation_policy",
            "docs_reviewed_on",
            "license",
            "loader",
            "loss_notes",
            "package",
            "primary_docs_url",
            "version_range",
            "workflow",
        ):
            if not str(getattr(self, field)).strip():
                raise ExportContractError(f"admission {field} must be nonempty")
        return self


class ProfileAdmissionCatalog(_StrictModel):
    contract_id: Literal["veriformis.consumer-profile-admission"]
    contract_version: Literal[1]
    records: tuple[ProfileAdmission, ...]
    schema_id: Literal["veriformis.profile-admission-discovery/v1"]

    @field_validator("records", mode="before")
    @classmethod
    def _tuple_records(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ProfileAdmissionCatalog:
        if self.schema_id != PROFILE_ADMISSION_SCHEMA_ID:
            raise ExportContractError("admission catalog schema_id mismatch")
        if self.contract_id != PROFILE_ADMISSION_CONTRACT_ID:
            raise ExportContractError("admission catalog contract_id mismatch")
        if self.contract_version != PROFILE_ADMISSION_CONTRACT_VERSION:
            raise ExportContractError("admission catalog contract_version mismatch")
        ids = tuple(record.profile_id for record in self.records)
        if ids != IMPLEMENTED_EXPORT_CONSUMER_PROFILES:
            raise ExportContractError(
                "admission records must match implemented export profiles in order"
            )
        return self


@lru_cache(maxsize=1)
def profile_admission_catalog() -> ProfileAdmissionCatalog:
    raw = (
        resources.files("veriformis.profiles")
        .joinpath(ADMISSION_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    if not isinstance(payload, MappingABC):
        raise ExportContractError("admission catalog must be an object")
    catalog = ProfileAdmissionCatalog.model_validate(payload)
    canonical = _canonical_json(catalog.model_dump(mode="json"))
    if raw != canonical:
        raise ExportContractError("admission catalog is not canonical JSON")
    return catalog


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def profile_admission_catalog_json() -> str:
    return _canonical_json(profile_admission_catalog().model_dump(mode="json"))


def discover_profile_admissions() -> dict[str, Any]:
    return json.loads(profile_admission_catalog_json())


def profile_admission_digest() -> str:
    return sha256_digest(profile_admission_catalog_json())


def require_profile_messages_payload(payload: MappingABC[str, Any]) -> None:
    """Refuse system roles, extra turns, tools, and nested non-string content."""
    if set(payload) != {"messages"}:
        raise ExportContractError("messages payload extra keys are refused")
    messages = payload["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ExportContractError(
            "messages export requires exactly two user then assistant turns"
        )
    expected_roles = ("user", "assistant")
    for index, (message, role) in enumerate(zip(messages, expected_roles)):
        if not isinstance(message, MappingABC):
            raise ExportContractError(f"messages turn {index} has an invalid shape")
        extra = set(message) - {"content", "role"}
        if extra:
            raise ExportContractError("messages extra keys are refused")
        if message.get("role") != role:
            raise ExportContractError(
                f"messages turn {index} must have role {role!r}; "
                "system roles and extra assistant turns are refused"
            )
        content = message.get("content")
        if not isinstance(content, str) or not content:
            raise ExportContractError("messages content must be a nonempty string")
