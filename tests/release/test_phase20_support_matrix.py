"""Phase 20.2: frozen CLI-first 1.0 support matrix. Not a version bump."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from veriformis import __version__
from veriformis.cli import app
from veriformis.contracts import (
    SUPPORT_MATRIX_CONTRACT_ID,
    SUPPORT_MATRIX_CONTRACT_VERSION,
    SUPPORT_MATRIX_SCHEMA_ID,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.release import (
    REQUIRED_EXCLUSIONS,
    support_matrix,
    support_matrix_discovery,
    support_matrix_json,
)
from veriformis.taxonomy import (
    CANDIDATE_CONSUMER_PROFILES,
    IMPLEMENTED_CONSUMER_PROFILES,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
    IMPLEMENTED_PHYSICAL_CONTAINERS,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "veriformis" / "release" / "support-matrix-v1.json"
RUNNER = CliRunner()
SERVICE = PipelineService()


def test_support_matrix_is_canonical_and_still_alpha() -> None:
    stored = DATA.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert support_matrix_json() == stored
    matrix = support_matrix()
    assert matrix.schema_id == SUPPORT_MATRIX_SCHEMA_ID
    assert matrix.contract_id == SUPPORT_MATRIX_CONTRACT_ID
    assert matrix.contract_version == SUPPORT_MATRIX_CONTRACT_VERSION
    assert matrix.claim == "cli-first-independent-core"
    assert matrix.product_version == __version__ == "0.1.0"
    assert matrix.maturity == "development-alpha"
    assert matrix.version_change_deferred_to == "20.10"
    assert matrix.platforms.public_signed_mac is False
    assert matrix.hub_execute is False
    assert matrix.generator is False
    assert matrix.plugin_loader is False
    assert matrix.hosted_training is False
    assert matrix.quality_report_command is True
    assert matrix.aptus_required is False
    assert matrix.published_corpus_tiers == ()
    assert tuple(item.exclusion_id for item in matrix.exclusions) == REQUIRED_EXCLUSIONS


def test_support_matrix_matches_implemented_registries() -> None:
    matrix = support_matrix()
    support = json.loads(
        (ROOT / "docs/governance/support-registry.json").read_text(encoding="utf-8")
    )
    assert matrix.containers == tuple(IMPLEMENTED_PHYSICAL_CONTAINERS)
    assert matrix.profiles.implemented == tuple(IMPLEMENTED_CONSUMER_PROFILES)
    assert matrix.profiles.optional_export_adapters == tuple(
        IMPLEMENTED_EXPORT_CONSUMER_PROFILES
    )
    assert matrix.profiles.candidate_not_executable == tuple(CANDIDATE_CONSUMER_PROFILES)
    assert matrix.profiles.extras_required == ()
    assert "unsloth" in matrix.profiles.candidate_not_executable
    assert matrix.training.goals == tuple(support["training"]["implemented_goals"])
    assert matrix.inputs.modes == tuple(support["inputs"]["implemented_modes"])
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = project["project"]["optional-dependencies"]
    for name in matrix.profiles.extras_empty:
        assert optional[name] == []


def test_python_cli_mcp_agree_on_support_matrix() -> None:
    python_payload = SERVICE.discover_support_matrix()
    assert python_payload == support_matrix_discovery()
    cli = RUNNER.invoke(app, ["support-matrix"])
    assert cli.exit_code == 0, cli.output
    cli_payload = json.loads(cli.output)
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp_text = tools["support_matrix"]()
    mcp_payload = json.loads(mcp_text)
    assert python_payload == cli_payload == mcp_payload
    assert mcp_text == cli.output
    assert python_payload["product_version"] == "0.1.0"
    assert python_payload["platforms"]["public_signed_mac"] is False
    assert python_payload["hub_execute"] is False


def test_unknown_field_fails_closed() -> None:
    from pydantic import ValidationError

    from veriformis.errors import SupportMatrixError
    from veriformis.release.matrix import SupportMatrix

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    payload["invented_field"] = True
    try:
        SupportMatrix.model_validate(payload)
    except (SupportMatrixError, ValidationError) as exc:
        assert "invented_field" in str(exc) or "Extra" in str(exc) or "extra" in str(exc)
    else:
        raise AssertionError("unknown support-matrix field must fail closed")
