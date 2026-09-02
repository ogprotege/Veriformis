"""Phase 19.10: adversarial automation closeout. Do not start Phase 20 from that packet."""

from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.publication import create_publication_adapter
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION, _STAGE_ORDER
from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "dev/active/independent-product/phase-19-automation-and-publication"
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
_FORBIDDEN = frozenset(
    {
        "generator",
        "hub-upload",
        "hub_upload",
        "install-extension",
    }
)


def _cli_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _mcp_names() -> set[str]:
    return {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}


def test_pipeline_v1_and_goldens_hold() -> None:
    assert PIPELINE_SCHEMA_VERSION == "veriformis.pipeline/v1"
    assert "map" not in _STAGE_ORDER
    assert "export" not in _STAGE_ORDER
    from veriformis.identity import sha256_digest

    assert sha256_digest(KIT.read_bytes()) == KIT_SHA256
    fingerprint = json.loads(
        (ROOT / "examples/project-spec/expected-fingerprint.json").read_text(encoding="utf-8")
    )
    assert fingerprint["manifest_sha256"]


def test_hub_and_package_mcp_stay_absent() -> None:
    cli_names = _cli_names()
    mcp_names = _mcp_names()
    assert cli_names.isdisjoint(_FORBIDDEN)
    assert mcp_names.isdisjoint(_FORBIDDEN)
    assert "quality-report" in cli_names
    assert "quality_report" not in mcp_names
    assert "package" not in mcp_names
    assert "package_verify" not in mcp_names
    assert "spec_run" in mcp_names
    assert "run_pipeline" in mcp_names
    assert not hasattr(PipelineService(), "hub_upload")
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    pin = create_publication_adapter(repository="ogprotege/example", revision="main")
    assert pin.execute_allowed is False
    assert pin.retry_allowed is False
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "HF_TOKEN" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "huggingface_hub" not in " ".join(project["project"]["dependencies"])
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "xcodebuild" in workflows
    assert "xcodebuild-debug (optional)" in workflows
    assert "secrets:" not in workflows.lower()
    assert support_matrix().platforms.public_signed_mac is False


def test_core_compile_names_no_network_client() -> None:
    path = ROOT / "src/veriformis/pipeline/service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint({"httpx", "huggingface_hub", "openai", "requests"})


def test_closeout_does_not_start_phase_20_from_this_packet() -> None:
    closeout = (PACKET / "closeout.md").read_text(encoding="utf-8")
    assert "**Status:** Complete" in closeout
    assert "Do not start Phase 20 from this packet." in closeout
    assert "ADR-0020 Decision A" in closeout
    program = json.loads(
        (ROOT / "dev/active/independent-product/program.json").read_text(encoding="utf-8")
    )
    phases = {item["number"]: item for item in program["phases"]}
    assert phases[19]["status"] == "completed"
    assert phases[20]["packet"] == "dev/active/independent-product/phase-20-stable-1.0"
    assert phases[20]["status"] in {"in_progress", "completed"}
    assert (PACKET / "skipped-package-mcp.md").is_file()
    assert (PACKET / "skipped-publication-retry.md").is_file()
    assert (ROOT / "docs/adr/0020-publication-boundary.md").is_file()
