"""Phase 14.8: supersession keeps prior reviews auditable."""

from __future__ import annotations

import pytest

from veriformis.construction import ReviewEvidence
from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.review import (
    assemble_review_bundle,
    record_supersession,
    supersede_review,
)


def _review(*, reviewer_id: str, verdict: str, rationale: str) -> ReviewEvidence:
    return ReviewEvidence.create(
        candidate_id=derive_id("cand", {"phase14": "supersession-candidate"}),
        reviewer_id=reviewer_id,
        verdict=verdict,  # type: ignore[arg-type]
        rationale=rationale,
    )


def test_supersession_keeps_prior_and_successor() -> None:
    prior = _review(
        reviewer_id="reviewer-a",
        verdict="accepted",
        rationale="First local attestation.",
    )
    successor = _review(
        reviewer_id="reviewer-b",
        verdict="rejected",
        rationale="Later local attestation.",
    )
    link = supersede_review(prior=prior, successor=successor)
    assert link.prior_review_id == prior.review_id
    assert link.successor_review_id == successor.review_id
    replay = supersede_review(prior=prior, successor=successor)
    assert replay == link
    plan_id = derive_id("fdp", {"phase14": "supersession-bundle"})
    bundle = assemble_review_bundle(
        plan_id=plan_id,
        verdicts=(prior.review_id,),
    )
    recorded = record_supersession(bundle, link)
    assert prior.review_id in recorded.verdicts
    assert successor.review_id in recorded.verdicts
    assert recorded.supersessions == (link,)
    assert recorded.verdicts == tuple(sorted((prior.review_id, successor.review_id)))


def test_supersession_refuses_same_review_or_other_candidate() -> None:
    prior = _review(
        reviewer_id="reviewer-a",
        verdict="accepted",
        rationale="First local attestation.",
    )
    with pytest.raises(ReviewError, match="same review"):
        supersede_review(prior=prior, successor=prior)
    other = ReviewEvidence.create(
        candidate_id=derive_id("cand", {"phase14": "other-candidate"}),
        reviewer_id="reviewer-b",
        verdict="rejected",
        rationale="Different candidate.",
    )
    with pytest.raises(ReviewError, match="same candidate"):
        supersede_review(prior=prior, successor=other)


def test_supersession_refuses_to_drop_the_prior() -> None:
    prior = _review(
        reviewer_id="reviewer-a",
        verdict="accepted",
        rationale="First local attestation.",
    )
    successor = _review(
        reviewer_id="reviewer-b",
        verdict="rejected",
        rationale="Later local attestation.",
    )
    link = supersede_review(prior=prior, successor=successor)
    plan_id = derive_id("fdp", {"phase14": "missing-prior"})
    empty = assemble_review_bundle(plan_id=plan_id, verdicts=(successor.review_id,))
    with pytest.raises(ReviewError, match="prior review is not in the bundle"):
        record_supersession(empty, link)
