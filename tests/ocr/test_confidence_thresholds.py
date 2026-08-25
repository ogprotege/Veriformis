"""Phase 12.5: OCR confidence warns, reviews, or refuses; it does not delete."""

from __future__ import annotations

from pathlib import Path

from veriformis.ocr.identity import OcrConfidence, build_ocr_page_identity
from veriformis.ocr.recovery import OcrPageRequest, OcrPageResult, recover_pages
from veriformis.ocr.thresholds import (
    REFUSE_BELOW_MINIMUM,
    REVIEW_BELOW_MEAN,
    WARN_BELOW_MEAN,
    decide_confidence,
)
from veriformis.parsers.pdf import parse_pdf_file


_G5 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "group5"
_DIGEST = "a" * 64


class _ConfidenceProvider:
    def __init__(self, confidence: OcrConfidence) -> None:
        self.confidence = confidence

    def recover_page(self, request: OcrPageRequest) -> OcrPageResult:
        identity = build_ocr_page_identity(
            source_sha256=request.source_sha256,
            page_index=request.page_index,
            raster_sha256="b" * 64,
            tessdata_language="eng",
            tessdata_sha256="c" * 64,
            engine_version="5.5.3",
            confidence=self.confidence,
        )
        return OcrPageResult(identity=identity, text="held OCR sentence")


def test_decide_confidence_thresholds() -> None:
    assert decide_confidence(None) == "accept"
    assert (
        decide_confidence(OcrConfidence(mean=90.0, minimum=85.0, word_count=3))
        == "accept"
    )
    assert (
        decide_confidence(OcrConfidence(mean=70.0, minimum=65.0, word_count=3))
        == "warn"
    )
    assert (
        decide_confidence(OcrConfidence(mean=50.0, minimum=40.0, word_count=3))
        == "review"
    )
    assert (
        decide_confidence(OcrConfidence(mean=90.0, minimum=10.0, word_count=3))
        == "refuse"
    )
    assert WARN_BELOW_MEAN == 80.0
    assert REVIEW_BELOW_MEAN == 60.0
    assert REFUSE_BELOW_MINIMUM == 30.0


def test_warn_and_review_keep_ocr_text() -> None:
    warned = recover_pages(
        ("",),
        source_sha256=_DIGEST,
        provider=_ConfidenceProvider(OcrConfidence(mean=70.0, minimum=65.0, word_count=2)),
    )
    assert warned.pages[0].confidence_action == "warn"
    assert warned.pages[0].text == "held OCR sentence"
    assert warned.pages[0].held_text == "held OCR sentence"
    reviewed = recover_pages(
        ("",),
        source_sha256=_DIGEST,
        provider=_ConfidenceProvider(OcrConfidence(mean=50.0, minimum=40.0, word_count=2)),
    )
    assert reviewed.pages[0].confidence_action == "review"
    assert reviewed.pages[0].text == "held OCR sentence"


def test_refuse_omits_stream_but_retains_held_text() -> None:
    recovery = recover_pages(
        ("",),
        source_sha256=_DIGEST,
        provider=_ConfidenceProvider(OcrConfidence(mean=90.0, minimum=10.0, word_count=2)),
    )
    assert recovery.pages[0].confidence_action == "refuse"
    assert recovery.pages[0].text == ""
    assert recovery.pages[0].held_text == "held OCR sentence"


def test_parse_refuse_keeps_held_text_out_of_extracted_stream() -> None:
    path = _G5 / "empty-text.pdf"
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=_ConfidenceProvider(
            OcrConfidence(mean=90.0, minimum=10.0, word_count=2)
        ),
    )
    assert result.diagnostics.status == "refused"
    assert "held OCR sentence" not in result.source.extracted_text
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "pdf.ocr-confidence-refuse" in codes


def test_parse_warn_preserves_ocr_text() -> None:
    path = _G5 / "empty-text.pdf"
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=_ConfidenceProvider(
            OcrConfidence(mean=70.0, minimum=65.0, word_count=2)
        ),
    )
    assert result.diagnostics.status == "degraded"
    assert "held OCR sentence" in result.source.extracted_text
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "pdf.ocr-confidence-warn" in codes
