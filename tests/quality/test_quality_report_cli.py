"""Post-20 remainder: thin quality-report CLI over the existing preview."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import pytest

from veriformis.cli import app
from veriformis.errors import MissingStageInputError, QualityReportError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality import V1_QUALITY_GATES, require_quality_report_not_enforcing
from veriformis.quality.report import QualityReport
from veriformis.workspace import IMPORT_REVISION_SCHEMA_VERSION, Workspace


RUNNER = CliRunner()


def _write_sources(root: Path) -> Path:
    sources = root / "src"
    sources.mkdir()
    (sources / "alpha.txt").write_text(
        "Contact alpha@example.test for the first independent source.\n",
        encoding="utf-8",
    )
    (sources / "beta.txt").write_text(
        "Key AKIAIOSFODNN7EXAMPLE stays a finding only in source two.\n",
        encoding="utf-8",
    )
    return sources


def _compile_through_split(tmp_path: Path) -> tuple[PipelineService, Path]:
    sources = _write_sources(tmp_path)
    workspace = tmp_path / "workspace"
    service = PipelineService()
    service.parse([sources], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="full_text")
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    return service, workspace


def test_cli_matches_library_preview(tmp_path: Path) -> None:
    service, workspace = _compile_through_split(tmp_path)
    python = service.quality_report(workspace)
    assert python.report is not None
    require_quality_report_not_enforcing(python.report)
    assert python.report.enforcing is False
    assert python.report.schema_id == "veriformis.quality-report/v1"
    cli = RUNNER.invoke(app, ["quality-report", str(workspace)])
    assert cli.exit_code == 0, cli.output
    assert cli.stdout == python.report.transport_text() + "\n"
    payload = json.loads(cli.stdout)
    assert payload == python.report.model_dump(mode="json")
    assert payload["enforcing"] is False
    reloaded = QualityReport.model_validate(payload)
    assert reloaded == python.report
    preview = json.loads(
        next(item.text_value for item in python.report.facts if item.name == "quality-gate-preview")
    )
    assert all(row["admitted-to-block"] is False for row in preview)
    would_block = next(
        item.integer_value
        for item in python.report.facts
        if item.name == "quality-gate-would-block-count"
    )
    assert would_block == 2


def test_seal_succeeds_when_report_contains_warnings(tmp_path: Path) -> None:
    service, workspace = _compile_through_split(tmp_path)
    report = service.quality_report(workspace).report
    assert report is not None
    require_quality_report_not_enforcing(report)
    assert report.enforcing is False
    would_block = next(
        item.integer_value
        for item in report.facts
        if item.name == "quality-gate-would-block-count"
    )
    assert would_block >= 1
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    service.format(workspace)
    validate = service.validate(workspace)
    assert validate.exit_status == 0
    assert validate.report is not None
    assert validate.report.status == "passed"
    bundle = tmp_path / "out.vfbundle"
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    assert (bundle / "manifest.json").is_file()


def test_sealed_bundle_is_refused(tmp_path: Path) -> None:
    service, workspace = _compile_through_split(tmp_path)
    service.format(workspace)
    service.validate(workspace)
    bundle = tmp_path / "out.vfbundle"
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    cli = RUNNER.invoke(app, ["quality-report", str(bundle)])
    assert cli.exit_code == 2
    assert "sealed bundle" in cli.output
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "quality_report" not in mcp_names
    assert "quality-report" not in mcp_names


def test_cli_help_names_workspace_not_bundle() -> None:
    help_text = RUNNER.invoke(app, ["quality-report", "--help"]).output
    assert "WORKSPACE_OR_BUNDLE" not in help_text
    assert "WORKSPACE" in help_text
    assert "sealed bundle" in help_text


def test_quality_report_dataset_row_does_not_ask_for_schema_3(tmp_path: Path) -> None:
    workspace = tmp_path / "import-ws"
    Workspace.create(workspace, schema_version=IMPORT_REVISION_SCHEMA_VERSION)
    with pytest.raises(Exception) as exc:
        PipelineService().quality_report(workspace)
    message = str(exc.value)
    assert "schema 3" not in message
    assert "upgrade-workspace" not in message


def test_quality_report_parse_only_does_not_tell_operator_to_split_first(
    tmp_path: Path,
) -> None:
    sources = _write_sources(tmp_path)
    workspace = tmp_path / "workspace"
    service = PipelineService()
    service.parse([sources], workspace, source_root=tmp_path)
    with pytest.raises(MissingStageInputError) as exc:
        service.quality_report(workspace)
    message = str(exc.value)
    assert "`veriformis split" not in message
    assert "construct" in message


def test_stray_manifest_is_not_called_a_sealed_bundle(tmp_path: Path) -> None:
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(QualityReportError) as exc:
        PipelineService().quality_report(stray)
    assert "sealed bundle" not in str(exc.value)
