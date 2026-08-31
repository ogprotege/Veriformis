"""Execute and resume a confirmed project spec through PipelineService."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from veriformis.automation.inspect import (
    DATASET_ROW_STAGES,
    ProjectLock,
    create_project_lock,
    pipeline_for_spec,
    resolve_spec_ref,
    spec_digest,
)
from veriformis.automation.spec import ProjectSpec
from veriformis.contracts import PROJECT_SPEC_DIAGNOSTIC_SCHEMA_ID
from veriformis.errors import ProjectSpecError
from veriformis.pipeline.service import PipelineService, StageOutcome
from veriformis.recipes.pipeline_spec import PipelineSpec
from veriformis.recipes.runner import PipelineRunResult, run_pipeline_spec


DIAGNOSTIC_SCHEMA_ID = PROJECT_SPEC_DIAGNOSTIC_SCHEMA_ID
DOCUMENT_SOURCE_MODE = "document-source"
DATASET_ROW_MODE = "dataset-row"
MIXED_MODE = "mixed"


def project_spec_diagnostic(
    exc: BaseException,
    *,
    spec_id: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_id": DIAGNOSTIC_SCHEMA_ID,
        "code": getattr(exc, "code", "invalid-data"),
        "message": getattr(exc, "message", str(exc)),
        "spec_id": spec_id,
        "stage": stage,
    }
    return json.loads(json.dumps(payload, sort_keys=True))


def load_project_spec_diagnostic(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectSpecError("truncated project spec diagnostic JSON") from exc
    if not isinstance(value, dict):
        raise ProjectSpecError("truncated project spec diagnostic JSON")
    required = ("schema_id", "code", "message")
    missing = [key for key in required if key not in value]
    if missing:
        raise ProjectSpecError("truncated project spec diagnostic JSON")
    if value.get("schema_id") != DIAGNOSTIC_SCHEMA_ID:
        raise ProjectSpecError("truncated project spec diagnostic JSON")
    return value


def _apply_spec_pins(spec: ProjectSpec, pipeline: PipelineSpec) -> PipelineSpec:
    stages = {name: dict(config) for name, config in pipeline.stages.items()}
    if spec.goal_id:
        for name in ("chunk", "construct", "curate"):
            if name in stages and not stages[name].get("goal") and not stages[name].get("objective"):
                stages[name]["goal"] = spec.goal_id
    if spec.preset_id:
        for name in ("chunk", "construct", "curate"):
            if name in stages and not stages[name].get("preset"):
                stages[name]["preset"] = spec.preset_id
    if spec.consumer_profile and "construct" in stages:
        stages["construct"].setdefault("consumer_profile", spec.consumer_profile)
    return replace(pipeline, stages=stages)


def _stage_complete(workspace: Path, stage: str) -> bool:
    from veriformis.workspace import Workspace

    if not workspace.exists():
        return False
    revision = Workspace.open(workspace).head()
    state = revision.stages.get(stage)
    return state is not None and state.status == "complete"


def _filter_incomplete(pipeline: PipelineSpec, skip_complete: bool) -> PipelineSpec | None:
    if not skip_complete:
        return pipeline
    remaining = {
        name: pipeline.stages[name]
        for name in pipeline.ordered_stage_names()
        if not _stage_complete(pipeline.workspace, name)
    }
    if not remaining:
        return None
    return replace(pipeline, stages=remaining)


def _sealed_bundle(pipeline: PipelineSpec) -> Path | None:
    config = pipeline.stages.get("seal") or {}
    out = config.get("out")
    if not isinstance(out, str) or not out.strip():
        return None
    out_path = Path(out)
    if not out_path.is_absolute():
        out_path = (pipeline.workspace.parent / out_path).resolve()
    return out_path if out_path.exists() else None


def _require_success(result: PipelineRunResult) -> PipelineRunResult:
    if result.outcomes and result.outcomes[-1].exit_status != 0:
        outcome = result.outcomes[-1]
        text = " ".join(message.text for message in outcome.messages) or "project spec stage failed"
        raise ProjectSpecError(text)
    return result


def _mapping_plan(spec: ProjectSpec, *, base_dir: Path) -> Any:
    from veriformis.mapping.models import MappingPlan

    if spec.mapping is None or spec.mapping.plan_path is None:
        raise ProjectSpecError("dataset-row execute requires mapping.plan_path")
    path = resolve_spec_ref(spec.mapping.plan_path, base_dir=base_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectSpecError(f"mapping plan is unreadable: {exc}") from exc
    try:
        plan = MappingPlan.model_validate(payload)
    except Exception as exc:
        raise ProjectSpecError("mapping plan is invalid") from exc
    if plan.mapping_plan_id != spec.mapping.mapping_plan_id:
        raise ProjectSpecError(
            "mismatched identity mapping_plan_id: expected "
            f"{spec.mapping.mapping_plan_id} got {plan.mapping_plan_id}"
        )
    if plan.confirmation_digest != spec.mapping.confirmation_digest:
        raise ProjectSpecError(
            "mismatched identity confirmation_digest: expected "
            f"{spec.mapping.confirmation_digest} got {plan.confirmation_digest}"
        )
    return plan


def _row_sources(pipeline: PipelineSpec) -> bool:
    from veriformis.mapping.capture import ROW_SUFFIXES

    suffixes = {path.suffix.lower() for path in pipeline.source_paths}
    return bool(suffixes) and suffixes <= set(ROW_SUFFIXES)


def _run_document_source(
    spec: ProjectSpec,
    pipeline: PipelineSpec,
    *,
    service: PipelineService,
    skip_complete: bool,
) -> PipelineRunResult:
    pinned = _apply_spec_pins(spec, pipeline)
    filtered = _filter_incomplete(pinned, skip_complete)
    if filtered is None:
        return PipelineRunResult(
            outcomes=(),
            workspace=pipeline.workspace,
            bundle=_sealed_bundle(pipeline),
        )
    return _require_success(run_pipeline_spec(filtered, service=service))


def _run_dataset_row(
    spec: ProjectSpec,
    pipeline: PipelineSpec,
    *,
    service: PipelineService,
    skip_complete: bool,
    base_dir: Path,
) -> PipelineRunResult:
    outcomes: list[StageOutcome] = []
    if not (skip_complete and _stage_complete(pipeline.workspace, "parse")):
        outcomes.append(
            service.parse(
                list(pipeline.source_paths),
                pipeline.workspace,
                source_root=pipeline.source_root,
                mode=DATASET_ROW_MODE,
            )
        )
    if not (skip_complete and _stage_complete(pipeline.workspace, "map")):
        plan = _mapping_plan(spec, base_dir=base_dir)
        if spec.goal_id is None:
            raise ProjectSpecError("dataset-row execute requires goal_id")
        if plan.goal_id != spec.goal_id:
            raise ProjectSpecError(
                f"mismatched identity goal_id: expected {spec.goal_id} got {plan.goal_id}"
            )
        outcomes.append(
            service.map_rows(
                pipeline.workspace,
                goal=spec.goal_id,
                representation=plan.representation_id,
                mapping_plan=plan,
            )
        )
    tail_names = [name for name in DATASET_ROW_STAGES if name not in {"parse", "map"}]
    tail_stages = {name: dict(pipeline.stages[name]) for name in tail_names if name in pipeline.stages}
    if not tail_stages:
        return PipelineRunResult(
            outcomes=tuple(outcomes),
            workspace=pipeline.workspace,
            bundle=_sealed_bundle(pipeline),
        )
    tail = _apply_spec_pins(spec, replace(pipeline, stages=tail_stages))
    filtered = _filter_incomplete(tail, skip_complete)
    bundle = _sealed_bundle(pipeline) if skip_complete else None
    if filtered is not None:
        tail_result = _require_success(run_pipeline_spec(filtered, service=service))
        outcomes.extend(tail_result.outcomes)
        bundle = tail_result.bundle
    return PipelineRunResult(
        outcomes=tuple(outcomes),
        workspace=pipeline.workspace,
        bundle=bundle,
    )


def _run_stages(
    spec: ProjectSpec,
    *,
    service: PipelineService,
    skip_complete: bool,
    base_dir: Path,
) -> PipelineRunResult:
    pipeline = pipeline_for_spec(spec, base_dir=base_dir)
    if spec.mode == DOCUMENT_SOURCE_MODE:
        return _run_document_source(
            spec,
            pipeline,
            service=service,
            skip_complete=skip_complete,
        )
    if spec.mode == MIXED_MODE and not _row_sources(pipeline):
        raise ProjectSpecError(
            "mixed execute requires row sources; compile document-source and "
            "dataset-row workspaces separately"
        )
    return _run_dataset_row(
        spec,
        pipeline,
        service=service,
        skip_complete=skip_complete,
        base_dir=base_dir,
    )


def run_project_spec(
    spec: ProjectSpec,
    *,
    service: PipelineService,
    base_dir: Path | None = None,
) -> PipelineRunResult:
    """Execute a confirmed spec. Export is not auto-run."""
    return _run_stages(
        spec,
        service=service,
        skip_complete=False,
        base_dir=base_dir or Path.cwd(),
    )


def resume_project_spec(
    spec: ProjectSpec,
    lock: ProjectLock,
    *,
    service: PipelineService,
    base_dir: Path | None = None,
) -> PipelineRunResult:
    """Resume only when lock, HEAD, and source identities match."""
    from veriformis.workspace import Workspace

    digest = spec_digest(spec)
    if digest != lock.spec_digest:
        raise ProjectSpecError(
            f"mismatched identity spec_digest: expected {lock.spec_digest} got {digest}"
        )
    pipeline = pipeline_for_spec(spec, base_dir=base_dir or Path.cwd())
    store = Workspace.open(pipeline.workspace)
    head = store.head_id
    sources = tuple(sorted(store.head().sources))
    if lock.workspace_head is None:
        raise ProjectSpecError("mismatched identity workspace_head: lock does not pin HEAD")
    if lock.workspace_head != head:
        raise ProjectSpecError(
            f"mismatched identity workspace_head: expected {lock.workspace_head} got {head}"
        )
    pinned = tuple(lock.source_identities or ())
    if not pinned:
        raise ProjectSpecError(
            "mismatched identity source_identities: lock does not pin sources"
        )
    if pinned != sources:
        raise ProjectSpecError(
            "mismatched identity source_identities: expected "
            f"{list(pinned)} got {list(sources)}"
        )
    return _run_stages(
        spec,
        service=service,
        skip_complete=True,
        base_dir=base_dir or Path.cwd(),
    )


def lock_after_workspace(spec: ProjectSpec, workspace: Path) -> ProjectLock:
    from veriformis.workspace import Workspace

    store = Workspace.open(workspace)
    return create_project_lock(
        spec,
        workspace_head=store.head_id,
        source_identities=tuple(sorted(store.head().sources)),
    )
