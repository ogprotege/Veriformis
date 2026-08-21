"""Named deterministic recipe and finished-plan builders."""

from __future__ import annotations

from typing import Any, Mapping

from veriformis.construction import (
    ConstructionPass,
    DatasetRecipe,
    SegmentationPolicy,
    TrainingObjective,
)
from veriformis.datasets import (
    CurationPolicy,
    FinishedDatasetPlan,
    SerializationPlan,
    SplitPolicy,
)
from veriformis.errors import ConstructionError, TaxonomyError
from veriformis.taxonomy import (
    CANONICAL_CONSUMER_PROFILE,
    assert_compile_combination,
    default_row_schema,
)

RECIPE_LIBRARY_IDS: tuple[str, ...] = (
    "full_text.default",
    "continuation.default",
    "section_reconstruction.default",
    "before_after_transformation.default",
    "structured_field.default",
)

_OBJECTIVE_BY_RECIPE = {
    "full_text.default": "full_text",
    "continuation.default": "continuation",
    "section_reconstruction.default": "section_reconstruction",
    "before_after_transformation.default": "before_after_transformation",
    "structured_field.default": "structured_field",
}

def list_named_recipes() -> tuple[dict[str, str], ...]:
    """Return stable metadata for every library recipe id."""
    return tuple(
        {
            "recipe_library_id": recipe_id,
            "objective": _OBJECTIVE_BY_RECIPE[recipe_id],
            "target_row_schema": default_row_schema(
                _OBJECTIVE_BY_RECIPE[recipe_id]
            ),
        }
        for recipe_id in RECIPE_LIBRARY_IDS
    )


def build_named_recipe(
    recipe_library_id: str,
    *,
    source_ids: tuple[str, ...],
    cleaning_config_digest: str,
    segmentation: SegmentationPolicy | Mapping[str, Any] | None = None,
    split_ratio_ppm: int = 500_000,
    require_review: bool = False,
    target_row_schema: str | None = None,
    consumer_profile: str = CANONICAL_CONSUMER_PROFILE,
) -> DatasetRecipe:
    """Build one versioned DatasetRecipe from a library id and workspace facts."""
    if recipe_library_id not in _OBJECTIVE_BY_RECIPE:
        raise ConstructionError(
            f"unknown recipe library id {recipe_library_id!r}; "
            f"expected one of {list(RECIPE_LIBRARY_IDS)!r}"
        )
    objective_kind = _OBJECTIVE_BY_RECIPE[recipe_library_id]
    try:
        row_schema = (
            default_row_schema(objective_kind)
            if target_row_schema is None
            else target_row_schema
        )
        assert_compile_combination(
            objective_kind,
            row_schema,
            profile=consumer_profile,
        )
    except TaxonomyError as exc:
        raise ConstructionError(exc.message) from exc
    if segmentation is None:
        if objective_kind == "section_reconstruction":
            segmentation = SegmentationPolicy(
                schema_version="veriformis.segmentation-policy/v1",
                strategy="structure",
                size=1000,
                overlap=100,
            )
        else:
            segmentation = SegmentationPolicy(
                schema_version="veriformis.segmentation-policy/v1",
                strategy="paragraph",
                size=1000,
                overlap=100,
            )
    elif not isinstance(segmentation, SegmentationPolicy):
        segmentation = SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy=str(segmentation["strategy"]),
            size=int(segmentation["size"]),
            overlap=int(segmentation["overlap"]),
        )
    parameters = (
        {"split_ratio_ppm": split_ratio_ppm}
        if objective_kind == "continuation"
        else None
    )
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind=objective_kind,
        parameters=parameters,
    )
    try:
        return DatasetRecipe.create(
            objective=TrainingObjective.create(objective_kind),
            source_ids=source_ids,
            cleaning_config_digest=cleaning_config_digest,
            segmentation=segmentation,
            passes=(construction_pass,),
            target_row_schema=row_schema,
            review_policy="required" if require_review else "none",
        )
    except (TypeError, ValueError) as exc:
        raise ConstructionError(f"invalid dataset recipe: {exc}") from exc


def build_default_finished_plan(
    *,
    recipe_id: str,
    construction_result_id: str,
    target_row_schema: str,
    minimum_target_characters: int = 1,
    balance_mode: str = "none",
    maximum_records_per_primary_source: int | None = None,
    evaluation_ratio_ppm: int = 500_000,
    evaluation_required: bool = True,
    split_seed: str = "veriformis-v1",
    instruction: str | None = None,
) -> FinishedDatasetPlan:
    """Build a finished-dataset plan with library defaults."""
    curation_policy = CurationPolicy.create(
        minimum_target_characters=minimum_target_characters,
        balance_mode=balance_mode,  # type: ignore[arg-type]
        maximum_records_per_primary_source=maximum_records_per_primary_source,
    )
    split_policy = SplitPolicy.create(
        evaluation_ratio_ppm=evaluation_ratio_ppm,
        evaluation_required=evaluation_required,
        seed=split_seed,
    )
    serialization_plan = SerializationPlan.create(
        row_schema=target_row_schema,
        instruction_text=instruction,
    )
    return FinishedDatasetPlan.create(
        recipe_id=recipe_id,
        construction_result_id=construction_result_id,
        curation_policy=curation_policy,
        split_policy=split_policy,
        serialization_plan=serialization_plan,
    )
