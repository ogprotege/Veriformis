"""Phase 12.2: retained OCR corpus, still no extra, still refuse image-only PDF."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from veriformis.parsers.pdf import parse_pdf_file
from veriformis.taxonomy import EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fixtures" / "phase12" / "ocr-eval"
PACKET = ROOT / "dev" / "active" / "independent-product" / "phase-12-optional-ocr"
MANIFEST = CORPUS / "manifest.json"
RESULTS = PACKET / "evaluation.md"
RESULTS_JSON = PACKET / "evaluation-results.json"


def _parse(path: Path):
    payload = path.read_bytes()
    return parse_pdf_file(path, logical_path=path.name, raw_bytes=payload)


def test_corpus_manifest_matches_retained_bytes() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "veriformis.phase12-ocr-eval-corpus/v1"
    assert manifest["excluded"]["handwriting"]
    assert manifest["excluded"]["cloud-ocr"]
    from veriformis.identity import sha256_digest

    files = manifest["files"]
    assert files
    for name, digest in files.items():
        payload = (CORPUS / name).read_bytes()
        assert sha256_digest(payload) == digest, name


def test_image_only_corpus_pdfs_still_refuse_ocr() -> None:
    paths = sorted(CORPUS.glob("*.image.pdf"))
    assert paths
    for path in paths:
        result = _parse(path)
        assert result.diagnostics.status == "refused", path.name
        codes = {item.code for item in result.diagnostics.diagnostics}
        assert "pdf.ocr-required" in codes, path.name
        assert any(
            item.details.get("limitation") == "ocr-unsupported"
            for item in result.diagnostics.diagnostics
        ), path.name
        assert result.source.extracted_text == ""


def test_text_layer_corpus_pdfs_still_extract() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for case_id, spec in manifest["cases"].items():
        if case_id == "mixed-en":
            continue
        path = CORPUS / f"{case_id}.text.pdf"
        result = _parse(path)
        assert result.diagnostics.status == "complete", case_id
        assert spec["expected"].split()[0] in result.source.extracted_text


def test_mixed_pdf_keeps_digital_text_and_does_not_refuse() -> None:
    result = _parse(CORPUS / "mixed-en.text.pdf")
    assert result.diagnostics.status == "degraded"
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "pdf.empty-text-pages" in codes
    assert "pdf.ocr-required" not in codes
    assert "Digital text on page one." in result.source.extracted_text


def test_ocr_image_and_extra_remain_absent() -> None:
    assert EXPLICITLY_UNSUPPORTED_INPUT_FAMILIES == ("ocr-image",)
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["optional-dependencies"]
    assert "ocr" not in extras


def test_evaluation_report_and_results_are_retained() -> None:
    assert RESULTS.is_file()
    text = RESULTS.read_text(encoding="utf-8")
    assert "Tesseract 5" in text
    assert "Surya" in text
    assert "Awaiting operator ADR or deferral" in text
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    assert payload["schema"] == "veriformis.phase12-ocr-eval-results/v1"
    assert payload["tesseract"]["available"] is True
    measured = {item["id"]: item for item in payload["tesseract"]["measurements"]}
    assert measured["clean-en"]["character_error_rate"] == 0.0
    assert measured["table-en"]["character_error_rate"] == 0.0
    assert measured["rotated-en"]["character_error_rate"] > 1.0
    assert "Orientation in degrees: 90" in payload["tesseract"]["osd_probe_rotated_en"][
        "stdout"
    ]
