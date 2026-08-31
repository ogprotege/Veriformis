"""Project spec contract v1. Pins only; loading is not execute."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from veriformis.contracts import (
    PROJECT_SPEC_CONTRACT_ID,
    PROJECT_SPEC_CONTRACT_VERSION,
    PROJECT_SPEC_SCHEMA_ID,
)
from veriformis.errors import ProjectSpecError
from veriformis.identity import derive_id, validate_id, validate_sha256
from veriformis.taxonomy import (
    IMPLEMENTED_CONSUMER_PROFILES,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
)

INPUT_MODE_IDS: tuple[str, ...] = (
    "dataset-row",
    "document-source",
    "mixed",
)


SFT_TRAINING_FAMILIES: tuple[str, ...] = (
    "source-grounded-language-modeling",
    "source-grounded-supervised-fine-tuning",
)
PROJECT_SPEC_EXPORT_CONTAINERS: tuple[str, ...] = (
    "arrow",
    "constrained-csv",
    "hugging-face-dataset",
    "json",
    "parquet",
    "split-jsonl-directory",
)
PROJECT_SPEC_LIMITATIONS: tuple[str, ...] = (
    "no-hub-upload",
)
OVERWRITE_POLICIES: tuple[str, ...] = ("refuse",)
ADMITTED_COMPILE_PROFILES: frozenset[str] = frozenset(IMPLEMENTED_CONSUMER_PROFILES)
ADMITTED_EXPORT_PROFILES: frozenset[str] = frozenset(IMPLEMENTED_EXPORT_CONSUMER_PROFILES)
InputModeId = Literal["dataset-row", "document-source", "mixed"]
OverwritePolicy = Literal["refuse"]
ExportContainer = Literal[
    "arrow",
    "constrained-csv",
    "hugging-face-dataset",
    "json",
    "parquet",
    "split-jsonl-directory",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class ProjectSpecMapping(_StrictModel):
    confirmation_digest: str
    mapping_plan_id: str
    plan_path: str | None = None


class ProjectSpecExport(_StrictModel):
    container: ExportContainer
    overwrite: OverwritePolicy
    profile: str | None = None


class ProjectSpec(_StrictModel):
    """One project-spec pin. Loading a pin is not execute."""

    contract_id: Literal["veriformis.project-spec"]
    contract_version: Literal[1]
    generation_allowed: Literal[False]
    mode: InputModeId
    plugin_install_allowed: Literal[False]
    publication_allowed: Literal[False]
    schema_id: Literal["veriformis.project-spec/v1"]
    spec_id: str
    consumer_profile: str | None = None
    export: ProjectSpecExport | None = None
    goal_id: str | None = None
    mapping: ProjectSpecMapping | None = None
    pipeline: dict[str, Any] | None = None
    pipeline_ref: str | None = None
    preset_id: str | None = None

    @model_validator(mode="after")
    def _closed(self) -> ProjectSpec:
        if self.contract_id != PROJECT_SPEC_CONTRACT_ID:
            raise ProjectSpecError("project spec contract_id mismatch")
        if self.contract_version != PROJECT_SPEC_CONTRACT_VERSION:
            raise ProjectSpecError("project spec contract_version mismatch")
        if self.schema_id != PROJECT_SPEC_SCHEMA_ID:
            raise ProjectSpecError("project spec schema_id mismatch")
        if self.mode not in INPUT_MODE_IDS:
            raise ProjectSpecError(
                f"unknown input mode {self.mode!r}; expected one of "
                f"{list(INPUT_MODE_IDS)!r}"
            )
        if self.generation_allowed is not False:
            raise ProjectSpecError(
                "project-spec/v1 cannot allow generation; "
                "ADR-0018 Decision A forbids a compile-path generator"
            )
        if self.plugin_install_allowed is not False:
            raise ProjectSpecError(
                "project-spec/v1 cannot allow plugin install; "
                "ADR-0017 Decision A forbids an untrusted loader"
            )
        if self.publication_allowed is not False:
            raise ProjectSpecError(
                "project-spec/v1 cannot allow publication; "
                "network publication is absent from the default local path"
            )
        _require_mapping_policy(self)
        _require_pipeline(self)
        _require_goal_and_preset(self)
        _require_profiles(self)
        validate_id(self.spec_id, kind="psp")
        expected = derive_id(
            "psp",
            self.model_dump(mode="json", exclude={"spec_id"}, exclude_none=True),
        )
        if self.spec_id != expected:
            raise ProjectSpecError("project spec identity mismatch")
        return self


def _require_mapping_policy(spec: ProjectSpec) -> None:
    if spec.mode == "document-source":
        if spec.mapping is not None:
            raise ProjectSpecError("document-source cannot name mapping")
        return
    mapping = spec.mapping
    if mapping is None or not mapping.confirmation_digest:
        raise ProjectSpecError(
            f"unconfirmed mapping: {spec.mode} requires a confirmation_digest"
        )
    try:
        validate_sha256(mapping.confirmation_digest)
    except ValueError as exc:
        raise ProjectSpecError("unconfirmed mapping: confirmation_digest is not SHA-256") from exc
    try:
        validate_id(mapping.mapping_plan_id, kind="mpl")
    except ValueError as exc:
        raise ProjectSpecError(
            f"unconfirmed mapping: mapping_plan_id {mapping.mapping_plan_id!r} "
            "is not a mapping-plan identity"
        ) from exc
    if mapping.plan_path is not None:
        _require_safe_ref(mapping.plan_path, "mapping.plan_path")


def _require_pipeline(spec: ProjectSpec) -> None:
    if spec.pipeline is not None and spec.pipeline_ref is not None:
        raise ProjectSpecError("project spec cannot name both pipeline and pipeline_ref")
    if spec.pipeline_ref is not None:
        _require_safe_ref(spec.pipeline_ref, "pipeline_ref")
        if spec.mode == "mixed":
            raise ProjectSpecError(
                "mixed mode with pipeline_ref cannot prove members are not fused; "
                "embed pipeline sources"
            )
    if spec.pipeline is None:
        return
    from veriformis.recipes.pipeline_spec import (
        PIPELINE_SCHEMA_VERSION,
        PipelineSpecError,
        pipeline_spec_from_dict,
    )

    if spec.pipeline.get("schema_version") != PIPELINE_SCHEMA_VERSION:
        raise ProjectSpecError(
            "embedded pipeline must be "
            f"{PIPELINE_SCHEMA_VERSION}; loading a project spec does not "
            "teach pipeline/v1 new keys"
        )
    try:
        pipeline_spec_from_dict(spec.pipeline, base_dir=Path("/"))
    except PipelineSpecError as exc:
        raise ProjectSpecError(f"embedded pipeline is invalid: {exc.message}") from exc
    if spec.mode == "mixed":
        _refuse_fused_members(spec.pipeline.get("sources"))


def _refuse_fused_members(sources: object) -> None:
    paths: list[str] = []
    if not isinstance(sources, list):
        return
    for item in sources:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            paths.append(item["path"])
    from veriformis.mapping.capture import ROW_SUFFIXES

    suffixes = {Path(path).suffix.lower() for path in paths}
    row_suffixes = set(ROW_SUFFIXES)
    if suffixes & row_suffixes and not suffixes <= row_suffixes:
        raise ProjectSpecError(
            "mixed mode keeps construction and imported-row provenance "
            "distinct; compile document-source and dataset-row workspaces "
            "separately rather than fusing them in one stage graph"
        )


def _require_goal_and_preset(spec: ProjectSpec) -> None:
    from veriformis.goals import goal_catalog, preset_catalog

    catalog = goal_catalog()
    goal = None
    if spec.goal_id is not None:
        try:
            goal = catalog.goal(spec.goal_id)
        except Exception as exc:
            raise ProjectSpecError(f"unknown goal_id {spec.goal_id!r}") from exc
    if spec.preset_id is None:
        return
    try:
        preset = preset_catalog().preset(spec.preset_id)
    except Exception as exc:
        raise ProjectSpecError(f"unknown preset_id {spec.preset_id!r}") from exc
    if spec.goal_id is not None and preset.goal_id != spec.goal_id:
        raise ProjectSpecError(
            f"preset {spec.preset_id!r} belongs to goal {preset.goal_id!r}, "
            f"not {spec.goal_id!r}"
        )
    if goal is None:
        try:
            catalog.goal(preset.goal_id)
        except Exception as exc:
            raise ProjectSpecError(f"unknown preset goal {preset.goal_id!r}") from exc


def _require_profiles(spec: ProjectSpec) -> None:
    if spec.consumer_profile is not None:
        if spec.consumer_profile not in ADMITTED_COMPILE_PROFILES:
            raise ProjectSpecError(
                f"consumer profile {spec.consumer_profile!r} is not independently "
                "admitted"
            )
    export = spec.export
    if export is not None:
        if export.container not in PROJECT_SPEC_EXPORT_CONTAINERS:
            raise ProjectSpecError(
                f"unknown export container {export.container!r}; expected one of "
                f"{list(PROJECT_SPEC_EXPORT_CONTAINERS)!r}"
            )
        if export.overwrite not in OVERWRITE_POLICIES:
            raise ProjectSpecError("export overwrite must be refuse")
        if export.profile is not None and export.profile not in ADMITTED_EXPORT_PROFILES:
            raise ProjectSpecError(
                f"export profile {export.profile!r} is not independently admitted"
            )
    refusing = [
        name
        for name in (spec.consumer_profile, export.profile if export is not None else None)
        if name in ADMITTED_EXPORT_PROFILES
    ]
    if not refusing:
        return
    from veriformis.goals import goal_catalog, preset_catalog

    goal_id = spec.goal_id
    if goal_id is None and spec.preset_id is not None:
        try:
            goal_id = preset_catalog().preset(spec.preset_id).goal_id
        except Exception:
            return
    if goal_id is None:
        return
    try:
        family = goal_catalog().goal(goal_id).training_family
    except Exception:
        return
    if family not in SFT_TRAINING_FAMILIES:
        raise ProjectSpecError(
            f"family goal {goal_id!r} cannot select refusing profile "
            f"{refusing[0]!r}"
        )


def _require_safe_ref(value: str, label: str) -> None:
    if not value or value.strip() != value:
        raise ProjectSpecError(f"{label} must be a nonempty path string")
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise ProjectSpecError(f"{label} cannot contain parent-directory segments")


def _omit_none(value: dict[str, Any]) -> dict[str, Any]:
    """Drop top-level null optional fields. Do not rewrite embedded pipeline."""
    return {key: item for key, item in value.items() if item is not None}


def _supported_contract_label() -> str:
    return (
        f"contract_id={PROJECT_SPEC_CONTRACT_ID!r} "
        f"contract_version={PROJECT_SPEC_CONTRACT_VERSION} "
        f"schema_id={PROJECT_SPEC_SCHEMA_ID!r}"
    )


def _require_known_contract(payload: dict[str, Any]) -> None:
    missing = [
        name
        for name in ("contract_id", "contract_version", "schema_id")
        if name not in payload
    ]
    if missing:
        raise ProjectSpecError(
            "unknown project spec contract version: requested missing "
            f"{', '.join(missing)}, supported {_supported_contract_label()}"
        )
    requested_id = payload["contract_id"]
    requested_version = payload["contract_version"]
    requested_schema = payload["schema_id"]
    if (
        requested_id != PROJECT_SPEC_CONTRACT_ID
        or requested_version != PROJECT_SPEC_CONTRACT_VERSION
        or requested_schema != PROJECT_SPEC_SCHEMA_ID
    ):
        raise ProjectSpecError(
            "unknown project spec contract version: requested "
            f"contract_id={requested_id!r} "
            f"contract_version={requested_version!r} "
            f"schema_id={requested_schema!r}, supported "
            f"{_supported_contract_label()}"
        )


def _error_from_validation(exc: ValidationError) -> ProjectSpecError:
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        error_type = error.get("type")
        if error_type == "extra_forbidden":
            return ProjectSpecError(f"project spec contains unknown field {loc}")
        if error_type == "missing":
            if loc.startswith("mapping") or loc == "mapping":
                return ProjectSpecError("unconfirmed mapping: mapping is incomplete")
            return ProjectSpecError(f"project spec missing {loc or 'required field'}")
        if loc == "mode":
            return ProjectSpecError(
                f"unknown input mode {error.get('input')!r}; expected one of "
                f"{list(INPUT_MODE_IDS)!r}"
            )
        if loc == "export.container":
            return ProjectSpecError(
                f"unknown export container {error.get('input')!r}; expected one of "
                f"{list(PROJECT_SPEC_EXPORT_CONTAINERS)!r}"
            )
        if loc == "export.overwrite":
            return ProjectSpecError("export overwrite must be refuse")
        if loc in {"contract_version", "contract_id", "schema_id"}:
            return ProjectSpecError(
                "unknown project spec contract version: requested "
                f"{error.get('input')!r}, supported {_supported_contract_label()}"
            )
    return ProjectSpecError("project spec is invalid")


def create_project_spec(
    *,
    mode: str,
    goal_id: str | None = None,
    preset_id: str | None = None,
    mapping: dict[str, Any] | None = None,
    pipeline: dict[str, Any] | None = None,
    pipeline_ref: str | None = None,
    export: dict[str, Any] | None = None,
    consumer_profile: str | None = None,
    generation_allowed: bool = False,
    plugin_install_allowed: bool = False,
    publication_allowed: bool = False,
) -> ProjectSpec:
    """Build one pin with a derived identity. This is not execute."""
    payload: dict[str, Any] = {
        "contract_id": PROJECT_SPEC_CONTRACT_ID,
        "contract_version": PROJECT_SPEC_CONTRACT_VERSION,
        "schema_id": PROJECT_SPEC_SCHEMA_ID,
        "mode": mode,
        "generation_allowed": generation_allowed,
        "plugin_install_allowed": plugin_install_allowed,
        "publication_allowed": publication_allowed,
        "goal_id": goal_id,
        "preset_id": preset_id,
        "mapping": mapping,
        "pipeline": pipeline,
        "pipeline_ref": pipeline_ref,
        "export": export,
        "consumer_profile": consumer_profile,
    }
    payload["spec_id"] = derive_id(
        "psp",
        _omit_none({key: value for key, value in payload.items() if key != "spec_id"}),
    )
    return load_project_spec(payload)


def load_project_spec(payload: object) -> ProjectSpec:
    """Load one pin. Unknown fields, versions, and unconfirmed maps fail closed."""
    if not isinstance(payload, dict):
        raise ProjectSpecError("project spec must be an object")
    _require_known_contract(payload)
    if "mode" in payload and payload["mode"] not in INPUT_MODE_IDS:
        raise ProjectSpecError(
            f"unknown input mode {payload['mode']!r}; expected one of "
            f"{list(INPUT_MODE_IDS)!r}"
        )
    try:
        return ProjectSpec.model_validate(payload)
    except ProjectSpecError:
        raise
    except ValidationError as exc:
        raise _error_from_validation(exc) from exc
