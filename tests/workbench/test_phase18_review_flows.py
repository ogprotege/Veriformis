"""Phase 18.8: Mac Review wraps existing review packets."""

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


def test_sidebar_includes_review() -> None:
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
    assert "ReviewView.swift" in views
    content = _read("macos/Sources/Views/ContentView.swift")
    assert "case .review:" in content
    assert "ReviewView()" in content


def test_review_view_wraps_export_import_and_confirmed_submit() -> None:
    view = _read("macos/Sources/Views/ReviewView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "Default review_policy stays none" in view
    assert "Required unresolved reviews still block seal" in view
    assert "Corrections bind a new transform or mapping-plan identity" in view
    assert "does not invent a review policy" in view
    assert "I confirm this packet for submit" in view
    assert "func exportReviewPacket(" in model
    assert "func importReviewPacket(" in model
    assert "func submitConfirmedReview(" in model
    assert "canImportReviewPacket && reviewSubmitConfirmed" in model
    assert '"review-export"' in cli
    assert '"review-import"' in cli
    assert '"review-submit"' in cli
    assert "var currentReviewCLIEquivalent: String?" in model
    assert "review_policy = \"required\"" not in model
    assert "reviewPolicy = \"required\"" not in view


def test_corrections_are_new_identities() -> None:
    view = _read("macos/Sources/Views/ReviewView.swift")
    assert "Corrections are new identities" in view
    assert "do not mutate accepted records in place" in view
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    assert "resultID" in models
    assert '"veriformis.review-packet/v1"' in models
    assert '"veriformis.review-bundle/v1"' in models


def test_quality_stays_preview_only_and_aptus_stays_off() -> None:
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "defaultWriteAptusHandoff = false" in model


def test_public_surfaces_still_have_no_generator() -> None:
    forbidden = {"generator", "install-extension"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
