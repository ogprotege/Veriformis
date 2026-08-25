"""Phase 12.8: no-network, missing tessdata, corrupt raster, identity replay."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from veriformis.errors import OcrIdentityError
from veriformis.identity import sha256_digest
from veriformis.ocr.identity import build_ocr_page_identity, ocr_page_identity_id
from veriformis.ocr.recovery import OcrPageRequest
from veriformis.ocr.tesseract import TesseractProvider, tesseract_binary
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES


_CORPUS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase12" / "ocr-eval"
_DIGEST = "a" * 64


def test_default_parse_still_refuses_and_does_not_claim_ocr_image() -> None:
    path = _CORPUS / "clean-en.image.pdf"
    refused = parse_pdf_file(path, logical_path=path.name, raw_bytes=path.read_bytes())
    assert refused.diagnostics.status == "refused"
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)


def test_page_identity_replay_is_stable() -> None:
    first = build_ocr_page_identity(
        source_sha256=_DIGEST,
        page_index=1,
        raster_sha256="b" * 64,
        tessdata_language="eng",
        tessdata_sha256="c" * 64,
        engine_version="5.5.3",
    )
    second = build_ocr_page_identity(
        source_sha256=_DIGEST,
        page_index=1,
        raster_sha256="b" * 64,
        tessdata_language="eng",
        tessdata_sha256="c" * 64,
        engine_version="5.5.3",
    )
    assert ocr_page_identity_id(first) == ocr_page_identity_id(second)


def test_tesseract_missing_tessdata_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veriformis.ocr.tesseract.tessdata_path", lambda language: None)
    monkeypatch.setattr("veriformis.ocr.tesseract.tesseract_binary", lambda: "/usr/bin/tesseract")
    provider = TesseractProvider("eng")
    with pytest.raises(OcrIdentityError, match="tessdata"):
        provider.recover_page(
            OcrPageRequest(
                digital_text="",
                page_index=1,
                raster_png=b"\x89PNG",
                source_sha256=_DIGEST,
            )
        )


def test_tesseract_missing_binary_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("veriformis.ocr.tesseract.tesseract_binary", lambda: None)
    provider = TesseractProvider("eng")
    with pytest.raises(OcrIdentityError, match="PATH"):
        provider.recover_page(
            OcrPageRequest(
                digital_text="",
                page_index=1,
                raster_png=b"\x89PNG",
                source_sha256=_DIGEST,
            )
        )


@pytest.mark.skipif(tesseract_binary() is None, reason="tesseract is not on PATH")
def test_tesseract_corrupt_raster_fails_closed() -> None:
    provider = TesseractProvider("eng")
    with pytest.raises(OcrIdentityError, match="failed|raster"):
        provider.recover_page(
            OcrPageRequest(
                digital_text="",
                page_index=1,
                raster_png=b"this is not a png",
                source_sha256=_DIGEST,
            )
        )


@pytest.mark.skipif(tesseract_binary() is None, reason="tesseract is not on PATH")
def test_tesseract_provider_does_not_open_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args, **_kwargs):
        raise AssertionError("OCR provider opened a network socket")

    monkeypatch.setattr(socket, "socket", refuse)
    path = _CORPUS / "clean-en.image.pdf"
    result = parse_pdf_file(
        path,
        logical_path=path.name,
        raw_bytes=path.read_bytes(),
        ocr_provider=TesseractProvider("eng"),
    )
    assert "Veriformis" in result.source.extracted_text
    assert sha256_digest(path.read_bytes())
