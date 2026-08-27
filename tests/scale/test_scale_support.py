"""Phase 15.4: operator-reviewed scale support; published tiers stay empty."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    SCALE_SUPPORT_CONTRACT_ID,
    SCALE_SUPPORT_CONTRACT_VERSION,
    SCALE_SUPPORT_DISCOVERY_SCHEMA_ID,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.scale.support import (
    scale_support_catalog,
    scale_support_catalog_json,
    scale_support_discovery,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "veriformis" / "scale" / "support-v1.json"
RUNNER = CliRunner()
SERVICE = PipelineService()


def test_support_catalog_is_canonical() -> None:
    stored = DATA.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert scale_support_catalog_json() == stored


def test_published_tiers_are_empty_and_not_an_sla() -> None:
    catalog = scale_support_catalog()
    assert catalog.schema_id == SCALE_SUPPORT_DISCOVERY_SCHEMA_ID
    assert catalog.contract_id == SCALE_SUPPORT_CONTRACT_ID
    assert catalog.contract_version == SCALE_SUPPORT_CONTRACT_VERSION
    assert catalog.published_tiers == ()
    assert catalog.sla_claim is False
    assert catalog.statistical_meaning is False
    assert catalog.operator_review == "2026-08-27"
    assert all(item.seal_observed for item in catalog.observed)
    ids = {item.observation_id for item in catalog.observed}
    assert "measure-markdown-100-1000" in ids
    assert "dataset-row-text-jsonl-cli" in ids
    refused = {item.observation_id for item in catalog.refusals}
    assert refused == {"ci-tiny-jsonl", "measure-markdown-duplicates-10-40"}
    assert catalog.unmeasured == (
        "dataset-row-at-ladder-scale",
        "document-source-above-1-mib",
        "export-sharding-as-bottleneck",
        "streaming-compile",
    )
    for item in catalog.observed:
        evidence = ROOT / item.evidence
        assert evidence.is_file(), item.evidence
    for item in catalog.refusals:
        assert (ROOT / item.evidence).is_file()
        assert item.sla_claim is False


def test_python_cli_mcp_agree_on_scale_support() -> None:
    python_payload = SERVICE.discover_scale_support()
    assert python_payload == scale_support_discovery()
    cli = RUNNER.invoke(app, ["scale-support"])
    assert cli.exit_code == 0, cli.output
    cli_payload = json.loads(cli.output)
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp_payload = json.loads(tools["scale_support"]())
    assert python_payload == cli_payload == mcp_payload
    assert python_payload["published_tiers"] == []
    assert python_payload["sla_claim"] is False
