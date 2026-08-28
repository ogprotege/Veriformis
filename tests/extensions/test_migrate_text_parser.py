"""Phase 16.5: text is selected only through the extension protocol."""

from __future__ import annotations

import inspect

import pytest

from veriformis.errors import ExtensionProtocolError
from veriformis.extensions import bound_text_parser
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.text import parse_text


def test_txt_dispatch_uses_the_protocol_and_matches_parse_text(tmp_path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("Hello.\n\nWorld.", encoding="utf-8")
    raw = path.read_bytes()
    dispatched = parse_captured_source(path, logical_path=path.name, raw_bytes=raw)
    direct = parse_text(path, logical_path=path.name, raw_bytes=raw)
    via_protocol = bound_text_parser()(path, logical_path=path.name, raw_bytes=raw)
    assert dispatched.source.id == direct.source.id == via_protocol.source.id
    assert (
        dispatched.diagnostics.report_digest
        == direct.diagnostics.report_digest
        == via_protocol.diagnostics.report_digest
    )
    source = inspect.getsource(parse_captured_source)
    assert "parse_text_via_protocol" in source
    assert 'if extension == ".txt"' in source
    assert "parse_md_file" in source


def test_markdown_and_code_still_use_existing_dispatch() -> None:
    source = inspect.getsource(parse_captured_source)
    assert "parse_md_file" in source
    assert "if extension in CODE_EXTENSIONS" in source
    assert source.index("parse_text_via_protocol") < source.index("parse_md_file")


def test_unknown_text_parser_contract_version_names_supported_version() -> None:
    from types import SimpleNamespace

    tampered = SimpleNamespace(
        kind="source-parser",
        origin="builtin",
        contract_version=2,
        discovery=SimpleNamespace(selector="text"),
    )
    with pytest.raises(
        ExtensionProtocolError,
        match=r"unknown extension contract version: requested 2, supported 1 \(veriformis.extension-protocol/v1\)",
    ):
        bound_text_parser(declaration=tampered)  # type: ignore[arg-type]
