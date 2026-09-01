"""Phase 19.9: skip retry because ADR-0020 Decision A installs no execute."""

from __future__ import annotations

from pathlib import Path

from veriformis.cli import app
from veriformis.mcp.server import create_mcp_server
from veriformis.publication import PUBLICATION_ADAPTER_LIMITATIONS, create_publication_adapter


ROOT = Path(__file__).resolve().parents[2]
SKIP = (
    ROOT
    / "dev/active/independent-product/phase-19-automation-and-publication"
    / "skipped-publication-retry.md"
)


def test_retry_is_skipped_because_decision_a_has_no_execute() -> None:
    text = SKIP.read_text(encoding="utf-8")
    assert "ADR-0020 Decision A" in text
    assert "retry" in text.lower()
    assert "idempotency" in text.lower()
    pin = create_publication_adapter(
        repository="ogprotege/example-dataset",
        revision="main",
    )
    assert pin.execute_allowed is False
    assert pin.retry_allowed is False
    assert "no-retry" in PUBLICATION_ADAPTER_LIMITATIONS
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "hub-upload" not in cli_names
    assert "hub_upload" not in mcp_names
    assert "hub-retry" not in cli_names
    assert "hub_retry" not in mcp_names
