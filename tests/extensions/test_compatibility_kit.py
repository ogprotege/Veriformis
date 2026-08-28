"""Phase 16.7: frozen compatibility kit for the two migrated exemplars.

The kit is test-only. It is not a product plugin runner and it does not scan
a project-local plugins path.
"""

from __future__ import annotations

import base64
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from veriformis.cli import app
from veriformis.errors import ExtensionProtocolError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA_V2,
    ExportDryRunRequestV2,
    ExportExecuteRequestV2,
    ExportService,
)
from veriformis.exports.split_jsonl import SplitJsonlOptions
from veriformis.extensions import (
    bound_split_jsonl_exporter,
    bound_text_parser,
    create_capability_declaration,
    load_capability_declaration,
)
from veriformis.identity import sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.text import parse_text


ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)


def _strict_object(data: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate fixture key {key!r}")
            result[key] = value
        return result

    value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    if type(value) is not dict:
        raise ValueError("compatibility kit must be one object")
    return value


@pytest.fixture(scope="module")
def kit() -> dict[str, Any]:
    data = KIT.read_bytes()
    assert sha256_digest(data) == KIT_SHA256
    fixture = _strict_object(data)
    assert fixture["schema_version"] == (
        "veriformis.phase16-extension-compatibility-kit/v1"
    )
    assert fixture["contract_id"] == "veriformis.extension-protocol"
    assert fixture["contract_version"] == 1
    assert fixture["schema_id"] == "veriformis.extension-protocol/v1"
    return fixture


def _materialize_bundle(root: Path, *, source_fixture: str) -> Path:
    fixture = _strict_object(ROOT.joinpath(*source_fixture.split("/")).read_bytes())
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _selection(bundle: Path) -> dict[str, object]:
    return {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA_V2,
        "bundle": str(bundle),
        "container_id": "split-jsonl-directory",
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def _options(spec: dict[str, Any]) -> dict[str, str | bool | int | None]:
    return SplitJsonlOptions(
        train_partition_name=spec["train"],
        evaluation_partition_name=spec["evaluation"],
        include_provenance=spec["provenance"],
    ).model_dump(mode="json")


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_kit_is_test_only_and_not_a_plugin_runner() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "compatibility-kit" not in cli_names
    assert "compatibility_kit" not in mcp_names
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    assert not (ROOT / "src/veriformis/extensions/kit.py").exists()
    assert not (ROOT / "plugins").exists()
    runtime = (ROOT / "src/veriformis/extensions/runtime.py").read_text(
        encoding="utf-8"
    )
    assert "entry_points" not in runtime
    assert "plugins/" not in runtime


def test_text_parser_golden_matches_protocol_and_direct(tmp_path, kit) -> None:
    spec = kit["text_parser"]
    raw = spec["utf8"].encode("utf-8")
    assert sha256_digest(raw) == spec["bytes_sha256"]
    path = tmp_path / spec["logical_path"]
    path.write_bytes(raw)
    dispatched = parse_captured_source(
        path, logical_path=spec["logical_path"], raw_bytes=raw
    )
    direct = parse_text(path, logical_path=spec["logical_path"], raw_bytes=raw)
    via_protocol = bound_text_parser()(
        path, logical_path=spec["logical_path"], raw_bytes=raw
    )
    assert (
        dispatched.source.id
        == direct.source.id
        == via_protocol.source.id
        == spec["source_id"]
    )
    assert (
        dispatched.diagnostics.report_digest
        == direct.diagnostics.report_digest
        == via_protocol.diagnostics.report_digest
        == spec["report_digest"]
    )


def test_split_jsonl_golden_matches_protocol_bound_export(tmp_path, kit) -> None:
    spec = kit["split_jsonl"]
    service = ExportService()
    bound = bound_split_jsonl_exporter(catalog=service._catalog())
    catalog_item = next(
        item
        for item in service._catalog()
        if item.descriptor.container_profile.container_id == spec["container_id"]
        and item.descriptor.consumer_profile is None
    )
    assert bound is catalog_item
    bundle = _materialize_bundle(tmp_path, source_fixture=spec["source_fixture"])
    options = _options(spec["options"])
    plan = service.dry_run_export(
        ExportDryRunRequestV2(
            operation="dry_run",
            container_options=options,
            **_selection(bundle),
        )
    )
    destination = tmp_path / "published"
    service.execute_export(
        ExportExecuteRequestV2(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            container_options=options,
            **_selection(bundle),
        )
    )
    tree = _tree_bytes(destination)
    assert set(tree) == set(spec["files"])
    assert {
        path: {"sha256": sha256_digest(data), "size": len(data)}
        for path, data in tree.items()
    } == spec["files"]


def test_unknown_kind_names_admitted_kinds() -> None:
    payload = create_capability_declaration(
        kind="source-parser",
        origin="builtin",
        lifecycle="supported",
        extra=None,
        selector="text",
        title="Plain text parser",
        fixture_ids=("phase16-text",),
    ).model_dump(mode="json")
    payload["kind"] = "summary-generator"
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            "unknown extension kind: 'summary-generator'; admitted kinds are "
            "source-parser"
        ),
    ):
        load_capability_declaration(payload)


