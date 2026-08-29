"""Phase 18.1 isolation: current Mac workbench is a document-source CLI shell."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "generator",
        "generator-pass",
        "generator_pass",
        "install-extension",
        "install_plugin",
        "install-plugin",
        "plugin-load",
    }
)
_COMPILE_PLAN_STAGES = (
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


def test_sidebar_remains_home_compile_history_settings() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    block = re.search(
        r"enum SidebarDestination[^{]*\{(?P<body>.*?)\n\}",
        models,
        re.S,
    )
    assert block is not None
    cases = re.findall(r"^\s*case (\w+)$", block.group("body"), re.M)
    assert cases == ["home", "compile", "exports", "history", "settings"]
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "ReviewView.swift" not in views
    assert "ExportsView.swift" in views
    assert "MappingView.swift" not in views


def test_default_compile_plan_still_omits_mode_flag() -> None:
    plan = _compile_plan_source()
    parse = re.search(r"var parseArgs = \[([^\]]+)\]", plan)
    assert parse is not None
    assert parse.group(1) == '"parse"'
    assert "mode: CompilerInputMode = .documentSource" in plan
    assert 'parseArgs.append(contentsOf: ["--mode", mode.rawValue])' in plan
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    pipeline = re.search(
        r"static var pipelineStages: \[WorkbenchStage\] \{\s*\[([^\]]+)\]",
        models,
    )
    assert pipeline is not None
    stages = tuple(re.findall(r"\.(\w+)", pipeline.group(1)))
    assert stages == _COMPILE_PLAN_STAGES
    assert '"map"' in plan
    assert ".datasetRow" in plan


def test_mapping_is_wired_and_export_review_remain_unused_by_views() -> None:
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "mapping-detect" in cli
    assert "mapping-preview" in cli
    assert "func discoverExports(" in cli
    assert '["export", "discover"]' in cli
    assert '["export", "dry-run"' in cli
    assert '["export", "execute"' in cli
    views = "\n".join(
        path.read_text(encoding="utf-8") for path in (MACOS / "Views").glob("*.swift")
    )
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "detectMapping" in model
    assert "confirmSelectedMappingPlan" in model
    assert "mapping-detect" in views or "Detect mapping" in views
    assert "discoverExports" in model
    assert "executeConfirmedExport" in model
    assert "ExportsView.swift" in {path.name for path in (MACOS / "Views").glob("*.swift")}
    for haystack in (views, model):
        assert "review-export" not in haystack
        assert "review-submit" not in haystack


def test_workbench_aptus_handoff_defaults_off() -> None:
    source = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    match = re.search(r"defaultWriteAptusHandoff\s*=\s*(true|false)\b", source)
    assert match is not None
    assert match.group(1) == "false"


def test_adr_0017_and_0018_still_forbid_loader_and_generator() -> None:
    adr17 = _read("docs/adr/0017-no-untrusted-extension-loader.md")
    adr18 = _read("docs/adr/0018-no-compile-path-generator.md")
    assert "Phase 16 does not install an untrusted loader." in adr17
    assert "Phase 17 does not install a compile-path generator." in adr18
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    assert not (ROOT / "src/veriformis/generation").exists()
    assert not (ROOT / "src/veriformis/generator.py").exists()
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    assert project["scripts"] == {"veriformis": "veriformis.cli:main"}
    assert "entry-points" not in project


def test_public_surfaces_still_have_no_generator_or_plugin_operation() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))


def test_pipeline_service_still_names_no_generator() -> None:
    source = _read("src/veriformis/pipeline/service.py")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "GeneratorPass" not in names
    assert "openai" not in names
    assert "httpx" not in names
    macos = "\n".join(path.read_text(encoding="utf-8") for path in MACOS.rglob("*.swift"))
    assert "GeneratorPass" not in macos


def test_quality_stays_preview_only() -> None:
    assert V1_QUALITY_GATES
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
