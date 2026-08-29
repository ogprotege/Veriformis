"""Phase 18.6: pre-publication samples. No renderer, no destination write."""

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


def test_result_view_shows_prepublication_samples() -> None:
    result = _read("macos/Sources/Views/ResultView.swift")
    assert "Pre-publication samples" in result
    assert "Quality findings are preview-only and do not block seal" in result
    assert "Source recovery" in result
    assert "recoveredSource" in result
    assert "Split assignment digest" in result
    assert "Mapping plan" in result
    assert "does not call a renderer or write a destination" in result
    assert "Quality findings (preview only)" in result
    assert "are not required review" in result


def test_samples_do_not_execute_export_or_quality_report() -> None:
    result = _read("macos/Sources/Views/ResultView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ExportsView.swift" not in views
    assert "ReviewView.swift" not in views
    for haystack in (result, model):
        assert "executeExport" not in haystack
        assert "quality-report" not in haystack
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_public_surfaces_still_have_no_generator() -> None:
    forbidden = {"generator", "install-extension"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
