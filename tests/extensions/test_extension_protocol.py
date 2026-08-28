"""Phase 16.2 extension protocol: load and refuse declarations only."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriformis.cli import app
from veriformis.contracts import (
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
    EXTENSION_PROTOCOL_SCHEMA_ID,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.extensions import (
    EXTENSION_KINDS,
    EXTENSION_LIFECYCLES,
    EXTENSION_ORIGINS,
    PROTOCOL_LIMITATIONS,
    CapabilityDeclaration,
    create_capability_declaration,
    load_capability_declaration,
)
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


def _declaration(**overrides: object) -> CapabilityDeclaration:
    kind = overrides.get("kind", "source-parser")
    defaults: dict[str, object] = {
        "kind": "source-parser",
        "origin": "builtin",
        "lifecycle": "supported",
        "extra": None,
        "selector": "text",
        "title": "Plain text parser",
        "diagnostic_ids": ("parse-error",),
        "fixture_ids": ("phase16-text",),
    }
    if kind == "consumer-profile":
        defaults["selector"] = "trl"
        defaults["title"] = "TRL adapter"
        defaults["consumer_id"] = "trl"
    defaults.update(overrides)
    return create_capability_declaration(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize("kind", EXTENSION_KINDS)
def test_load_accepts_each_kind(kind: str) -> None:
    declaration = _declaration(kind=kind)
    loaded = load_capability_declaration(declaration.model_dump(mode="json"))
    assert loaded == declaration
    assert loaded.contract_version == EXTENSION_PROTOCOL_CONTRACT_VERSION
    assert loaded.schema_id == EXTENSION_PROTOCOL_SCHEMA_ID
    assert loaded.origin == "builtin"
    assert loaded.lifecycle == "supported"
    assert loaded.requirements.network is False
    assert loaded.requirements.llm_generation is False
    assert loaded.requirements.offline is True


def test_closed_vocabularies_match_the_contract() -> None:
    assert EXTENSION_KINDS == (
        "source-parser",
        "row-mapper",
        "deterministic-constructor",
        "quality-check",
        "container-exporter",
        "consumer-profile",
    )
    assert EXTENSION_ORIGINS == ("builtin", "third_party")
    assert EXTENSION_LIFECYCLES == (
        "experimental",
        "supported",
        "deprecated",
        "removed",
        "migrated",
    )
    assert "no-public-plugin-api" in PROTOCOL_LIMITATIONS
    assert "no-loader" in PROTOCOL_LIMITATIONS


def test_third_party_origin_is_a_declaration_not_a_loader() -> None:
    declaration = _declaration(origin="third_party")
    loaded = load_capability_declaration(declaration.model_dump(mode="json"))
    assert loaded.origin == "third_party"
    assert not hasattr(loaded, "entry_point")
    assert not hasattr(loaded, "module")


def test_unknown_kind_names_admitted_kinds() -> None:
    payload = _declaration().model_dump(mode="json")
    payload["kind"] = "summary-generator"
    with pytest.raises(
        ExtensionProtocolError,
        match="unknown extension kind: 'summary-generator'; admitted kinds are source-parser",
    ):
        load_capability_declaration(payload)


def test_unknown_contract_version_names_requested_and_supported() -> None:
    payload = _declaration().model_dump(mode="json")
    payload["contract_version"] = 2
    with pytest.raises(
        ExtensionProtocolError,
        match=r"unknown extension contract version: requested 2, supported 1 \(veriformis.extension-protocol/v1\)",
    ):
        load_capability_declaration(payload)


def test_missing_contract_version_names_supported_version() -> None:
    payload = _declaration().model_dump(mode="json")
    del payload["contract_version"]
    with pytest.raises(
        ExtensionProtocolError,
        match=r"unknown extension contract version: requested None, supported 1 \(veriformis.extension-protocol/v1\)",
    ):
        load_capability_declaration(payload)


def test_unknown_field_fails_closed() -> None:
    payload = _declaration().model_dump(mode="json")
    payload["plugin_path"] = "./plugins"
    with pytest.raises(
        ExtensionProtocolError,
        match="unknown field plugin_path",
    ):
        load_capability_declaration(payload)


def test_network_requirement_fails_closed() -> None:
    payload = _declaration().model_dump(mode="json")
    payload["requirements"]["network"] = True
    payload["declaration_id"] = derive_id(
        "exd",
        {key: value for key, value in payload.items() if key != "declaration_id"},
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="cannot require network",
    ):
        load_capability_declaration(payload)


def test_consumer_profile_requires_consumer_id() -> None:
    with pytest.raises(
        ExtensionProtocolError,
        match="consumer-profile declaration requires discovery.consumer_id",
    ):
        create_capability_declaration(
            kind="consumer-profile",
            origin="builtin",
            lifecycle="supported",
            extra="trl",
            selector="trl",
            title="TRL adapter",
        )


def test_non_profile_cannot_set_consumer_id() -> None:
    with pytest.raises(
        ExtensionProtocolError,
        match="only consumer-profile declarations may set discovery.consumer_id",
    ):
        create_capability_declaration(
            kind="source-parser",
            origin="builtin",
            lifecycle="supported",
            extra=None,
            selector="text",
            title="Plain text parser",
            consumer_id="trl",
        )


def test_declaration_identity_is_stable_and_mismatch_fails() -> None:
    first = _declaration()
    second = _declaration()
    assert first == second
    payload = first.model_dump(mode="json")
    payload["declaration_id"] = derive_id("exd", {"tampered": True})
    with pytest.raises(
        (ExtensionProtocolError, ValidationError),
        match="identity mismatch",
    ):
        load_capability_declaration(payload)


def test_protocol_does_not_add_cli_mcp_or_service_operations() -> None:
    names = {command.name for command in app.registered_commands}
    tools = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    forbidden = {
        "extension",
        "extensions",
        "plugin",
        "plugins",
        "install-extension",
        "install_extension",
    }
    assert names.isdisjoint(forbidden)
    assert tools.isdisjoint(forbidden)
    service = PipelineService()
    for name in forbidden:
        assert not hasattr(service, name.replace("-", "_"))
