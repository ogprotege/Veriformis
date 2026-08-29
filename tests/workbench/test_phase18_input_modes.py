"""Phase 18.4: ADR-0010 input modes and confirm-then-map."""

from __future__ import annotations

import json
import re
from pathlib import Path

from veriformis.cli import app
from veriformis.mapping.modes import (
    DATASET_ROW_MODE,
    DOCUMENT_SOURCE_MODE,
    MIXED_MODE,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"
FAMILY_GOAL_IDS = (
    "classify-with-provided-labels",
    "prefer-chosen-over-rejected",
    "use-provided-tool-traces",
    "use-provided-steps",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _compile_plan_source() -> str:
    source = _read("macos/Sources/Services/VeriformisCLI.swift")
    match = re.search(
        r"static func compilePlan\([\s\S]*?\n    static func ",
        source,
    )
    assert match is not None
    return match.group(0)


def test_input_mode_identifiers_match_adr_0010() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    block = re.search(
        r"enum CompilerInputMode[^{]*\{(?P<body>.*?)\n\}",
        models,
        re.S,
    )
    assert block is not None
    raw = re.findall(r'= "([^"]+)"', block.group("body"))
    assert raw == [DOCUMENT_SOURCE_MODE, DATASET_ROW_MODE, MIXED_MODE]
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "CompilerInputMode.allCases" in compile_view
    assert "Text(mode.rawValue)" in compile_view


def test_dataset_row_compile_plan_parses_then_maps_without_construct() -> None:
    plan = _compile_plan_source()
    assert '["map", workspace.path, "--goal", goal]' in plan
    assert '["--plan", mappingPlanURL.path]' in plan
    assert "StageCommand(stage: .map," in plan
    assert "includesMapping" in plan
    assert "clean" in plan
    document_return = plan[plan.index("let hasSegmentationOverride") :]
    assert "StageCommand(stage: .clean," in document_return
    mapping_return = plan[
        plan.index("if includesMapping, let mappingPlanURL") : plan.index(
            "let hasSegmentationOverride"
        )
    ]
    assert "StageCommand(stage: .clean," not in mapping_return
    assert "StageCommand(stage: .chunk," not in mapping_return
    assert "StageCommand(stage: .construct," not in mapping_return
    assert "StageCommand(stage: .map," in mapping_return


def test_unconfirmed_mapping_cannot_compile() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "Confirm a mapping plan before compiling. The workbench does not auto-confirm." in model
    assert "func confirmSelectedMappingPlan()" in model
    assert "confirmedMappingPlan = plan" in model
    detect = re.search(
        r"func detectMapping\(\) \{(?P<body>.*?)\n    \}",
        model,
        re.S,
    )
    assert detect is not None
    assert "confirmedMappingPlan =" not in detect.group("body")
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "Confirm mapping plan" in compile_view
    assert "does not auto-confirm" in compile_view or "Detecting a plan does not confirm" in compile_view


def test_family_goals_wait_for_confirmed_dataset_row_mapping() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "requiresMappedValueEvidence" in model
    assert "confirmedMappingPlan?.goalID == goal.goalID" in model
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    assert "var requiresMappedValueEvidence: Bool" in models
    assert ".explicitLabel, .preferencePair, .toolCall, .stepwise" in models
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "workbench.selectableGoals" in compile_view
    catalog = json.loads(_read("src/veriformis/goals/catalog-v1.json"))
    ids = {item["goal_id"] for item in catalog["goals"]}
    assert set(FAMILY_GOAL_IDS) <= ids


def test_mixed_refuses_fused_document_and_row_members() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "mixedSourcesAreFused" in model
    assert (
        "mixed mode keeps construction and imported-row provenance distinct; "
        "compile document-source and dataset-row workspaces separately rather "
        "than fusing them in one stage graph"
    ) in model
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "mixedSourcesAreFused" in compile_view


def test_mapping_preview_is_wired_and_not_an_execute() -> None:
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "mapping-preview" in cli
    assert "func previewMapping(" in cli
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "previewConfirmedMapping" in model
    assert "case .ready = mappingPreviewState" in model
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "MappingView.swift" not in views


def test_no_family_to_trainer_chrome() -> None:
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    for haystack in (compile_view, model):
        assert "family-to-trainer" not in haystack
        assert "trl-sft" not in haystack
        assert "llama-factory" not in haystack.lower()
        assert "axolotl" not in haystack.lower()


def test_public_surfaces_still_have_no_generator() -> None:
    forbidden = {"generator", "install-extension"}
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(forbidden)
    assert mcp_names.isdisjoint(forbidden)
    service = PipelineService()
    assert not hasattr(service, "generator_pass")
