"""Frozen CLI-first 1.0 support matrix. Loading is not a version bump."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from veriformis.contracts import (
    SUPPORT_MATRIX_CONTRACT_ID,
    SUPPORT_MATRIX_CONTRACT_VERSION,
    SUPPORT_MATRIX_SCHEMA_ID,
)
from veriformis.errors import SupportMatrixError


MATRIX_DATA_NAME = "support-matrix-v1.json"
REQUIRED_EXCLUSIONS: tuple[str, ...] = (
    "default-parse-ocr-image",
    "generator",
    "hosted-training",
    "hub-execute",
    "plugin-loader",
    "public-signed-mac",
    "published-corpus-tiers",
    "quality-report-command",
    "required-trainer-extras",
    "unsloth-execute",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class SupportMatrixHost(_StrictModel):
    os: Literal["macos", "ubuntu"]
    python: str

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrixHost:
        if self.python not in {"3.11", "3.12", "3.13"}:
            raise SupportMatrixError("support-matrix host python must be 3.11, 3.12, or 3.13")
        if self.os == "macos" and self.python != "3.12":
            raise SupportMatrixError("support-matrix macos CI host is python 3.12 only")
        return self


class SupportMatrixPlatforms(_StrictModel):
    ci_hosts: tuple[SupportMatrixHost, ...]
    macos_workbench: Literal["local-dev-thin-adapter"]
    public_signed_mac: Literal[False]
    python: tuple[str, ...]

    @field_validator("ci_hosts", "python", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrixPlatforms:
        if self.python != ("3.11", "3.12", "3.13"):
            raise SupportMatrixError("support-matrix python must be 3.11, 3.12, and 3.13")
        if self.public_signed_mac is not False:
            raise SupportMatrixError("support-matrix cannot claim a public signed Mac")
        hosts = tuple((item.os, item.python) for item in self.ci_hosts)
        if hosts != (
            ("macos", "3.12"),
            ("ubuntu", "3.11"),
            ("ubuntu", "3.12"),
            ("ubuntu", "3.13"),
        ):
            raise SupportMatrixError("support-matrix CI hosts must match the required Python jobs")
        return self


class SupportMatrixInputs(_StrictModel):
    explicitly_unsupported: tuple[str, ...]
    extensions: tuple[str, ...]
    families: tuple[str, ...]
    modes: tuple[str, ...]

    @field_validator(
        "explicitly_unsupported",
        "extensions",
        "families",
        "modes",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrixInputs:
        if self.modes != ("document-source", "dataset-row", "mixed"):
            raise SupportMatrixError("support-matrix modes must be the three compiler paths")
        if "ocr-image" not in self.explicitly_unsupported:
            raise SupportMatrixError("support-matrix must exclude default-parse ocr-image")
        if tuple(sorted(self.extensions)) != self.extensions:
            raise SupportMatrixError("support-matrix extensions must be sorted")
        return self


class SupportMatrixTraining(_StrictModel):
    explicitly_unsupported_families: tuple[str, ...]
    families: tuple[str, ...]
    goals: tuple[str, ...]
    loss_policies: tuple[str, ...]
    objectives: tuple[str, ...]
    planned_families: tuple[str, ...]
    presets: tuple[str, ...]
    row_schemas: tuple[str, ...]

    @field_validator(
        "explicitly_unsupported_families",
        "families",
        "goals",
        "loss_policies",
        "objectives",
        "planned_families",
        "presets",
        "row_schemas",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value


class SupportMatrixProfiles(_StrictModel):
    candidate_not_executable: tuple[str, ...]
    extras_empty: tuple[str, ...]
    extras_required: tuple[()]
    implemented: tuple[str, ...]
    optional_export_adapters: tuple[str, ...]

    @field_validator(
        "candidate_not_executable",
        "extras_empty",
        "implemented",
        "optional_export_adapters",
        mode="before",
    )
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("extras_required", mode="before")
    @classmethod
    def _empty_required(cls, value: Any) -> Any:
        if value not in ((), []):
            raise SupportMatrixError("support-matrix extras_required must stay empty")
        return ()

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrixProfiles:
        if "unsloth" not in self.candidate_not_executable:
            raise SupportMatrixError("support-matrix must keep unsloth non-executable")
        if tuple(sorted(self.extras_empty)) != self.extras_empty:
            raise SupportMatrixError("support-matrix extras_empty must be sorted")
        return self


class SupportMatrixExclusion(_StrictModel):
    exclusion_id: str
    reason: str

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrixExclusion:
        if not self.exclusion_id.strip() or self.exclusion_id.strip() != self.exclusion_id:
            raise SupportMatrixError("support-matrix exclusion_id must be a nonempty token")
        if not self.reason.strip() or self.reason.strip() != self.reason:
            raise SupportMatrixError("support-matrix exclusion reason must be nonempty")
        return self


class SupportMatrix(_StrictModel):
    """Frozen CLI-first capability set. This is not a 1.0 version claim."""

    aptus_required: Literal[False]
    claim: Literal["cli-first-independent-core"]
    containers: tuple[str, ...]
    contract_id: Literal["veriformis.support-matrix"]
    contract_version: Literal[1]
    core_surfaces: tuple[str, ...]
    exclusions: tuple[SupportMatrixExclusion, ...]
    generator: Literal[False]
    hosted_training: Literal[False]
    hub_execute: Literal[False]
    inputs: SupportMatrixInputs
    maturity: Literal["development-alpha"]
    platforms: SupportMatrixPlatforms
    plugin_loader: Literal[False]
    product_version: Literal["0.1.0"]
    profiles: SupportMatrixProfiles
    published_corpus_tiers: tuple[()]
    quality_report_command: Literal[False]
    schema_id: Literal["veriformis.support-matrix/v1"]
    training: SupportMatrixTraining
    version_change_deferred_to: Literal["20.10"]

    @field_validator("containers", "core_surfaces", "exclusions", mode="before")
    @classmethod
    def _tuple_fields(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("published_corpus_tiers", mode="before")
    @classmethod
    def _empty_tiers(cls, value: Any) -> Any:
        if value not in ((), []):
            raise SupportMatrixError("support-matrix published_corpus_tiers must stay empty")
        return ()

    @model_validator(mode="after")
    def _closed(self) -> SupportMatrix:
        if self.contract_id != SUPPORT_MATRIX_CONTRACT_ID:
            raise SupportMatrixError("support-matrix contract_id mismatch")
        if self.contract_version != SUPPORT_MATRIX_CONTRACT_VERSION:
            raise SupportMatrixError("support-matrix contract_version mismatch")
        if self.schema_id != SUPPORT_MATRIX_SCHEMA_ID:
            raise SupportMatrixError("support-matrix schema_id mismatch")
        if self.core_surfaces != (
            "local-mcp",
            "python-pipeline-service",
            "typer-cli",
        ):
            raise SupportMatrixError("support-matrix core surfaces must be CLI, MCP, and Python")
        ids = tuple(item.exclusion_id for item in self.exclusions)
        if ids != REQUIRED_EXCLUSIONS:
            raise SupportMatrixError("support-matrix exclusions must be the frozen sorted set")
        if self.product_version != "0.1.0":
            raise SupportMatrixError("support-matrix cannot bump version; that waits for 20.10")
        return self


def _load_matrix() -> tuple[str, SupportMatrix]:
    raw = (
        resources.files("veriformis.release")
        .joinpath(MATRIX_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SupportMatrixError(f"support-matrix JSON is malformed: {exc}") from exc
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if canonical != raw:
        raise SupportMatrixError("support-matrix catalog is not canonical JSON")
    try:
        matrix = SupportMatrix.model_validate(payload)
    except (SupportMatrixError, ValidationError) as exc:
        raise SupportMatrixError(str(exc)) from exc
    return canonical, matrix


@lru_cache(maxsize=1)
def support_matrix() -> SupportMatrix:
    return _load_matrix()[1]


def support_matrix_json() -> str:
    return _load_matrix()[0]


def support_matrix_discovery() -> dict[str, Any]:
    return json.loads(support_matrix_json())
