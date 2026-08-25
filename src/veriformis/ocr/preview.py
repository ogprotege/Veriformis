"""Read-only OCR page previews and review hooks. No Phase 14 review platform."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from veriformis.identity import lossless_json_bytes
from veriformis.ocr.recovery import PdfDocumentRecovery
from veriformis.ocr.thresholds import ConfidenceAction


class OcrPagePreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    confidence_action: ConfidenceAction | None
    has_held_text: bool
    page_index: int
    pending_review: bool
    recovery_path: str


class OcrPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    pages: tuple[OcrPagePreview, ...]
    recovery_path: str
    schema_id: str = "veriformis.ocr-preview/v1"

    def transport_text(self) -> str:
        payload: dict[str, Any] = self.model_dump(mode="json")
        return lossless_json_bytes(payload).decode("utf-8")


def page_previews(recovery: PdfDocumentRecovery) -> OcrPreview:
    """Build review hooks from a classified recovery without mutating sources."""
    pages = tuple(
        OcrPagePreview(
            confidence_action=page.confidence_action,
            has_held_text=bool(page.held_text.strip()),
            page_index=page.page_index,
            pending_review=page.confidence_action == "review",
            recovery_path=page.recovery_path,
        )
        for page in recovery.pages
    )
    return OcrPreview(pages=pages, recovery_path=recovery.recovery_path)
