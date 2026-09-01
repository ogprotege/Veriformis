"""Phase 19.7: ADR-0020 Decision A publication pin. Loading is not upload."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.contracts import (
    PUBLICATION_ADAPTER_CONTRACT_ID,
    PUBLICATION_ADAPTER_CONTRACT_VERSION,
    PUBLICATION_ADAPTER_SCHEMA_ID,
)
from veriformis.errors import PublicationAdapterError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.publication import (
    PUBLICATION_ADAPTER_LIMITATIONS,
    create_publication_adapter,
    load_publication_adapter,
)


ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/0020-publication-boundary.md"


def _pin(**overrides: object):
    defaults: dict[str, object] = {
        "repository": "ogprotege/example-dataset",
        "revision": "main",
    }
    defaults.update(overrides)
    return create_publication_adapter(**defaults)  # type: ignore[arg-type]


def test_load_accepts_a_pin_and_is_not_upload() -> None:
    pin = _pin()
    loaded = load_publication_adapter(pin.model_dump(mode="json"))
    assert loaded == pin
    assert loaded.contract_id == PUBLICATION_ADAPTER_CONTRACT_ID
    assert loaded.contract_version == PUBLICATION_ADAPTER_CONTRACT_VERSION
    assert loaded.schema_id == PUBLICATION_ADAPTER_SCHEMA_ID
    assert loaded.execute_allowed is False
    assert loaded.retry_allowed is False
    assert loaded.credential_source == "none"
    assert loaded.local_container_is_not_upload is True
    assert loaded.generation_allowed is False
    assert loaded.plugin_install_allowed is False
    assert "no-hub-upload" in PUBLICATION_ADAPTER_LIMITATIONS
    assert "huggingface_hub" not in (
        ROOT / "src/veriformis/publication/adapter.py"
    ).read_text(encoding="utf-8")


def test_execute_and_credentials_fail_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["execute_allowed"] = True
    with pytest.raises(PublicationAdapterError, match="cannot allow execute"):
        load_publication_adapter(payload)
    payload = _pin().model_dump(mode="json")
    payload["credential_source"] = "hf_token"
    with pytest.raises(PublicationAdapterError, match="credential_source must be none"):
        load_publication_adapter(payload)
    payload = _pin().model_dump(mode="json")
    payload["hf_token"] = "secret"
    with pytest.raises(PublicationAdapterError, match="unknown"):
        load_publication_adapter(payload)


def test_unknown_version_fails_closed() -> None:
    payload = _pin().model_dump(mode="json")
    payload["schema_id"] = "veriformis.publication-adapter/v2"
    with pytest.raises(PublicationAdapterError):
        load_publication_adapter(payload)


def test_public_surfaces_have_no_hub_upload() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "hub-upload" not in cli_names
    assert "hub_upload" not in mcp_names
    assert not hasattr(PipelineService(), "hub_upload")
    assert ADR.is_file()
    text = ADR.read_text(encoding="utf-8")
    assert "Decision A" in text
    assert "no Hub execute" in text or "installs no Hub" in text
    assert (ROOT / "docs/contracts/publication-adapter-v1.md").is_file()