def test_unknown_contract_version_names_requested_and_supported() -> None:
    payload = {
        "contract_id": "veriformis.extension-protocol",
        "contract_version": 2,
        "schema_id": "veriformis.extension-protocol/v1",
        "kind": "source-parser",
        "origin": "builtin",
        "lifecycle": "supported",
        "extra": None,
        "diagnostic_ids": [],
        "fixture_ids": [],
        "discovery": {
            "consumer_id": None,
            "selector": "text",
            "title": "Plain text parser",
        },
        "requirements": {
            "llm_generation": False,
            "network": False,
            "offline": True,
            "profile": "offline-deterministic-v1",
        },
        "declaration_id": "placeholder",
    }
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            r"unknown extension contract version: requested "
            r"contract_id='veriformis.extension-protocol' contract_version=2 "
            r"schema_id='veriformis.extension-protocol/v1', supported "
            r"contract_id='veriformis.extension-protocol' contract_version=1 "
            r"schema_id='veriformis.extension-protocol/v1'"
        ),
    ):
        load_capability_declaration(payload)


def test_missing_extra_fails_closed() -> None:
    payload = {
        "contract_id": "veriformis.extension-protocol",
        "contract_version": 1,
        "schema_id": "veriformis.extension-protocol/v1",
        "kind": "source-parser",
        "origin": "builtin",
        "lifecycle": "supported",
        "diagnostic_ids": [],
        "fixture_ids": [],
        "discovery": {
            "consumer_id": None,
            "selector": "text",
            "title": "Plain text parser",
        },
        "requirements": {
            "llm_generation": False,
            "network": False,
            "offline": True,
            "profile": "offline-deterministic-v1",
        },
        "declaration_id": "placeholder",
    }
    with pytest.raises(
        ExtensionProtocolError,
        match="extension declaration missing extra",
    ):
        load_capability_declaration(payload)
    tampered = SimpleNamespace(
        kind="source-parser",
        origin="builtin",
        extra="ocr",
        contract_version=1,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="text parser requires extra null; requested extra 'ocr'",
    ):
        bound_text_parser(declaration=tampered)  # type: ignore[arg-type]
    tampered_export = SimpleNamespace(
        kind="container-exporter",
        origin="builtin",
        extra="columnar",
        contract_version=1,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            "split-jsonl-directory requires extra null; requested extra 'columnar'"
        ),
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=tampered_export,  # type: ignore[arg-type]
        )


def test_broken_declaration_identity_fails_closed() -> None:
    payload = {
        "contract_id": "veriformis.extension-protocol",
        "contract_version": 1,
        "schema_id": "veriformis.extension-protocol/v1",
        "kind": "container-exporter",
        "origin": "builtin",
        "lifecycle": "supported",
        "extra": None,
        "diagnostic_ids": [],
        "fixture_ids": ["phase16-split-jsonl"],
        "discovery": {
            "consumer_id": None,
            "selector": "split-jsonl-directory",
            "title": "split-jsonl-directory exporter",
        },
        "requirements": {
            "llm_generation": False,
            "network": False,
            "offline": True,
            "profile": "offline-deterministic-v1",
        },
        "declaration_id": "exd-v1-deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
    }
    with pytest.raises(
        ExtensionProtocolError,
        match="extension declaration identity mismatch",
    ):
        load_capability_declaration(payload)


def test_third_party_origin_is_refused_for_migrated_exemplars() -> None:
    text = SimpleNamespace(
        kind="source-parser",
        origin="third_party",
        extra=None,
        contract_version=1,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match="text parser selection requires a builtin source-parser declaration",
    ):
        bound_text_parser(declaration=text)  # type: ignore[arg-type]
    exporter = SimpleNamespace(
        kind="container-exporter",
        origin="third_party",
        extra=None,
        contract_version=1,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            "split-jsonl-directory selection requires a builtin "
            "container-exporter declaration"
        ),
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=exporter,  # type: ignore[arg-type]
        )


def test_runtime_unknown_versions_name_supported_contract() -> None:
    text = SimpleNamespace(
        kind="source-parser",
        origin="builtin",
        extra=None,
        contract_version=2,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            r"unknown extension contract version: requested 2, supported 1 "
            r"\(veriformis.extension-protocol/v1\)"
        ),
    ):
        bound_text_parser(declaration=text)  # type: ignore[arg-type]
    exporter = SimpleNamespace(
        kind="container-exporter",
        origin="builtin",
        extra=None,
        contract_version=2,
        discovery=SimpleNamespace(selector="split-jsonl-directory"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            r"unknown extension contract version: requested 2, supported 1 "
            r"\(veriformis.extension-protocol/v1\)"
        ),
    ):
        bound_split_jsonl_exporter(
            catalog=ExportService()._catalog(),
            declaration=exporter,  # type: ignore[arg-type]
        )


def test_kit_does_not_scan_a_project_local_plugin_path() -> None:
    source = inspect.getsource(ExportService._resolve_implementation)
    assert "plugins" not in source
    assert "entry_point" not in source
    assert "bound_split_jsonl_exporter" in source
