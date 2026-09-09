"""Post-20 defect D-02: HTML capture decoding is explicit, exact, and closed.

Before the fix, lxml received raw bytes with ``encoding=None`` and libxml2
assumed ISO-8859-1 for undeclared captures, so valid UTF-8 HTML became
mojibake (``café`` -> ``cafÃ©``) with no diagnostic.
"""

from __future__ import annotations

import codecs
from pathlib import Path

from veriformis.parsers.html import PARSER_VERSION, parse_html_file

UNICODE_TEXT = "café — naïve ☃ 日本語"


def _parse(tmp_path: Path, raw: bytes):
    path = tmp_path / "page.html"
    path.write_bytes(raw)
    return parse_html_file(path, logical_path=path.name)


def _codes(result) -> set[str]:
    return {item.code for item in result.diagnostics.diagnostics}


def test_undeclared_utf8_is_decoded_exactly(tmp_path: Path) -> None:
    raw = f"<html><body><p>{UNICODE_TEXT}</p></body></html>".encode("utf-8")
    result = _parse(tmp_path, raw)
    assert result.source.extracted_text == UNICODE_TEXT
    assert result.diagnostics.status == "complete"
    assert "html.charset-declared" not in _codes(result)
    assert result.source.parser_version == PARSER_VERSION == "1.1.0"


def test_declared_latin1_is_decoded_with_a_diagnostic(tmp_path: Path) -> None:
    raw = (
        '<html><head><meta http-equiv="Content-Type" '
        'content="text/html; charset=iso-8859-1"></head>'
        "<body><p>café — naïve</p></body></html>"
    )
    # An em dash is not encodable in Latin-1; use a Latin-1 safe body.
    raw = raw.replace(" — naïve", " naïve")
    result = _parse(tmp_path, raw.encode("iso-8859-1"))
    assert result.source.extracted_text == "café naïve"
    assert "html.charset-declared" in _codes(result)
    declared = next(
        item for item in result.diagnostics.diagnostics if item.code == "html.charset-declared"
    )
    assert declared.details == {
        "charset": "iso-8859-1",
        "declared_by": "meta",
        "codec": "iso8859-1",
    }
    assert declared.loss_kind == "metadata"
    assert declared.disposition == "normalized"


def test_meta_charset_attribute_form_is_recognized(tmp_path: Path) -> None:
    raw = '<html><head><meta charset="windows-1252"></head><body><p>café “quoted”</p></body></html>'
    result = _parse(tmp_path, raw.encode("cp1252"))
    assert result.source.extracted_text == "café “quoted”"
    assert "html.charset-declared" in _codes(result)


def test_utf8_bom_is_removed_and_diagnosed(tmp_path: Path) -> None:
    raw = codecs.BOM_UTF8 + f"<html><body><p>{UNICODE_TEXT}</p></body></html>".encode("utf-8")
    result = _parse(tmp_path, raw)
    assert result.source.extracted_text == UNICODE_TEXT
    assert "html.bom-removed" in _codes(result)
    assert not result.source.extracted_text.startswith("\ufeff")


def test_utf16_bom_is_decoded_and_diagnosed(tmp_path: Path) -> None:
    raw = codecs.BOM_UTF16_LE + f"<html><body><p>{UNICODE_TEXT}</p></body></html>".encode(
        "utf-16-le"
    )
    result = _parse(tmp_path, raw)
    assert result.source.extracted_text == UNICODE_TEXT
    declared = next(
        item for item in result.diagnostics.diagnostics if item.code == "html.charset-declared"
    )
    assert declared.details == {"charset": "utf-16-le", "declared_by": "bom"}


def test_invalid_utf8_without_declaration_refuses(tmp_path: Path) -> None:
    raw = "<html><body><p>café</p></body></html>".encode("iso-8859-1")
    result = _parse(tmp_path, raw)
    assert result.diagnostics.status == "refused"
    assert result.source.extracted_text == ""
    assert result.document.children == []
    refusal = next(
        item for item in result.diagnostics.diagnostics if item.code == "html.charset-unknown"
    )
    assert refusal.severity == "error"
    assert refusal.disposition == "refused"
    assert refusal.loss_kind == "text"
    assert "utf8_error" in (refusal.details or {})


def test_declared_utf8_that_is_not_utf8_refuses_as_invalid(tmp_path: Path) -> None:
    raw = '<html><head><meta charset="utf-8"></head><body><p>café</p></body></html>'.encode(
        "iso-8859-1"
    )
    result = _parse(tmp_path, raw)
    assert result.diagnostics.status == "refused"
    assert "html.charset-invalid" in _codes(result)


def test_declared_unknown_charset_refuses(tmp_path: Path) -> None:
    raw = b'<html><head><meta charset="x-no-such-charset"></head><body><p>caf\xe9</p></body></html>'
    result = _parse(tmp_path, raw)
    assert result.diagnostics.status == "refused"
    refusal = next(
        item for item in result.diagnostics.diagnostics if item.code == "html.charset-unknown"
    )
    assert refusal.details == {"charset": "x-no-such-charset", "declared_by": "meta"}


def test_declared_charset_that_cannot_decode_refuses_as_invalid(tmp_path: Path) -> None:
    raw = b'<html><head><meta charset="ascii"></head><body><p>caf\xe9</p></body></html>'
    result = _parse(tmp_path, raw)
    assert result.diagnostics.status == "refused"
    assert "html.charset-invalid" in _codes(result)


def test_contradicting_meta_charset_does_not_override_valid_utf8(tmp_path: Path) -> None:
    raw = (
        '<html><head><meta charset="iso-8859-1"></head>'
        f"<body><p>{UNICODE_TEXT}</p></body></html>"
    ).encode("utf-8")
    result = _parse(tmp_path, raw)
    assert result.source.extracted_text == UNICODE_TEXT
    assert "html.charset-declared" not in _codes(result)


def test_decoding_is_deterministic(tmp_path: Path) -> None:
    raw = f"<html><body><p>{UNICODE_TEXT}</p></body></html>".encode("utf-8")
    first = _parse(tmp_path, raw)
    second = _parse(tmp_path, raw)
    assert first.source.artifact_id == second.source.artifact_id
    assert first.diagnostics.report_digest == second.diagnostics.report_digest
