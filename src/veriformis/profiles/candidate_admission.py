"""Section-5 admission pins for Phase 10 candidate consumer profiles."""

from __future__ import annotations

import json
from collections.abc import Mapping as MappingABC
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.contracts import (
    CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID,
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    PROFILE_ADMISSION_CONTRACT_ID,
    PROFILE_ADMISSION_CONTRACT_VERSION,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import ExportContractError
from veriformis.identity import sha256_digest
from veriformis.taxonomy import (
    CANDIDATE_CONSUMER_PROFILES,
    OBJECTIVE_ROW_COMPATIBILITY,
)

CANDIDATE_ADMISSION_DATA_NAME = "candidate-admission-v1.json"
CANDIDATE_PROFILE_IDS: tuple[str, ...] = CANDIDATE_CONSUMER_PROFILES
RowSchema = Literal["instruction_output", "messages", "prompt_completion", "text"]
MappingKind = Literal["identity", "assemble-prompt", "remap"]
CandidateState = Literal["admitted", "deferred", "experimental"]
LaterItem = Literal["10.3-10.5", "10.6", "none"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class CandidateRowMappingPin(_StrictModel):
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
    def _closed(self) -> CandidateRowMappingPin:
        if self.source_row_schema not in V1_ROW_SCHEMA_KINDS:
            raise ExportContractError("candidate admission names an unsupported row schema")
        if not self.destination_format.strip() or not self.notes.strip():
            raise ExportContractError("candidate mapping notes must be nonempty")
        if self.destination_keys != tuple(sorted(self.destination_keys)):
            raise ExportContractError("destination_keys must be sorted")
        if len(self.destination_keys) != len(set(self.destination_keys)):
            raise ExportContractError("destination_keys must be unique")
        return self


class CandidateProfileAdmission(_StrictModel):
    accepted_goals: tuple[str, ...]
    admitted_row_schemas: tuple[RowSchema, ...]
    admission_verdict: str
    deprecation_policy: str
    docs_reviewed_on: str
    emit_eligible: bool
    extra: str
    later_item: LaterItem
    license: str
    loader: str
    loss_notes: str
    machine_checkable_contract: bool
    package: str
    partition_mapping: dict[str, str]
    primary_docs_url: str
    profile_id: str
    refused_dataset_types: tuple[str, ...]
    rejected_goals: tuple[str, ...]
    round_trip: bool
    row_mappings: tuple[CandidateRowMappingPin, ...]
    state: CandidateState
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
    def _closed(self) -> CandidateProfileAdmission:
        if self.profile_id not in CANDIDATE_PROFILE_IDS:
            raise ExportContractError(
                f"candidate admission profile {self.profile_id!r} is not a Phase 10 pin"
            )
        if self.profile_id == "aptus":
            if self.extra != "":
                raise ExportContractError("aptus pin extra must be empty")
            if self.state != "deferred" or self.later_item != "10.6":
                raise ExportContractError("aptus pin must defer to item 10.6")
        else:
            if self.extra != self.profile_id:
                raise ExportContractError("candidate extra must equal profile_id")
        if self.emit_eligible is not (self.state == "admitted"):
            raise ExportContractError("emit_eligible is true only for admitted pins")
        if self.state == "admitted" and self.later_item != "10.3-10.5":
            raise ExportContractError("admitted pins name later items 10.3-10.5")
        if self.state == "experimental" and self.later_item != "none":
            raise ExportContractError("experimental pins do not name an emit item")
        if self.state == "experimental" and self.machine_checkable_contract:
            raise ExportContractError("experimental pins are not machine-checkable contracts")
        if self.state == "admitted" and not self.machine_checkable_contract:
            raise ExportContractError("admitted pins require a machine-checkable contract")
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
        if tuple(sorted(self.partition_mapping)) != ("evaluation", "train"):
            raise ExportContractError("partition_mapping must name train and evaluation")
        if self.round_trip is not False:
            raise ExportContractError("candidate pins do not claim round-trip")
        for field in (
            "admission_verdict",
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
                raise ExportContractError(f"candidate admission {field} must be nonempty")
        return self


class CandidateProfileAdmissionCatalog(_StrictModel):
    contract_id: Literal["veriformis.consumer-profile-admission"]
    contract_version: Literal[1]
    records: tuple[CandidateProfileAdmission, ...]
    schema_id: Literal["veriformis.candidate-profile-admission-discovery/v1"]

    @field_validator("records", mode="before")
    @classmethod
    def _tuple_records(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> CandidateProfileAdmissionCatalog:
        if self.schema_id != CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID:
            raise ExportContractError("candidate admission catalog schema_id mismatch")
        if self.contract_id != PROFILE_ADMISSION_CONTRACT_ID:
            raise ExportContractError("candidate admission catalog contract_id mismatch")
        if self.contract_version != PROFILE_ADMISSION_CONTRACT_VERSION:
            raise ExportContractError("candidate admission catalog contract_version mismatch")
        ids = tuple(record.profile_id for record in self.records)
        if ids != CANDIDATE_PROFILE_IDS:
            raise ExportContractError(
                "candidate admission records must match Phase 10 pins in order"
            )
        return self


@lru_cache(maxsize=1)
def candidate_profile_admission_catalog() -> CandidateProfileAdmissionCatalog:
    raw = (
        resources.files("veriformis.profiles")
        .joinpath(CANDIDATE_ADMISSION_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    if not isinstance(payload, MappingABC):
        raise ExportContractError("candidate admission catalog must be an object")
    catalog = CandidateProfileAdmissionCatalog.model_validate(payload)
    canonical = _canonical_json(catalog.model_dump(mode="json"))
    if raw != canonical:
        raise ExportContractError("candidate admission catalog is not canonical JSON")
    return catalog


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def candidate_profile_admission_catalog_json() -> str:
    return _canonical_json(candidate_profile_admission_catalog().model_dump(mode="json"))


def discover_candidate_profile_admissions() -> dict[str, Any]:
    return json.loads(candidate_profile_admission_catalog_json())


def candidate_profile_admission_digest() -> str:
    return sha256_digest(candidate_profile_admission_catalog_json())
