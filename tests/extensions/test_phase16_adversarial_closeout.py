"""Phase 16.10: adversarial refusals, unchanged goldens, skipped public loader."""

from __future__ import annotations

import base64
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from veriformis.errors import ExtensionProtocolError
from veriformis.exports.service import ExportService
from veriformis.exports.split_jsonl import SPLIT_JSONL_IMPLEMENTATION
from veriformis.extensions import bound_split_jsonl_exporter, bound_text_parser
from veriformis.extensions.protocol import load_capability_declaration
from veriformis.extensions.registry import BuiltinBinding, _unique_bindings
from veriformis.identity import sha256_digest
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.text import parse_text
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace


ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/0017-no-untrusted-extension-loader.md"
KIT = ROOT / "tests/regressions/fixtures/phase16/compatibility-kit.json"
KIT_SHA256 = "746f258df2ae41445df6d2a108e7169279304aa4db156f6407ebf437e132b8f7"
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
EXPECTED_BUNDLE_ID = (
    "bundle-v1-49a6b50ed50218b8a22ce834dc69a64eb8d47f0605267bc029b3f938a6b13b4a"
)


def test_public_plugin_loading_is_skipped_under_decision_a() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert "**Decision A.** Phase 16 does not install an untrusted loader." in text
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    assert not (ROOT / "plugins").exists()
    payload = PipelineService().discover_extensions()
    assert payload["public_plugin_api"] is False
    assert payload["third_party_loading"] is False


def test_unknown_version_duplicate_selector_and_third_party_fail_closed() -> None:
    tampered = SimpleNamespace(
        kind="source-parser",
        origin="builtin",
        extra=None,
        contract_version=99,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=(
            r"unknown extension contract version: requested 99, supported 1 "
            r"\(veriformis.extension-protocol/v1\)"
        ),
    ):
        bound_text_parser(declaration=tampered)  # type: ignore[arg-type]
    with pytest.raises(
        ExtensionProtocolError,
        match="parser selectors must be unique",
    ):
        _unique_bindings(
            (
                BuiltinBinding(
                    "source-parser", "text", None, "builtin", parse_text
                ),
                BuiltinBinding(
                    "source-parser", "text", None, "builtin", parse_text
                ),
            ),
            label="parser",
        )
    with pytest.raises(
        ExtensionProtocolError,
        match="internal registry admits origin builtin only; requested third_party",
    ):
        BuiltinBinding(
            kind="source-parser",
            selector="hostile",
            extra=None,
            origin="third_party",
            target=parse_text,
        )


def test_declaration_tamper_and_registry_mutation_fail_closed() -> None:
    payload = {
        "contract_id": "veriformis.extension-protocol",
        "contract_version": 1,
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
        "declaration_id": (
            "exd-v1-deadbeefdeadbeefdeadbeefdeadbeef"
            "deadbeefdeadbeefdeadbeefdeadbeef"
        ),
    }
    with pytest.raises(
        ExtensionProtocolError,
        match="extension declaration identity mismatch",
    ):
        load_capability_declaration(payload)
    registry = PipelineService().extension_registry
    with pytest.raises(FrozenInstanceError):
        registry.parsers = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        registry.exporters = ()  # type: ignore[misc]


def test_workspace_plugins_directory_is_ignored(tmp_path: Path) -> None:
    workspace = Workspace.create(tmp_path / "workspace")
    plugin = workspace.root / "plugins" / "evil.py"
    plugin.parent.mkdir()
    plugin.write_text("raise SystemExit('workspace plugin loaded')\n", encoding="utf-8")
    payload = PipelineService().discover_extensions()
    assert payload["public_plugin_api"] is False
    assert payload["third_party_loading"] is False
    selectors = {
        item["discovery"]["selector"] for item in payload["declarations"]
    }
    assert "evil" not in selectors
    assert "plugins" not in selectors
    for relative in (
        "src/veriformis/extensions/runtime.py",
        "src/veriformis/extensions/registry.py",
        "src/veriformis/extensions/declarations.py",
        "src/veriformis/pipeline/service.py",
        "src/veriformis/cli.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "plugins/" not in source
        assert "entry_points" not in source


def test_text_and_split_jsonl_goldens_and_sealed_bundle_identity_hold(
    tmp_path: Path,
) -> None:
    kit_bytes = KIT.read_bytes()
    assert sha256_digest(kit_bytes) == KIT_SHA256
    kit = json.loads(kit_bytes.decode("utf-8"))
    spec = kit["text_parser"]
    raw = spec["utf8"].encode("utf-8")
    path = tmp_path / spec["logical_path"]
    path.write_bytes(raw)
    dispatched = parse_captured_source(
        path, logical_path=spec["logical_path"], raw_bytes=raw
    )
    direct = parse_text(path, logical_path=spec["logical_path"], raw_bytes=raw)
    via = bound_text_parser()(
        path, logical_path=spec["logical_path"], raw_bytes=raw
    )
    assert dispatched.source.id == direct.source.id == via.source.id == spec["source_id"]
    assert (
        dispatched.diagnostics.report_digest
        == direct.diagnostics.report_digest
        == via.diagnostics.report_digest
        == spec["report_digest"]
    )
    bound = bound_split_jsonl_exporter(catalog=ExportService()._catalog())
    assert bound is SPLIT_JSONL_IMPLEMENTATION
    fixture = json.loads(
        (
            ROOT
            / "tests/regressions/fixtures/phase3/pre-taxonomy-full-text.vfbundle.json"
        ).read_text(encoding="utf-8")
    )
    bundle = tmp_path / "sealed.vfbundle"
    for relative_path, encoded in fixture["files_base64"].items():
        destination = bundle.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(base64.b64decode(encoded, validate=True))
    assert (
        sha256_digest((bundle / "manifest.json").read_bytes())
        == EXPECTED_MANIFEST_SHA256
    )
    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    assert outcome.exit_status == 0
    assert outcome.verification is not None
    assert outcome.verification.bundle_id == EXPECTED_BUNDLE_ID
