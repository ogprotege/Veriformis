"""Phase 16.3 internal registries wrap existing bindings without dispatch change."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path

import pytest

from veriformis.cli import app
from veriformis.construction.constructors import _CONSTRUCTORS, get_constructor
from veriformis.errors import ExtensionProtocolError
from veriformis.exports.service import ExportService
from veriformis.extensions import BuiltinBinding, builtin_registry
from veriformis.mapping.execute import execute_mapping
from veriformis.mcp.server import create_mcp_server
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.identity import PARSER_KIND_VERSIONS
from veriformis.parsers.text import parse_text
from veriformis.pipeline import PipelineService
from veriformis.quality.detectors import _DETECTORS
from veriformis.quality.gates import V1_QUALITY_GATES


def test_pipeline_service_owns_the_built_in_registry() -> None:
    service = PipelineService()
    registry = service.extension_registry
    catalog = service.export_service._catalog()
    assert registry.exporters == catalog
    assert all(left is right for left, right in zip(registry.exporters, catalog, strict=True))


def test_parsers_wrap_dispatch_functions_without_replacing_suffix_policy() -> None:
    registry = PipelineService().extension_registry
    assert tuple(item.selector for item in registry.parsers) == tuple(
        PARSER_KIND_VERSIONS
    )
    assert registry.parser("text").target is parse_text
    source = inspect.getsource(parse_captured_source)
    assert "extension = Path(logical_path).suffix.lower()" in source
    assert 'if extension == ".txt"' in source
    assert "registry" not in source


def test_mapper_is_execute_mapping() -> None:
    registry = PipelineService().extension_registry
    assert registry.mapper.kind == "row-mapper"
    assert registry.mapper.selector == "execute-mapping"
    assert registry.mapper.target is execute_mapping


def test_constructors_wrap_the_private_exact_lookup() -> None:
    registry = PipelineService().extension_registry
    wrapped = {
        tuple(item.selector.split("/", 1)): item.target
        for item in registry.constructors
    }
    assert wrapped == _CONSTRUCTORS
    for (constructor_id, version), target in _CONSTRUCTORS.items():
        assert registry.constructor(constructor_id, version) is target
        assert get_constructor(constructor_id, version) is target


def test_quality_wraps_detectors_and_preview_only_gates() -> None:
    registry = PipelineService().extension_registry
    detector_ids = tuple(detector_id for _category, detector_id, _pattern in _DETECTORS)
    gate_ids = tuple(spec.gate_id for spec in V1_QUALITY_GATES)
    assert tuple(item.selector for item in registry.quality_checks) == (
        *detector_ids,
        *gate_ids,
    )
    assert all(spec.admitted_to_block is False for spec in V1_QUALITY_GATES)
    wrapped_gates = [
        item.target for item in registry.quality_checks if item.selector in gate_ids
    ]
    assert wrapped_gates == list(V1_QUALITY_GATES)
    assert all(spec.admitted_to_block is False for spec in wrapped_gates)


def test_export_selectors_stay_on_the_one_private_catalog() -> None:
    catalog = ExportService()._catalog()
    registry = builtin_registry(export_catalog=catalog)
    assert tuple(item.descriptor.selector for item in registry.exporters) == tuple(
        item.descriptor.selector for item in catalog
    )
    assert any(item.descriptor.consumer_profile is None for item in registry.exporters)
    assert any(
        item.descriptor.consumer_profile is not None for item in registry.exporters
    )


def test_third_party_origin_is_refused() -> None:
    with pytest.raises(
        ExtensionProtocolError,
        match="internal registry admits origin builtin only; requested third_party",
    ):
        BuiltinBinding(
            kind="source-parser",
            selector="text",
            extra=None,
            origin="third_party",
            target=parse_text,
        )


def test_registry_is_frozen() -> None:
    registry = PipelineService().extension_registry
    with pytest.raises(FrozenInstanceError):
        registry.parsers = ()  # type: ignore[misc]


def test_text_parse_report_matches_the_wrapped_parser(tmp_path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("Hello.\n\nWorld.", encoding="utf-8")
    raw = path.read_bytes()
    dispatched = parse_captured_source(path, logical_path=path.name, raw_bytes=raw)
    wrapped = PipelineService().extension_registry.parser("text").target(
        path,
        logical_path=path.name,
        raw_bytes=raw,
    )
    assert dispatched.source.id == wrapped.source.id
    assert dispatched.diagnostics.report_digest == wrapped.diagnostics.report_digest
    assert dispatched.diagnostics.parser_name == "text"
    assert wrapped.diagnostics.parser_name == "text"


def test_wrapped_registry_does_not_change_sealed_bundle_identity(tmp_path) -> None:
    import base64
    import json

    from veriformis.identity import sha256_digest

    fixture = (
        Path(__file__).resolve().parents[1]
        / "regressions"
        / "fixtures"
        / "phase3"
        / "pre-taxonomy-full-text.vfbundle.json"
    )
    expected_manifest_sha256 = (
        "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
    )
    expected_bundle_id = (
        "bundle-v1-49a6b50ed50218b8a22ce834dc69a64eb8d47f0605267bc029b3f938a6b13b4a"
    )
    encoded = json.loads(fixture.read_text(encoding="utf-8"))
    bundle = tmp_path / "pre-taxonomy-full-text.vfbundle"
    for relative_path, payload in encoded["files_base64"].items():
        destination = bundle.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = base64.b64decode(payload, validate=True)
        destination.write_bytes(content)
    assert sha256_digest((bundle / "manifest.json").read_bytes()) == expected_manifest_sha256
    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=expected_manifest_sha256,
    )
    assert outcome.exit_status == 0
    assert outcome.verification is not None
    assert outcome.verification.bundle_id == expected_bundle_id


def test_registry_does_not_add_cli_mcp_or_loader_operations() -> None:
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
