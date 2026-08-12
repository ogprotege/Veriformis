"""Defect closure: partial seal publication surfaces on every adapter.

When a bundle becomes visible but the workspace receipt does not commit,
``veriformis run`` and both MCP tools must surface the publication receipt
facts (bundle path, manifest SHA-256, guidance) instead of a raw traceback or
an opaque framework error. The MCP seal tool must also report a handoff
failure alongside — never instead of — a successful seal outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis import workspace as workspace_module
from veriformis.cli import app
from veriformis.handoff import AptusHandoffError
from veriformis.identity import sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

runner = CliRunner()


def _tool_map(server):
    manager = server._tool_manager
    return {tool.name: tool.fn for tool in manager.list_tools()}


def _call(fn, *args, **kwargs):
    """Call one registered MCP tool regardless of sync wrapper choice."""
    result = fn(*args, **kwargs)
    if hasattr(result, "__await__"):
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(result)
    return result


def _validated_workspace(tmp_path: Path, service: PipelineService) -> Path:
    source = tmp_path / "source.txt"
    source.write_text(
        "First paragraph with enough grounded text for one record.\n\n"
        "Second paragraph keeps the corpus multi-block.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="full_text")
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    return workspace


def _seal_only_spec(tmp_path: Path, workspace: Path, bundle: Path) -> Path:
    spec = tmp_path / "pipeline.yaml"
    spec.write_text(
        f"""
schema_version: veriformis.pipeline/v1
workspace: {workspace}
sources:
  - {tmp_path / "source.txt"}
stages:
  seal:
    out: {bundle}
""".strip(),
        encoding="utf-8",
    )
    return spec


def _fail_head_promotion(path: Path, data: bytes) -> bool:
    raise OSError(f"injected HEAD failure for {path}")


def test_cli_run_partial_publication_reports_guidance(tmp_path, monkeypatch):
    workspace = _validated_workspace(tmp_path, PipelineService())
    bundle = tmp_path / "partial.vfbundle"
    spec = _seal_only_spec(tmp_path, workspace, bundle)
    monkeypatch.setattr(
        workspace_module, "_promote_commit_pointer", _fail_head_promotion
    )

    result = runner.invoke(app, ["run", str(spec)])

    assert result.exit_code == 1, result.output
    assert "published bundle remains visible at" in result.output
    assert str(bundle) in result.output
    assert "workspace receipt did not commit" in result.output
    assert bundle.is_dir()
    digest = sha256_digest((bundle / "manifest.json").read_bytes())
    assert digest in result.output


def test_mcp_seal_partial_publication_payload_carries_receipt_facts(
    tmp_path,
    monkeypatch,
):
    service = PipelineService()
    workspace = _validated_workspace(tmp_path, service)
    bundle = tmp_path / "mcp-partial.vfbundle"
    tools = _tool_map(create_mcp_server(service))
    monkeypatch.setattr(
        workspace_module, "_promote_commit_pointer", _fail_head_promotion
    )

    payload = json.loads(_call(tools["seal"], str(workspace), str(bundle)))

    error = payload["error"]
    assert error["code"] == "seal-partial-publication"
    assert error["bundle_path"] == str(bundle)
    assert "workspace receipt did not commit" in error["explanation"]
    assert bundle.is_dir()
    digest = sha256_digest((bundle / "manifest.json").read_bytes())
    assert error["manifest_sha256"] == digest


def test_mcp_run_pipeline_partial_publication_payload_carries_receipt_facts(
    tmp_path,
    monkeypatch,
):
    service = PipelineService()
    workspace = _validated_workspace(tmp_path, service)
    bundle = tmp_path / "mcp-run-partial.vfbundle"
    spec = _seal_only_spec(tmp_path, workspace, bundle)
    tools = _tool_map(create_mcp_server(service))
    monkeypatch.setattr(
        workspace_module, "_promote_commit_pointer", _fail_head_promotion
    )

    payload = json.loads(_call(tools["run_pipeline"], str(spec)))

    error = payload["error"]
    assert error["code"] == "seal-partial-publication"
    assert error["bundle_path"] == str(bundle)
    assert "workspace receipt did not commit" in error["explanation"]
    assert bundle.is_dir()
    digest = sha256_digest((bundle / "manifest.json").read_bytes())
    assert error["manifest_sha256"] == digest


def test_mcp_seal_reports_handoff_failure_alongside_seal_outcome(
    tmp_path,
    monkeypatch,
):
    service = PipelineService()
    workspace = _validated_workspace(tmp_path, service)
    bundle = tmp_path / "handoff-fail.vfbundle"
    tools = _tool_map(create_mcp_server(service))

    def fail_build(*args, **kwargs):
        raise AptusHandoffError("injected handoff failure")

    monkeypatch.setattr("veriformis.handoff.build_aptus_handoff", fail_build)

    payload = json.loads(_call(tools["seal"], str(workspace), str(bundle), True))

    assert payload["publication"]["manifest_sha256"]
    assert payload["exit_status"] == 0
    handoff_error = payload["aptus_handoff_error"]
    assert handoff_error["code"] == "aptus-handoff-invalid"
    assert "injected handoff failure" in handoff_error["message"]
    assert bundle.is_dir()
