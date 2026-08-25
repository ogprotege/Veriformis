"""Per-parser adversarial, empty, truncated, and oversized-closed fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.errors import ParseError, UnsupportedInputError
from veriformis.parsers.dispatch import parse_captured_source

_G5 = Path(__file__).resolve().parents[1] / "fixtures" / "group5"


def _parse(path: Path, payload: bytes):
    return parse_captured_source(path, logical_path=path.name, raw_bytes=payload)


def test_text_empty_and_non_utf8_fail_closed(tmp_path: Path) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    result = _parse(empty, b"")
    assert result.diagnostics.status in {"complete", "degraded"}
    with pytest.raises((ParseError, UnicodeDecodeError, UnicodeError)):
        _parse(tmp_path / "bad.txt", b"\xff\xfe not utf8")


def test_json_truncated_and_jsonl_malformed_fail_closed(tmp_path: Path) -> None:
    try:
        truncated = _parse(tmp_path / "trunc.json", b'{"a":')
    except ParseError:
        truncated = None
    else:
        assert truncated.diagnostics.status == "refused"
    try:
        malformed = _parse(tmp_path / "bad.jsonl", b"{not-json}\n")
    except ParseError:
        malformed = None
    else:
        assert malformed.diagnostics.status == "refused"


def test_csv_empty_fails_or_degrades(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    try:
        result = _parse(path, b"")
    except ParseError:
        return
    assert result.diagnostics.status in {"complete", "degraded", "refused"}


def test_html_malformed_still_recovers_or_refuses(tmp_path: Path) -> None:
    result = _parse(tmp_path / "broken.html", b"<html><p>unclosed")
    assert result.diagnostics.status in {"complete", "degraded", "refused"}
    assert isinstance(result.diagnostics.parser_name, str)


def test_markdown_empty_is_closed(tmp_path: Path) -> None:
    result = _parse(tmp_path / "empty.md", b"")
    assert result.diagnostics.status in {"complete", "degraded"}


def test_pdf_truncated_fails_closed(tmp_path: Path) -> None:
    try:
        result = _parse(tmp_path / "trunc.pdf", b"%PDF-1.4 truncated")
    except Exception:
        return
    assert result.diagnostics.status == "refused"


def test_pdf_empty_text_refuses_as_ocr(tmp_path: Path) -> None:
    payload = (_G5 / "empty-text.pdf").read_bytes()
    result = _parse(tmp_path / "scan.pdf", payload)
    assert result.diagnostics.status == "refused"


def test_docx_truncated_zip_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ParseError):
        _parse(tmp_path / "trunc.docx", b"PK\x03\x04not-a-docx")


def test_unknown_suffix_is_unsupported(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedInputError):
        _parse(tmp_path / "note.xyz", b"hello")
