"""Versioned YAML/JSON pipeline specifications for PipelineService."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from veriformis.errors import VeriformisError

PIPELINE_SCHEMA_VERSION = "veriformis.pipeline/v1"
_STAGE_ORDER = (
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


class PipelineSpecError(VeriformisError):
    code = "pipeline-spec-invalid"


@dataclass(frozen=True)
class PipelineSpec:
    schema_version: str
    workspace: Path
    source_paths: tuple[Path, ...]
    source_root: Path | None
    stages: dict[str, dict[str, Any]]
    recipe_library_id: str | None = None

    def ordered_stage_names(self) -> tuple[str, ...]:
        return tuple(name for name in _STAGE_ORDER if name in self.stages)


def load_pipeline_spec(path: Path) -> PipelineSpec:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PipelineSpecError(f"pipeline document is not UTF-8: {exc}") from exc
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PipelineSpecError(f"pipeline document is not valid YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineSpecError("pipeline document root must be a mapping")
    base = path.parent
    return pipeline_spec_from_dict(value, base_dir=base)


def pipeline_spec_from_dict(
    value: dict[str, Any],
    *,
    base_dir: Path,
) -> PipelineSpec:
    if value.get("schema_version") != PIPELINE_SCHEMA_VERSION:
        raise PipelineSpecError(
            f"unsupported pipeline schema {value.get('schema_version')!r}; "
            f"expected {PIPELINE_SCHEMA_VERSION!r}"
        )
    workspace = _resolve_path(value.get("workspace"), base_dir=base_dir, field="workspace")
    source_root = value.get("source_root")
    resolved_root = (
        _resolve_path(source_root, base_dir=base_dir, field="source_root")
        if source_root is not None
        else None
    )
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise PipelineSpecError("pipeline requires a nonempty sources list")
    # Source paths resolve against source_root when present, else the document dir.
    source_base = resolved_root if resolved_root is not None else base_dir
    source_paths: list[Path] = []
    for index, item in enumerate(sources):
        if isinstance(item, str):
            source_paths.append(
                _resolve_path(item, base_dir=source_base, field=f"sources[{index}]")
            )
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            source_paths.append(
                _resolve_path(
                    item["path"],
                    base_dir=source_base,
                    field=f"sources[{index}].path",
                )
            )
        else:
            raise PipelineSpecError(
                f"sources[{index}] must be a path string or {{path: ...}} mapping"
            )
    stages = value.get("stages")
    if not isinstance(stages, dict) or not stages:
        raise PipelineSpecError("pipeline requires a nonempty stages mapping")
    unknown = sorted(set(stages) - set(_STAGE_ORDER))
    if unknown:
        raise PipelineSpecError(f"pipeline stages contain unknown names: {unknown}")
    normalized_stages: dict[str, dict[str, Any]] = {}
    for name, config in stages.items():
        if config is None:
            normalized_stages[name] = {}
        elif isinstance(config, dict):
            normalized_stages[name] = dict(config)
        else:
            raise PipelineSpecError(f"stage {name!r} config must be a mapping")
    if "parse" in normalized_stages and "seal" in normalized_stages:
        # Full compile path requires intermediate stages explicitly or defaults.
        for required in ("clean", "chunk", "construct", "curate", "split", "format", "validate"):
            normalized_stages.setdefault(required, {})
    recipe_library_id = value.get("recipe_library_id")
    if recipe_library_id is not None and not isinstance(recipe_library_id, str):
        raise PipelineSpecError("recipe_library_id must be a string when provided")
    return PipelineSpec(
        schema_version=PIPELINE_SCHEMA_VERSION,
        workspace=workspace,
        source_paths=tuple(source_paths),
        source_root=resolved_root,
        stages=normalized_stages,
        recipe_library_id=recipe_library_id,
    )


def _resolve_path(value: Any, *, base_dir: Path, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PipelineSpecError(f"{field} must be a nonempty path string")
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path
