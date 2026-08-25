"""Phase 12.3 OCR identity pin: Tesseract 5 is named, recovery is not executable."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

from veriformis.contracts import (
    OCR_RECOVERY_IDENTITY_CONTRACT_ID,
    OCR_RECOVERY_IDENTITY_SCHEMA_ID,
)
from veriformis.errors import OcrIdentityError
from veriformis.ocr import (
    ADMITTED_LANGUAGES,
    LIMITATIONS,
    PREPROCESS_IDS,
    admitted_ocr_engine,
    build_ocr_page_identity,
    ocr_page_identity_id,
    require_ocr_recovery_not_executable,
)
from veriformis.ocr.identity import OcrBoundingBox, OcrConfidence, OcrPreprocess
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES


ROOT = Path(__file__).resolve().parents[2]
_DIGEST = "a" * 64
_G5 = ROOT / "tests" / "fixtures" / "group5"


def test_admitted_engine_is_tesseract_5_and_not_executable() -> None:
    pin = admitted_ocr_engine()
    assert pin.engine_id == "tesseract"
    assert pin.engine_family == "tesseract-5"
    assert pin.license == "Apache-2.0"
    assert pin.measured_version == "5.5.3"
    assert pin.admitted_languages == ("eng", "fra", "lat")
    assert pin.admitted_psm == (6,)
    assert pin.executable is False
    assert pin.extra_declared is False
    assert pin.contract_id == OCR_RECOVERY_IDENTITY_CONTRACT_ID
    assert pin.schema_id == OCR_RECOVERY_IDENTITY_SCHEMA_ID
    assert "handwriting-unsupported" in LIMITATIONS
    assert "osd-rotate/v1" in PREPROCESS_IDS
    assert ADMITTED_LANGUAGES == pin.admitted_languages


def test_ocr_recovery_is_not_executable() -> None:
    with pytest.raises(OcrIdentityError, match="not executable"):
        require_ocr_recovery_not_executable()


def test_page_identity_binds_engine_tessdata_page_and_raster() -> None:
    identity = build_ocr_page_identity(
        source_sha256=_DIGEST,
        page_index=1,
        raster_sha256="b" * 64,
        tessdata_language="eng",
        tessdata_sha256="c" * 64,
        engine_version="5.5.3",
        preprocess=(
            OcrPreprocess(
                transform_id="render-pdf-page/v1",
                parameters={"dpi": 200},
            ),
        ),
        boxes=(
            OcrBoundingBox(
                page_index=1,
                unit="raster-pixel",
                x0=0.0,
                y0=0.0,
                x1=10.0,
                y1=10.0,
            ),
        ),
        confidence=OcrConfidence(mean=90.0, minimum=80.0, word_count=4),
    )
    assert identity.recovery_path == "ocr"
    assert identity.psm == 6
    first = ocr_page_identity_id(identity)
    second = ocr_page_identity_id(identity)
    assert first == second
    assert first.startswith("ocr-page-v1-")


def test_unknown_language_preprocess_and_psm_fail_closed() -> None:
    with pytest.raises(OcrIdentityError, match="language"):
        build_ocr_page_identity(
            source_sha256=_DIGEST,
            page_index=1,
            raster_sha256=_DIGEST,
            tessdata_language="jpn",
            tessdata_sha256=_DIGEST,
            engine_version="5.5.3",
        )
    with pytest.raises(OcrIdentityError, match="PSM"):
        build_ocr_page_identity(
            source_sha256=_DIGEST,
            page_index=1,
            raster_sha256=_DIGEST,
            tessdata_language="eng",
            tessdata_sha256=_DIGEST,
            engine_version="5.5.3",
            psm=0,
        )
    with pytest.raises(OcrIdentityError, match="preprocess"):
        OcrPreprocess(transform_id="deskew/v1", parameters={})


def test_invalid_digest_and_backward_box_fail_closed() -> None:
    with pytest.raises(OcrIdentityError, match="SHA-256"):
        build_ocr_page_identity(
            source_sha256="abcd",
            page_index=1,
            raster_sha256=_DIGEST,
            tessdata_language="eng",
            tessdata_sha256=_DIGEST,
            engine_version="5.5.3",
        )
    with pytest.raises(OcrIdentityError, match="backward"):
        OcrBoundingBox(
            page_index=1,
            unit="pdf-point",
            x0=10.0,
            y0=10.0,
            x1=1.0,
            y1=1.0,
        )


def test_taxonomy_and_extra_unchanged() -> None:
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["optional-dependencies"]
    assert "ocr" not in extras


def test_empty_text_pdf_still_refuses() -> None:
    path = _G5 / "empty-text.pdf"
    refused = parse_pdf_file(path, logical_path=path.name, raw_bytes=path.read_bytes())
    assert refused.diagnostics.status == "refused"
    assert any(item.code == "pdf.ocr-required" for item in refused.diagnostics.diagnostics)


def test_identity_module_does_not_import_tesseract() -> None:
    assert "pytesseract" not in sys.modules
    admitted_ocr_engine()
    assert "pytesseract" not in sys.modules
    assert "tesseract" not in sys.modules
