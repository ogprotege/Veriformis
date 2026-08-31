"""Phase 19.4: spec diagnostics, execute, and lock-matched resume."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.automation import (
    create_project_lock,
    create_project_spec,
    load_project_spec_diagnostic,
    project_spec_diagnostic,
)
from veriformis.automation.execute import lock_after_workspace, resume_project_spec
from veriformis.automation.spec import PROJECT_SPEC_LIMITATIONS, ProjectSpec
from veriformis.cli import app
from veriformis.contracts import PROJECT_SPEC_DIAGNOSTIC_SCHEMA_ID
from veriformis.errors import ProjectSpecError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION
from veriformis.workspace import IMPORT_REVISION_SCHEMA_VERSION, Workspace


RUNNER = CliRunner()
SERVICE = PipelineService()


def _document_spec(tmp_path: Path) -> tuple[ProjectSpec, Path]:
    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "doc.txt"
    source.write_text(
        "Alpha paragraph with enough text for a record.\n\n"
        "Beta paragraph keeps the corpus multi-block.\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "out.vfbundle"
    spec = create_project_spec(
        mode="document-source",
        goal_id="learn-the-text",
        pipeline={
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": str(workspace),
            "source_root": str(raw),
            "sources": [str(source)],
            "stages": {
                "parse": {},
                "construct": {"goal": "learn-the-text"},
                "curate": {"allow_empty_evaluation": True},
                "seal": {"out": str(bundle)},
            },
        },
    )
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))
    return spec, path


def test_truncated_diagnostic_fails_closed() -> None:
    complete = project_spec_diagnostic(ProjectSpecError("boom"), spec_id="psp-v1-" + "a" * 64)
    loaded = load_project_spec_diagnostic(json.dumps(complete, sort_keys=True))
    assert loaded["schema_id"] == PROJECT_SPEC_DIAGNOSTIC_SCHEMA_ID
    assert loaded["code"] == "project-spec-invalid"
    assert loaded["message"] == "boom"
    assert PROJECT_SPEC_LIMITATIONS == ("no-hub-upload",)
    with pytest.raises(ProjectSpecError, match="truncated"):
        load_project_spec_diagnostic('{"code":"project-spec-invalid"')
    with pytest.raises(ProjectSpecError, match="truncated"):
        load_project_spec_diagnostic('{"code":"x"}')


def test_spec_run_document_source_omits_mode_and_does_not_export(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    result = RUNNER.invoke(app, ["spec-run", str(path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["spec_id"] == spec.spec_id
    workspace = Workspace.open(Path(payload["workspace"]))
    head = workspace.head()
    assert "map" not in head.stages or head.stages["map"].status == "absent"
    assert head.stages["parse"].status == "complete"
    assert head.stages["seal"].status == "complete"
    assert payload["bundle"] is not None
    assert payload["lock"]["workspace_head"] == workspace.head_id
    assert payload["lock"]["source_identities"] == list(sorted(workspace.head().sources))
    assert not list(tmp_path.glob("**/*.vfexport.zip"))


def test_spec_run_emits_json_diagnostic_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema_id":"nope"}\n', encoding="utf-8")
    result = RUNNER.invoke(app, ["spec-run", str(path)])
    assert result.exit_code == 2
    assert "error[" in result.output
    lines = [line for line in result.output.splitlines() if line.startswith("{")]
    assert lines
    diagnostic = load_project_spec_diagnostic(lines[-1])
    assert diagnostic["code"]


def test_resume_matches_lock_and_rejects_drift(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    SERVICE.run_project_spec(spec)
    lock = lock_after_workspace(spec, Path(spec.pipeline["workspace"]))
    resumed = resume_project_spec(spec, lock, service=SERVICE)
    assert resumed.workspace == Path(spec.pipeline["workspace"])
    drifted = create_project_lock(spec)
    with pytest.raises(ProjectSpecError, match="mismatched identity workspace_head"):
        resume_project_spec(spec, drifted, service=SERVICE)


def test_spec_run_dataset_row_parses_with_mode_then_maps(tmp_path: Path) -> None:
    from veriformis.mapping import FieldMapping, MappingPlan, mapping_confirmation_digest

    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "rows.jsonl"
    source.write_bytes(
        (Path(__file__).resolve().parents[1] / "regressions" / "fixtures" / "phase7" / "text.jsonl").read_bytes()
    )
    probe = tmp_path / "probe"
    SERVICE.parse([source], probe, source_root=raw, mode="dataset-row")
    probe_head = Workspace.open(probe).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in probe_head.sources.values()
    )
    mappings = (FieldMapping.create(source_path="text", target_key="text"),)
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=source_digests,
    )
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "out.vfbundle"
    spec = create_project_spec(
        mode="dataset-row",
        goal_id="learn-the-text",
        mapping={
            "mapping_plan_id": plan.mapping_plan_id,
            "confirmation_digest": confirmation,
            "plan_path": str(plan_path),
        },
        pipeline={
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": str(workspace),
            "source_root": str(raw),
            "sources": [str(source)],
            "stages": {
                "parse": {},
                "curate": {"allow_empty_evaluation": True},
                "split": {},
                "format": {},
                "validate": {},
                "seal": {"out": str(bundle)},
            },
        },
    )
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))
    result = RUNNER.invoke(app, ["spec-run", str(path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    head = Workspace.open(Path(payload["workspace"])).head()
    assert head.schema_version == IMPORT_REVISION_SCHEMA_VERSION
    assert head.stages["parse"].status == "complete"
    assert head.stages["map"].status == "complete"
    assert head.stages["seal"].status == "complete"
    assert payload["bundle"] is not None
    assert not list(tmp_path.glob("**/*.vfexport.zip"))


def test_mcp_has_no_hub_upload_tool() -> None:
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "hub_upload" not in mcp_names
    assert "quality_report" not in mcp_names


def test_cli_spec_resume_requires_matching_lock(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    ran = RUNNER.invoke(app, ["spec-run", str(path)])
    assert ran.exit_code == 0, ran.output
    payload = json.loads(ran.output)
    lock_path = tmp_path / "spec.lock.json"
    lock_path.write_text(json.dumps(payload["lock"], indent=2, sort_keys=True))
    ok = RUNNER.invoke(app, ["spec-resume", str(path), "--lock", str(lock_path)])
    assert ok.exit_code == 0, ok.output
    assert json.loads(ok.output)["bundle"] is not None
    bare = create_project_lock(spec)
    lock_path.write_text(json.dumps(bare.model_dump(mode="json"), indent=2, sort_keys=True))
    bad = RUNNER.invoke(app, ["spec-resume", str(path), "--lock", str(lock_path)])
    assert bad.exit_code == 2
    assert "mismatched identity" in bad.output


def test_spec_lock_workspace_pins_head_for_resume(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    ran = RUNNER.invoke(app, ["spec-run", str(path)])
    payload = json.loads(ran.output)
    lock_path = tmp_path / "from-workspace.lock.json"
    locked = RUNNER.invoke(
        app,
        ["spec-lock", str(path), "--workspace", payload["workspace"], "--out", str(lock_path)],
    )
    assert locked.exit_code == 0, locked.output
    ok = RUNNER.invoke(app, ["spec-resume", str(path), "--lock", str(lock_path)])
    assert ok.exit_code == 0, ok.output


def test_spec_run_resolves_paths_against_spec_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    raw = project / "raw"
    raw.mkdir(parents=True)
    (raw / "doc.txt").write_text(
        "Alpha paragraph with enough text for a record.\n\n"
        "Beta paragraph keeps the corpus multi-block.\n",
        encoding="utf-8",
    )
    spec = create_project_spec(
        mode="document-source",
        goal_id="learn-the-text",
        pipeline={
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": "ws",
            "source_root": "raw",
            "sources": ["doc.txt"],
            "stages": {
                "parse": {},
                "construct": {"goal": "learn-the-text"},
                "curate": {"allow_empty_evaluation": True},
                "seal": {"out": "out.vfbundle"},
            },
        },
    )
    path = project / "spec.json"
    path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))
    result = RUNNER.invoke(app, ["spec-run", str(path)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert Path(payload["workspace"]) == (project / "ws").resolve()
    assert Path(payload["bundle"]).exists()
    assert Path(payload["workspace"]).is_dir()


def test_spec_run_refuses_mapping_plan_identity_drift(tmp_path: Path) -> None:
    from veriformis.identity import sha256_digest
    from veriformis.mapping import FieldMapping, MappingPlan, mapping_confirmation_digest

    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "rows.jsonl"
    source.write_bytes(
        (Path(__file__).resolve().parents[1] / "regressions" / "fixtures" / "phase7" / "text.jsonl").read_bytes()
    )
    probe = tmp_path / "probe"
    SERVICE.parse([source], probe, source_root=raw, mode="dataset-row")
    probe_head = Workspace.open(probe).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in probe_head.sources.values()
    )
    mappings = (FieldMapping.create(source_path="text", target_key="text"),)
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=source_digests,
    )
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
    other = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=sha256_digest("other-confirmation"),
        field_mappings=mappings,
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(other.model_dump(mode="json"), indent=2, sort_keys=True))
    spec = create_project_spec(
        mode="dataset-row",
        goal_id="learn-the-text",
        mapping={
            "mapping_plan_id": plan.mapping_plan_id,
            "confirmation_digest": confirmation,
            "plan_path": str(plan_path),
        },
        pipeline={
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": str(tmp_path / "ws"),
            "source_root": str(raw),
            "sources": [str(source)],
            "stages": {"parse": {}, "seal": {"out": str(tmp_path / "out.vfbundle")}},
        },
    )
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True))
    result = RUNNER.invoke(app, ["spec-run", str(path)])
    assert result.exit_code == 2
    assert "mismatched identity mapping_plan_id" in result.output
