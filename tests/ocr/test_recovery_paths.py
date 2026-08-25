"""Phase 12.4: digital text is never replaced; pages are classified."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.errors import OcrIdentityError
from veriformis.ocr.identity import build_ocr_page_identity
from veriformis.ocr.recovery import (
    OcrPageRequest,
    OcrPageResult,
    document_recovery_path,
    page_kind,
    recover_pages,
)
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES


ROOT = Path(__file__).resolve().parents[2]
_G5 = ROOT / "tests" / "fixtures" / "group5"
_CORPUS = ROOT / "tests" / "fixtures" / "phase12" / "ocr-eval"
_DIGEST = "a" * 64


class _RecordingProvider:
    def __init__(self, text: str = "OCR recovered line.") -> None:
        self.called: list[int] = []
        self.text = text

    def recover_page(self, request: OcrPageRequest) -> OcrPageResult:
        self.called.append(request.page_index)
        if request.digital_text.strip():
            raise OcrIdentityError("OCR must not replace recoverable digital text")
        identity = build_ocr_page_identity(
            source_sha256=request.source_sha256,
            page_index=request.page_index,
            raster_sha256="b" * 64,
            tessdata_language="eng",
            tessdata_sha256="c" * 64,
            engine_version="5.5.3",
        )
        return OcrPageResult(identity=identity, text=self.text)


def test_page_and_document_classification() -> None:
    assert page_kind("Hello") == "digital"
    assert page_kind("  ") == "ocr"
    assert document_recovery_path(("digital",)) == "digital"
    assert document_recovery_path(("ocr",)) == "ocr"
    assert document_recovery_path(("digital", "ocr")) == "merged"


def test_recover_pages_never_calls_provider_for_digital_text() -> None:
    provider = _RecordingProvider()
    recovery = recover_pages(
        ("Digital page one.", ""),
        source_sha256=_DIGEST,
        provider=provider,
    )
    assert recovery.recovery_path == "merged"
    assert [page.recovery_path for page in recovery.pages] == ["digital", "ocr"]
    assert recovery.pages[0].text == "Digital page one."
    assert recovery.pages[1].text == "OCR recovered line."
    assert provider.called == [2]


def test_request_with_digital_text_fails_closed() -> None:
    with pytest.raises(OcrIdentityError, match="must not replace"):
        OcrPageRequest(digital_text="keep me", page_index=1, source_sha256=_DIGEST)


def test_mixed_pdf_without_provider_keeps_digital_and_omits_empty() -> None:
    path = _CORPUS / "mixed-en.text.pdf"
    result = parse_pdf_file(path, logical_path=path.name, raw_bytes=path.read_bytes())
    assert result.diagnostics.status == "degraded"
    assert "Digital text on page one." in result.source.extracted_text
    empty = next(
        item
        for item in result.diagnostics.diagnostics
        if item.code == "pdf.empty-text-pages"
    )
    assert empty.details["recovery_path"] == "merged"
    assert empty.details["pages"] == [
        {"page_index": 1, "recovery_path": "digital"},
        {"page_index": 2, "recovery_path": "ocr"},
    ]


def test_mixed_pdf_with_provider_merges_without_replacing_digital() -> None:
    path = _CORPUS / "mixed-en.text.pdf"
    provider = _RecordingProvider("OCR page two.")
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=provider,
    )
    assert result.diagnostics.status == "complete"
    assert "Digital text on page one." in result.source.extracted_text
    assert "OCR page two." in result.source.extracted_text
    assert provider.called == [2]


def test_image_only_pdf_without_provider_still_refuses() -> None:
    path = _G5 / "empty-text.pdf"
    refused = parse_pdf_file(path, logical_path=path.name, raw_bytes=path.read_bytes())
    assert refused.diagnostics.status == "refused"
    required = next(
        item
        for item in refused.diagnostics.diagnostics
        if item.code == "pdf.ocr-required"
    )
    assert required.details["recovery_path"] == "ocr"
    assert required.details["limitation"] == "ocr-unsupported"


def test_image_only_pdf_with_provider_emits_ocr_path() -> None:
    path = _G5 / "empty-text.pdf"
    provider = _RecordingProvider("Scanned sentence.")
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=provider,
    )
    assert result.diagnostics.status == "complete"
    assert "Scanned sentence." in result.source.extracted_text
    assert provider.called == [1]


def test_digitally_born_pdf_does_not_invoke_provider() -> None:
    path = _G5 / "minimal-text.pdf"
    provider = _RecordingProvider()
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=provider,
    )
    assert result.diagnostics.status == "complete"
    assert "Hello" in result.source.extracted_text
    assert provider.called == []
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)



