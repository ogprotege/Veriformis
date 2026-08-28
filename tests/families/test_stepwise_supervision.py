"""Phase 17.8: admit stepwise-supervision from user-provided steps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import DatasetRecipe, TrainingObjective, construct_dataset
from veriformis.construction.constructors import construct_stepwise
from veriformis.errors import ConstructionError, ExportContractError, MappingError, SplitError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportService,
)
from veriformis.families.stepwise import (
    STEPWISE_FAMILY_ID,
    STEPWISE_LOSS_POLICY,
    STEPWISE_OBJECTIVE,
    STEPWISE_ROW_SCHEMA,
    stepwise_admission,
)
from veriformis.mapping import FieldMapping, MappingPlan, mapping_confirmation_digest
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import (
    IMPLEMENTED_TRAINING_FAMILIES,
    PLANNED_TRAINING_FAMILIES,
    assert_profile_row_compatible,
    family_for_objective,
    loss_policy_for_row,
)
from veriformis.workspace import Workspace, is_import_revision


RUNNER = CliRunner()
SERVICE = PipelineService()
GOAL = "use-provided-steps"
REPRESENTATION = "prompt-and-steps"
PAIRS = (("prompt", "prompt"), ("steps", "steps"))


def _write_row(path: Path, *, prompt: str, steps: list[str]) -> None:
    path.write_text(
        json.dumps({"prompt": prompt, "steps": steps}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _plan(workspace: Path) -> MappingPlan:
    head = Workspace.open(workspace).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in head.sources.values()
    )
    mappings = [
        FieldMapping.create(source_path=source, target_key=target)
        for source, target in PAIRS
    ]
    return MappingPlan.create(
        goal_id=GOAL,
        representation_id=REPRESENTATION,
        row_schema=STEPWISE_ROW_SCHEMA,
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id=GOAL,
            representation_id=REPRESENTATION,
            row_schema=STEPWISE_ROW_SCHEMA,
            field_mappings=mappings,
            source_digests=source_digests,
        ),
        field_mappings=mappings,
    )


def _compile_two_sources(tmp_path: Path) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    _write_row(first, prompt="add two and two", steps=["write 2+2", "the sum is 4"])
    _write_row(
        second, prompt="name a primary color", steps=["consider the set", "red"]
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle"
    SERVICE.parse([first, second], workspace, source_root=tmp_path, mode="dataset-row")
    plan = _plan(workspace)
    mapped = SERVICE.map_rows(
        workspace, goal=GOAL, representation=REPRESENTATION, mapping_plan=plan
    )
    SERVICE.curate(workspace, goal=GOAL)
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    validated = SERVICE.validate(workspace)
    assert validated.exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    verified = SERVICE.verify(
        bundle, manifest_sha256=sealed.publication.manifest_sha256
    )
    return {
        "workspace": workspace,
        "bundle": bundle,
        "manifest_sha256": sealed.publication.manifest_sha256,
        "mapping_plan_id": mapped.mapping_plan_id,
        "schema_version": Workspace.open(workspace).head().schema_version,
        "trust_grade": verified.verification.trust_grade,
    }


def test_stepwise_is_implemented_with_new_schema_and_loss() -> None:
    assert STEPWISE_FAMILY_ID in IMPLEMENTED_TRAINING_FAMILIES
    assert STEPWISE_FAMILY_ID not in PLANNED_TRAINING_FAMILIES
    assert family_for_objective(STEPWISE_OBJECTIVE) == STEPWISE_FAMILY_ID
    assert loss_policy_for_row(STEPWISE_ROW_SCHEMA) == STEPWISE_LOSS_POLICY
    pin = stepwise_admission()
    assert pin.lifecycle == "admitted"
    assert pin.generation_allowed is False
    assert pin.profile_eligibility == ()
    assert pin.row_schema_ids == (STEPWISE_ROW_SCHEMA,)
    assert pin.leakage_grouping_keys == ("shared-prompt", "source")


def test_stepwise_maps_seals_verifies_and_replays(tmp_path: Path) -> None:
    first = _compile_two_sources(tmp_path / "one")
    second = _compile_two_sources(tmp_path / "two")
    assert is_import_revision(int(first["schema_version"]))
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["mapping_plan_id"] == second["mapping_plan_id"]
    assert first["trust_grade"] in {"self_consistent", "external_digest"}


def test_empty_or_short_steps_are_refused(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        json.dumps({"prompt": "add", "steps": ["only one"]}) + "\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    plan = _plan(workspace)
    with pytest.raises(MappingError, match="at least two"):
        SERVICE.map_rows(
            workspace, goal=GOAL, representation=REPRESENTATION, mapping_plan=plan
        )


def test_shared_prompt_cannot_straddle_partitions(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    _write_row(first, prompt="same prompt", steps=["first", "last a"])
    _write_row(second, prompt="same prompt", steps=["first", "last a"])
    workspace = tmp_path / "ws"
    SERVICE.parse([first, second], workspace, source_root=tmp_path, mode="dataset-row")
    plan = _plan(workspace)
    SERVICE.map_rows(
        workspace, goal=GOAL, representation=REPRESENTATION, mapping_plan=plan
    )
    SERVICE.curate(workspace, goal=GOAL)
    with pytest.raises(SplitError, match="fewer than two leakage groups"):
        SERVICE.split(workspace)


def test_document_source_constructor_refuses_invented_steps() -> None:
    with pytest.raises(ConstructionError, match="cannot invent stepwise traces"):
        construct_stepwise(
            recipe=None,  # type: ignore[arg-type]
            construction_pass=None,  # type: ignore[arg-type]
            sources={},
            chunks=(),
            transforms=(),
            ir_artifacts={},
        )


def test_existing_profiles_refuse_stepwise_schema() -> None:
    for profile in ("trl", "mlx-lm", "axolotl", "llama-factory", "aptus"):
        with pytest.raises(Exception, match="stepwise-trace"):
            assert_profile_row_compatible(profile, STEPWISE_ROW_SCHEMA)


def test_constrained_csv_refuses_stepwise_export(tmp_path: Path) -> None:
    compiled = _compile_two_sources(tmp_path)
    selection = {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(compiled["bundle"]),
        "container_id": "constrained-csv",
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": compiled["manifest_sha256"],
        "overwrite_policy": "refuse",
    }
    with pytest.raises(ExportContractError, match="stepwise-trace"):
        ExportService().dry_run_export(
            ExportDryRunRequest(operation="dry_run", **selection)
        )


def test_split_jsonl_and_json_emit_stepwise_rows(tmp_path: Path) -> None:
    compiled = _compile_two_sources(tmp_path)
    service = ExportService()
    for container_id in ("split-jsonl-directory", "json"):
        destination = tmp_path / container_id
        selection = {
            "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
            "bundle": str(compiled["bundle"]),
            "container_id": container_id,
            "container_version": 1,
            "consumer_id": None,
            "consumer_profile_version": None,
            "source_trust_policy": "require_external_digest",
            "expected_manifest_sha256": compiled["manifest_sha256"],
            "overwrite_policy": "refuse",
        }
        dry = service.dry_run_export(ExportDryRunRequest(operation="dry_run", **selection))
        plan_id = getattr(dry, "export_plan_id", None) or getattr(dry.plan, "export_plan_id")
        from veriformis.exports import ExportExecuteRequest

        service.execute_export(
            ExportExecuteRequest(
                operation="execute",
                destination_root=str(destination),
                expected_export_plan_id=plan_id,
                **selection,
            )
        )
        if container_id == "split-jsonl-directory":
            train = (destination / "data" / "train.jsonl").read_text(encoding="utf-8")
            evaluation = (destination / "data" / "evaluation.jsonl").read_text(
                encoding="utf-8"
            )
            assert '"steps"' in train + evaluation


def test_cli_maps_stepwise_goal(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    _write_row(first, prompt="alpha", steps=["a1", "a2"])
    _write_row(second, prompt="beta", steps=["b1", "b2"])
    workspace = tmp_path / "ws"
    parse = RUNNER.invoke(
        app,
        [
            "parse",
            str(first),
            str(second),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
            "--mode",
            "dataset-row",
        ],
    )
    assert parse.exit_code == 0, parse.output
    plan = _plan(workspace)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    mapped = RUNNER.invoke(
        app,
        [
            "map",
            str(workspace),
            "--goal",
            GOAL,
            "--representation",
            REPRESENTATION,
            "--plan",
            str(plan_path),
        ],
    )
    assert mapped.exit_code == 0, mapped.output


def test_named_recipe_exists_but_document_source_cannot_construct() -> None:
    objective = TrainingObjective.create(STEPWISE_OBJECTIVE)
    assert objective.kind == STEPWISE_OBJECTIVE
    assert DatasetRecipe.model_fields["review_policy"].default == "none"
    assert construct_dataset is not None
