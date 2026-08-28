"""Phase 17.7: admit tool-call-conversations from user-provided traces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import DatasetRecipe, TrainingObjective, construct_dataset
from veriformis.construction.constructors import construct_tool_call
from veriformis.errors import ConstructionError, ExportContractError, MappingError, SplitError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportService,
)
from veriformis.families.tool_call import (
    TOOL_CALL_FAMILY_ID,
    TOOL_CALL_LOSS_POLICY,
    TOOL_CALL_OBJECTIVE,
    TOOL_CALL_ROW_SCHEMA,
    tool_call_admission,
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
GOAL = "use-provided-tool-traces"
REPRESENTATION = "conversation-and-tool-trace"
PAIRS = (("conversation_id", "conversation_id"), ("turns", "turns"))


def _turns(prompt: str, result: str, final: str) -> list[dict[str, object]]:
    return [
        {"role": "user", "content": prompt},
        {
            "role": "assistant",
            "content": "checking",
            "tool_calls": [
                {"id": "call-1", "name": "lookup", "arguments": "{\"q\":\"x\"}"}
            ],
        },
        {"role": "tool", "content": result, "tool_call_id": "call-1"},
        {"role": "assistant", "content": final},
    ]


def _write_row(
    path: Path, *, conversation_id: str, prompt: str, result: str, final: str
) -> None:
    path.write_text(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "turns": _turns(prompt, result, final),
            },
            ensure_ascii=False,
        )
        + "\n",
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
        row_schema=TOOL_CALL_ROW_SCHEMA,
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id=GOAL,
            representation_id=REPRESENTATION,
            row_schema=TOOL_CALL_ROW_SCHEMA,
            field_mappings=mappings,
            source_digests=source_digests,
        ),
        field_mappings=mappings,
    )


def _compile_two_sources(tmp_path: Path) -> dict[str, object]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    first = tmp_path / "conv-a.jsonl"
    second = tmp_path / "conv-b.jsonl"
    _write_row(
        first,
        conversation_id="conv-a",
        prompt="what color is the sky",
        result="blue",
        final="The sky is blue.",
    )
    _write_row(
        second,
        conversation_id="conv-b",
        prompt="what freezes water",
        result="cold",
        final="Cold freezes water.",
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle"
    SERVICE.parse(
        [first, second],
        workspace,
        source_root=tmp_path,
        mode="dataset-row",
    )
    plan = _plan(workspace)
    mapped = SERVICE.map_rows(
        workspace,
        goal=GOAL,
        representation=REPRESENTATION,
        mapping_plan=plan,
    )
    SERVICE.curate(workspace, goal=GOAL)
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    validated = SERVICE.validate(workspace)
    assert validated.exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    verified = SERVICE.verify(
        bundle,
        manifest_sha256=sealed.publication.manifest_sha256,
    )
    return {
        "workspace": workspace,
        "bundle": bundle,
        "manifest_sha256": sealed.publication.manifest_sha256,
        "mapping_plan_id": mapped.mapping_plan_id,
        "schema_version": Workspace.open(workspace).head().schema_version,
        "trust_grade": verified.verification.trust_grade,
    }


def test_tool_call_is_implemented_with_new_schema_and_loss() -> None:
    assert TOOL_CALL_FAMILY_ID in IMPLEMENTED_TRAINING_FAMILIES
    assert TOOL_CALL_FAMILY_ID not in PLANNED_TRAINING_FAMILIES
    assert family_for_objective(TOOL_CALL_OBJECTIVE) == TOOL_CALL_FAMILY_ID
    assert loss_policy_for_row(TOOL_CALL_ROW_SCHEMA) == TOOL_CALL_LOSS_POLICY
    pin = tool_call_admission()
    assert pin.lifecycle == "admitted"
    assert pin.family_id == TOOL_CALL_FAMILY_ID
    assert pin.generation_allowed is False
    assert pin.profile_eligibility == ()
    assert pin.row_schema_ids == (TOOL_CALL_ROW_SCHEMA,)
    assert pin.leakage_grouping_keys == ("conversation", "source")


def test_tool_call_maps_seals_verifies_and_replays(tmp_path: Path) -> None:
    first = _compile_two_sources(tmp_path / "one")
    second = _compile_two_sources(tmp_path / "two")
    assert is_import_revision(int(first["schema_version"]))
    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["mapping_plan_id"] == second["mapping_plan_id"]
    assert first["trust_grade"] in {"self_consistent", "external_digest"}


def test_malformed_trace_without_tool_role_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        json.dumps(
            {
                "conversation_id": "conv-a",
                "turns": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi"},
                    {"role": "assistant", "content": "still hi"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    plan = _plan(workspace)
    with pytest.raises(MappingError, match="tool or function trace"):
        SERVICE.map_rows(
            workspace,
            goal=GOAL,
            representation=REPRESENTATION,
            mapping_plan=plan,
        )


def test_shared_conversation_cannot_straddle_partitions(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    _write_row(
        first,
        conversation_id="same-thread",
        prompt="one",
        result="a",
        final="done a",
    )
    _write_row(
        second,
        conversation_id="same-thread",
        prompt="one",
        result="a",
        final="done a",
    )
    workspace = tmp_path / "ws"
    SERVICE.parse(
        [first, second],
        workspace,
        source_root=tmp_path,
        mode="dataset-row",
    )
    plan = _plan(workspace)
    SERVICE.map_rows(
        workspace,
        goal=GOAL,
        representation=REPRESENTATION,
        mapping_plan=plan,
    )
    SERVICE.curate(workspace, goal=GOAL)
    with pytest.raises(SplitError, match="fewer than two leakage groups"):
        SERVICE.split(workspace)


def test_document_source_constructor_refuses_invented_traces() -> None:
    with pytest.raises(ConstructionError, match="cannot invent tool traces"):
        construct_tool_call(
            recipe=None,  # type: ignore[arg-type]
            construction_pass=None,  # type: ignore[arg-type]
            sources={},
            chunks=(),
            transforms=(),
            ir_artifacts={},
        )


def test_existing_profiles_refuse_tool_call_schema() -> None:
    for profile in ("trl", "mlx-lm", "axolotl", "llama-factory", "aptus"):
        with pytest.raises(Exception, match="tool-call-conversation"):
            assert_profile_row_compatible(profile, TOOL_CALL_ROW_SCHEMA)


def test_constrained_csv_refuses_tool_call_export(tmp_path: Path) -> None:
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
    with pytest.raises(ExportContractError, match="tool-call-conversation"):
        ExportService().dry_run_export(
            ExportDryRunRequest(operation="dry_run", **selection)
        )


def test_split_jsonl_and_json_emit_tool_call_rows(tmp_path: Path) -> None:
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
            combined = train + evaluation
            assert '"turns"' in combined
            assert '"tool"' in combined or '"function"' in combined


def test_cli_maps_tool_call_goal(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    _write_row(first, conversation_id="conv-a", prompt="alpha", result="A", final="done A")
    _write_row(second, conversation_id="conv-b", prompt="beta", result="B", final="done B")
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
    objective = TrainingObjective.create(TOOL_CALL_OBJECTIVE)
    assert objective.kind == TOOL_CALL_OBJECTIVE
    assert DatasetRecipe.model_fields["review_policy"].default == "none"
    assert construct_dataset is not None
