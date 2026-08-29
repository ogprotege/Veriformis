"""Phase 18.3: goal-first workbench copy. No new compile path."""

from __future__ import annotations

import re
from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_sidebar_still_excludes_review_and_exports() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    block = re.search(
        r"enum SidebarDestination[^{]*\{(?P<body>.*?)\n\}",
        models,
        re.S,
    )
    assert block is not None
    cases = re.findall(r"^\s*case (\w+)$", block.group("body"), re.M)
    assert cases == ["home", "compile", "history", "settings"]
    title_block = re.search(
        r"var title: String \{(?P<body>.*?)\n    \}",
        models,
        re.S,
    )
    assert title_block is not None
    titles = re.findall(r'case \.\w+: return "([^"]+)"', title_block.group("body"))
    assert titles == ["Home", "Compile", "History", "Settings"]
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ReviewView.swift" not in views
    assert "ExportsView.swift" not in views
    assert "MappingView.swift" not in views


def test_home_and_compile_copy_does_not_require_aptus() -> None:
    home = _read("macos/Sources/Views/HomeView.swift")
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    settings = _read("macos/Sources/Views/SettingsView.swift")
    assert "required Aptus" not in home
    assert "requires Aptus" not in home
    assert "Aptus is optional Integrations. It is not required." in home
    assert "sealed, independently verified .vfbundle" in home
    assert "Add sources, choose a goal, and compile a sealed .vfbundle." in compile_view
    assert "Aptus is optional Integrations, not required." in compile_view
    assert "The workbench does not require a trainer." in settings
    for haystack in (home, compile_view, settings):
        assert "dataset-row" not in haystack
        assert "Review queue" not in haystack
        assert "export execute" not in haystack.lower()


def test_compile_surfaces_copyable_cli_equivalent() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "CLI equivalent" in compile_view
    assert "Copy CLI equivalent" in compile_view
    assert "currentCompileCLIEquivalent" in compile_view
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "static func cliEquivalent(for plan: [StageCommand])" in cli
    assert "static func shellQuote(" in cli
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "var currentCompileCLIEquivalent: String?" in model
    assert "includeHandoff: writeAptusHandoff" in model


def test_compile_plan_remains_document_source() -> None:
    source = _read("macos/Sources/Services/VeriformisCLI.swift")
    match = re.search(
        r"static func compilePlan\([\s\S]*?\n    static func ",
        source,
    )
    assert match is not None
    plan = match.group(0)
    stages = tuple(re.findall(r"StageCommand\(stage: \.(\w+)", plan))
    assert stages == (
        "parse",
        "clean",
        "chunk",
        "construct",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    )
    assert "--mode" not in plan
    assert "dataset-row" not in plan


def test_public_surfaces_still_have_no_new_execute() -> None:
    forbidden = {"generator", "install-extension", "workbench-adapter"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "load_workbench_adapter")
