"""Phase 18.10: adversarial workbench refusals, unchanged goldens, skipped extras."""

from __future__ import annotations

import ast
import base64
import json
import re
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from veriformis.cli import app
from veriformis.contracts import PRODUCT_ROW_SCHEMA_KINDS, V1_ROW_SCHEMA_KINDS
from veriformis.errors import ReviewError, TaxonomyError, WorkbenchAdapterError
from veriformis.exports.constrained_csv import _COLUMNS_BY_ROW_SCHEMA
from veriformis.identity import derive_id, sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.review.seal import assert_required_reviews_resolved
from veriformis.taxonomy import (
    PROFILE_FORBIDDEN_ROW_SCHEMAS,
    assert_profile_row_compatible,
)
from veriformis.workbench import (
    FAIL_CLOSED_REASONS,
    WRAP_COMMANDS,
    create_workbench_adapter,
    load_workbench_adapter,
)


ROOT = Path(__file__).resolve().parents[2]
MACOS = ROOT / "macos/Sources"
ADR17 = ROOT / "docs/adr/0017-no-untrusted-extension-loader.md"
ADR18 = ROOT / "docs/adr/0018-no-compile-path-generator.md"
ADR19 = ROOT / "docs/adr/0019-thin-workbench-adapter.md"
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
EXPECTED_BUNDLE_ID = (
    "bundle-v1-49a6b50ed50218b8a22ce834dc69a64eb8d47f0605267bc029b3f938a6b13b4a"
)
_FAMILY_SCHEMAS = (
    "label-classification",
    "preference-pair",
    "tool-call-conversation",
    "stepwise-trace",
)
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "generator",
        "generator-pass",
        "generator_pass",
        "install-extension",
        "install_plugin",
        "install-plugin",
        "plugin-load",
        "hub-upload",
    }
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _macos() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in MACOS.rglob("*.swift"))


def test_unconfirmed_mapping_cannot_compile() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert (
        "Confirm a mapping plan before compiling. The workbench does not auto-confirm."
        in model
    )
    assert "func confirmSelectedMappingPlan()" in model
    detect = re.search(
        r"func detectMapping\(\) \{(?P<body>.*?)\n    \}",
        model,
        re.S,
    )
    assert detect is not None
    assert "confirmedMappingPlan =" not in detect.group("body")
    compile_gate = model[model.index("var canCompile: Bool") : model.index("var canPreflight")]
    assert "confirmedMappingPlan" in compile_gate
    assert "plan.goalID == selectedGoalID" in compile_gate
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    assert "Mapping preview requires a confirmed mapping plan for this file." in models


def test_truncated_discovery_fails_closed() -> None:
    assert FAIL_CLOSED_REASONS == ("cancelled", "schema-invalid", "truncated")
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    assert "standardOutputTruncated" in cli
    assert cli.count("guard !result.standardOutputTruncated else {") >= 8
    assert "output was truncated; no response was accepted." in cli
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    for message in (
        "Taxonomy discovery output was truncated.",
        "Goal discovery output was truncated.",
        "Mapping detection output was truncated.",
        "Mapping preview output was truncated.",
        "Review command output was truncated.",
    ):
        assert message in models


def test_family_schemas_cannot_select_a_refusing_profile() -> None:
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    admitted = models[models.index("static func admitted(") :]
    assert "guard let rowSchema else { return generic }" in admitted
    assert "consumer.acceptedRowSchemas.contains(rowSchema)" in admitted
    assert "profile.supportedRowSchemas.contains(rowSchema)" in admitted
    view = _read("macos/Sources/Views/ExportsView.swift")
    assert "No named profile admits schema" in view
    assert "family-to-trainer" not in view
    for profile in ("trl", "mlx-lm", "axolotl", "llama-factory", "aptus"):
        forbidden = set(PROFILE_FORBIDDEN_ROW_SCHEMAS[profile])
        assert set(_FAMILY_SCHEMAS) <= forbidden
        for schema in _FAMILY_SCHEMAS:
            with pytest.raises(TaxonomyError, match=schema):
                assert_profile_row_compatible(profile, schema)


def test_constrained_csv_still_refuses_nested_and_family_rows() -> None:
    assert dict(_COLUMNS_BY_ROW_SCHEMA) == {
        "instruction_output": ("instruction", "input", "output"),
        "prompt_completion": ("prompt", "completion"),
        "text": ("text",),
    }
    for schema in _FAMILY_SCHEMAS:
        assert schema not in _COLUMNS_BY_ROW_SCHEMA
        assert schema in PRODUCT_ROW_SCHEMA_KINDS
        assert schema not in V1_ROW_SCHEMA_KINDS
    view = _read("macos/Sources/Views/ExportsView.swift")
    assert "Constrained CSV still refuses nested and family rows" in view
    models = _read("macos/Sources/Models/WorkbenchModels.swift")
    assert '"constrained-csv"' in models
    assert "WorkbenchGenericExportContainers.order" in models


