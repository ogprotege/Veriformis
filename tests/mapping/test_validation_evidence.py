"""Imported validation requires source replay and a complete, bound gate report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.errors import DatasetValidationError, MappingError
from veriformis.identity import derive_id
from veriformis.mapping.finish import (
    FinishedImportPlan, ImportedCurationResult, ImportedGateResult, ImportedRowSet,
    ImportedSplitResult, ImportedValidationReport, validate_imported_dataset,
)
from veriformis.mapping.models import MappingPlan
from veriformis.mapping.result import MappingRecipe, MappingResult
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace


def _case(tmp_path: Path):
    service = PipelineService()
    source = tmp_path / "rows.jsonl"
    source.write_text('{"text":"Alpha exact source record"}\n{"text":"Beta independent source record"}\n', encoding="utf-8")
    proposal = service.detect_mapping(source, source_root=tmp_path)["proposals"][0]
    workspace = tmp_path / "workspace"
    service.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    service.map_rows(workspace, goal=proposal["goal_id"], representation=proposal["representation_id"], mapping_plan=proposal)
    service.curate(workspace)
    service.split(workspace)
    service.format(workspace)
    store = Workspace.open(workspace)
    head = store.head()

    def raw(stage, name):
        return store.read_artifact(head.stages[stage].outputs[name], revision=head)

    values = tuple(model.model_validate_json(raw(stage, name)) for model, stage, name in (
        (FinishedImportPlan, "curate", "plan"), (MappingRecipe, "map", "recipe"),
        (MappingPlan, "map", "plan"), (MappingResult, "map", "result"),
        (ImportedCurationResult, "curate", "result"), (ImportedSplitResult, "split", "result"),
        (ImportedRowSet, "format", "row-set"),
    ))
    args = {
        "raw_sources": {sid: (item.logical_path, store.read_artifact(item.raw_artifact_id, revision=head)) for sid, item in head.sources.items()},
        "train_jsonl": raw("format", "train"), "evaluation_jsonl": raw("format", "evaluation"),
        "provenance_jsonl": raw("format", "provenance"),
    }
    return values, args


@pytest.mark.parametrize("defect", ["empty-gates", "duplicate-gate", "foreign-snapshot", "passed-with-finding", "missing-file", "wrong-row-count"])
def test_rehashed_forged_validation_still_refuses(tmp_path: Path, defect: str) -> None:
    values, args = _case(tmp_path)
    report = validate_imported_dataset(*values, **args)
    assert report.status == "passed"
    body = report.model_dump(mode="json")
    if defect == "empty-gates":
        body["gate_results"] = []
    elif defect == "duplicate-gate":
        body["gate_results"][1] = body["gate_results"][0]
    elif defect in {"foreign-snapshot", "passed-with-finding"}:
        gate = body["gate_results"][0]
        if defect == "foreign-snapshot":
            gate["snapshot_id"] = derive_id("dss", {"foreign": True})
        else:
            gate["finding_codes"] = ["unresolved"]
        gate["gate_result_id"] = derive_id("dgr", {key: value for key, value in gate.items() if key != "gate_result_id"})
    else:
        snapshot = body["snapshot"]
        if defect == "missing-file":
            snapshot["file_bindings"].pop()
        else:
            snapshot["file_bindings"][2]["record_count"] += 1
        snapshot["snapshot_id"] = derive_id("dss", {key: value for key, value in snapshot.items() if key != "snapshot_id"})
        body["snapshot_id"] = snapshot["snapshot_id"]
    body["report_id"] = derive_id("dvr", {key: value for key, value in body.items() if key != "report_id"})
    with pytest.raises(MappingError):
        ImportedValidationReport.model_validate_json(json.dumps(body))


def test_mapping_replay_uses_raw_capture_instead_of_split_claim(tmp_path: Path) -> None:
    values, args = _case(tmp_path)
    sid = next(iter(args["raw_sources"]))
    name, raw = args["raw_sources"][sid]
    args["raw_sources"][sid] = (name, raw.replace(b"Alpha", b"Forged"))
    with pytest.raises(DatasetValidationError, match="source identity differs"):
        validate_imported_dataset(*values, **args)
    args["raw_sources"] = {}
    with pytest.raises(DatasetValidationError, match="exact captured source set"):
        validate_imported_dataset(*values, **args)


def test_failed_gate_requires_a_finding() -> None:
    with pytest.raises(MappingError, match="contradicts its findings"):
        ImportedGateResult.create(snapshot_id=derive_id("dss", {"case": 1}), gate_id="mapping-replay", status="failed")


def test_import_coverage_cannot_pass_after_a_selected_source_loses_every_row(tmp_path: Path) -> None:
    from veriformis.mapping import FieldMapping, mapping_confirmation_digest

    service = PipelineService()
    sources = []
    for name in ("a.jsonl", "b.jsonl"):
        source = tmp_path / name
        source.write_text('{"text":"An exact duplicate in both selected files"}\n', encoding="utf-8")
        sources.append(source)
    workspace = tmp_path / "workspace"
    service.parse(sources, workspace, source_root=tmp_path, mode="dataset-row")
    head = Workspace.open(workspace).head()
    fields = (FieldMapping.create(source_path="text", target_key="text"),)
    plan = MappingPlan.create(
        goal_id="learn-the-text", representation_id="whole-text", row_schema="text", container_kind="jsonl",
        field_mappings=fields,
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text", representation_id="whole-text", row_schema="text", field_mappings=fields,
            source_digests=tuple((item.logical_path, item.sha256) for item in head.sources.values()),
        ),
    )
    service.map_rows(workspace, goal=plan.goal_id, representation=plan.representation_id, mapping_plan=plan)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    result = service.validate(workspace)
    assert result.exit_status == 1
    assert next(gate for gate in result.report.gate_results if gate.gate_id == "coverage").status == "failed"
    assert not (tmp_path / "bundle").exists()
