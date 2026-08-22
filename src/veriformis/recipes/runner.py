"""Execute a versioned pipeline specification through PipelineService only."""

from __future__ import annotations

from typing import Any

from dataclasses import dataclass
from pathlib import Path

from veriformis.pipeline.service import PipelineService, StageOutcome
from veriformis.recipes.library import RECIPE_LIBRARY_IDS
from veriformis.recipes.pipeline_spec import PipelineSpec, PipelineSpecError
from veriformis.workspace import Workspace


@dataclass(frozen=True)
class PipelineRunResult:
    outcomes: tuple[StageOutcome, ...]
    workspace: Path
    bundle: Path | None = None


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_bool(value: Any) -> bool | None:
    return None if value is None else bool(value)


def run_pipeline_spec(
    spec: PipelineSpec,
    *,
    service: PipelineService | None = None,
) -> PipelineRunResult:
    """Run ordered stages. Construct may use recipe_library_id for objective defaults."""
    pipeline = service or PipelineService()
    outcomes: list[StageOutcome] = []
    bundle: Path | None = None
    for stage in spec.ordered_stage_names():
        config = dict(spec.stages.get(stage) or {})
        if stage == "parse":
            outcomes.append(
                pipeline.parse(
                    list(spec.source_paths),
                    spec.workspace,
                    source_root=spec.source_root,
                )
            )
        elif stage == "clean":
            outcomes.append(
                pipeline.clean(
                    spec.workspace,
                    rules=str(config.get("rules", "")),
                    custom=str(config.get("custom", "")),
                )
            )
        elif stage == "chunk":
            outcomes.append(
                pipeline.chunk(
                    spec.workspace,
                    strategy=_optional_str(config.get("strategy")),
                    size=_optional_int(config.get("size")),
                    overlap=_optional_int(config.get("overlap")),
                    goal=_optional_str(config.get("goal")),
                    preset=_optional_str(config.get("preset")),
                )
            )
        elif stage == "construct":
            objective = config.get("objective")
            goal = _optional_str(config.get("goal"))
            preset = _optional_str(config.get("preset"))
            if spec.recipe_library_id:
                if spec.recipe_library_id not in RECIPE_LIBRARY_IDS:
                    raise PipelineSpecError(
                        f"unknown recipe_library_id {spec.recipe_library_id!r}; "
                        f"expected one of {list(RECIPE_LIBRARY_IDS)!r}"
                    )
                library_objective = spec.recipe_library_id.split(".", 1)[0]
                if objective is not None and objective != library_objective:
                    raise PipelineSpecError(
                        f"construct objective {objective!r} conflicts with "
                        f"recipe_library_id {spec.recipe_library_id!r}"
                    )
                # Always pass the library objective so a conflicting stage goal or
                # preset fails closed in resolution instead of being ignored.
                objective = library_objective
            if objective is None and goal is None and preset is None:
                raise PipelineSpecError(
                    "construct stage requires objective, goal, preset, or top-level "
                    "recipe_library_id"
                )
            if objective is not None and (not isinstance(objective, str) or not objective):
                raise PipelineSpecError("construct objective must be a non-empty string")
            outcomes.append(
                pipeline.construct(
                    spec.workspace,
                    objective=objective,
                    goal=goal,
                    preset=preset,
                    representation=_optional_str(config.get("representation")),
                    source=list(config["source"])
                    if isinstance(config.get("source"), list)
                    else None,
                    target_row_schema=config.get("target_row_schema"),
                    split_ratio_ppm=_optional_int(config.get("split_ratio_ppm")),
                    require_review=_optional_bool(config.get("require_review")),
                    consumer_profile=_optional_str(config.get("consumer_profile")),
                )
            )
        elif stage == "curate":
            evaluation_required = _optional_bool(config.get("evaluation_required"))
            if evaluation_required is None and "allow_empty_evaluation" in config:
                # YAML may use allow_empty_evaluation like the CLI flag sense.
                evaluation_required = not bool(config["allow_empty_evaluation"])
            outcomes.append(
                pipeline.curate(
                    spec.workspace,
                    goal=_optional_str(config.get("goal")),
                    preset=_optional_str(config.get("preset")),
                    minimum_target_characters=_optional_int(
                        config.get("minimum_target_characters")
                    ),
                    balance_mode=_optional_str(config.get("balance_mode")),
                    maximum_records_per_primary_source=config.get(
                        "maximum_records_per_primary_source"
                    ),
                    evaluation_ratio_ppm=_optional_int(config.get("evaluation_ratio_ppm")),
                    evaluation_required=evaluation_required,
                    split_seed=_optional_str(config.get("split_seed")),
                    instruction=config.get("instruction"),
                )
            )
        elif stage == "split":
            outcomes.append(pipeline.split(spec.workspace))
        elif stage == "format":
            outcomes.append(pipeline.format(spec.workspace))
        elif stage == "validate":
            outcome = pipeline.validate(spec.workspace)
            outcomes.append(outcome)
            if outcome.exit_status != 0:
                return PipelineRunResult(
                    outcomes=tuple(outcomes),
                    workspace=spec.workspace,
                    bundle=None,
                )
        elif stage == "seal":
            out = config.get("out")
            if not isinstance(out, str) or not out.strip():
                raise PipelineSpecError("seal stage requires out path")
            out_path = Path(out)
            if not out_path.is_absolute():
                out_path = (spec.workspace.parent / out_path).resolve()
            seal_outcome = pipeline.seal(spec.workspace, out_path)
            outcomes.append(seal_outcome)
            bundle = out_path
        else:
            raise PipelineSpecError(f"unsupported pipeline stage {stage!r}")
    # Touch workspace to prove it exists for callers.
    if spec.workspace.exists():
        Workspace.open(spec.workspace)
    return PipelineRunResult(
        outcomes=tuple(outcomes),
        workspace=spec.workspace,
        bundle=bundle,
    )