def test_required_unresolved_reviews_still_block_seal() -> None:
    with pytest.raises(ReviewError, match="required review is unresolved"):
        assert_required_reviews_resolved(
            SimpleNamespace(
                decisions=(SimpleNamespace(status="pending_review"),),
            )
        )
    view = _read("macos/Sources/Views/ReviewView.swift")
    assert "Required unresolved reviews still block seal" in view
    assert "Default review_policy stays none" in view
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "review_policy = \"required\"" not in model
    assert "reviewPolicy = \"required\"" not in view
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_generator_and_plugin_ui_remain_absent() -> None:
    adr17 = ADR17.read_text(encoding="utf-8")
    adr18 = ADR18.read_text(encoding="utf-8")
    adr19 = ADR19.read_text(encoding="utf-8")
    assert "Phase 16 does not install an untrusted loader." in adr17
    assert "Phase 17 does not install a compile-path generator." in adr18
    assert (
        "**Decision A.** The Mac workbench is a process adapter over "
        "PipelineService and the CLI."
    ) in adr19
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    assert not (ROOT / "src/veriformis/generation").exists()
    assert not (ROOT / "src/veriformis/generator.py").exists()
    views = {path.name for path in (MACOS / "Views").glob("*.swift")}
    assert "GeneratorView.swift" not in views
    assert "PluginView.swift" not in views
    macos = _macos()
    assert "GeneratorPass" not in macos
    assert "install-extension" not in macos
    assert "hub-upload" not in macos
    payload = create_workbench_adapter(
        command="goals",
        surface="discover",
        request_schema_id="veriformis.goal-catalog/v1",
        response_schema_id="veriformis.goal-catalog/v1",
    ).model_dump(mode="json")
    payload["generation_allowed"] = True
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(WorkbenchAdapterError, match="ADR-0018"):
        load_workbench_adapter(payload)
    payload["generation_allowed"] = False
    payload["plugin_install_allowed"] = True
    payload["adapter_id"] = derive_id(
        "wba",
        {key: value for key, value in payload.items() if key != "adapter_id"},
    )
    with pytest.raises(WorkbenchAdapterError, match="ADR-0017"):
        load_workbench_adapter(payload)
    assert "generator" not in WRAP_COMMANDS
    assert "install-extension" not in WRAP_COMMANDS


def test_aptus_handoff_stays_off_by_default() -> None:
    model = _read("macos/Sources/ViewModels/WorkbenchViewModel.swift")
    assert "defaultWriteAptusHandoff = false" in model
    compile_view = _read("macos/Sources/Views/CompileView.swift")
    assert "Aptus is optional Integrations, not required." in compile_view
    assert "Integrations (optional)" in compile_view
    cli = _read("macos/Sources/Services/VeriformisCLI.swift")
    plan = re.search(
        r"static func compilePlan\([\s\S]*?\n    static func ",
        cli,
    )
    assert plan is not None
    assert "includeHandoff: Bool = false" in plan.group(0)
    home = _read("macos/Sources/Views/HomeView.swift")
    assert "Aptus is optional Integrations. It is not required." in home


def test_public_surfaces_still_have_no_generator_plugin_or_hub() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))
    source = _read("src/veriformis/pipeline/service.py")
    tree = ast.parse(source)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "GeneratorPass" not in names
    project = tomllib.loads(_read("pyproject.toml"))["project"]
    assert project["scripts"] == {"veriformis": "veriformis.cli:main"}
    assert "entry-points" not in project


def test_skipped_extras_have_records_and_phase_19_did_not_start_from_this_packet() -> None:
    closeout = _read(
        "dev/active/independent-product/phase-18-goal-first-workbench/closeout.md"
    )
    assert "**Status:** Complete" in closeout
    assert "Do not start Phase 19 from this packet." in closeout
    for skipped in (
        "Family-to-trainer mapping UI",
        "Generator UI",
        "Plugin UI",
        "Hub upload",
        "Signed/notarized Mac",
        "GitHub xcodebuild",
        "Virtualization",
        "Full localization",
    ):
        assert skipped in closeout
    workflows = ROOT / ".github/workflows"
    texts = "\n".join(path.read_text(encoding="utf-8") for path in workflows.glob("*.yml"))
    assert "xcodebuild" in texts
    assert "xcodebuild-debug (optional)" in texts
    pbx = _read("macos/Veriformis.xcodeproj/project.pbxproj")
    assert "developmentRegion = en;" in pbx
    sources = _read("macos/Sources/Views/SourceDropView.swift")
    assert "LazyVStack" not in sources
    program = json.loads(_read("dev/active/independent-product/program.json"))
    phases = {item["number"]: item for item in program["phases"]}
    assert phases[18]["status"] == "completed"
    assert phases[19]["packet"] == (
        "dev/active/independent-product/phase-19-automation-and-publication"
    )
    assert phases[19]["status"] == "completed"
    assert phases[20]["packet"] == "dev/active/independent-product/phase-20-stable-1.0"
    assert phases[20]["status"] in {"in_progress", "completed"}


def test_phase16_kit_and_sft_sealed_bundle_identities_hold(tmp_path: Path) -> None:
    kit_bytes = KIT.read_bytes()
    assert sha256_digest(kit_bytes) == KIT_SHA256
    fixture = json.loads(
        (
            ROOT
            / "tests/regressions/fixtures/phase3/pre-taxonomy-full-text.vfbundle.json"
        ).read_text(encoding="utf-8")
    )
    bundle = tmp_path / "sealed.vfbundle"
    for relative_path, encoded in fixture["files_base64"].items():
        destination = bundle.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(base64.b64decode(encoded, validate=True))
    assert (
        sha256_digest((bundle / "manifest.json").read_bytes())
        == EXPECTED_MANIFEST_SHA256
    )
    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    assert outcome.exit_status == 0
    assert outcome.verification is not None
    assert outcome.verification.bundle_id == EXPECTED_BUNDLE_ID
