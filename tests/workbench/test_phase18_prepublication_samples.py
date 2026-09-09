"""Result previews retain evidence without a renderer or destination write."""

from __future__ import annotations

from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_result_view_labels_compiled_previews_and_retains_evidence() -> None:
    result = _read("macos/Sources/Views/ResultView.swift")
    assert "Compiled dataset preview" in result
    assert "Quality findings are preview-only and do not block seal" in result
    assert "Source recovery" in result
    assert "recoveredSource" in result
    assert "Split assignment digest" in result
    assert "Mapping plan" in result
    assert "does not call a renderer or write a destination" in result
    assert "Preview diagnostics" in result
    assert "are not required review" in result


def test_samples_do_not_execute_export_or_quality_report() -> None:
    result = _read("macos/Sources/Views/ResultView.swift")
    assert "executeExport" not in result
    assert "quality-report" not in result
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_public_surfaces_still_have_no_generator() -> None:
    forbidden = {"generator", "install-extension"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
