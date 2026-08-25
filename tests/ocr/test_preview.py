"""Phase 12.6: page previews and review hooks do not mutate sources."""

from __future__ import annotations

import json
from pathlib import Path

from veriformis.ocr.preview import page_previews
from veriformis.ocr.recovery import recover_pages
from veriformis.pipeline.service import PipelineService


_CORPUS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase12" / "ocr-eval"
_G5 = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "group5"


def test_mixed_preview_marks_ocr_page_without_review() -> None:
    recovery = recover_pages(
        ("Digital page one.", ""),
        source_sha256="a" * 64,
    )
    preview = page_previews(recovery)
    assert preview.recovery_path == "merged"
    assert preview.pages[0].recovery_path == "digital"
    assert preview.pages[0].pending_review is False
    assert preview.pages[1].recovery_path == "ocr"
    assert preview.pages[1].has_held_text is False


def test_pipeline_and_cli_preview_mixed_pdf(tmp_path: Path) -> None:
    path = _CORPUS / "mixed-en.text.pdf"
    outcome = PipelineService().ocr_preview([path])
    assert outcome.preview is not None
    assert outcome.preview.recovery_path == "merged"
    payload = json.loads(outcome.preview.transport_text())
    assert payload["schema_id"] == "veriformis.ocr-preview/v1"
    assert payload["pages"][0]["recovery_path"] == "digital"
    assert payload["pages"][1]["recovery_path"] == "ocr"


def test_image_only_preview_is_ocr_path() -> None:
    path = _G5 / "empty-text.pdf"
    outcome = PipelineService().ocr_preview([path])
    assert outcome.preview is not None
    assert outcome.preview.recovery_path == "ocr"
