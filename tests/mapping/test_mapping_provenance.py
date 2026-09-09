"""Phase 7.5: mapping confirmation, catalog binding, and independent replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.errors import MappingError
from veriformis.mapping import execute_mapping, mapping_confirmation_digest
from veriformis.mapping.capture import capture_jsonl
from veriformis.mapping.models import FieldMapping, MappingPlan
from veriformis.mapping.result import MappingRecipe
from veriformis.pipeline import PipelineService

SERVICE = PipelineService()


def test_confirmation_does_not_reuse_against_a_different_file(tmp_path: Path) -> None:
    first = tmp_path / "a.jsonl"
    first.write_text('{"text":"Alpha"}\n{"text":"Beta"}\n', encoding="utf-8")
    second = tmp_path / "b.jsonl"
    second.write_text('{"text":"Gamma"}\n{"text":"Delta"}\n', encoding="utf-8")
    detected = SERVICE.detect_mapping(first, source_root=tmp_path)
    proposal = detected["proposals"][0]
    workspace = tmp_path / "ws"
    SERVICE.parse([second], workspace, source_root=tmp_path, mode="dataset-row")
    with pytest.raises(MappingError, match="not confirmed"):
        SERVICE.map_rows(
            workspace,
            goal=proposal["goal_id"],
            representation=proposal["representation_id"],
            mapping_plan=proposal,
        )


@pytest.mark.parametrize("values", [("Alpha café", "Beta café"), ("café", "cafe\u0301")])
def test_independent_replay_matches_imported_record_ids(tmp_path: Path, values) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text("".join(json.dumps({"text": value}) + "\n" for value in values), encoding="utf-8")
    capture = capture_jsonl(source, logical_path="rows.jsonl")
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=(("rows.jsonl", capture.row_source.sha256),),
    )
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
    from veriformis.identity import derive_source_id

    source_id = derive_source_id("rows.jsonl", capture.row_source.sha256)
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    first = execute_mapping(plan, capture, source_id=source_id, recipe=recipe)
    replay = execute_mapping(plan, capture, source_id=source_id, recipe=recipe)
    assert tuple(item.record_id for item in first) == tuple(
        item.record_id for item in replay
    )
    from veriformis.mapping.finish import exact_imported_fingerprint

    assert len({exact_imported_fingerprint(record) for record in first}) == 2
    assert first[0].fields[0].evidence.kind == "mapped_value"
    assert "chk-" not in first[0].fields[0].evidence.evidence_id


def test_silent_mapping_edit_cannot_reuse_a_prior_recipe(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text('{"text":"Alpha"}\n', encoding="utf-8")
    capture = capture_jsonl(source, logical_path="rows.jsonl")
    from veriformis.identity import derive_source_id

    source_id = derive_source_id("rows.jsonl", capture.row_source.sha256)
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=(("rows.jsonl", capture.row_source.sha256),),
    )
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    swapped = [FieldMapping.create(source_path="other", target_key="text")]
    swapped_confirm = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=swapped,
        source_digests=(("rows.jsonl", capture.row_source.sha256),),
    )
    swapped_plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=swapped_confirm,
        field_mappings=swapped,
    )
    swapped_recipe = MappingRecipe.create(plan=swapped_plan, source_ids=(source_id,))
    assert swapped_recipe.recipe_id != recipe.recipe_id
    assert swapped_plan.mapping_plan_id != plan.mapping_plan_id


def test_required_import_review_refuses_instead_of_silently_accepting(tmp_path: Path) -> None:
    from veriformis.identity import derive_source_id
    from veriformis.workspace import Workspace

    source = tmp_path / "rows.jsonl"
    source.write_text('{"text":"Exact source value"}\n', encoding="utf-8")
    proposed = SERVICE.detect_mapping(source, source_root=tmp_path)["proposals"][0]
    fields = tuple(FieldMapping.model_validate(item) for item in proposed["field_mappings"])
    plan = MappingPlan.create(
        goal_id=proposed["goal_id"], representation_id=proposed["representation_id"],
        row_schema=proposed["row_schema"], container_kind="jsonl",
        confirmation_digest=proposed["confirmation_digest"], field_mappings=fields,
        review_policy="required",
    )
    capture = capture_jsonl(source, logical_path=source.name)
    source_id = derive_source_id(source.name, capture.row_source.sha256)
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    with pytest.raises(MappingError, match="no durable review receipt"):
        execute_mapping(plan, capture, source_id=source_id, recipe=recipe)
    workspace = tmp_path / "workspace"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    before = Workspace.open(workspace).head_id
    with pytest.raises(MappingError, match="no durable review receipt"):
        SERVICE.map_rows(workspace, goal=plan.goal_id, representation=plan.representation_id, mapping_plan=plan)
    assert Workspace.open(workspace).head_id == before
