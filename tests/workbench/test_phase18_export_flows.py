"""Phase 18.7: workbench export flows over verified bundles."""

from __future__ import annotations

import re
from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_sidebar_includes_exports_without_review() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    block = re.search(
        r"enum SidebarDestination[^{]*\{(?P<body>.*?)\n\}",
        models,
        re.S,
    )
    assert block is not None
    cases = re.findall(r"^\s*case (\w+)$", block.group("body"), re.M)
    assert cases == ["home", "compile", "review", "exports", "history", "settings"]
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ExportsView.swift" in views
    assert "ReviewView.swift" in views
    content = _read("macos/Sources/Views/ContentView.swift")
    assert "case .exports:" in content
    assert "ExportsView()" in content


def test_export_view_wires_discover_dry_run_confirmed_execute_and_verify() -> None:
    view = _read("macos/Sources/Views/ExportsView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "Source bundle and receipt" in view
    assert "sourceBundleID" in view
    assert "exportReceiptID" in view
    assert "I confirm this dry-run plan" in view
    assert "Execute export" in view
    assert "does not train, mutate membership, or upload to a Hub" in view
    assert "Generic containers" in view
    assert "func discoverExports(" in model
    assert "func dryRunSelectedExport(" in model
    assert "func executeConfirmedExport(" in model
    assert "func verifyExportDestination(" in model
    assert "var canExecuteExport: Bool" in model
    assert "canDryRunExport && hasExportDryRunPlan && exportPlanConfirmed" in model
    assert "WorkbenchExportProfiles.admitted" in model
    assert '["export", "discover"]' in cli
    assert '["export", "dry-run"' in cli
    assert '["export", "execute"' in cli
    assert '["export-verify"' in cli
    assert "static func exportCLIEquivalent(arguments: [String])" in cli
    assert "var currentExportCLIEquivalent: String?" in model
    assert "overwritePolicy" in view
    assert "review-submit" not in view


def test_named_profiles_filter_to_admitted_schemas() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    view = _read("macos/Sources/Views/ExportsView.swift")
    assert "static let order = [" in models
    assert '"split-jsonl-directory"' in models
    assert '"hugging-face-dataset"' in models
    assert "consumer.acceptedRowSchemas.contains(rowSchema)" in models
    assert "Named profiles wait until a row schema is known" in view
    assert "Constrained CSV still refuses nested and family rows" in view
    assert "family-to-trainer" not in view
    assert "huggingface.co" not in view.lower()


def test_dry_run_preview_accepts_product_row_schemas() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    assert "GoalCatalog.rowSchemaOrder.contains(rowSchema)" in models
    assert '"label-classification"' in models
    assert '"preference-pair"' in models
    assert '"tool-call-conversation"' in models
    assert '"stepwise-trace"' in models


def test_quality_and_review_remain_non_blocking() -> None:
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "defaultWriteAptusHandoff = false" in model
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "review-submit" not in compile_view


def test_public_surfaces_still_have_no_generator_or_hub() -> None:
    forbidden = {"generator", "install-extension", "hub-upload"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
    assert not hasattr(service, "hub_upload")
