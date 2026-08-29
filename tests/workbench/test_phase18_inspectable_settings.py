"""Phase 18.5: inspectable preset and goal contract. No Swift defaults."""

from __future__ import annotations

from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_recipe_settings_inspect_preset_and_goal_contract() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "Inspectable preset and goal contract" in compile_view
    assert "preset.reviewPolicy" in compile_view
    assert "goal.reviewPolicyDefault" in compile_view
    assert "compatibleGenericExports" in compile_view
    assert "goal.nonClaims" in compile_view
    assert "preset.segmentation.strategy" in compile_view
    assert "preset.construction.splitRatioPPM" in compile_view
    assert "preset.curation.splitSeed" in compile_view
    assert "selectedRepresentation" in model
    assert "Validation and profiles (inspect only)" in compile_view
    assert "This panel does not mutate membership." in compile_view
    assert "Named-profile export is on Exports and only for schemas the profile admits." in compile_view


def test_inspectable_settings_do_not_execute_export_or_review() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ReviewView.swift" not in views
    assert "executeExport" not in compile_view
    assert "review-submit" not in compile_view
    assert "review-submit" not in model
    assert "review_policy = \"required\"" not in compile_view
    assert "reviewPolicy = \"required\"" not in compile_view
    assert "review_policy = \"required\"" not in model
    assert "reviewPolicy = \"required\"" not in model


def test_overrides_remain_explicit_and_preset_sourced() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "Empty overrides keep that preset authoritative." in compile_view
    assert "$workbench.splitRatioPPM" in compile_view
    assert "$workbench.allowEmptyEvaluation" in compile_view
    assert "500000" not in compile_view
    assert "500_000" not in compile_view
    assert '"veriformis-v1"' not in compile_view
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "500000" not in model
    assert "500_000" not in model


def test_public_surfaces_still_have_no_generator() -> None:
    forbidden = {"generator", "install-extension"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
