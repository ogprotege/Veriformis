"""Inter-reviewer supersession. Prior reviews stay auditable."""

from __future__ import annotations

from veriformis.construction import ReviewEvidence
from veriformis.errors import ReviewError
from veriformis.review.models import (
    ReviewBundle,
    ReviewSupersession,
    assemble_review_bundle,
)


def supersede_review(
    *,
    prior: ReviewEvidence,
    successor: ReviewEvidence,
) -> ReviewSupersession:
    """Record a successor review. The prior review identity is retained."""
    if prior.review_id == successor.review_id:
        raise ReviewError("supersession cannot name the same review twice")
    if prior.candidate_id != successor.candidate_id:
        raise ReviewError("supersession must name the same candidate")
    return ReviewSupersession.create(
        prior_review_id=prior.review_id,
        successor_review_id=successor.review_id,
    )


def record_supersession(
    bundle: ReviewBundle,
    supersession: ReviewSupersession,
) -> ReviewBundle:
    """Attach a supersession. Both review identities remain in verdicts."""
    if supersession.prior_review_id not in bundle.verdicts:
        raise ReviewError("supersession prior review is not in the bundle")
    verdicts = tuple(
        sorted(
            {
                *bundle.verdicts,
                supersession.prior_review_id,
                supersession.successor_review_id,
            }
        )
    )
    existing = tuple(
        item.supersession_id for item in bundle.supersessions
    )
    if supersession.supersession_id in existing:
        raise ReviewError("supersession is already recorded")
    supersessions = tuple(
        sorted(
            (*bundle.supersessions, supersession),
            key=lambda item: item.supersession_id,
        )
    )
    return assemble_review_bundle(
        plan_id=bundle.plan_id,
        queues=bundle.queues,
        items=bundle.items,
        assignments=bundle.assignments,
        verdicts=verdicts,
        waivers=bundle.waivers,
        corrections=bundle.corrections,
        supersessions=supersessions,
        blocks_seal=bundle.blocks_seal,
    )
