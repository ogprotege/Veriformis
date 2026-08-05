"""Group 5 declared-format parser coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.errors import UnsupportedInputError
from veriformis.ir import validate_document_against_stream
from veriformis.parsers.dispatch import DECLARED_V1_EXTENSIONS, parse_captured_source
from veriformis.parsers.html import parse_html_file
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.parsers.structured import parse_csv_file, parse_json_file, parse_jsonl_file

_G5 = Path(__file__).resolve().parents[1] / "fixtures" / "group5"


def _pdf(name: str) -> bytes:
    return (_G5 / name).read_bytes()


def _assert_exact(result) -> None:
    validate_document_against_stream(
        result.document,
        result.source.extracted_text,
        exact=True,
    )


def test_html_omits_script_and_recovers_text(tmp_path):
    path = tmp_path / "page.html"
    path.write_text(
        "<html><head><style>x{}</style></head><body>"
        "<h1>Title</h1><p>Hello world.</p><script>alert(1)</script>"
        "</body></html>",
        encoding="utf-8",
    )
    result = parse_html_file(path, logical_path=path.name)
    _assert_exact(result)
    assert "Hello world." in result.source.extracted_text
    assert "alert" not in result.source.extracted_text
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "html.non-content-tags-omitted" in codes


def test_pdf_text_layer_and_ocr_refusal(tmp_path):
    good = tmp_path / "born.pdf"
    good.write_bytes(_pdf("minimal-text.pdf"))
    result = parse_pdf_file(good, logical_path=good.name)
    _assert_exact(result)
    assert result.diagnostics.status == "complete"
    assert "Hello" in result.source.extracted_text

    empty = tmp_path / "scan.pdf"
    empty.write_bytes(_pdf("empty-text.pdf"))
    refused = parse_pdf_file(empty, logical_path=empty.name)
    assert refused.diagnostics.status == "refused"
    codes = {item.code for item in refused.diagnostics.diagnostics}
    assert "pdf.ocr-required" in codes
    assert any(
        item.details.get("limitation") == "ocr-unsupported"
        for item in refused.diagnostics.diagnostics
    )


def test_csv_json_jsonl_projection(tmp_path):
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text("name,age\nAda,36\n", encoding="utf-8")
    csv_result = parse_csv_file(csv_path, logical_path=csv_path.name)
    _assert_exact(csv_result)
    assert "Ada" in csv_result.source.extracted_text

    json_path = tmp_path / "obj.json"
    json_path.write_text('{"prompt":"hi","completion":"there"}', encoding="utf-8")
    json_result = parse_json_file(json_path, logical_path=json_path.name)
    _assert_exact(json_result)
    assert "prompt: hi" in json_result.source.extracted_text

    jsonl_path = tmp_path / "rows.jsonl"
    jsonl_path.write_text('{"a":1}\n{"a":2}\n', encoding="utf-8")
    jsonl_result = parse_jsonl_file(jsonl_path, logical_path=jsonl_path.name)
    _assert_exact(jsonl_result)
    assert "record[0].a: 1" in jsonl_result.source.extracted_text


def test_dispatch_covers_declared_group5_suffixes(tmp_path):
    samples = {
        ".html": b"<html><body><p>x</p></body></html>",
        ".pdf": _pdf("minimal-text.pdf"),
        ".csv": b"a,b\n1,2\n",
        ".json": b'{"k":"v"}',
        ".jsonl": b'{"k":"v"}\n',
    }
    for suffix, payload in samples.items():
        path = tmp_path / f"sample{suffix}"
        path.write_bytes(payload)
        result = parse_captured_source(
            path,
            logical_path=path.name,
            raw_bytes=payload,
        )
        assert result.diagnostics.status in {"complete", "degraded"}
        if result.source.extracted_text:
            _assert_exact(result)
    assert ".pdf" in DECLARED_V1_EXTENSIONS
    assert ".html" in DECLARED_V1_EXTENSIONS


def test_unknown_suffix_still_unsupported(tmp_path):
    path = tmp_path / "x.webp"
    path.write_bytes(b"not-an-image-parser")
    with pytest.raises(UnsupportedInputError):
        parse_captured_source(
            path,
            logical_path=path.name,
            raw_bytes=path.read_bytes(),
        )
