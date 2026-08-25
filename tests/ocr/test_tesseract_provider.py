"""Phase 12.7: empty ocr extra and optional Tesseract subprocess provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.errors import OcrIdentityError
from veriformis.ocr.tesseract import TesseractProvider, tesseract_binary
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES


_CORPUS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase12" / "ocr-eval"
_G5 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "group5"

pytestmark = pytest.mark.skipif(
    tesseract_binary() is None, reason="tesseract is not on PATH"
)


def test_tesseract_provider_recovers_image_only_english() -> None:
    path = _CORPUS / "clean-en.image.pdf"
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=TesseractProvider("eng"),
    )
    assert "Veriformis recovers source text" in result.source.extracted_text
    assert result.diagnostics.status in {"complete", "degraded"}


def test_tesseract_provider_does_not_replace_digital_text() -> None:
    path = _G5 / "minimal-text.pdf"
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=TesseractProvider("eng"),
    )
    assert "Hello" in result.source.extracted_text
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)


def test_unknown_language_fails_closed() -> None:
    with pytest.raises(OcrIdentityError, match="language"):
        TesseractProvider("jpn")
