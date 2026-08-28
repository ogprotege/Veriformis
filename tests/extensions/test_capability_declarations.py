"""Phase 16.4 built-in capability declarations are read-only metadata."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    EXTENSION_DISCOVERY_SCHEMA_ID,
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.extensions import (
    builtin_declarations,
    discover_extensions,
    load_capability_declaration,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


RUNNER = CliRunner()
SERVICE = PipelineService()


def test_declarations_cover_the_registry_and_are_supported_builtins() -> None:
    registry = SERVICE.extension_registry
    declarations = builtin_declarations(registry)
    assert declarations
    assert all(item.origin == "builtin" for item in declarations)
    assert all(item.lifecycle == "supported" for item in declarations)
    assert all(
        item.contract_version == EXTENSION_PROTOCOL_CONTRACT_VERSION
        for item in declarations
    )
    selectors = {(item.kind, item.discovery.selector) for item in declarations}
    assert ("source-parser", "text") in selectors
    assert ("row-mapper", "execute-mapping") in selectors
    assert ("deterministic-constructor", "full-text-1") in selectors
    assert ("container-exporter", "split-jsonl-directory") in selectors
    assert ("consumer-profile", "trl") in selectors
    assert ("unsloth", "unsloth") not in selectors
    assert all("ocr-image" not in item.discovery.selector for item in declarations)
    assert all(item.discovery.selector != "unsloth" for item in declarations)


def test_consumer_profiles_keep_consumer_id_and_empty_extras_stay_named() -> None:
    declarations = {
        item.discovery.selector: item
        for item in builtin_declarations(SERVICE.extension_registry)
        if item.kind == "consumer-profile"
    }
    assert set(declarations) == {
        "aptus",
        "axolotl",
        "llama-factory",
        "mlx-lm",
        "trl",
    }
    for selector, item in declarations.items():
        assert item.discovery.consumer_id == selector
        assert item.extra == selector
    exporters = [
        item
        for item in builtin_declarations(SERVICE.extension_registry)
        if item.kind == "container-exporter"
    ]
    assert all(item.extra is None for item in exporters)
    assert all(item.discovery.consumer_id is None for item in exporters)


def test_python_cli_mcp_agree_on_extension_capabilities() -> None:
    python_payload = SERVICE.discover_extensions()
    assert python_payload == discover_extensions(SERVICE.extension_registry)
    assert python_payload["schema_id"] == EXTENSION_DISCOVERY_SCHEMA_ID
    assert python_payload["public_plugin_api"] is False
    assert python_payload["third_party_loading"] is False
    cli = RUNNER.invoke(app, ["extension-capabilities"])
    assert cli.exit_code == 0, cli.output
    cli_payload = json.loads(cli.output)
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp_payload = json.loads(tools["extension_capabilities"]())
    assert python_payload == cli_payload == mcp_payload


def test_unknown_declaration_version_names_supported_contract() -> None:
    payload = builtin_declarations(SERVICE.extension_registry)[0].model_dump(
        mode="json"
    )
    payload["contract_version"] = 2
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            r"unknown extension contract version: requested "
            r"contract_id='veriformis.extension-protocol' contract_version=2"
        ),
    ):
        load_capability_declaration(payload)


def test_declarations_are_not_executable_bindings() -> None:
    text = next(
        item
        for item in builtin_declarations(SERVICE.extension_registry)
        if item.kind == "source-parser" and item.discovery.selector == "text"
    )
    assert not hasattr(text, "target")
    assert not hasattr(text, "entry_point")
    registry = SERVICE.extension_registry
    assert registry.parser("text").target is not None
