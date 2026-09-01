"""Phase 20.1 isolation: still 0.1.0 alpha; no 1.0 claim, Hub, or signed Mac."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from veriformis import __version__
from veriformis.cli import app
from veriformis.goals import recipe_defaults
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.publication import create_publication_adapter
from veriformis.quality.gates import V1_QUALITY_GATES
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION, _STAGE_ORDER


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "dev/active/independent-product/phase-20-stable-1.0"
PHASE19 = ROOT / "dev/active/independent-product/phase-19-automation-and-publication"
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
_EMPTY_EXTRAS = (
    "trl",
    "mlx-lm",
    "columnar",
    "axolotl",
    "llama-factory",
    "unsloth",
    "ocr",
)


def _cli_names() -> set[str]:
    return {command.name for command in app.registered_commands}


def _mcp_names() -> set[str]:
    return {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}


def test_version_and_maturity_remain_alpha() -> None:
    assert __version__ == "0.1.0"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "Development Status :: 3 - Alpha" in project["project"]["classifiers"]
    assert "Development Status :: 5 - Production/Stable" not in project["project"]["classifiers"]
    support = json.loads(
        (ROOT / "docs/governance/support-registry.json").read_text(encoding="utf-8")
    )
    assert support["product"]["version"] == "0.1.0"
    assert support["product"]["maturity"] == "development-alpha"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Development alpha `0.1.0`" in readme
    assert "Not a public beta. Not production." in readme


def test_support_matrix_pin_exists_without_version_bump_or_lifecycle_docs() -> None:
    assert (ROOT / "docs/contracts/support-matrix-v1.md").is_file()
    assert (ROOT / "src/veriformis/release/support-matrix-v1.json").is_file()
    assert (ROOT / "src/veriformis/release/matrix.py").is_file()
    assert not (ROOT / "docs/support-lifecycle.md").is_file()
    assert (ROOT / "docs/migration.md").is_file()
    migration = (ROOT / "docs/migration.md").read_text(encoding="utf-8")
    assert "upgrade-workspace" in migration
    assert "Unknown versions fail closed" in migration
    from veriformis.release import support_matrix

    matrix = support_matrix()
    assert matrix.product_version == "0.1.0"
    assert matrix.maturity == "development-alpha"
    assert matrix.platforms.public_signed_mac is False
    assert matrix.hub_execute is False
    assert "support-matrix" in _cli_names()
    assert "support_matrix" in _mcp_names()


def test_pipeline_hub_quality_and_extras_hold() -> None:
    assert PIPELINE_SCHEMA_VERSION == "veriformis.pipeline/v1"
    assert "map" not in _STAGE_ORDER
    cli_names = _cli_names()
    mcp_names = _mcp_names()
    assert cli_names.isdisjoint(_FORBIDDEN)
    assert mcp_names.isdisjoint(_FORBIDDEN)
    assert not hasattr(PipelineService(), "hub_upload")
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
    assert recipe_defaults().review_policy == "none"
    pin = create_publication_adapter(repository="ogprotege/example", revision="main")
    assert pin.execute_allowed is False
    assert pin.retry_allowed is False
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = project["project"]["optional-dependencies"]
    for name in _EMPTY_EXTRAS:
        assert extras[name] == []
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "xcodebuild" not in workflows
    assert "HF_TOKEN" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_phase20_packet_opened_without_claiming_1_0() -> None:
    readme = (PACKET / "README.md").read_text(encoding="utf-8")
    assert "**Status:** In progress" in readme
    assert "Version stays `0.1.0` development alpha" in readme
    plan = (PACKET / "plan.md").read_text(encoding="utf-8")
    assert "Honesty only in 20.1" in plan
    closeout = (PACKET / "closeout.md").read_text(encoding="utf-8")
    assert "**Status:** Open" in closeout
    assert "Do not invent a Phase 21" in closeout
    phase19 = (PHASE19 / "closeout.md").read_text(encoding="utf-8")
    assert "Do not start Phase 20 from this packet." in phase19
    program = json.loads(
        (ROOT / "dev/active/independent-product/program.json").read_text(encoding="utf-8")
    )
    phases = {item["number"]: item for item in program["phases"]}
    assert phases[19]["status"] == "completed"
    assert phases[20]["status"] == "in_progress"
    assert phases[20]["packet"] == "dev/active/independent-product/phase-20-stable-1.0"
    assert phases[20]["completed_on"] is None
    assert not list((ROOT / "dev/active/independent-product").glob("phase-21-*"))
