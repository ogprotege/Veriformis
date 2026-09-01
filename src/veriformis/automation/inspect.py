"""Project-spec schema, dry-run, lockfile, and environment inspection."""

from __future__ import annotations

import importlib.metadata
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from veriformis.automation.spec import ProjectSpec, ProjectSpecExport, load_project_spec
from veriformis.contracts import (
    ENVIRONMENT_INSPECT_SCHEMA_ID,
    PROJECT_LOCK_CONTRACT_ID,
    PROJECT_LOCK_CONTRACT_VERSION,
    PROJECT_LOCK_SCHEMA_ID,
    PROJECT_SPEC_DRY_RUN_SCHEMA_ID,
)
from veriformis.errors import ProjectSpecError
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest, validate_id
from veriformis.taxonomy import implemented_discovery

import veriformis as veriformis_pkg


DOCUMENT_SOURCE_STAGES: tuple[str, ...] = (
    "parse",
    "clean",
    "chunk",
    "construct",
    "curate",
    "split",
    "format",
    "validate",
    "seal",
)
DATASET_ROW_STAGES: tuple[str, ...] = (
    "parse",
    "map",
    "curate",
    "split",
    "format",
    "validate",
    "seal",
)
PIPELINE_STAGE_ORDER: tuple[str, ...] = (
    "parse",
    "clean",
    "chunk",
    "construct",
    "curate",
    "split",
    "format",
    "validate",
    "seal",
)
_EXTRA_MARKER = re.compile(r'extra\s*==\s*["\']([^"\']+)["\']')


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class EnvironmentInspect(_StrictModel):
    extras: dict[str, str]
    python_version: str
    schema_id: Literal["veriformis.environment-inspect/v1"]
    taxonomy_implemented_counts: dict[str, int]
    veriformis_version: str

    @model_validator(mode="after")
    def _closed(self) -> EnvironmentInspect:
        if self.schema_id != ENVIRONMENT_INSPECT_SCHEMA_ID:
            raise ProjectSpecError("environment inspect schema_id mismatch")
        _require_extra_map(self.extras)
        if any(key.lower() in {"hf_token", "token", "authorization", "secret", "password"} for key in self.extras):
            raise ProjectSpecError("environment inspect cannot name secrets")
        return self


