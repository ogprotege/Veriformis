"""Bind a complete packet to the current pending construction candidates."""

from __future__ import annotations

from veriformis.construction import ConstructionResult, ReviewEvidence
from veriformis.errors import ReviewError
from veriformis.identity import lossless_json_bytes
from veriformis.review.exchange import load_review_packet, submit_review_packet
from veriformis.review.models import ReviewItem


def pending_construction_items(result: ConstructionResult) -> tuple[ReviewItem, ...]:
    return tuple(sorted((
        ReviewItem.create(
            queue_kind="construction-pending", subject_id=decision.candidate_id, required=True,
        )
        for decision in result.decisions if decision.status == "pending_review"
    ), key=lambda item: item.item_id))


def construction_review_evidence(
    payload: object, *, plan_id: str, construction: ConstructionResult,
) -> tuple[ReviewEvidence, ...]:
    packet = load_review_packet(payload)
    if packet.plan_id != plan_id:
        raise ReviewError("review packet names a different finished-dataset plan")
    expected = pending_construction_items(construction)
    if not expected or packet.items != expected:
        raise ReviewError("review packet must resolve exactly the current pending candidates")
    bundle = submit_review_packet(packet)
    if packet.corrections:
        raise ReviewError(
            "review corrections require a new source or mapping revision; "
            "they cannot promote the current candidate bytes"
        )
    decisions = {item.item_id: item for item in packet.decisions}
    waivers = {item.item_id: item for item in packet.waivers}
    reviews = []
    for item in expected:
        resolution = decisions.get(item.item_id) or waivers[item.item_id]
        # The existing evidence rationale carries the submitted bundle receipt
        # and the exact unsigned resolution, without adding persisted fields.
        receipt = lossless_json_bytes({
            "review_bundle_id": bundle.bundle_id,
            "review_packet_id": packet.packet_id,
            "resolution": resolution.model_dump(mode="json"),
        }).decode("utf-8")
        reviews.append(ReviewEvidence.create(
            candidate_id=item.subject_id, reviewer_id=resolution.reviewer_id,
            verdict=decisions[item.item_id].verdict if item.item_id in decisions else "accepted",
            rationale=receipt,
        ))
    return tuple(reviews)
