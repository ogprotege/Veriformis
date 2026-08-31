"""Named deterministic recipes, statistics, and YAML pipeline execution."""

from veriformis.recipes.library import (
    RECIPE_LIBRARY_IDS,
    build_named_recipe,
    list_named_recipes,
)
from veriformis.recipes.pipeline_spec import (
    PipelineSpec,
    load_pipeline_spec,
    pipeline_spec_from_dict,
)
from veriformis.recipes.statistics import (
    DatasetStatistics,
    measure_construction_statistics,
    measure_finished_statistics,
)

__all__ = [
    "RECIPE_LIBRARY_IDS",
    "DatasetStatistics",
    "PipelineSpec",
    "build_named_recipe",
    "list_named_recipes",
    "load_pipeline_spec",
    "measure_construction_statistics",
    "measure_finished_statistics",
    "pipeline_spec_from_dict",
    "run_pipeline_spec",
]


def __getattr__(name: str):
    if name == "run_pipeline_spec":
        from veriformis.recipes.runner import run_pipeline_spec

        return run_pipeline_spec
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
