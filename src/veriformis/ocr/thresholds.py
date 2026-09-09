"""OCR confidence policy. Low-confidence text is not deleted silently."""

from __future__ import annotations

from typing import Literal

from veriformis.ocr.identity import OcrConfidence


OCR_CONFIDENCE_POLICY_SCHEMA_ID = "veriformis.ocr-confidence-policy/v1"
REFUSE_BELOW_MINIMUM = 30.0
REVIEW_BELOW_MEAN = 60.0
WARN_BELOW_MEAN = 80.0
ConfidenceAction = Literal["accept", "warn", "review", "refuse"]


def decide_confidence(confidence: OcrConfidence | None) -> ConfidenceAction:
    """Return the v1 action for one OCR page.

    A page with no scored words has nothing to accept on; it requires review
    rather than passing silently (post-20 defect D-14).
    """
    if confidence is None:
        return "review"
    if confidence.minimum < REFUSE_BELOW_MINIMUM:
        return "refuse"
    if confidence.mean < REVIEW_BELOW_MEAN:
        return "review"
    if confidence.mean < WARN_BELOW_MEAN:
        return "warn"
    return "accept"
