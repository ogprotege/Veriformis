"""Versioned recipe presets v1: the single source of every recipe default.

``presets-v1.json`` is packaged versioned data validated by strict models. It
carries the recipe-wide defaults that every surface executes (segmentation,
construction, curation, review) and one named ``safe`` preset per goal. CLI
options, MCP tool parameters, the YAML runner, the recipe library, and the
workbench resolve their effective settings through
:func:`resolve_recipe_settings`; none of them holds an independent literal.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from veriformis.construction import SegmentationPolicy
from veriformis.errors import GoalCatalogError
from veriformis.goals.catalog import (
    REVIEW_POLICY_OPTIONS,
    CurationDefaults,
    goal_catalog,
    goal_for_objective,
    resolve_goal,
)
from veriformis.identity import canonical_digest
from veriformis.taxonomy import (
    IMPLEMENTED_CONSUMER_PROFILES,
    assert_compile_combination,
)

RECIPE_PRESET_DATA_NAME = "presets-v1.json"
SAFE_PRESET_NAME = "safe"
# Surfaces accept only the documented hyphenated spelling; the persisted
# CurationPolicy spelling is data, never an operator value.
SURFACE_BALANCE_MODES: dict[str, str] = {
    "none": "none",
    "primary-source-cap": "primary_source_cap",
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class SegmentationSettings(_StrictModel):
    strategy: str
    size: int
    overlap: int

    @model_validator(mode="after")
    def _executable(self) -> "SegmentationSettings":
        try:
            SegmentationPolicy(
                schema_version="veriformis.segmentation-policy/v1",
                strategy=self.strategy,  # type: ignore[arg-type]
                size=self.size,
                overlap=self.overlap,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            raise ValueError(f"segmentation is not an executable policy: {exc}") from exc
        return self


class ConstructionSettings(_StrictModel):
    split_ratio_ppm: int
    require_review: bool
    consumer_profile: str

    @field_validator("split_ratio_ppm")
    @classmethod
    def _ratio(cls, value: int) -> int:
        if type(value) is not int or not 1 <= value <= 999_999:
            raise ValueError("split_ratio_ppm must be an integer from 1 to 999999")
        return value

    @field_validator("consumer_profile")
    @classmethod
    def _profile(cls, value: str) -> str:
        if value not in IMPLEMENTED_CONSUMER_PROFILES:
            raise ValueError(f"consumer_profile {value!r} is not implemented")
        return value


def _require_review_consistent(construction: ConstructionSettings, review_policy: str) -> None:
    if construction.require_review != (review_policy == "required"):
        raise ValueError(
            "construction.require_review must equal (review_policy == 'required')"
        )


class RecipeDefaults(_StrictModel):
    """Recipe-wide defaults every surface executes when nothing is selected."""

    segmentation: SegmentationSettings
    construction: ConstructionSettings
    curation: CurationDefaults
    review_policy: Literal["none", "required"]

    @model_validator(mode="after")
    def _consistent(self) -> "RecipeDefaults":
        _require_review_consistent(self.construction, self.review_policy)
        return self


class RecipePreset(_StrictModel):
    """One safe, named configuration for one goal."""

    preset_id: str
    goal_id: str
    representation_id: str
    title: str
    plain_language: str
    segmentation: SegmentationSettings
    construction: ConstructionSettings
    curation: CurationDefaults
    review_policy: Literal["none", "required"]

    @model_validator(mode="after")
    def _bound(self) -> "RecipePreset":
        _require_review_consistent(self.construction, self.review_policy)
        name = self.preset_id.rsplit(".", 1)
        if len(name) != 2 or name[0] != self.goal_id or not name[1]:
            raise ValueError(
                f"preset_id {self.preset_id!r} must be '<goal_id>.<name>' for goal "
                f"{self.goal_id!r}"
            )
        if not self.title.strip() or self.title.strip() != self.title:
            raise ValueError("title must be non-empty without surrounding whitespace")
        if not self.plain_language.strip() or self.plain_language.strip() != self.plain_language:
            raise ValueError("plain_language must be non-empty without surrounding whitespace")
        return self


class PresetCatalog(_StrictModel):
    schema_id: Literal["veriformis.recipe-preset/v1"]
    contract_id: Literal["veriformis.recipe-preset"]
    contract_version: int
    defaults: RecipeDefaults
    presets: tuple[RecipePreset, ...]

    @field_validator("contract_version")
    @classmethod
    def _version(cls, value: int) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("contract_version must be exactly the integer 1")
        return value

    @model_validator(mode="after")
    def _closed(self) -> "PresetCatalog":
        catalog = goal_catalog()
        ids = [preset.preset_id for preset in self.presets]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate preset_id")
        safe = [preset for preset in self.presets if preset.preset_id.endswith(f".{SAFE_PRESET_NAME}")]
        if [preset.goal_id for preset in safe] != [goal.goal_id for goal in catalog.goals]:
            raise ValueError(
                "presets must contain exactly one safe preset per goal in catalog order"
            )
        for preset in self.presets:
            goal = catalog.goal(preset.goal_id)
            if preset.representation_id not in goal.compatible_representations:
                raise ValueError(
                    f"preset {preset.preset_id!r} names representation "
                    f"{preset.representation_id!r} that goal {goal.goal_id!r} does not allow"
                )
            objective, row_schema, _, _ = resolve_goal(goal.goal_id, preset.representation_id)
            try:
                assert_compile_combination(
                    objective, row_schema, profile=preset.construction.consumer_profile
                )
            except Exception as exc:  # TaxonomyError carries .message
                raise ValueError(f"preset {preset.preset_id!r} is not compilable: {exc}") from exc
        return self

    def preset(self, preset_id: str) -> RecipePreset:
        for preset in self.presets:
            if preset.preset_id == preset_id:
                return preset
        raise GoalCatalogError(
            f"unknown preset {preset_id!r}; expected one of "
            f"{[preset.preset_id for preset in self.presets]!r}"
        )

    def safe_preset(self, goal_id: str) -> RecipePreset:
        return self.preset(f"{goal_id}.{SAFE_PRESET_NAME}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _canonical_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def parse_preset_catalog(text: str, *, require_canonical: bool = False) -> PresetCatalog:
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise GoalCatalogError(f"recipe presets are not valid JSON: {exc}") from exc
    if require_canonical and _canonical_text(payload) != text:
        raise GoalCatalogError("recipe preset bytes are not canonical")
    try:
        return PresetCatalog.model_validate_json(json.dumps(payload))
    except ValidationError as exc:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise GoalCatalogError(f"recipe presets are invalid: {detail}") from exc
    except ValueError as exc:
        raise GoalCatalogError(f"recipe presets are invalid: {exc}") from exc


@lru_cache(maxsize=1)
def _packaged() -> tuple[str, PresetCatalog]:
    text = (
        resources.files("veriformis.goals")
        .joinpath(RECIPE_PRESET_DATA_NAME)
        .read_text(encoding="utf-8")
    )
    return text, parse_preset_catalog(text, require_canonical=True)


def preset_catalog() -> PresetCatalog:
    return _packaged()[1]


def preset_catalog_json() -> str:
    return _packaged()[0]


def discover_presets() -> dict[str, Any]:
    return json.loads(preset_catalog_json())


def recipe_defaults() -> RecipeDefaults:
    """The recipe-wide defaults every surface executes."""
    return preset_catalog().defaults


class ResolvedRecipeSettings(_StrictModel):
    """Effective, validated settings for one compile, with a stable digest."""

    goal_id: str
    preset_id: str | None
    representation_id: str
    objective: str
    row_schema: str
    recipe_library_id: str
    segmentation: SegmentationSettings
    construction: ConstructionSettings
    curation: CurationDefaults
    review_policy: Literal["none", "required"]
    settings_digest: str


def _pick(override: Any, base: Any) -> Any:
    return base if override is None else override


def resolve_recipe_settings(
    *,
    goal: str | None = None,
    preset: str | None = None,
    representation: str | None = None,
    objective: str | None = None,
    target_row_schema: str | None = None,
    strategy: str | None = None,
    size: int | None = None,
    overlap: int | None = None,
    split_ratio_ppm: int | None = None,
    require_review: bool | None = None,
    consumer_profile: str | None = None,
    minimum_target_characters: int | None = None,
    balance_mode: str | None = None,
    maximum_records_per_primary_source: int | None = None,
    evaluation_ratio_ppm: int | None = None,
    evaluation_required: bool | None = None,
    split_seed: str | None = None,
    review_policy: str | None = None,
) -> ResolvedRecipeSettings:
    """Resolve goal/preset/objective selections plus explicit overrides.

    Selection precedence: explicit overrides > preset values > the goal's
    safe preset. ``goal``, ``preset``, or ``objective`` selects the goal; a
    preset implies its goal and representation, and a goal without a preset
    resolves through its ``safe`` preset. Every result is validated as an
    executable, taxonomy-compatible configuration. The digest covers only the
    effective settings, so the same configuration reached by any selection
    path has the same digest.
    """
    catalog = preset_catalog()
    chosen_preset = None if preset is None else catalog.preset(preset)
    if chosen_preset is not None:
        if goal is not None and goal != chosen_preset.goal_id:
            raise GoalCatalogError(
                f"preset {preset!r} belongs to goal {chosen_preset.goal_id!r}, not {goal!r}"
            )
        goal = chosen_preset.goal_id
    if goal is None and objective is None:
        raise GoalCatalogError("select a goal, a preset, or an objective")
    if goal is None:
        goal = goal_for_objective(objective).goal_id
    goal_entry = goal_catalog().goal(goal)
    if chosen_preset is None:
        chosen_preset = catalog.safe_preset(goal)
    if objective is not None and objective != goal_entry.objective:
        raise GoalCatalogError(
            f"goal {goal!r} resolves to objective {goal_entry.objective!r}, not {objective!r}"
        )
    if representation is None:
        if target_row_schema is not None:
            matches = [
                rep.representation_id
                for rep in goal_catalog().representations
                if rep.row_schema == target_row_schema
            ]
            representation = matches[0] if matches else target_row_schema
        elif preset is not None:
            representation = chosen_preset.representation_id
        else:
            representation = goal_entry.default_representation
    elif target_row_schema is not None:
        _, expected_row, _, _ = resolve_goal(goal, representation)
        if expected_row != target_row_schema:
            raise GoalCatalogError(
                f"representation {representation!r} resolves to row schema "
                f"{expected_row!r}, not {target_row_schema!r}"
            )
    objective_kind, row_schema, recipe_library_id, _ = resolve_goal(goal, representation)

    base_segmentation = chosen_preset.segmentation
    base_construction = chosen_preset.construction
    base_curation = chosen_preset.curation
    base_review = chosen_preset.review_policy

    if balance_mode is not None:
        if balance_mode not in SURFACE_BALANCE_MODES:
            raise GoalCatalogError(
                f"balance mode {balance_mode!r} is not one of "
                f"{sorted(SURFACE_BALANCE_MODES)!r}"
            )
        balance_mode = SURFACE_BALANCE_MODES[balance_mode]
    if review_policy is not None and review_policy not in REVIEW_POLICY_OPTIONS:
        raise GoalCatalogError(f"review policy must be one of {list(REVIEW_POLICY_OPTIONS)!r}")
    if require_review is not None:
        implied = "required" if require_review else "none"
        if review_policy is not None and review_policy != implied:
            raise GoalCatalogError(
                f"require_review={require_review!r} conflicts with review_policy "
                f"{review_policy!r}"
            )
        review_policy = implied

    try:
        segmentation = SegmentationSettings(
            strategy=_pick(strategy, base_segmentation.strategy),
            size=_pick(size, base_segmentation.size),
            overlap=_pick(overlap, base_segmentation.overlap),
        )
        construction = ConstructionSettings(
            split_ratio_ppm=_pick(split_ratio_ppm, base_construction.split_ratio_ppm),
            require_review=(_pick(review_policy, base_review) == "required"),
            consumer_profile=_pick(consumer_profile, base_construction.consumer_profile),
        )
        curation = CurationDefaults(
            minimum_target_characters=_pick(
                minimum_target_characters, base_curation.minimum_target_characters
            ),
            balance_mode=_pick(balance_mode, base_curation.balance_mode),
            maximum_records_per_primary_source=(
                base_curation.maximum_records_per_primary_source
                if maximum_records_per_primary_source is None and balance_mode is None
                else maximum_records_per_primary_source
            ),
            evaluation_ratio_ppm=_pick(evaluation_ratio_ppm, base_curation.evaluation_ratio_ppm),
            evaluation_required=_pick(evaluation_required, base_curation.evaluation_required),
            split_seed=_pick(split_seed, base_curation.split_seed),
        )
        assert_compile_combination(
            objective_kind, row_schema, profile=construction.consumer_profile
        )
    except ValidationError as exc:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise GoalCatalogError(f"recipe settings are invalid: {detail}") from exc
    except (ValueError, TypeError) as exc:
        raise GoalCatalogError(f"recipe settings are invalid: {exc}") from exc
    except Exception as exc:  # TaxonomyError
        message = getattr(exc, "message", str(exc))
        raise GoalCatalogError(f"recipe settings are not compilable: {message}") from exc

    effective = {
        "objective": objective_kind,
        "row_schema": row_schema,
        "recipe_library_id": recipe_library_id,
        "segmentation": segmentation.model_dump(mode="json"),
        "construction": construction.model_dump(mode="json"),
        "curation": curation.model_dump(mode="json"),
        "review_policy": "required" if construction.require_review else "none",
    }
    return ResolvedRecipeSettings(
        goal_id=goal,
        preset_id=None if preset is None else chosen_preset.preset_id,
        representation_id=representation,
        **effective,
        settings_digest=canonical_digest(effective),
    )


__all__ = [
    "RECIPE_PRESET_DATA_NAME",
    "SAFE_PRESET_NAME",
    "SURFACE_BALANCE_MODES",
    "ConstructionSettings",
    "PresetCatalog",
    "RecipeDefaults",
    "RecipePreset",
    "ResolvedRecipeSettings",
    "SegmentationSettings",
    "discover_presets",
    "parse_preset_catalog",
    "preset_catalog",
    "preset_catalog_json",
    "recipe_defaults",
    "resolve_recipe_settings",
]
