"""Phase 12.1 isolation: OCR remains refused and is not an extra."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import (
    EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES,
    implemented_discovery,
)


ROOT = Path(__file__).resolve().parents[2]
_G5 = Path(__file__).resolve().parents[1] / "fixtures" / "group5"
_OCR_ENGINE_MODULES = (
    "pytesseract",
    "easyocr",
    "paddleocr",
    "paddleocr.paddleocr",
    "rapidocr_onnxruntime",
    "rapidocr",
    "surya",
    "ocrmypdf",
    "doctr",
    "ocrmac",
)
_LOCK_EXTRAS = (
    'provides-extras = ["test", "trl", "mlx-lm", "columnar", "axolotl", '
    '"llama-factory", "unsloth"]'
)


def test_ocr_image_remains_explicitly_unsupported() -> None:
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)
    assert "ocr-image" not in implemented_discovery()["input_family"]


def test_pyproject_has_no_ocr_extra() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    extras = tomllib.loads(text)["project"]["optional-dependencies"]
    assert "ocr" not in extras
    assert "ocr =" not in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert _LOCK_EXTRAS in lock
    assert 'name = "pytesseract"\n' not in lock
    assert 'name = "easyocr"\n' not in lock
    assert 'name = "paddleocr"\n' not in lock
    assert 'name = "rapidocr"\n' not in lock
    assert 'name = "rapidocr-onnxruntime"\n' not in lock
    assert 'name = "surya-ocr"\n' not in lock
    assert 'name = "ocrmypdf"\n' not in lock
    assert 'name = "python-doctr"\n' not in lock
    assert 'name = "ocrmac"\n' not in lock


def test_empty_text_pdf_still_refuses_as_ocr_required(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    payload = (_G5 / "empty-text.pdf").read_bytes()
    path.write_bytes(payload)
    refused = parse_pdf_file(path, logical_path=path.name, raw_bytes=payload)
    assert refused.diagnostics.status == "refused"
    codes = {item.code for item in refused.diagnostics.diagnostics}
    assert "pdf.ocr-required" in codes
    assert any(
        item.details.get("limitation") == "ocr-unsupported"
        for item in refused.diagnostics.diagnostics
    )
    dispatched = parse_captured_source(
        path, logical_path=path.name, raw_bytes=payload
    )
    assert dispatched.diagnostics.status == "refused"
    assert any(
        item.code == "pdf.ocr-required" for item in dispatched.diagnostics.diagnostics
    )


def test_digitally_born_pdf_still_extracts_text_layer(tmp_path: Path) -> None:
    path = tmp_path / "born.pdf"
    payload = (_G5 / "minimal-text.pdf").read_bytes()
    path.write_bytes(payload)
    result = parse_pdf_file(path, logical_path=path.name, raw_bytes=payload)
    assert result.diagnostics.status == "complete"
    assert "Hello" in result.source.extracted_text
    assert "pdf.ocr-required" not in {
        item.code for item in result.diagnostics.diagnostics
    }


def test_core_parse_does_not_import_ocr_libraries(tmp_path: Path) -> None:
    for name in _OCR_ENGINE_MODULES:
        assert name not in sys.modules
    payload = (_G5 / "empty-text.pdf").read_bytes()
    parse_pdf_file(tmp_path / "scan.pdf", logical_path="scan.pdf", raw_bytes=payload)
    parse_captured_source(
        tmp_path / "born.pdf",
        logical_path="born.pdf",
        raw_bytes=(_G5 / "minimal-text.pdf").read_bytes(),
    )
    for name in _OCR_ENGINE_MODULES:
        assert name not in sys.modules
