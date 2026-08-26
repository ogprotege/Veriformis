"""Required unresolved reviews block seal. Default recipes stay none."""

from __future__ import annotations

from veriformis.construction import ConstructionResult
from veriformis.errors import ReviewError


def required_reviews_block_seal(construction: ConstructionResult) -> bool:
    """True when construction still has pending required-review decisions."""
    return any(decision.status == "pending_review" for decision in construction.decisions)


def assert_required_reviews_resolved(construction: ConstructionResult) -> None:
    """Fail closed before validate or seal when required reviews remain."""
    if required_reviews_block_seal(construction):
        raise ReviewError("required review is unresolved")
