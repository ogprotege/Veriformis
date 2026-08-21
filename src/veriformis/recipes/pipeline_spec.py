"""Versioned YAML/JSON pipeline specifications for PipelineService."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from veriformis.errors import VeriformisError
from veriformis.recipes.library import RECIPE_LIBRARY_IDS

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

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "workspace",
        "source_root",
        "sources",
        "stages",
        "recipe_library_id",
    }
)

# The exact per-stage config keys veriformis.recipes.runner reads. Anything
# else is a silent no-op (e.g. a `siz:` typo sealing a dataset with defaults),
# so unknown keys fail closed here.
_STAGE_CONFIG_KEYS: dict[str, frozenset[str]] = {
    "parse": frozenset(),
    "clean": frozenset({"rules", "custom"}),
    "chunk": frozenset({"strategy", "size", "overlap"}),
    "construct": frozenset(
        {
            "objective",
            "source",
            "target_row_schema",
            "split_ratio_ppm",
            "require_review",
        }
    ),
    "curate": frozenset(
        {
            "evaluation_required",
            "allow_empty_evaluation",
            "minimum_target_characters",
            "balance_mode",
            "maximum_records_per_primary_source",
            "evaluation_ratio_ppm",
            "split_seed",
            "instruction",
        }
    ),
    "split": frozenset(),
    "format": frozenset(),
    "validate": frozenset(),
    "seal": frozenset({"out"}),
}


class PipelineSpecError(VeriformisError):
    code = "pipeline-spec-invalid"


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that fails closed on duplicate mapping keys.

    ``yaml.safe_load`` accepts duplicates last-one-wins, which silently drops
    an earlier value from a pipeline document.
    """

    def construct_mapping(self, node, deep=False):
        seen: set[Any] = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=True)
            try:
                duplicate = key in seen
            except TypeError:
                # Unhashable keys are rejected by SafeLoader itself below.
                continue
            if duplicate:
                raise PipelineSpecError(
                    f"pipeline document contains duplicate mapping key {key!r}"
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


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
        value = yaml.load(text, Loader=_StrictSafeLoader)  # noqa: S506 - SafeLoader subclass
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
    unknown_top = sorted(set(value) - _TOP_LEVEL_KEYS)
    if unknown_top:
        raise PipelineSpecError(
            f"pipeline document contains unknown top-level key(s): {unknown_top}"
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
            unknown_keys = sorted(set(config) - _STAGE_CONFIG_KEYS[name])
            if unknown_keys:
                raise PipelineSpecError(
                    f"stage {name!r} config contains unknown key(s): {unknown_keys}"
                )
            normalized_stages[name] = dict(config)
        else:
            raise PipelineSpecError(f"stage {name!r} config must be a mapping")
    if "parse" in normalized_stages and "seal" in normalized_stages:
        # Full compile path requires intermediate stages explicitly or defaults.
        for required in ("clean", "chunk", "construct", "curate", "split", "format", "validate"):
            normalized_stages.setdefault(required, {})
    recipe_library_id = value.get("recipe_library_id")
    if recipe_library_id is not None:
        if not isinstance(recipe_library_id, str):
            raise PipelineSpecError("recipe_library_id must be a string when provided")
        if recipe_library_id not in RECIPE_LIBRARY_IDS:
            raise PipelineSpecError(
                f"unknown recipe_library_id {recipe_library_id!r}; "
                f"expected one of {list(RECIPE_LIBRARY_IDS)!r}"
            )
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
