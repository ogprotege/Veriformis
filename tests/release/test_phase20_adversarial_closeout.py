"""Phase 20.10: retain 0.1.0 alpha. Do not invent a Phase 21."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from veriformis import __version__
from veriformis.cli import app
from veriformis.identity import sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.publication import create_publication_adapter
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION, _STAGE_ORDER
from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "dev/active/independent-product/phase-20-stable-1.0"
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
_FORBIDDEN = frozenset(
    {
        "generator",
        "hub-upload",
        "hub_upload",
        "install-extension",
        "quality-report",
        "quality_report",
    }
)


def _cli_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _mcp_names() -> set[str]:
    return {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}


def test_version_classifier_and_matrix_stay_alpha() -> None:
    assert __version__ == "0.1.0"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "Development Status :: 3 - Alpha" in project["project"]["classifiers"]
    assert "Development Status :: 5 - Production/Stable" not in project["project"]["classifiers"]
    matrix = support_matrix()
    assert matrix.product_version == "0.1.0"
    assert matrix.maturity == "development-alpha"
    assert matrix.claim == "cli-first-independent-core"
    assert matrix.platforms.public_signed_mac is False
    assert matrix.hub_execute is False
    assert matrix.generator is False
    assert matrix.plugin_loader is False
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Development alpha `0.1.0`" in readme
    assert "Not a public beta. Not production." in readme


def test_goldens_and_forbidden_surfaces_hold() -> None:
    assert PIPELINE_SCHEMA_VERSION == "veriformis.pipeline/v1"
    assert "map" not in _STAGE_ORDER
    assert sha256_digest(KIT.read_bytes()) == KIT_SHA256
    fingerprint = json.loads(
        (ROOT / "examples/project-spec/expected-fingerprint.json").read_text(encoding="utf-8")
    )
    assert (
        fingerprint["manifest_sha256"]
        == "d3f76eb9993476def1bb373ed80eccc9ac7a1bc529c96c04e6667eaa02e88ac8"
    )
    cli_names = _cli_names()
    mcp_names = _mcp_names()
    assert cli_names.isdisjoint(_FORBIDDEN)
    assert mcp_names.isdisjoint(_FORBIDDEN)
    assert not hasattr(PipelineService(), "hub_upload")
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    pin = create_publication_adapter(repository="ogprotege/example", revision="main")
    assert pin.execute_allowed is False
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "xcodebuild" not in workflows


def test_closeout_retains_alpha_and_does_not_invent_phase_21() -> None:
    closeout = (PACKET / "closeout.md").read_text(encoding="utf-8")
    assert "**Status:** Complete" in closeout
    assert "Version remains `0.1.0` development alpha" in closeout
    assert "Do not invent a Phase 21" in closeout
    assert "goldens stay byte-identical" in closeout
    readme = (PACKET / "README.md").read_text(encoding="utf-8")
    assert "**Status:** Complete" in readme
    program = json.loads(
        (ROOT / "dev/active/independent-product/program.json").read_text(encoding="utf-8")
    )
    phases = {item["number"]: item for item in program["phases"]}
    assert phases[19]["status"] == "completed"
    assert phases[20]["status"] == "completed"
    assert phases[20]["completed_on"] == "2026-09-01"
    assert phases[20]["packet"] == "dev/active/independent-product/phase-20-stable-1.0"
    assert not list((ROOT / "dev/active/independent-product").glob("phase-21-*"))
    assert (PACKET / "skipped-signed-mac.md").is_file()
    assert (ROOT / "docs/support-lifecycle.md").is_file()
    assert (ROOT / "docs/consumer-profiles.md").is_file()