class ProjectLock(_StrictModel):
    contract_id: Literal["veriformis.project-lock"]
    contract_version: Literal[1]
    extras: dict[str, str]
    lock_id: str
    python_version: str
    schema_id: Literal["veriformis.project-lock/v1"]
    spec_digest: str
    spec_id: str
    veriformis_version: str
    source_identities: tuple[str, ...] | None = None
    workspace_head: str | None = None

    @field_validator("source_identities", mode="before")
    @classmethod
    def _tuple_sources(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ProjectLock:
        if self.contract_id != PROJECT_LOCK_CONTRACT_ID:
            raise ProjectSpecError("project lock contract_id mismatch")
        if self.contract_version != PROJECT_LOCK_CONTRACT_VERSION:
            raise ProjectSpecError("project lock contract_version mismatch")
        if self.schema_id != PROJECT_LOCK_SCHEMA_ID:
            raise ProjectSpecError("project lock schema_id mismatch")
        _require_extra_map(self.extras)
        validate_id(self.spec_id, kind="psp")
        from veriformis.identity import validate_sha256

        validate_sha256(self.spec_digest)
        if self.python_version.count(".") != 1:
            raise ProjectSpecError("project lock python_version must be major.minor")
        validate_id(self.lock_id, kind="plk")
        if self.workspace_head is not None:
            try:
                validate_id(self.workspace_head, kind="rev")
            except ValueError as exc:
                raise ProjectSpecError(
                    "lock workspace_head is not a revision identity"
                ) from exc
        if self.source_identities is not None:
            if self.source_identities != tuple(sorted(self.source_identities)):
                raise ProjectSpecError("lock source_identities must be sorted")
            try:
                for item in self.source_identities:
                    validate_id(item, kind="src")
            except ValueError as exc:
                raise ProjectSpecError(
                    "lock source_identities must be source identities"
                ) from exc
        expected = derive_id(
            "plk",
            self.model_dump(mode="json", exclude={"lock_id"}, exclude_none=True),
        )
        if self.lock_id != expected:
            raise ProjectSpecError("project lock identity mismatch")
        return self


class ProjectSpecDryRun(_StrictModel):
    environment: EnvironmentInspect
    export: ProjectSpecExport | None = None
    mapping_confirmed: bool
    mapping_required: bool
    mode: str
    schema_id: Literal["veriformis.project-spec-dry-run/v1"]
    spec_id: str
    stages: tuple[str, ...]
    writes_bundle: Literal[False]
    writes_destination: Literal[False]
    writes_workspace: Literal[False]

    @field_validator("stages", mode="before")
    @classmethod
    def _tuple_stages(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _closed(self) -> ProjectSpecDryRun:
        if self.schema_id != PROJECT_SPEC_DRY_RUN_SCHEMA_ID:
            raise ProjectSpecError("project spec dry-run schema_id mismatch")
        if True in (self.writes_bundle, self.writes_destination, self.writes_workspace):
            raise ProjectSpecError("project spec dry-run cannot write")
        return self


def _require_extra_map(extras: dict[str, str]) -> None:
    if list(extras) != sorted(extras):
        raise ProjectSpecError("extra names must be sorted")
    for name, state in extras.items():
        if state not in {"empty", "present"}:
            raise ProjectSpecError(f"extra {name!r} presence must be empty or present")
        if "token" in name.lower() or name.upper() in {"HF_TOKEN", "AWS_SECRET_ACCESS_KEY"}:
            raise ProjectSpecError("extra map cannot name credentials")


def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def declared_extra_presence() -> dict[str, str]:
    names = sorted(importlib.metadata.metadata("veriformis").get_all("Provides-Extra") or [])
    nonempty: set[str] = set()
    for requirement in importlib.metadata.requires("veriformis") or []:
        marker = requirement.split(";", 1)[1] if ";" in requirement else ""
        match = _EXTRA_MARKER.search(marker)
        if match:
            nonempty.add(match.group(1))
    return {name: ("present" if name in nonempty else "empty") for name in names}


def taxonomy_implemented_counts() -> dict[str, int]:
    discovery = implemented_discovery()
    skip = {"contract_id", "contract_version", "schema_id"}
    counts = {
        str(axis): len(values)
        for axis, values in discovery.items()
        if axis not in skip
    }
    return {key: counts[key] for key in sorted(counts)}


def inspect_environment() -> EnvironmentInspect:
    return EnvironmentInspect(
        schema_id=ENVIRONMENT_INSPECT_SCHEMA_ID,
        veriformis_version=veriformis_pkg.__version__,
        python_version=python_version(),
        extras=declared_extra_presence(),
        taxonomy_implemented_counts=taxonomy_implemented_counts(),
    )


def project_spec_json_schema() -> dict[str, Any]:
    from veriformis.automation.spec import ProjectSpec as SpecModel

    return json.loads(json.dumps(SpecModel.model_json_schema(), sort_keys=True))


def spec_digest(spec: ProjectSpec) -> str:
    return sha256_digest(
        lossless_json_bytes(
            spec.model_dump(mode="json", exclude={"spec_id"}, exclude_none=True)
        )
    )


def planned_stages(spec: ProjectSpec, *, pipeline_stages: dict[str, Any] | None = None) -> tuple[str, ...]:
    stages_map = pipeline_stages
    if stages_map is None and spec.pipeline is not None:
        stages_map = spec.pipeline.get("stages") or {}
    if stages_map is None and spec.pipeline_ref is not None and spec.pipeline is None:
        raise ProjectSpecError(
            "cannot reconstruct stages from unresolved pipeline_ref; embed pipeline sources"
        )
    if stages_map is not None:
        order = (
            DATASET_ROW_STAGES
            if spec.mode in {"dataset-row", "mixed"}
            else PIPELINE_STAGE_ORDER
        )
        names = [
            name
            for name in order
            if name == "map" or name in stages_map
        ]
        return tuple(names)
    if spec.mode == "document-source":
        return DOCUMENT_SOURCE_STAGES
    return DATASET_ROW_STAGES


def resolve_spec_ref(value: str, *, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path


def pipeline_for_spec(spec: ProjectSpec, *, base_dir: Path):
    from veriformis.recipes.pipeline_spec import load_pipeline_spec, pipeline_spec_from_dict

    if spec.pipeline is not None:
        return pipeline_spec_from_dict(spec.pipeline, base_dir=base_dir)
    if spec.pipeline_ref is None:
        raise ProjectSpecError("spec execute requires embedded pipeline or pipeline_ref")
    try:
        return load_pipeline_spec(resolve_spec_ref(spec.pipeline_ref, base_dir=base_dir))
    except FileNotFoundError as exc:
        raise ProjectSpecError(
            "cannot reconstruct stages from unresolved pipeline_ref; embed pipeline sources"
        ) from exc


def dry_run_project_spec(spec: ProjectSpec, *, base_dir: Path | None = None) -> ProjectSpecDryRun:
    required = spec.mode in {"dataset-row", "mixed"}
    if spec.pipeline is not None or spec.pipeline_ref is not None:
        pipeline = pipeline_for_spec(spec, base_dir=base_dir or Path("."))
        stages = planned_stages(spec, pipeline_stages=pipeline.stages)
    else:
        stages = planned_stages(spec)
    return ProjectSpecDryRun(
        schema_id=PROJECT_SPEC_DRY_RUN_SCHEMA_ID,
        spec_id=spec.spec_id,
        mode=spec.mode,
        stages=stages,
        mapping_required=required,
        mapping_confirmed=required and spec.mapping is not None,
        export=spec.export,
        environment=inspect_environment(),
        writes_workspace=False,
        writes_bundle=False,
        writes_destination=False,
    )


def create_project_lock(
    spec: ProjectSpec,
    *,
    workspace_head: str | None = None,
    source_identities: tuple[str, ...] | None = None,
) -> ProjectLock:
    payload = {
        "contract_id": PROJECT_LOCK_CONTRACT_ID,
        "contract_version": PROJECT_LOCK_CONTRACT_VERSION,
        "schema_id": PROJECT_LOCK_SCHEMA_ID,
        "spec_id": spec.spec_id,
        "spec_digest": spec_digest(spec),
        "veriformis_version": veriformis_pkg.__version__,
        "python_version": python_version(),
        "extras": declared_extra_presence(),
    }
    if workspace_head is not None:
        payload["workspace_head"] = workspace_head
    if source_identities is not None:
        payload["source_identities"] = list(source_identities)
    payload["lock_id"] = derive_id("plk", payload)
    return ProjectLock.model_validate(payload)


def load_project_lock(payload: object) -> ProjectLock:
    if not isinstance(payload, dict):
        raise ProjectSpecError("project lock must be an object")
    from veriformis.automation.spec import refuse_credential_fields

    refuse_credential_fields(payload, label="project lock")
    try:
        return ProjectLock.model_validate(payload)
    except ProjectSpecError:
        raise
    except Exception as exc:
        raise ProjectSpecError("project lock is invalid") from exc


def load_project_spec_document(path: Any) -> ProjectSpec:
    from pathlib import Path

    import yaml

    target = Path(path)
    try:
        text = target.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectSpecError(f"project spec document is not UTF-8: {exc}") from exc
    suffix = target.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        from veriformis.recipes.pipeline_spec import PipelineSpecError, _StrictSafeLoader

        try:
            value = yaml.load(text, Loader=_StrictSafeLoader)  # noqa: S506
        except yaml.YAMLError as exc:
            raise ProjectSpecError(f"project spec document is not valid YAML: {exc}") from exc
        except PipelineSpecError as exc:
            raise ProjectSpecError(f"project spec document is invalid: {exc.message}") from exc
    else:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectSpecError(f"project spec document is not valid JSON: {exc}") from exc
    return load_project_spec(value)
