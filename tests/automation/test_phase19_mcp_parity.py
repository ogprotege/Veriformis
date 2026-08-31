"""Phase 19.5: MCP wraps project-spec packets; no Hub or package tools."""

from __future__ import annotations

import json
from pathlib import Path

from veriformis.automation import create_project_spec, load_project_spec_diagnostic
from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION
from veriformis.workspace import Workspace


ROOT = Path(__file__).resolve().parents[2]
SERVICE = PipelineService()


def _tool_map(server):
    return {tool.name: tool.fn for tool in server._tool_manager.list_tools()}


def _document_spec(tmp_path: Path):
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


def test_mcp_wraps_spec_schema_dry_run_lock_and_env(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    tools = _tool_map(create_mcp_server(SERVICE))
    schema = json.loads(tools["spec_schema"]())
    assert schema == SERVICE.project_spec_schema()
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    preview = json.loads(tools["spec_dry_run"](str(path)))
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert after == before
    assert preview["writes_workspace"] is False
    assert preview["spec_id"] == spec.spec_id
    env = json.loads(tools["env_inspect"]())
    assert "HF_TOKEN" not in json.dumps(env)
    assert env["extras"]["trl"] == "empty"
    lock = json.loads(tools["spec_lock"](str(path)))
    assert lock["spec_id"] == spec.spec_id
    assert "workspace_head" not in lock


def test_mcp_spec_run_and_resume_match_service(tmp_path: Path) -> None:
    spec, path = _document_spec(tmp_path)
    tools = _tool_map(create_mcp_server(SERVICE))
    payload = json.loads(tools["spec_run"](str(path)))
    assert payload["spec_id"] == spec.spec_id
    head = Workspace.open(Path(payload["workspace"])).head()
    assert head.stages["parse"].status == "complete"
    assert head.stages["seal"].status == "complete"
    assert payload["lock"]["workspace_head"]
    lock_path = tmp_path / "spec.lock.json"
    lock_path.write_text(json.dumps(payload["lock"], indent=2, sort_keys=True))
    resumed = json.loads(tools["spec_resume"](str(path), str(lock_path)))
    assert resumed["spec_id"] == spec.spec_id
    assert resumed["bundle"] is not None
    assert "run_pipeline" in tools
    assert tools["run_pipeline"].__doc__ is not None
    assert "YAML pipeline" in tools["run_pipeline"].__doc__


def test_mcp_spec_failure_returns_diagnostic(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema_id":"nope"}\n', encoding="utf-8")
    tools = _tool_map(create_mcp_server())
    payload = json.loads(tools["spec_run"](str(path)))
    diagnostic = load_project_spec_diagnostic(json.dumps(payload, sort_keys=True))
    assert diagnostic["code"]
    assert diagnostic["schema_id"] == "veriformis.project-spec-diagnostic/v1"
    spec, spec_path = _document_spec(tmp_path)
    json.loads(tools["spec_run"](str(spec_path)))
    lock_path = tmp_path / "bare.lock.json"
    lock_path.write_text(
        json.dumps(SERVICE.lock_project_spec(spec), indent=2, sort_keys=True)
    )
    drifted = json.loads(tools["spec_resume"](str(spec_path), str(lock_path)))
    diagnostic = load_project_spec_diagnostic(json.dumps(drifted, sort_keys=True))
    assert diagnostic["spec_id"] == spec.spec_id
    assert "mismatched identity" in diagnostic["message"]


def test_mcp_skips_package_hub_and_quality_report() -> None:
    names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "package" not in names
    assert "package_verify" not in names
    assert "hub_upload" not in names
    assert "quality_report" not in names
    assert "spec_schema" in names
    assert "spec_dry_run" in names
    assert "spec_lock" in names
    assert "env_inspect" in names
    assert "spec_run" in names
    assert "spec_resume" in names
    skip = ROOT / (
        "dev/active/independent-product/phase-19-automation-and-publication/"
        "skipped-package-mcp.md"
    )
    text = skip.read_text(encoding="utf-8")
    assert "package" in text
    assert "package-verify" in text
    cli_names = {command.name for command in app.registered_commands}
    assert "package" in cli_names
    assert "package-verify" in cli_names
