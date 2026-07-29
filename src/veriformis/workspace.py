"""Immutable, transactional workspace revisions and content-addressed artifacts."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from veriformis.contracts import (
    CANONICAL_STREAM_CONTRACT_VERSION,
    CONSTRUCTION_STAGE_SCHEMA_ID,
)
from veriformis.errors import (
    ArtifactDigestMismatchError,
    DuplicateIdentityError,
    MissingStageInputError,
    ParseError,
    StaleStageError,
    UnsupportedWorkspaceVersionError,
    VeriformisError,
    WorkspaceCorruptError,
    WorkspaceLockedError,
    WorkspaceNotFoundError,
    WorkspaceRevisionConflict,
)
from veriformis.identity import (
    canonical_digest,
    derive_artifact_id,
    derive_id,
    derive_source_id,
    normalize_logical_path,
    lossless_json_bytes,
    sha256_digest,
    validate_id,
    validate_sha256,
)

WORKSPACE_LAYOUT_SCHEMA_VERSION = 1
LEGACY_REVISION_SCHEMA_VERSION = 1
WORKSPACE_REVISION_SCHEMA_VERSION = 2
CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION = CONSTRUCTION_STAGE_SCHEMA_ID

# Compatibility alias for callers that used the original name for the
# workspace.json layout contract. Revision manifests now carry their own,
# independently versioned schema.
WORKSPACE_SCHEMA_VERSION = WORKSPACE_LAYOUT_SCHEMA_VERSION

StageName = Literal[
    "parse", "clean", "chunk", "construct", "format", "validate", "seal"
]
StageStatus = Literal["complete", "failed", "stale", "absent"]
CommitStage = Literal[
    "init",
    "migration",
    "parse",
    "clean",
    "chunk",
    "construct",
    "format",
    "validate",
    "seal",
]

LEGACY_STAGES: tuple[StageName, ...] = (
    "parse",
    "clean",
    "chunk",
    "format",
    "validate",
    "seal",
)
STAGES: tuple[StageName, ...] = (
    "parse",
    "clean",
    "chunk",
    "construct",
    "format",
    "validate",
    "seal",
)

LEGACY_STAGE_DEPENDENCIES: dict[StageName, tuple[StageName, ...]] = {
    "parse": (),
    "clean": ("parse",),
    "chunk": ("clean",),
    "format": ("chunk",),
    "validate": ("parse", "clean", "chunk", "format"),
    "seal": ("parse", "clean", "chunk", "format", "validate"),
}
STAGE_DEPENDENCIES: dict[StageName, tuple[StageName, ...]] = {
    **LEGACY_STAGE_DEPENDENCIES,
    "construct": ("parse", "clean", "chunk"),
}


def _stages_for_revision(schema_version: int) -> tuple[StageName, ...]:
    if schema_version == LEGACY_REVISION_SCHEMA_VERSION:
        return LEGACY_STAGES
    if schema_version == WORKSPACE_REVISION_SCHEMA_VERSION:
        return STAGES
    raise UnsupportedWorkspaceVersionError(
        f"workspace revision schema {schema_version} is not supported"
    )


def _dependencies_for_revision(
    schema_version: int,
) -> dict[StageName, tuple[StageName, ...]]:
    _stages_for_revision(schema_version)
    return (
        LEGACY_STAGE_DEPENDENCIES
        if schema_version == LEGACY_REVISION_SCHEMA_VERSION
        else STAGE_DEPENDENCIES
    )


def _descendants(
    stage: StageName,
    *,
    stages: tuple[StageName, ...] = STAGES,
    dependencies: Mapping[StageName, tuple[StageName, ...]] = STAGE_DEPENDENCIES,
) -> tuple[StageName, ...]:
    found: set[StageName] = set()
    pending: list[StageName] = [stage]
    while pending:
        parent = pending.pop()
        for candidate, required in dependencies.items():
            if parent in required and candidate not in found:
                found.add(candidate)
                pending.append(candidate)
    return tuple(item for item in stages if item in found)


STAGE_DESCENDANTS: dict[StageName, tuple[StageName, ...]] = {
    stage: _descendants(stage) for stage in STAGES
}


def _descendants_for_revision(
    schema_version: int,
    stage: StageName,
) -> tuple[StageName, ...]:
    stages = _stages_for_revision(schema_version)
    dependencies = _dependencies_for_revision(schema_version)
    return _descendants(stage, stages=stages, dependencies=dependencies)


class _PersistedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class WorkspaceMetadata(_PersistedModel):
    schema_version: int = WORKSPACE_LAYOUT_SCHEMA_VERSION
    workspace_id: str
    created_at: str

    @field_validator("workspace_id")
    @classmethod
    def _valid_workspace_id(cls, value: str) -> str:
        return validate_id(value, kind="ws")


class SourceDescriptor(_PersistedModel):
    id: str
    logical_path: str
    original_path: str | None = None
    sha256: str
    size: int
    parser_id: str
    parser_version: str
    canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION
    raw_artifact_id: str | None = None
    extracted_artifact_id: str | None = None
    document_artifact_id: str | None = None

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        return validate_id(value, kind="src")

    @field_validator("logical_path")
    @classmethod
    def _valid_logical_path(cls, value: str) -> str:
        return normalize_logical_path(value)

    @field_validator("sha256")
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("raw_artifact_id", "extracted_artifact_id", "document_artifact_id")
    @classmethod
    def _valid_artifact_id(cls, value: str | None) -> str | None:
        return validate_id(value, kind="art") if value is not None else None

    @field_validator("canonical_stream_contract_version")
    @classmethod
    def _valid_stream_contract_version(cls, value: int) -> int:
        if value != CANONICAL_STREAM_CONTRACT_VERSION:
            raise UnsupportedWorkspaceVersionError(
                f"canonical stream contract {value} is not supported; "
                f"expected {CANONICAL_STREAM_CONTRACT_VERSION}"
            )
        return value

    @model_validator(mode="after")
    def _consistent_identity(self) -> SourceDescriptor:
        expected = derive_source_id(self.logical_path, self.sha256)
        if self.id != expected:
            raise DuplicateIdentityError(
                f"source identity does not match logical path and raw digest: {self.id}"
            )
        if self.size < 0:
            raise ValueError("source size cannot be negative")
        return self

    @classmethod
    def create(
        cls,
        *,
        logical_path: str,
        sha256: str,
        size: int,
        parser_id: str,
        parser_version: str,
        canonical_stream_contract_version: int = CANONICAL_STREAM_CONTRACT_VERSION,
        original_path: str | None = None,
        raw_artifact_id: str | None = None,
        extracted_artifact_id: str | None = None,
        document_artifact_id: str | None = None,
    ) -> SourceDescriptor:
        normalized = normalize_logical_path(logical_path)
        return cls(
            id=derive_source_id(normalized, sha256),
            logical_path=normalized,
            original_path=original_path,
            sha256=sha256,
            size=size,
            parser_id=parser_id,
            parser_version=parser_version,
            canonical_stream_contract_version=canonical_stream_contract_version,
            raw_artifact_id=raw_artifact_id,
            extracted_artifact_id=extracted_artifact_id,
            document_artifact_id=document_artifact_id,
        )


class ArtifactRef(_PersistedModel):
    id: str
    kind: str
    sha256: str
    size: int
    media_type: str
    source_ids: tuple[str, ...] = ()
    producer_id: str
    producer_version: str
    config_digest: str

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        return validate_id(value, kind="art")

    @field_validator("sha256", "config_digest")
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("source_ids")
    @classmethod
    def _valid_sources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted(validate_id(item, kind="src") for item in value))
        if len(normalized) != len(set(normalized)):
            raise DuplicateIdentityError(
                "artifact source_ids contain duplicate identities"
            )
        return normalized

    @model_validator(mode="after")
    def _consistent_identity(self) -> ArtifactRef:
        if self.size < 0:
            raise ValueError("artifact size cannot be negative")
        expected = derive_artifact_id(
            kind=self.kind,
            content_sha256=self.sha256,
            source_ids=self.source_ids,
            producer_id=self.producer_id,
            producer_version=self.producer_version,
            config_digest=self.config_digest,
        )
        if self.id != expected:
            raise DuplicateIdentityError(
                f"artifact identity does not match its payload: {self.id}"
            )
        return self

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        kind: str,
        media_type: str,
        source_ids: Iterable[str] = (),
        producer_id: str,
        producer_version: str,
        config: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        digest = sha256_digest(data)
        config_digest = canonical_digest(dict(config or {}))
        normalized_sources = tuple(sorted(source_ids))
        return cls(
            id=derive_artifact_id(
                kind=kind,
                content_sha256=digest,
                source_ids=normalized_sources,
                producer_id=producer_id,
                producer_version=producer_version,
                config_digest=config_digest,
            ),
            kind=kind,
            sha256=digest,
            size=len(data),
            media_type=media_type,
            source_ids=normalized_sources,
            producer_id=producer_id,
            producer_version=producer_version,
            config_digest=config_digest,
        )


class StageState(_PersistedModel):
    stage: StageName
    status: StageStatus
    input_artifact_ids: tuple[str, ...] = ()
    input_digest: str
    config: dict[str, Any]
    config_digest: str
    outputs: dict[str, str]
    invalidated_by: StageName | None = None
    prior_revision_id: str | None = None

    @field_validator("input_artifact_ids")
    @classmethod
    def _valid_inputs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(sorted(validate_id(item, kind="art") for item in value))
        if len(normalized) != len(set(normalized)):
            raise DuplicateIdentityError(
                "stage inputs contain duplicate artifact identities"
            )
        return normalized

    @field_validator("input_digest", "config_digest")
    @classmethod
    def _valid_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @field_validator("outputs")
    @classmethod
    def _valid_outputs(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key for key in value):
            raise ValueError("stage output names cannot be empty")
        return {
            key: validate_id(artifact_id, kind="art")
            for key, artifact_id in value.items()
        }

    @field_validator("prior_revision_id")
    @classmethod
    def _valid_prior_revision(cls, value: str | None) -> str | None:
        return validate_id(value, kind="rev") if value is not None else None

    @model_validator(mode="after")
    def _consistent_state(self) -> StageState:
        if canonical_digest(self.config) != self.config_digest:
            raise WorkspaceCorruptError(
                f"{self.stage} config digest does not match config"
            )
        if self.status == "stale":
            if self.invalidated_by is None or self.prior_revision_id is None:
                raise WorkspaceCorruptError(
                    f"stale stage {self.stage} lacks invalidation evidence"
                )
            if self.stage not in STAGE_DESCENDANTS[self.invalidated_by]:
                raise WorkspaceCorruptError(
                    f"stale stage {self.stage} is not downstream of "
                    f"invalidating stage {self.invalidated_by}"
                )
            expected_input_digest = canonical_digest(
                {
                    "stage": self.stage,
                    "status": "stale",
                    "invalidated_by": self.invalidated_by,
                }
            )
        elif self.status == "absent":
            if self.invalidated_by is not None or self.prior_revision_id is not None:
                raise WorkspaceCorruptError(
                    f"absent stage {self.stage} carries invalidation evidence"
                )
            expected_input_digest = canonical_digest(
                {"stage": self.stage, "inputs": (), "status": "absent"}
            )
        else:
            if self.invalidated_by is not None or self.prior_revision_id is not None:
                raise WorkspaceCorruptError(
                    f"active stage {self.stage} carries invalidation evidence"
                )
            expected_input_digest = canonical_digest(
                {
                    "stage": self.stage,
                    "inputs": self.input_artifact_ids,
                    "config_digest": self.config_digest,
                }
            )
        if self.input_digest != expected_input_digest:
            raise WorkspaceCorruptError(
                f"{self.stage} input digest does not match its state"
            )
        if self.status in ("absent", "stale") and (
            self.input_artifact_ids or self.outputs
        ):
            raise WorkspaceCorruptError(
                f"{self.status} stage {self.stage} retains active artifacts"
            )
        if self.status == "failed" and self.stage != "validate":
            raise WorkspaceCorruptError(
                "only validation may persist a failed stage result"
            )
        return self

    @classmethod
    def absent(cls, stage: StageName) -> StageState:
        config: dict[str, Any] = {}
        return cls(
            stage=stage,
            status="absent",
            input_artifact_ids=(),
            input_digest=canonical_digest(
                {"stage": stage, "inputs": (), "status": "absent"}
            ),
            config=config,
            config_digest=canonical_digest(config),
            outputs={},
        )

    def as_stale(
        self, *, invalidated_by: StageName, prior_revision_id: str
    ) -> StageState:
        return StageState(
            stage=self.stage,
            status="stale",
            input_artifact_ids=(),
            input_digest=canonical_digest(
                {
                    "stage": self.stage,
                    "status": "stale",
                    "invalidated_by": invalidated_by,
                }
            ),
            config=self.config,
            config_digest=self.config_digest,
            outputs={},
            invalidated_by=invalidated_by,
            prior_revision_id=prior_revision_id,
        )


def _semantic_payload(
    *,
    schema_version: int,
    sources: Mapping[str, SourceDescriptor],
    artifacts: Mapping[str, ArtifactRef],
    stages: Mapping[str, StageState],
) -> dict[str, Any]:
    semantic_sources = {
        source_id: source.model_dump(mode="json", exclude={"original_path"})
        for source_id, source in sorted(sources.items())
    }
    semantic_stages: dict[str, Any] = {}
    for stage, state in sorted(stages.items()):
        dumped = state.model_dump(mode="json", exclude={"prior_revision_id"})
        semantic_stages[stage] = dumped
    return {
        "schema_version": schema_version,
        "sources": semantic_sources,
        "artifacts": {
            artifact_id: artifact.model_dump(mode="json")
            for artifact_id, artifact in sorted(artifacts.items())
        },
        "stages": semantic_stages,
    }


_SOURCE_ARTIFACT_BINDINGS: tuple[tuple[str, str], ...] = (
    ("raw_artifact_id", "raw-source"),
    ("extracted_artifact_id", "canonical-source-text"),
    ("document_artifact_id", "document-ir"),
)

_FIXED_STAGE_OUTPUT_KINDS: dict[tuple[StageName, str], str] = {
    ("parse", "registry"): "source-registry",
    ("clean", "transforms"): "transform-records",
    ("chunk", "chunks"): "chunks",
    ("construct", "recipe"): "dataset-recipe",
    ("construct", "result"): "construction-result",
    ("format", "records"): "formatted-records",
    ("format", "records-meta"): "records-metadata",
    ("validate", "validations"): "validation-report",
}

_SOURCE_STAGE_OUTPUT_KINDS: dict[StageName, dict[str, str]] = {
    "parse": {
        "raw": "raw-source",
        "canonical": "canonical-source-text",
        "document": "document-ir",
        "diagnostics": "parse-report",
    },
    "clean": {
        "document": "cleaned-document-ir",
        "cleaning-plan": "cleaning-plan",
        "block-derivations": "block-derivations",
    },
}

_PARSE_OUTPUT_LINK_FIELDS: dict[str, str] = {
    "raw": "raw_artifact_id",
    "canonical": "extracted_artifact_id",
    "document": "document_artifact_id",
}


def _required_stage_output_kinds(
    stage: StageName,
    source_ids: tuple[str, ...],
) -> dict[str, str] | None:
    if stage == "seal":
        return None
    expected = {
        name: kind
        for (schema_stage, name), kind in _FIXED_STAGE_OUTPUT_KINDS.items()
        if schema_stage == stage
    }
    role_kinds = _SOURCE_STAGE_OUTPUT_KINDS.get(stage, {})
    for source_id in source_ids:
        for role, kind in role_kinds.items():
            expected[f"source/{source_id}/{role}"] = kind
    return expected


def _construct_source_scope(
    state: StageState,
    sources: Mapping[str, SourceDescriptor],
) -> tuple[str, ...]:
    """Return the exact source set selected by a construction recipe."""
    expected_keys = {"schema_version", "recipe_id", "selected_source_ids"}
    if set(state.config) != expected_keys:
        raise WorkspaceCorruptError(
            "construct config keys do not match the v1 stage schema"
        )
    if state.config["schema_version"] != CONSTRUCTION_STAGE_CONFIG_SCHEMA_VERSION:
        raise WorkspaceCorruptError(
            "construct config uses an unsupported stage schema"
        )
    try:
        validate_id(state.config["recipe_id"], kind="rcp")
    except (TypeError, ValueError) as exc:
        raise WorkspaceCorruptError(
            "construct config requires a valid recipe_id"
        ) from exc
    raw = state.config.get("selected_source_ids")
    if not isinstance(raw, list) or not raw:
        raise WorkspaceCorruptError(
            "construct config requires a non-empty selected_source_ids list"
        )
    try:
        selected = tuple(validate_id(item, kind="src") for item in raw)
    except (TypeError, ValueError) as exc:
        raise WorkspaceCorruptError(
            "construct config contains an invalid selected source identity"
        ) from exc
    if selected != tuple(sorted(selected)) or len(selected) != len(set(selected)):
        raise WorkspaceCorruptError(
            "construct selected_source_ids must be sorted and unique"
        )
    missing = set(selected) - set(sources)
    if missing:
        raise WorkspaceCorruptError(
            f"construct config selects unknown sources: {sorted(missing)}"
        )
    return selected


def _validate_source_artifact_bindings(
    sources: Mapping[str, SourceDescriptor],
    artifacts: Mapping[str, ArtifactRef],
) -> None:
    """Verify that each source link names the artifact it claims to name."""
    for source in sources.values():
        for field_name, expected_kind in _SOURCE_ARTIFACT_BINDINGS:
            artifact_id = getattr(source, field_name)
            if artifact_id is None:
                continue
            try:
                artifact = artifacts[artifact_id]
            except KeyError as exc:
                raise WorkspaceCorruptError(
                    f"source {source.id} refers to missing artifact {artifact_id}"
                ) from exc
            if artifact.kind != expected_kind:
                raise WorkspaceCorruptError(
                    f"source {source.id} {field_name} has kind {artifact.kind!r}; "
                    f"expected {expected_kind!r}"
                )
            if artifact.source_ids != (source.id,):
                raise WorkspaceCorruptError(
                    f"source {source.id} {field_name} has incorrect source scope"
                )
            if field_name == "raw_artifact_id" and (
                artifact.sha256 != source.sha256 or artifact.size != source.size
            ):
                raise WorkspaceCorruptError(
                    f"source {source.id} raw artifact does not match captured bytes"
                )
            if field_name in ("extracted_artifact_id", "document_artifact_id"):
                expected_producer = f"veriformis.parser.{source.parser_id}"
                expected_config_digest = canonical_digest(
                    {
                        "parser": source.parser_id,
                        "parser_version": source.parser_version,
                        "canonical_stream_contract_version": (
                            source.canonical_stream_contract_version
                        ),
                    }
                )
                if (
                    artifact.producer_id != expected_producer
                    or artifact.producer_version != source.parser_version
                    or artifact.config_digest != expected_config_digest
                ):
                    raise WorkspaceCorruptError(
                        f"source {source.id} {field_name} does not match its parser identity"
                    )


def _validate_stage_output_bindings(
    stages: Mapping[str, StageState],
    sources: Mapping[str, SourceDescriptor],
    artifacts: Mapping[str, ArtifactRef],
) -> None:
    """Validate the stable output names that currently have defined schemas."""
    all_source_ids = tuple(sorted(sources))

    def require_lineage(
        artifact: ArtifactRef,
        *,
        producer_id: str,
        producer_version: str,
        config_digest: str | None,
        output_name: str,
    ) -> None:
        config_matches = (
            config_digest is None or artifact.config_digest == config_digest
        )
        if (
            artifact.producer_id != producer_id
            or artifact.producer_version != producer_version
            or not config_matches
        ):
            raise WorkspaceCorruptError(
                f"artifact lineage for output {output_name!r} does not match "
                f"its declared stage producer"
            )

    for stage_name, state in stages.items():
        required = _required_stage_output_kinds(state.stage, all_source_ids)
        enforce_complete_schema = state.status == "complete" or (
            state.stage == "validate" and state.status == "failed"
        )
        if enforce_complete_schema and required is not None:
            missing = set(required) - set(state.outputs)
            unexpected = set(state.outputs) - set(required)
            if missing or unexpected:
                raise WorkspaceCorruptError(
                    f"{stage_name} output schema mismatch; missing={sorted(missing)}, "
                    f"unexpected={sorted(unexpected)}"
                )
        if state.stage == "parse" and state.status == "complete":
            expected_config = {
                "sources": [
                    source.logical_path
                    for source in sorted(sources.values(), key=lambda item: item.id)
                ]
            }
            if state.config != expected_config:
                raise WorkspaceCorruptError(
                    "parse stage config does not match its source inventory"
                )
        construct_source_ids = (
            _construct_source_scope(state, sources)
            if state.stage == "construct" and state.status == "complete"
            else None
        )
        for output_name, artifact_id in state.outputs.items():
            artifact = artifacts[artifact_id]
            expected_kind = _FIXED_STAGE_OUTPUT_KINDS.get((state.stage, output_name))
            if expected_kind is not None:
                if artifact.kind != expected_kind:
                    raise WorkspaceCorruptError(
                        f"{stage_name} output {output_name!r} has kind {artifact.kind!r}; "
                        f"expected {expected_kind!r}"
                    )
                expected_source_ids = (
                    construct_source_ids
                    if state.stage == "construct"
                    else all_source_ids
                )
                if artifact.source_ids != expected_source_ids:
                    raise WorkspaceCorruptError(
                        f"{stage_name} output {output_name!r} has incorrect source scope"
                    )
                if state.stage == "parse":
                    producer_id = "veriformis.parse-stage"
                    producer_version = "1"
                    expected_config_digest = canonical_digest(
                        {"source_count": len(sources)}
                    )
                elif state.stage == "clean":
                    producer_id = "veriformis.cleaning"
                    producer_version = "1"
                    expected_config_digest = state.config_digest
                elif state.stage == "chunk":
                    strategy = state.config.get("strategy")
                    if not isinstance(strategy, str) or not strategy:
                        raise WorkspaceCorruptError(
                            "chunk stage lacks a valid producer strategy"
                        )
                    producer_id = f"veriformis.chunker.{strategy}"
                    producer_version = "1"
                    expected_config_digest = state.config_digest
                elif state.stage == "construct":
                    producer_id = f"veriformis.construction.{output_name}"
                    producer_version = "1"
                    expected_config_digest = state.config_digest
                elif state.stage == "format":
                    record_format = state.config.get("format")
                    if not isinstance(record_format, str) or not record_format:
                        raise WorkspaceCorruptError(
                            "format stage lacks a valid serializer format"
                        )
                    producer_id = f"veriformis.serializer.{record_format}"
                    producer_version = "1"
                    expected_config_digest = state.config_digest
                elif state.stage == "validate":
                    producer_id = "veriformis.validation"
                    producer_version = "1"
                    expected_config_digest = state.config_digest
                else:  # pragma: no cover - fixed outputs exclude seal
                    raise WorkspaceCorruptError(
                        f"stage {state.stage} has no declared artifact producer"
                    )
                require_lineage(
                    artifact,
                    producer_id=producer_id,
                    producer_version=producer_version,
                    config_digest=expected_config_digest,
                    output_name=output_name,
                )
                continue

            parts = output_name.split("/")
            role_kinds = _SOURCE_STAGE_OUTPUT_KINDS.get(state.stage, {})
            if len(parts) != 3 or parts[0] != "source" or parts[2] not in role_kinds:
                continue
            source_id, role = parts[1], parts[2]
            try:
                source = sources[source_id]
            except KeyError as exc:
                raise WorkspaceCorruptError(
                    f"{stage_name} output {output_name!r} names an unknown source"
                ) from exc
            expected_kind = role_kinds[role]
            if artifact.kind != expected_kind:
                raise WorkspaceCorruptError(
                    f"{stage_name} output {output_name!r} has kind {artifact.kind!r}; "
                    f"expected {expected_kind!r}"
                )
            if artifact.source_ids != (source_id,):
                raise WorkspaceCorruptError(
                    f"{stage_name} output {output_name!r} has incorrect source scope"
                )
            if state.stage == "parse" and role == "raw":
                require_lineage(
                    artifact,
                    producer_id="veriformis.source-capture",
                    producer_version="1",
                    config_digest=canonical_digest(
                        {"logical_path": source.logical_path}
                    ),
                    output_name=output_name,
                )
            elif state.stage == "parse":
                require_lineage(
                    artifact,
                    producer_id=f"veriformis.parser.{source.parser_id}",
                    producer_version=source.parser_version,
                    config_digest=canonical_digest(
                        {
                            "parser": source.parser_id,
                            "parser_version": source.parser_version,
                            "canonical_stream_contract_version": (
                                source.canonical_stream_contract_version
                            ),
                        }
                    ),
                    output_name=output_name,
                )
            elif state.stage == "clean":
                require_lineage(
                    artifact,
                    producer_id="veriformis.cleaning",
                    producer_version="1",
                    # The derivation artifact also binds the cleaning-plan ID.
                    # Its exact digest is checked during deterministic replay.
                    config_digest=(
                        None if role == "block-derivations" else state.config_digest
                    ),
                    output_name=output_name,
                )
            link_field = _PARSE_OUTPUT_LINK_FIELDS.get(role)
            if state.stage == "parse" and link_field is not None:
                if getattr(source, link_field) != artifact_id:
                    raise WorkspaceCorruptError(
                        f"{stage_name} output {output_name!r} does not match its source link"
                    )


class WorkspaceRevision(_PersistedModel):
    # Preserve Group 1's programmatic/model-level default. The persisted loader
    # separately rejects schema-less manifests unless their stage set is exact v1.
    schema_version: int = LEGACY_REVISION_SCHEMA_VERSION
    revision_id: str
    state_digest: str
    parent_revision_id: str | None
    committed_stage: CommitStage
    committed_at: str
    sources: dict[str, SourceDescriptor]
    artifacts: dict[str, ArtifactRef]
    stages: dict[str, StageState]

    @field_validator("revision_id")
    @classmethod
    def _valid_revision_id(cls, value: str) -> str:
        return validate_id(value, kind="rev")

    @field_validator("parent_revision_id")
    @classmethod
    def _valid_parent_id(cls, value: str | None) -> str | None:
        return validate_id(value, kind="rev") if value is not None else None

    @field_validator("state_digest")
    @classmethod
    def _valid_state_digest(cls, value: str) -> str:
        return validate_sha256(value)

    @model_validator(mode="after")
    def _consistent_revision(self) -> WorkspaceRevision:
        revision_stages = _stages_for_revision(self.schema_version)
        dependencies = _dependencies_for_revision(self.schema_version)
        if set(self.stages) != set(revision_stages):
            raise WorkspaceCorruptError("revision does not contain the exact stage set")
        for stage, state in self.stages.items():
            if stage != state.stage:
                raise DuplicateIdentityError(
                    f"stage key {stage!r} does not match {state.stage!r}"
                )
        if self.committed_stage == "migration":
            if (
                self.schema_version != WORKSPACE_REVISION_SCHEMA_VERSION
                or self.parent_revision_id is None
                or self.stages["construct"] != StageState.absent("construct")
            ):
                raise UnsupportedWorkspaceVersionError(
                    "migration revision does not match the v1-to-v2 migration contract"
                )
        elif self.committed_stage == "init":
            if (
                self.parent_revision_id is not None
                or self.sources
                or self.artifacts
                or any(state.status != "absent" for state in self.stages.values())
            ):
                raise WorkspaceCorruptError(
                    "init revision must be an empty root with all stages absent"
                )
        else:
            if self.committed_stage not in revision_stages:
                raise WorkspaceCorruptError(
                    f"revision schema {self.schema_version} does not define "
                    f"stage {self.committed_stage}"
                )
            if self.parent_revision_id is None:
                raise WorkspaceCorruptError(
                    f"{self.committed_stage} revision lacks a parent revision"
                )
            committed = self.stages[self.committed_stage]
            allowed_statuses = (
                {"complete", "failed"}
                if self.committed_stage == "validate"
                else {"complete"}
            )
            if committed.status not in allowed_statuses:
                raise WorkspaceCorruptError(
                    f"committed stage {self.committed_stage} has invalid status "
                    f"{committed.status}"
                )
            for state in self.stages.values():
                if state.status != "stale":
                    continue
                if (
                    state.stage
                    not in _descendants_for_revision(
                        self.schema_version, self.committed_stage
                    )
                    or state.invalidated_by != self.committed_stage
                    or state.prior_revision_id != self.parent_revision_id
                ):
                    raise WorkspaceCorruptError(
                        f"stale stage {state.stage} does not carry the "
                        f"{self.committed_stage} commit lineage"
                    )
        for stage, state in self.stages.items():
            if state.status in ("complete", "failed"):
                expected_inputs: set[str] = set()
                for dependency in dependencies[state.stage]:
                    if self.stages[dependency].status != "complete":
                        raise WorkspaceCorruptError(
                            f"active stage {stage} requires complete dependency "
                            f"{dependency}"
                        )
                    expected_inputs.update(self.stages[dependency].outputs.values())
                if set(state.input_artifact_ids) != expected_inputs:
                    raise WorkspaceCorruptError(
                        f"active stage {stage} input lineage does not exactly match "
                        "its declared dependencies"
                    )
            if state.status == "absent":
                present_descendants = [
                    descendant
                    for descendant in _descendants_for_revision(
                        self.schema_version, state.stage
                    )
                    if self.stages[descendant].status != "absent"
                ]
                if present_descendants:
                    raise WorkspaceCorruptError(
                        f"absent stage {stage} has non-absent descendants: "
                        f"{present_descendants}"
                    )
        if any(key != source.id for key, source in self.sources.items()):
            raise DuplicateIdentityError(
                "source map key does not match source identity"
            )
        if any(key != artifact.id for key, artifact in self.artifacts.items()):
            raise DuplicateIdentityError(
                "artifact map key does not match artifact identity"
            )
        logical_paths = [source.logical_path for source in self.sources.values()]
        if len(logical_paths) != len(set(logical_paths)):
            raise DuplicateIdentityError(
                "revision contains duplicate logical source paths"
            )
        for artifact in self.artifacts.values():
            missing_sources = set(artifact.source_ids) - set(self.sources)
            if missing_sources:
                raise WorkspaceCorruptError(
                    f"artifact {artifact.id} refers to missing sources: {sorted(missing_sources)}"
                )
        _validate_source_artifact_bindings(self.sources, self.artifacts)
        for state in self.stages.values():
            referenced = set(state.input_artifact_ids) | set(state.outputs.values())
            missing = referenced - set(self.artifacts)
            if missing:
                raise WorkspaceCorruptError(
                    f"stage {state.stage} refers to missing artifacts: {sorted(missing)}"
                )
        _validate_stage_output_bindings(self.stages, self.sources, self.artifacts)
        referenced_artifacts: set[str] = set()
        for source in self.sources.values():
            referenced_artifacts.update(
                artifact_id
                for artifact_id in (
                    source.raw_artifact_id,
                    source.extracted_artifact_id,
                    source.document_artifact_id,
                )
                if artifact_id is not None
            )
        for state in self.stages.values():
            referenced_artifacts.update(state.input_artifact_ids)
            referenced_artifacts.update(state.outputs.values())
        if set(self.artifacts) != referenced_artifacts:
            raise WorkspaceCorruptError(
                "revision artifact registry is not the exact referenced set"
            )
        semantic = _semantic_payload(
            schema_version=self.schema_version,
            sources=self.sources,
            artifacts=self.artifacts,
            stages=self.stages,
        )
        if canonical_digest(semantic) != self.state_digest:
            raise WorkspaceCorruptError("revision semantic state digest does not match")
        expected_revision_id = _derive_revision_id(
            schema_version=self.schema_version,
            state_digest=self.state_digest,
            parent_revision_id=self.parent_revision_id,
            committed_stage=self.committed_stage,
            committed_at=self.committed_at,
            sources=self.sources,
            artifacts=self.artifacts,
            stages=self.stages,
        )
        if self.revision_id != expected_revision_id:
            raise WorkspaceCorruptError("revision identity does not match its manifest")
        return self


def _validate_revision_transition(
    child: WorkspaceRevision,
    parent: WorkspaceRevision,
) -> None:
    """Prove that one immutable revision is a legal transition from its parent."""
    if child.parent_revision_id != parent.revision_id:
        raise WorkspaceCorruptError("workspace revision parent link is inconsistent")
    stage = child.committed_stage
    if stage == "migration":
        expected_construct = StageState.absent("construct")
        if (
            parent.schema_version != LEGACY_REVISION_SCHEMA_VERSION
            or child.schema_version != WORKSPACE_REVISION_SCHEMA_VERSION
            or child.sources != parent.sources
            or child.artifacts != parent.artifacts
            or child.stages.get("construct") != expected_construct
            or any(
                child.stages.get(stage_name) != parent.stages.get(stage_name)
                for stage_name in LEGACY_STAGES
            )
        ):
            raise UnsupportedWorkspaceVersionError(
                "migration revision does not match the v1-to-v2 migration contract"
            )
        return
    if stage == "init":
        raise WorkspaceCorruptError(
            f"workspace history contains an invalid {stage} child revision"
        )
    if child.schema_version != parent.schema_version:
        raise UnsupportedWorkspaceVersionError(
            "workspace revision schema changes require the v1-to-v2 migration contract"
        )
    if stage != "parse" and child.sources != parent.sources:
        raise WorkspaceCorruptError(
            f"{stage} revision rewrites inherited source capture facts"
        )
    if (
        child.sources == parent.sources
        and child.artifacts == parent.artifacts
        and child.stages == parent.stages
    ):
        raise WorkspaceCorruptError(
            "workspace history contains a fabricated no-op child revision"
        )

    revision_stages = _stages_for_revision(child.schema_version)
    if stage not in revision_stages:
        raise WorkspaceCorruptError(
            f"revision schema {child.schema_version} does not define stage {stage}"
        )
    descendants = set(_descendants_for_revision(child.schema_version, stage))
    for stage_name in revision_stages:
        current = child.stages[stage_name]
        previous = parent.stages[stage_name]
        if stage_name == stage:
            continue
        if stage_name not in descendants:
            if current != previous:
                raise WorkspaceCorruptError(
                    f"{stage} revision rewrites unaffected stage {stage_name}"
                )
            continue
        expected = (
            previous
            if previous.status == "absent"
            else previous.as_stale(
                invalidated_by=stage,
                prior_revision_id=parent.revision_id,
            )
        )
        if current != expected:
            raise WorkspaceCorruptError(
                f"{stage} revision has an invalid {stage_name} transition"
            )


def _derive_revision_id(
    *,
    schema_version: int,
    state_digest: str,
    parent_revision_id: str | None,
    committed_stage: CommitStage,
    committed_at: str,
    sources: Mapping[str, SourceDescriptor],
    artifacts: Mapping[str, ArtifactRef],
    stages: Mapping[str, StageState],
) -> str:
    return derive_id(
        "rev",
        {
            "schema_version": schema_version,
            "state_digest": state_digest,
            "parent_revision_id": parent_revision_id,
            "committed_stage": committed_stage,
            "committed_at": committed_at,
            "sources": {
                source_id: source.model_dump(mode="json")
                for source_id, source in sorted(sources.items())
            },
            "artifacts": {
                artifact_id: artifact.model_dump(mode="json")
                for artifact_id, artifact in sorted(artifacts.items())
            },
            "stages": {
                stage: state.model_dump(mode="json")
                for stage, state in sorted(stages.items())
            },
        },
    )


def _new_revision(
    *,
    schema_version: int,
    parent_revision_id: str | None,
    committed_stage: CommitStage,
    committed_at: str,
    sources: Mapping[str, SourceDescriptor],
    artifacts: Mapping[str, ArtifactRef],
    stages: Mapping[str, StageState],
) -> WorkspaceRevision:
    source_copy = dict(sources)
    artifact_copy = dict(artifacts)
    stage_copy = dict(stages)
    state_digest = canonical_digest(
        _semantic_payload(
            schema_version=schema_version,
            sources=source_copy,
            artifacts=artifact_copy,
            stages=stage_copy,
        )
    )
    revision_id = _derive_revision_id(
        schema_version=schema_version,
        state_digest=state_digest,
        parent_revision_id=parent_revision_id,
        committed_stage=committed_stage,
        committed_at=committed_at,
        sources=source_copy,
        artifacts=artifact_copy,
        stages=stage_copy,
    )
    return WorkspaceRevision(
        schema_version=schema_version,
        revision_id=revision_id,
        state_digest=state_digest,
        parent_revision_id=parent_revision_id,
        committed_stage=committed_stage,
        committed_at=committed_at,
        sources=source_copy,
        artifacts=artifact_copy,
        stages=stage_copy,
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateIdentityError(
                f"persisted JSON contains duplicate key {key!r}"
            )
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def _strict_json(data: str) -> Any:
    return json.loads(
        data,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_json_constant,
    )


def _revision_json_with_dispatched_schema(data: str) -> str:
    """Version-dispatch a persisted revision before strict JSON-mode validation."""
    payload = _strict_json(data)
    if not isinstance(payload, dict) or "schema_version" in payload:
        return data
    stages = payload.get("stages")
    if isinstance(stages, Mapping) and set(stages) == set(LEGACY_STAGES):
        payload["schema_version"] = LEGACY_REVISION_SCHEMA_VERSION
        return lossless_json_bytes(payload).decode("utf-8")
    raise UnsupportedWorkspaceVersionError(
        "schema-less workspace revisions are supported only for the exact "
        "legacy stage set"
    )


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_fsync(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write(path: Path, data: bytes) -> None:
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        _write_fsync(temp, data)
        os.replace(temp, path)
        _fsync_dir(path.parent)
    finally:
        temp.unlink(missing_ok=True)


def _promote_commit_pointer(path: Path, data: bytes) -> bool:
    """Replace a commit pointer without reporting failure after visibility.

    The rename is the commit point. A directory-fsync error after that point
    cannot truthfully be reported as a failed transaction because readers can
    already observe the new HEAD. The file itself is fully written and synced
    before replacement; a later open still validates the complete revision.
    """
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    promoted = False
    durability_confirmed = True
    try:
        _write_fsync(temp, data)
        os.replace(temp, path)
        promoted = True
        try:
            _fsync_dir(path.parent)
        except OSError:
            # Visibility has changed. Return the committed outcome instead of
            # raising a false rollback signal to the caller.
            durability_confirmed = False
    finally:
        if not promoted:
            temp.unlink(missing_ok=True)
    return durability_confirmed


def _install_revision_directory(
    root: Path,
    temp_dir: Path,
    revision: WorkspaceRevision,
) -> None:
    """Install one immutable revision manifest before HEAD is promoted."""
    staged_dir = temp_dir / "revision"
    staged_dir.mkdir()
    manifest = lossless_json_bytes(revision)
    _write_fsync(staged_dir / "revision.json", manifest)
    _fsync_dir(staged_dir)
    target = root / "revisions" / revision.revision_id
    if target.exists():
        existing = target / "revision.json"
        if not existing.exists() or existing.read_bytes() != manifest:
            raise WorkspaceCorruptError(
                f"revision identity collision: {revision.revision_id}"
            )
        shutil.rmtree(staged_dir)
    else:
        os.replace(staged_dir, target)
        _fsync_dir(target.parent)


class Workspace:
    """A versioned workspace whose only mutable commit pointer is ``HEAD``."""

    def __init__(
        self,
        root: Path,
        metadata: WorkspaceMetadata,
        *,
        lock_timeout: float = 10.0,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.root = root
        self.metadata = metadata
        self.lock_timeout = lock_timeout
        self._failure_injector = failure_injector
        self.last_commit_durability_warning: str | None = None

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        lock_timeout: float = 10.0,
        failure_injector: Callable[[str], None] | None = None,
    ) -> Workspace:
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        if (root / "workspace.json").exists() or (root / "HEAD").exists():
            return cls.open(
                root,
                lock_timeout=lock_timeout,
                failure_injector=failure_injector,
            )
        existing = [item.name for item in root.iterdir()]
        if existing:
            if "registry.json" in existing:
                raise UnsupportedWorkspaceVersionError(
                    "legacy flat workspace requires explicit migration"
                )
            raise WorkspaceCorruptError(
                f"cannot create a workspace in a non-empty directory: {root}"
            )
        for directory in (
            root / "objects" / "sha256",
            root / "revisions",
            root / ".txn",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        (root / "LOCK").touch(exist_ok=True)
        now = datetime.now(UTC).isoformat()
        metadata = WorkspaceMetadata(
            workspace_id=derive_id("ws", {"nonce": uuid.uuid4().hex}),
            created_at=now,
        )
        _atomic_write(root / "workspace.json", lossless_json_bytes(metadata))
        stages = {stage: StageState.absent(stage) for stage in STAGES}
        initial = _new_revision(
            schema_version=WORKSPACE_REVISION_SCHEMA_VERSION,
            parent_revision_id=None,
            committed_stage="init",
            committed_at="1970-01-01T00:00:00+00:00",
            sources={},
            artifacts={},
            stages=stages,
        )
        revision_dir = root / "revisions" / initial.revision_id
        revision_dir.mkdir()
        _write_fsync(revision_dir / "revision.json", lossless_json_bytes(initial))
        _fsync_dir(revision_dir)
        _fsync_dir(revision_dir.parent)
        _atomic_write(root / "HEAD", (initial.revision_id + "\n").encode("ascii"))
        return cls(
            root,
            metadata,
            lock_timeout=lock_timeout,
            failure_injector=failure_injector,
        )

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        lock_timeout: float = 10.0,
        failure_injector: Callable[[str], None] | None = None,
    ) -> Workspace:
        root = Path(path)
        if not root.exists():
            raise WorkspaceNotFoundError(f"workspace does not exist: {root}")
        metadata_path = root / "workspace.json"
        if not metadata_path.exists():
            if (root / "registry.json").exists():
                raise UnsupportedWorkspaceVersionError(
                    "legacy flat workspace requires explicit migration"
                )
            raise WorkspaceNotFoundError(f"workspace metadata is missing: {root}")
        try:
            metadata_text = metadata_path.read_text(encoding="utf-8")
            _strict_json(metadata_text)
            metadata = WorkspaceMetadata.model_validate_json(metadata_text)
        except (
            OSError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise WorkspaceCorruptError(f"invalid workspace metadata: {root}") from exc
        if metadata.schema_version != WORKSPACE_LAYOUT_SCHEMA_VERSION:
            raise UnsupportedWorkspaceVersionError(
                f"workspace layout schema {metadata.schema_version} is not supported"
            )
        workspace = cls(
            root,
            metadata,
            lock_timeout=lock_timeout,
            failure_injector=failure_injector,
        )
        # Opening is an integrity boundary: validate the complete parent chain
        # and every content-addressed object before returning a handle.
        workspace.verify_history()
        return workspace

    @property
    def head_id(self) -> str:
        head_path = self.root / "HEAD"
        try:
            value = head_path.read_text(encoding="ascii").strip()
            return validate_id(value, kind="rev")
        except (OSError, UnicodeError, ValueError) as exc:
            raise WorkspaceCorruptError("workspace HEAD is missing or invalid") from exc

    def head(
        self,
        *,
        verify_objects: bool = True,
        verify_history: bool = True,
    ) -> WorkspaceRevision:
        if verify_history:
            revision_ids = self.verify_history(verify_objects=verify_objects)
            return self.get_revision(revision_ids[0], verify_objects=False)
        return self.get_revision(self.head_id, verify_objects=verify_objects)

    def verify_history(self, *, verify_objects: bool = True) -> tuple[str, ...]:
        """Verify the complete HEAD-to-root audit chain.

        Every referenced parent manifest must exist and validate. By default,
        every historical revision's content-addressed objects are verified too,
        so immutable history cannot silently degrade behind a valid active HEAD.
        The returned IDs are ordered from HEAD through the root revision.
        """
        current = self.get_revision(self.head_id, verify_objects=verify_objects)
        revision_ids: list[str] = []
        seen: set[str] = set()
        while True:
            if current.revision_id in seen:
                raise WorkspaceCorruptError("workspace revision history contains a cycle")
            seen.add(current.revision_id)
            revision_ids.append(current.revision_id)
            parent_id = current.parent_revision_id
            if parent_id is None:
                if current.committed_stage != "init":
                    raise WorkspaceCorruptError(
                        "workspace revision history lacks an init root"
                    )
                return tuple(revision_ids)
            parent = self.get_revision(parent_id, verify_objects=verify_objects)
            _validate_revision_transition(current, parent)
            current = parent

    def get_revision(
        self, revision_id: str, *, verify_objects: bool = True
    ) -> WorkspaceRevision:
        validate_id(revision_id, kind="rev")
        path = self.root / "revisions" / revision_id / "revision.json"
        try:
            revision_text = path.read_text(encoding="utf-8")
            dispatched_text = _revision_json_with_dispatched_schema(revision_text)
            revision = WorkspaceRevision.model_validate_json(dispatched_text)
        except DuplicateIdentityError:
            raise
        except UnsupportedWorkspaceVersionError:
            raise
        except (
            OSError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise WorkspaceCorruptError(
                f"invalid workspace revision: {revision_id}"
            ) from exc
        if revision.revision_id != revision_id:
            raise WorkspaceCorruptError(
                "revision directory does not match manifest identity"
            )
        if verify_objects:
            self._verify_objects(revision)
        return revision

    def begin(
        self,
        stage: StageName,
        expected_revision_id: str | None = None,
    ) -> WorkspaceTransaction:
        if stage not in STAGES:
            raise ValueError(f"unknown workspace stage: {stage!r}")
        # A transaction is also the read boundary for commands such as seal,
        # which may intentionally produce an external artifact without a new
        # workspace revision. Verify the complete active snapshot once here.
        base = self.head()
        expected = expected_revision_id or base.revision_id
        validate_id(expected, kind="rev")
        if expected != base.revision_id:
            raise WorkspaceRevisionConflict(expected, base.revision_id)
        revision_stages = _stages_for_revision(base.schema_version)
        if stage not in revision_stages:
            if (
                stage == "construct"
                and base.schema_version == LEGACY_REVISION_SCHEMA_VERSION
            ):
                raise UnsupportedWorkspaceVersionError(
                    "construct requires workspace revision schema 2; "
                    "call migrate_to_current() first"
                )
            raise UnsupportedWorkspaceVersionError(
                f"workspace revision schema {base.schema_version} does not define "
                f"stage {stage}"
            )
        self._required_artifacts(base, stage)
        return WorkspaceTransaction(self, stage, base)

    def migrate_to_current(
        self,
        expected_revision_id: str | None = None,
    ) -> WorkspaceRevision:
        """Append the exact v1-to-v2 revision migration and atomically promote HEAD."""
        base = self.head()
        expected = expected_revision_id or base.revision_id
        validate_id(expected, kind="rev")
        if expected != base.revision_id:
            raise WorkspaceRevisionConflict(expected, base.revision_id)

        with self._exclusive_lock():
            actual = self.head(verify_objects=False)
            if actual.revision_id != expected:
                raise WorkspaceRevisionConflict(expected, actual.revision_id)
            if actual.schema_version == WORKSPACE_REVISION_SCHEMA_VERSION:
                self.last_commit_durability_warning = None
                return actual
            if actual.schema_version != LEGACY_REVISION_SCHEMA_VERSION:
                raise UnsupportedWorkspaceVersionError(
                    f"workspace revision schema {actual.schema_version} cannot be "
                    "migrated to the current schema"
                )

            stages = dict(actual.stages)
            stages["construct"] = StageState.absent("construct")
            candidate = _new_revision(
                schema_version=WORKSPACE_REVISION_SCHEMA_VERSION,
                parent_revision_id=actual.revision_id,
                committed_stage="migration",
                committed_at=datetime.now(UTC).isoformat(),
                sources=actual.sources,
                artifacts=actual.artifacts,
                stages=stages,
            )
            _validate_revision_transition(candidate, actual)

            temp_dir = Path(
                tempfile.mkdtemp(prefix="migration-", dir=self.root / ".txn")
            )
            try:
                self._inject_failure("before-revision")
                _install_revision_directory(self.root, temp_dir, candidate)
                self._inject_failure("after-revision")
                self._inject_failure("before-head")
                durability_confirmed = _promote_commit_pointer(
                    self.root / "HEAD",
                    (candidate.revision_id + "\n").encode("ascii"),
                )
                self.last_commit_durability_warning = (
                    None
                    if durability_confirmed
                    else (
                        "HEAD was committed, but the workspace directory sync failed; "
                        "crash durability could not be confirmed"
                    )
                )
                # HEAD is the commit point. Do no fallible work after promotion.
                return candidate
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def read_artifact(
        self,
        artifact_id: str,
        *,
        revision: WorkspaceRevision | None = None,
    ) -> bytes:
        current = revision or self.head()
        try:
            artifact = current.artifacts[artifact_id]
        except KeyError as exc:
            raise WorkspaceCorruptError(
                f"artifact is not part of revision: {artifact_id}"
            ) from exc
        path = self._object_path(artifact.sha256)
        data = path.read_bytes()
        if len(data) != artifact.size or sha256_digest(data) != artifact.sha256:
            raise ArtifactDigestMismatchError(
                f"artifact bytes do not match {artifact.id}"
            )
        return data

    def _object_path(self, digest: str) -> Path:
        validate_sha256(digest)
        return self.root / "objects" / "sha256" / digest[:2] / digest

    def _verify_objects(self, revision: WorkspaceRevision) -> None:
        for artifact in revision.artifacts.values():
            path = self._object_path(artifact.sha256)
            try:
                stat = path.stat()
            except OSError as exc:
                raise ArtifactDigestMismatchError(
                    f"artifact object is missing: {artifact.id}"
                ) from exc
            if (
                stat.st_size != artifact.size
                or sha256_digest(path.read_bytes()) != artifact.sha256
            ):
                raise ArtifactDigestMismatchError(
                    f"artifact bytes do not match {artifact.id}"
                )

    def _required_artifacts(
        self, revision: WorkspaceRevision, stage: StageName
    ) -> tuple[str, ...]:
        artifact_ids: set[str] = set()
        dependencies = _dependencies_for_revision(revision.schema_version)
        if stage not in dependencies:
            raise UnsupportedWorkspaceVersionError(
                f"workspace revision schema {revision.schema_version} does not define "
                f"stage {stage}"
            )
        for dependency in dependencies[stage]:
            state = revision.stages[dependency]
            if state.status == "stale":
                raise StaleStageError(
                    f"stage {stage} requires stale stage {dependency} to be rerun"
                )
            if state.status != "complete":
                raise MissingStageInputError(
                    f"stage {stage} requires completed stage {dependency}"
                )
            artifact_ids.update(state.outputs.values())
        return tuple(sorted(artifact_ids))

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        lock_path = self.root / "LOCK"
        handle = lock_path.open("a+b")
        deadline = time.monotonic() + max(0.0, self.lock_timeout)
        try:
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise WorkspaceLockedError(
                            f"workspace commit lock timed out: {self.root}"
                        ) from exc
                    time.sleep(0.01)
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def _inject_failure(self, point: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(point)


class WorkspaceTransaction:
    """Optimistic stage transaction against one expected workspace revision."""

    def __init__(
        self, workspace: Workspace, stage: StageName, base: WorkspaceRevision
    ) -> None:
        self.workspace = workspace
        self.stage = stage
        self.base = base
        self._base_manifest = lossless_json_bytes(base)
        self.expected_revision_id = base.revision_id
        self.sources: dict[str, SourceDescriptor] = dict(base.sources)
        self.artifacts: dict[str, ArtifactRef] = dict(base.artifacts)
        self._temp_dir = Path(
            tempfile.mkdtemp(prefix=f"{stage}-", dir=workspace.root / ".txn")
        )
        self._staged_objects = self._temp_dir / "objects"
        self._staged_objects.mkdir()
        self._closed = False

    def __enter__(self) -> WorkspaceTransaction:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if not self._closed:
            self.abort()

    def set_sources(self, sources: Iterable[SourceDescriptor]) -> None:
        self._ensure_open()
        if self.stage != "parse":
            raise WorkspaceCorruptError(
                "only the parse stage may replace source membership"
            )
        by_id: dict[str, SourceDescriptor] = {}
        paths: set[str] = set()
        for source in sources:
            if source.id in by_id or source.logical_path in paths:
                raise DuplicateIdentityError(
                    f"duplicate source identity or logical path: {source.logical_path}"
                )
            by_id[source.id] = source
            paths.add(source.logical_path)
        self.sources = by_id

    def add_source(self, source: SourceDescriptor) -> None:
        self._ensure_open()
        if self.stage != "parse":
            raise WorkspaceCorruptError("only the parse stage may add sources")
        current = self.sources.get(source.id)
        if current is not None and current != source:
            raise DuplicateIdentityError(f"duplicate source identity: {source.id}")
        for other in self.sources.values():
            if other.logical_path == source.logical_path and other.id != source.id:
                raise DuplicateIdentityError(
                    f"duplicate logical source path: {source.logical_path}"
                )
        self.sources[source.id] = source

    def put_artifact(
        self,
        data: bytes | str,
        *,
        kind: str,
        media_type: str,
        source_ids: Iterable[str] = (),
        producer_id: str,
        producer_version: str,
        config: Mapping[str, Any] | None = None,
    ) -> ArtifactRef:
        self._ensure_open()
        payload = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        artifact = ArtifactRef.from_bytes(
            payload,
            kind=kind,
            media_type=media_type,
            source_ids=tuple(source_ids),
            producer_id=producer_id,
            producer_version=producer_version,
            config=config,
        )
        current = self.artifacts.get(artifact.id)
        if current is not None and current != artifact:
            raise DuplicateIdentityError(f"duplicate artifact identity: {artifact.id}")
        self.artifacts[artifact.id] = artifact
        staged_path = self._staged_objects / artifact.sha256
        if staged_path.exists():
            if sha256_digest(staged_path.read_bytes()) != artifact.sha256:
                raise ArtifactDigestMismatchError(
                    f"staged object digest mismatch: {artifact.id}"
                )
        else:
            _write_fsync(staged_path, payload)
        return artifact

    def commit(
        self,
        *,
        outputs: Mapping[str, ArtifactRef | str],
        input_artifact_ids: Iterable[str] | None = None,
        config: Mapping[str, Any] | None = None,
        status: Literal["complete", "failed"] = "complete",
    ) -> WorkspaceRevision:
        self._ensure_open()
        try:
            return self._commit(
                outputs=outputs,
                input_artifact_ids=input_artifact_ids,
                config=config,
                status=status,
            )
        finally:
            self._closed = True
            shutil.rmtree(self._temp_dir, ignore_errors=True)

    def abort(self) -> None:
        if not self._closed:
            self._closed = True
            shutil.rmtree(self._temp_dir, ignore_errors=True)

    def _commit(
        self,
        *,
        outputs: Mapping[str, ArtifactRef | str],
        input_artifact_ids: Iterable[str] | None,
        config: Mapping[str, Any] | None,
        status: Literal["complete", "failed"],
    ) -> WorkspaceRevision:
        output_ids: dict[str, str] = {}
        for name, value in outputs.items():
            if not name:
                raise ValueError("stage output names cannot be empty")
            artifact_id = value.id if isinstance(value, ArtifactRef) else value
            validate_id(artifact_id, kind="art")
            if artifact_id not in self.artifacts:
                raise WorkspaceCorruptError(
                    f"stage {self.stage} output is not registered: {artifact_id}"
                )
            output_ids[name] = artifact_id
        normalized_config = _strict_json(
            lossless_json_bytes(dict(config or {})).decode("utf-8")
        )
        config_digest = canonical_digest(normalized_config)
        requested_inputs = (
            None if input_artifact_ids is None else tuple(input_artifact_ids)
        )

        with self.workspace._exclusive_lock():
            actual = self.workspace.head(verify_objects=False)
            if actual.revision_id != self.expected_revision_id:
                raise WorkspaceRevisionConflict(
                    self.expected_revision_id, actual.revision_id
                )
            try:
                base_is_unchanged = (
                    lossless_json_bytes(actual) == self._base_manifest
                    and lossless_json_bytes(self.base) == self._base_manifest
                )
            except (TypeError, ValueError) as exc:
                raise WorkspaceCorruptError(
                    "transaction base contains an invalid in-memory mutation"
                ) from exc
            if not base_is_unchanged:
                raise WorkspaceCorruptError(
                    "transaction base does not exactly match the persisted HEAD revision"
                )

            required = set(self.workspace._required_artifacts(actual, self.stage))
            supplied_inputs = (
                required if requested_inputs is None else set(requested_inputs)
            )
            if requested_inputs is not None and len(requested_inputs) != len(
                supplied_inputs
            ):
                raise DuplicateIdentityError(
                    f"stage {self.stage} input artifacts contain duplicates"
                )
            missing_required = required - supplied_inputs
            if missing_required:
                raise MissingStageInputError(
                    f"stage {self.stage} omitted required artifacts: "
                    f"{sorted(missing_required)}"
                )
            unexpected_inputs = supplied_inputs - required
            if unexpected_inputs:
                raise MissingStageInputError(
                    f"stage {self.stage} included undeclared artifacts: "
                    f"{sorted(unexpected_inputs)}"
                )
            missing_inputs = supplied_inputs - set(self.artifacts)
            if missing_inputs:
                raise MissingStageInputError(
                    f"stage {self.stage} references unknown artifacts: "
                    f"{sorted(missing_inputs)}"
                )
            normalized_inputs = tuple(sorted(supplied_inputs))
            stage_state = StageState(
                stage=self.stage,
                status=status,
                input_artifact_ids=normalized_inputs,
                input_digest=canonical_digest(
                    {
                        "stage": self.stage,
                        "inputs": normalized_inputs,
                        "config_digest": config_digest,
                    }
                ),
                config=normalized_config,
                config_digest=config_digest,
                outputs=output_ids,
            )
            if self.stage != "parse" and self.sources != actual.sources:
                raise WorkspaceCorruptError(
                    "only the parse stage may change source membership"
                )

            states = dict(actual.stages)
            exact_noop = (
                self.sources == actual.sources
                and self.artifacts == actual.artifacts
                and stage_state == actual.stages[self.stage]
            )
            states[self.stage] = stage_state
            if not exact_noop:
                for descendant in _descendants_for_revision(
                    actual.schema_version, self.stage
                ):
                    previous = states[descendant]
                    if previous.status != "absent":
                        states[descendant] = previous.as_stale(
                            invalidated_by=self.stage,
                            prior_revision_id=actual.revision_id,
                        )

            active_artifact_ids: set[str] = set()
            for source in self.sources.values():
                active_artifact_ids.update(
                    artifact_id
                    for artifact_id in (
                        source.raw_artifact_id,
                        source.extracted_artifact_id,
                        source.document_artifact_id,
                    )
                    if artifact_id is not None
                )
            for state in states.values():
                active_artifact_ids.update(state.input_artifact_ids)
                active_artifact_ids.update(state.outputs.values())
            artifacts = {
                artifact_id: artifact
                for artifact_id, artifact in self.artifacts.items()
                if artifact_id in active_artifact_ids
            }
            if active_artifact_ids - set(artifacts):
                raise WorkspaceCorruptError(
                    "revision references artifacts not present in transaction"
                )

            if exact_noop:
                candidate = actual
            else:
                candidate = _new_revision(
                    schema_version=actual.schema_version,
                    parent_revision_id=actual.revision_id,
                    committed_stage=self.stage,
                    committed_at=datetime.now(UTC).isoformat(),
                    sources=self.sources,
                    artifacts=artifacts,
                    stages=states,
                )
            if exact_noop:
                self.workspace._verify_objects(actual)
                self.workspace.last_commit_durability_warning = None
                return actual
            self._validate_stage_semantics(candidate)
            self.workspace._inject_failure("before-objects")
            self._install_objects(candidate)
            self.workspace._inject_failure("after-objects")
            self.workspace._inject_failure("before-revision")
            self._install_revision(candidate)
            self.workspace._inject_failure("after-revision")
            self.workspace._inject_failure("before-head")
            durability_confirmed = _promote_commit_pointer(
                self.workspace.root / "HEAD",
                (candidate.revision_id + "\n").encode("ascii"),
            )
            self.workspace.last_commit_durability_warning = (
                None
                if durability_confirmed
                else (
                    "HEAD was committed, but the workspace directory sync failed; "
                    "crash durability could not be confirmed"
                )
            )
            # Replacing HEAD is the transaction's commit point.  No injectable
            # or fallible work may run after it, or callers could observe an
            # exception even though the candidate is already current.
            return candidate

    def _candidate_artifact_bytes(
        self,
        revision: WorkspaceRevision,
        artifact_id: str,
    ) -> bytes:
        artifact = revision.artifacts[artifact_id]
        staged = self._staged_objects / artifact.sha256
        path = (
            staged if staged.exists() else self.workspace._object_path(artifact.sha256)
        )
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise WorkspaceCorruptError(
                f"candidate artifact bytes are missing: {artifact.id}"
            ) from exc
        if len(data) != artifact.size or sha256_digest(data) != artifact.sha256:
            raise ArtifactDigestMismatchError(
                f"candidate artifact bytes do not match {artifact.id}"
            )
        return data

    def _validate_stage_semantics(self, revision: WorkspaceRevision) -> None:
        """Validate cross-artifact meaning before the atomic commit point."""
        if self.stage not in {"parse", "clean", "chunk", "construct"}:
            return

        def load_json(artifact_id: str) -> Any:
            data = self._candidate_artifact_bytes(revision, artifact_id)
            try:
                return json.loads(
                    data.decode("utf-8"),
                    object_pairs_hook=_strict_object,
                    parse_constant=_reject_json_constant,
                )
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                raise WorkspaceCorruptError(
                    "candidate stage artifact is not valid UTF-8 JSON"
                ) from exc

        if self.stage == "construct":
            from veriformis.chunkers.base import chunk_from_dict
            from veriformis.construction import (
                ConstructionInputs,
                IRArtifactInput,
                construction_result_from_dict,
                construction_result_to_dict,
                dataset_recipe_from_dict,
                dataset_recipe_to_dict,
                validate_construction_result,
            )
            from veriformis.rules.engine import transform_record_from_dict
            from veriformis.sources import SourceRef

            try:
                construct_state = revision.stages["construct"]
                selected_source_ids = _construct_source_scope(
                    construct_state,
                    revision.sources,
                )
                recipe_bytes = self._candidate_artifact_bytes(
                    revision,
                    construct_state.outputs["recipe"],
                )
                result_bytes = self._candidate_artifact_bytes(
                    revision,
                    construct_state.outputs["result"],
                )
                raw_recipe = load_json(construct_state.outputs["recipe"])
                raw_result = load_json(construct_state.outputs["result"])
                if not isinstance(raw_recipe, dict) or not isinstance(raw_result, dict):
                    raise WorkspaceCorruptError(
                        "construct artifacts must contain JSON objects"
                    )
                recipe = dataset_recipe_from_dict(raw_recipe)
                result = construction_result_from_dict(raw_result)
                if recipe_bytes != lossless_json_bytes(
                    dataset_recipe_to_dict(recipe)
                ):
                    raise WorkspaceCorruptError(
                        "dataset recipe artifact is not canonical JSON"
                    )
                if result_bytes != lossless_json_bytes(
                    construction_result_to_dict(result)
                ):
                    raise WorkspaceCorruptError(
                        "construction result artifact is not canonical JSON"
                    )
                if (
                    recipe.recipe_id != construct_state.config["recipe_id"]
                    or recipe.source_ids != selected_source_ids
                    or result.recipe_id != recipe.recipe_id
                ):
                    raise WorkspaceCorruptError(
                        "construct config, recipe, and result identities disagree"
                    )

                clean_state = revision.stages["clean"]
                chunk_state = revision.stages["chunk"]
                if recipe.cleaning_config_digest != clean_state.config_digest:
                    raise WorkspaceCorruptError(
                        "dataset recipe does not bind the active clean config"
                    )
                chunk_config = chunk_state.config
                if set(chunk_config) != {"strategy", "size", "overlap"} or (
                    recipe.segmentation.strategy != chunk_config["strategy"]
                    or recipe.segmentation.size != chunk_config["size"]
                    or recipe.segmentation.overlap != chunk_config["overlap"]
                ):
                    raise WorkspaceCorruptError(
                        "dataset recipe does not bind the active segmentation"
                    )

                sources: list[SourceRef] = []
                for source_id in selected_source_ids:
                    descriptor = revision.sources[source_id]
                    artifact_id = descriptor.extracted_artifact_id
                    if artifact_id is None:
                        raise WorkspaceCorruptError(
                            f"source {source_id} has no canonical text artifact"
                        )
                    extracted = self._candidate_artifact_bytes(
                        revision,
                        artifact_id,
                    ).decode("utf-8")
                    sources.append(
                        SourceRef(
                            id=descriptor.id,
                            path=(
                                descriptor.original_path
                                or descriptor.logical_path
                            ),
                            sha256=descriptor.sha256,
                            size=descriptor.size,
                            parser=descriptor.parser_id,
                            extracted_text=extracted,
                            logical_path=descriptor.logical_path,
                            parser_version=descriptor.parser_version,
                            canonical_stream_contract_version=(
                                descriptor.canonical_stream_contract_version
                            ),
                            stream_sha256=sha256_digest(extracted),
                            artifact_id=artifact_id,
                        )
                    )

                raw_chunks = load_json(chunk_state.outputs["chunks"])
                if not isinstance(raw_chunks, list):
                    raise WorkspaceCorruptError(
                        "chunk artifact must contain a JSON array"
                    )
                selected_set = set(selected_source_ids)
                chunks = tuple(
                    chunk
                    for chunk in (chunk_from_dict(item) for item in raw_chunks)
                    if chunk.source_id in selected_set
                )

                raw_transforms = load_json(clean_state.outputs["transforms"])
                if not isinstance(raw_transforms, list):
                    raise WorkspaceCorruptError(
                        "transform artifact must contain a JSON array"
                    )
                transforms = tuple(
                    record
                    for record in (
                        transform_record_from_dict(item)
                        for item in raw_transforms
                    )
                    if record.source_id in selected_set
                )

                ir_artifacts: list[IRArtifactInput] = []
                for source_id in selected_source_ids:
                    document_artifact_id = clean_state.outputs[
                        f"source/{source_id}/document"
                    ]
                    artifact = revision.artifacts[document_artifact_id]
                    ir_artifacts.append(
                        IRArtifactInput.create(
                            source_id=source_id,
                            artifact_id=document_artifact_id,
                            artifact_kind="cleaned-document-ir",
                            document_json=self._candidate_artifact_bytes(
                                revision,
                                document_artifact_id,
                            ),
                            producer_id=artifact.producer_id,
                            producer_version=artifact.producer_version,
                            config_digest=artifact.config_digest,
                        )
                    )

                reviews = tuple(
                    decision.review
                    for decision in result.decisions
                    if decision.review is not None
                )
                inputs = ConstructionInputs.create(
                    cleaning_config_digest=clean_state.config_digest,
                    sources=sources,
                    chunks=chunks,
                    transforms=transforms,
                    ir_artifacts=ir_artifacts,
                    reviews=reviews,
                )
                validate_construction_result(recipe, inputs, result)
            except WorkspaceCorruptError:
                raise
            except (
                VeriformisError,
                KeyError,
                UnicodeError,
                ValueError,
                TypeError,
            ) as exc:
                raise WorkspaceCorruptError(
                    "construct artifacts do not match their declared inputs"
                ) from exc
            return

        if self.stage == "chunk":
            from veriformis.chunkers.base import chunk_from_dict
            from veriformis.chunkers.pipeline import build_chunks
            from veriformis.errors import EvidenceError
            from veriformis.evidence import derivation_from_dict, replay_derivations
            from veriformis.ir import (
                block_text,
                document_from_dict,
                iter_document_blocks,
                validate_document_against_stream,
            )
            from veriformis.rules.cleaning import (
                cleaning_input_digest,
                cleaning_plan_from_dict,
                plan_cleaning,
            )
            from veriformis.rules.derivations import (
                block_derivations_from_dict,
                build_block_derivations,
            )
            from veriformis.rules.engine import transform_record_from_dict
            from veriformis.rules.library import rules_from_clean_config
            from veriformis.sources import SourceRef

            raw_chunks = load_json(revision.stages["chunk"].outputs["chunks"])
            if not isinstance(raw_chunks, list):
                raise WorkspaceCorruptError("chunk artifact must contain a JSON array")
            try:
                chunks = [chunk_from_dict(item) for item in raw_chunks]
                ids = [chunk.id for chunk in chunks]
                if len(ids) != len(set(ids)):
                    raise EvidenceError("chunk artifact contains duplicate identities")
                sources: dict[str, SourceRef] = {}
                documents = {}
                derivations_by_source = {}
                expected_records = []
                clean_state = revision.stages["clean"]
                parse_state = revision.stages["parse"]
                configured_rules = rules_from_clean_config(clean_state.config)
                for source_id, descriptor in sorted(revision.sources.items()):
                    artifact_id = descriptor.extracted_artifact_id
                    if artifact_id is None:
                        raise EvidenceError(
                            f"source {source_id} has no canonical text artifact"
                        )
                    extracted = self._candidate_artifact_bytes(
                        revision, artifact_id
                    ).decode("utf-8")
                    sources[source_id] = SourceRef(
                        id=descriptor.id,
                        path=descriptor.original_path or descriptor.logical_path,
                        sha256=descriptor.sha256,
                        size=descriptor.size,
                        parser=descriptor.parser_id,
                        extracted_text=extracted,
                        logical_path=descriptor.logical_path,
                        parser_version=descriptor.parser_version,
                        canonical_stream_contract_version=(
                            descriptor.canonical_stream_contract_version
                        ),
                        stream_sha256=sha256_digest(extracted),
                        artifact_id=artifact_id,
                    )
                    parsed = document_from_dict(
                        load_json(
                            parse_state.outputs[f"source/{source_id}/document"]
                        )
                    )
                    validate_document_against_stream(parsed, extracted, exact=True)
                    plan = cleaning_plan_from_dict(
                        load_json(
                            clean_state.outputs[
                                f"source/{source_id}/cleaning-plan"
                            ]
                        )
                    )
                    expected_input = cleaning_input_digest(
                        parsed,
                        source_id=source_id,
                        raw_sha256=descriptor.sha256,
                        canonical_artifact_id=artifact_id,
                        canonical_stream_sha256=sha256_digest(extracted),
                        parser=descriptor.parser_id,
                        parser_version=descriptor.parser_version,
                        canonical_stream_contract_version=(
                            descriptor.canonical_stream_contract_version
                        ),
                    )
                    if plan.base_input_sha256 != expected_input:
                        raise EvidenceError(
                            f"cleaning plan is not bound to source {source_id}"
                        )
                    expected_preview = plan_cleaning(
                        parsed,
                        configured_rules,
                        max_remove_frac=(
                            clean_state.config["max_remove_ppm"] / 1_000_000
                        ),
                        base_input_sha256=expected_input,
                    )
                    if plan != expected_preview.plan:
                        raise EvidenceError(
                            "cleaning plan does not match configured replay"
                        )
                    cleaned = document_from_dict(
                        load_json(
                            clean_state.outputs[f"source/{source_id}/document"]
                        )
                    )
                    if cleaned != expected_preview.document:
                        raise EvidenceError(
                            f"cleaned document does not replay for source {source_id}"
                        )
                    validate_document_against_stream(cleaned, extracted, exact=False)
                    documents[source_id] = cleaned
                    expected_records.extend(expected_preview.records)

                    derivation_artifact_id = clean_state.outputs[
                        f"source/{source_id}/block-derivations"
                    ]
                    if revision.artifacts[
                        derivation_artifact_id
                    ].config_digest != canonical_digest(
                        {**clean_state.config, "cleaning_plan_id": plan.id}
                    ):
                        raise EvidenceError(
                            "block derivation artifact is not configured for its plan"
                        )
                    raw_derivations = load_json(derivation_artifact_id)
                    actual_derivations = block_derivations_from_dict(
                        raw_derivations
                    )
                    expected_derivations = build_block_derivations(
                        sources[source_id],
                        cleaned,
                        cleaning_plan_id=plan.id,
                    )
                    if actual_derivations != expected_derivations:
                        raise EvidenceError(
                            "block derivations are not the canonical replay"
                        )
                    expected_indexes = {
                        str(block.block_index)
                        for block in iter_document_blocks(cleaned)
                    }
                    if (
                        not isinstance(raw_derivations, dict)
                        or set(raw_derivations) != expected_indexes
                    ):
                        raise EvidenceError(
                            "block derivations do not cover the cleaned document"
                        )
                    source_derivations = {}
                    for block in iter_document_blocks(cleaned):
                        raw_steps = raw_derivations[str(block.block_index)]
                        if not isinstance(raw_steps, list) or block.span is None:
                            raise EvidenceError("invalid block derivation entry")
                        steps = tuple(
                            derivation_from_dict(item) for item in raw_steps
                        )
                        original = extracted[block.span.start : block.span.end]
                        cleaned_text = block_text(block)
                        if original == cleaned_text:
                            if steps:
                                raise EvidenceError(
                                    "unchanged block carries cleaning derivations"
                                )
                        else:
                            expected_context = canonical_digest(
                                {
                                    "cleaning_plan_id": plan.id,
                                    "source_id": source_id,
                                    "block_index": block.block_index,
                                }
                            )
                            if (
                                len(steps) != 1
                                or steps[0].kind != "edits"
                                or steps[0].context_digest != expected_context
                                or replay_derivations(original, steps)
                                != cleaned_text
                            ):
                                raise EvidenceError(
                                    "block derivation is not bound to its plan"
                                )
                        source_derivations[block.block_index] = steps
                    derivations_by_source[source_id] = source_derivations

                raw_records = load_json(clean_state.outputs["transforms"])
                if not isinstance(raw_records, list):
                    raise EvidenceError("transform artifact must be an array")
                records = [
                    transform_record_from_dict(item) for item in raw_records
                ]
                if records != expected_records:
                    raise EvidenceError(
                        "transform metadata does not match cleaning plan replay"
                    )
                config = revision.stages["chunk"].config
                if set(config) != {"strategy", "size", "overlap"}:
                    raise EvidenceError(
                        "chunk stage config does not match its v1 schema"
                    )
                expected_chunks = build_chunks(
                    documents,
                    sources,
                    records,
                    derivations_by_source,
                    strategy=config["strategy"],
                    size=config["size"],
                    overlap=config["overlap"],
                )
                if chunks != expected_chunks:
                    raise EvidenceError(
                        "chunk artifact does not match deterministic replay"
                    )
            except WorkspaceCorruptError:
                raise
            except (
                VeriformisError,
                KeyError,
                UnicodeError,
                ValueError,
                TypeError,
            ) as exc:
                raise WorkspaceCorruptError(
                    "chunk artifact does not match its registered clean state"
                ) from exc
            return

        from veriformis.ir import (
            block_text,
            document_from_dict,
            iter_document_blocks,
            validate_document_against_stream,
        )

        parse_state = revision.stages["parse"]
        if self.stage == "clean":
            from veriformis.evidence import (
                derivation_from_dict,
                replay_derivations,
            )
            from veriformis.rules.cleaning import (
                cleaning_input_digest,
                cleaning_plan_from_dict,
                plan_cleaning,
            )
            from veriformis.rules.derivations import (
                block_derivations_from_dict,
                build_block_derivations,
            )
            from veriformis.rules.engine import transform_record_from_dict
            from veriformis.rules.library import rules_from_clean_config
            from veriformis.sources import SourceRef

            clean_state = revision.stages["clean"]
            try:
                configured_rules = rules_from_clean_config(clean_state.config)
            except VeriformisError as exc:
                raise WorkspaceCorruptError("clean stage config is invalid") from exc
            expected_records = []
            for source_id, source in sorted(revision.sources.items()):
                canonical_artifact_id = source.extracted_artifact_id
                if canonical_artifact_id is None:
                    raise WorkspaceCorruptError(
                        f"source {source_id} lacks canonical input"
                    )
                canonical = self._candidate_artifact_bytes(
                    revision, canonical_artifact_id
                ).decode("utf-8")
                parsed = document_from_dict(
                    load_json(parse_state.outputs[f"source/{source_id}/document"])
                )
                validate_document_against_stream(parsed, canonical, exact=True)
                plan = cleaning_plan_from_dict(
                    load_json(clean_state.outputs[f"source/{source_id}/cleaning-plan"])
                )
                expected_input = cleaning_input_digest(
                    parsed,
                    source_id=source_id,
                    raw_sha256=source.sha256,
                    canonical_artifact_id=canonical_artifact_id,
                    canonical_stream_sha256=sha256_digest(canonical),
                    parser=source.parser_id,
                    parser_version=source.parser_version,
                    canonical_stream_contract_version=(
                        source.canonical_stream_contract_version
                    ),
                )
                if plan.base_input_sha256 != expected_input:
                    raise WorkspaceCorruptError(
                        f"cleaning plan is not bound to source {source_id}"
                    )
                expected_preview = plan_cleaning(
                    parsed,
                    configured_rules,
                    max_remove_frac=clean_state.config["max_remove_ppm"] / 1_000_000,
                    base_input_sha256=expected_input,
                )
                if plan != expected_preview.plan:
                    raise WorkspaceCorruptError(
                        f"cleaning plan is not the configured replay for source {source_id}"
                    )
                expected_records.extend(expected_preview.records)
                cleaned = document_from_dict(
                    load_json(clean_state.outputs[f"source/{source_id}/document"])
                )
                expected_cleaned = expected_preview.document
                if cleaned != expected_cleaned:
                    raise WorkspaceCorruptError(
                        f"cleaned document does not replay for source {source_id}"
                    )
                validate_document_against_stream(cleaned, canonical, exact=False)

                raw_derivations = load_json(
                    clean_state.outputs[f"source/{source_id}/block-derivations"]
                )
                if not isinstance(raw_derivations, dict):
                    raise WorkspaceCorruptError(
                        "block derivations must be a JSON object"
                    )
                actual_derivations = block_derivations_from_dict(raw_derivations)
                expected_derivations = build_block_derivations(
                    SourceRef(
                        id=source.id,
                        path=source.logical_path,
                        sha256=source.sha256,
                        size=source.size,
                        parser=source.parser_id,
                        extracted_text=canonical,
                        logical_path=source.logical_path,
                        parser_version=source.parser_version,
                        canonical_stream_contract_version=(
                            source.canonical_stream_contract_version
                        ),
                        stream_sha256=sha256_digest(canonical),
                        artifact_id=canonical_artifact_id,
                    ),
                    cleaned,
                    cleaning_plan_id=plan.id,
                )
                if actual_derivations != expected_derivations:
                    raise WorkspaceCorruptError(
                        "block derivations do not match canonical cleaning replay"
                    )
                derivation_artifact_id = clean_state.outputs[
                    f"source/{source_id}/block-derivations"
                ]
                expected_derivation_config = canonical_digest(
                    {**clean_state.config, "cleaning_plan_id": plan.id}
                )
                if (
                    revision.artifacts[derivation_artifact_id].config_digest
                    != expected_derivation_config
                ):
                    raise WorkspaceCorruptError(
                        f"block derivations are not configured for plan {plan.id}"
                    )
                expected_indexes = {
                    str(block.block_index) for block in iter_document_blocks(cleaned)
                }
                if set(raw_derivations) != expected_indexes:
                    raise WorkspaceCorruptError(
                        f"block derivations do not cover source {source_id}"
                    )
                for block in iter_document_blocks(cleaned):
                    raw_steps = raw_derivations[str(block.block_index)]
                    if not isinstance(raw_steps, list):
                        raise WorkspaceCorruptError(
                            "block derivation entry must be an array"
                        )
                    steps = tuple(derivation_from_dict(item) for item in raw_steps)
                    if block.span is None:
                        raise WorkspaceCorruptError(
                            "cleaned block lacks immutable source span"
                        )
                    original = canonical[block.span.start : block.span.end]
                    cleaned_text = block_text(block)
                    if original == cleaned_text:
                        if steps:
                            raise WorkspaceCorruptError(
                                "unchanged block carries cleaning derivations"
                            )
                        continue
                    expected_context = canonical_digest(
                        {
                            "cleaning_plan_id": plan.id,
                            "source_id": source_id,
                            "block_index": block.block_index,
                        }
                    )
                    if (
                        len(steps) != 1
                        or steps[0].kind != "edits"
                        or steps[0].context_digest != expected_context
                    ):
                        raise WorkspaceCorruptError(
                            "block derivation is not bound to its cleaning plan"
                        )
                    if replay_derivations(original, steps) != cleaned_text:
                        raise WorkspaceCorruptError(
                            f"block derivations do not reconstruct source {source_id}"
                        )

            raw_records = load_json(clean_state.outputs["transforms"])
            if not isinstance(raw_records, list):
                raise WorkspaceCorruptError("transform artifact must be a JSON array")
            records = [transform_record_from_dict(item) for item in raw_records]
            if records != expected_records:
                raise WorkspaceCorruptError(
                    "transform artifact metadata does not match plan replay"
                )
            return

        from veriformis.diagnostics import (
            parse_report_from_dict,
            validate_parse_report_locations,
        )
        from veriformis.parsers.dispatch import parse_captured_source

        registry = load_json(parse_state.outputs["registry"])
        expected_registry = [
            source.model_dump(mode="json", exclude={"original_path"})
            for source in sorted(revision.sources.values(), key=lambda item: item.id)
        ]
        if registry != expected_registry:
            raise WorkspaceCorruptError(
                "parse registry does not match the candidate source descriptors"
            )

        for source_id, source in sorted(revision.sources.items()):
            if source.raw_artifact_id is None:
                raise WorkspaceCorruptError(
                    f"source {source_id} lacks captured raw input"
                )
            raw_bytes = self._candidate_artifact_bytes(
                revision,
                source.raw_artifact_id,
            )
            canonical = self._candidate_artifact_bytes(
                revision,
                parse_state.outputs[f"source/{source_id}/canonical"],
            ).decode("utf-8")
            document = document_from_dict(
                load_json(parse_state.outputs[f"source/{source_id}/document"])
            )
            if document.source_id != source_id:
                raise WorkspaceCorruptError(
                    f"parse document source does not match {source_id}"
                )
            validate_document_against_stream(document, canonical, exact=True)
            report = parse_report_from_dict(
                load_json(parse_state.outputs[f"source/{source_id}/diagnostics"])
            )
            if (
                report.source_id != source_id
                or report.parser_name != source.parser_id
                or report.parser_version != source.parser_version
                or report.status == "refused"
            ):
                raise WorkspaceCorruptError(
                    f"parse report does not match source {source_id}"
                )
            try:
                validate_parse_report_locations(report, raw_bytes)
            except ParseError as exc:
                raise WorkspaceCorruptError(
                    f"parse report locations do not match source {source_id}"
                ) from exc
            try:
                expected = parse_captured_source(
                    source.logical_path,
                    logical_path=source.logical_path,
                    raw_bytes=raw_bytes,
                )
            except (VeriformisError, OSError, UnicodeError, ValueError) as exc:
                raise WorkspaceCorruptError(
                    f"captured raw source {source_id} cannot be deterministically parsed"
                ) from exc
            expected_source = expected.source
            descriptor_semantics = (
                source.id,
                source.logical_path,
                source.sha256,
                source.size,
                source.parser_id,
                source.parser_version,
                source.canonical_stream_contract_version,
                source.extracted_artifact_id,
            )
            expected_semantics = (
                expected_source.id,
                expected_source.logical_path,
                expected_source.sha256,
                expected_source.size,
                expected_source.parser,
                expected_source.parser_version,
                expected_source.canonical_stream_contract_version,
                expected_source.artifact_id,
            )
            if descriptor_semantics != expected_semantics:
                raise WorkspaceCorruptError(
                    f"source descriptor does not match raw parser result {source_id}"
                )
            if (
                canonical != expected_source.extracted_text
                or document != expected.document
                or report != expected.diagnostics
            ):
                raise WorkspaceCorruptError(
                    f"parse artifacts do not match captured raw source {source_id}"
                )

    def _install_objects(self, revision: WorkspaceRevision) -> None:
        for artifact in revision.artifacts.values():
            target = self.workspace._object_path(artifact.sha256)
            if target.exists():
                if (
                    target.stat().st_size != artifact.size
                    or sha256_digest(target.read_bytes()) != artifact.sha256
                ):
                    raise ArtifactDigestMismatchError(
                        f"existing object does not match artifact {artifact.id}"
                    )
                continue
            staged = self._staged_objects / artifact.sha256
            if not staged.exists():
                raise WorkspaceCorruptError(
                    f"transaction did not stage bytes for artifact {artifact.id}"
                )
            prefix_was_missing = not target.parent.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            if prefix_was_missing:
                _fsync_dir(target.parent.parent)
            os.replace(staged, target)
            os.chmod(target, 0o444)
            _fsync_dir(target.parent)

    def _install_revision(self, revision: WorkspaceRevision) -> None:
        _install_revision_directory(
            self.workspace.root,
            self._temp_dir,
            revision,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("workspace transaction is closed")
