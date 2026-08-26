"""Export, import, and submit review packets.

CLI, MCP, and Python call the same functions. A required item must be
resolved by a decision, waiver, or correction before submit. The bundle
still does not block seal.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from veriformis.errors import ReviewError
from veriformis.review.models import (
    ReviewBundle,
    ReviewItem,
    ReviewPacket,
    assemble_review_bundle,
)


def export_review_packet(
    *,
    plan_id: str,
    items: Sequence[ReviewItem],
) -> ReviewPacket:
    """Write a pending packet. Decisions, waivers, and corrections stay vacant."""
    return ReviewPacket.create(plan_id=plan_id, items=tuple(items))


def load_review_packet(payload: ReviewPacket | dict[str, Any] | str | bytes) -> ReviewPacket:
    """Reload a packet from JSON text, bytes, or an object dump."""
    if isinstance(payload, ReviewPacket):
        return payload
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ReviewError("review packet payload is invalid")
    return ReviewPacket.model_validate(payload)


def submit_review_packet(packet: ReviewPacket) -> ReviewBundle:
    """Bind completed review evidence. Required items must be resolved."""
    resolved: dict[str, str] = {}
    for decision in packet.decisions:
        resolved[decision.item_id] = "decision"
    for waiver in packet.waivers:
        if waiver.item_id in resolved:
            raise ReviewError("review item is resolved twice")
        resolved[waiver.item_id] = "waiver"
    for correction in packet.corrections:
        if correction.item_id in resolved:
            raise ReviewError("review item is resolved twice")
        resolved[correction.item_id] = "correction"
    for item in packet.items:
        if item.required and item.item_id not in resolved:
            raise ReviewError("required review item is unresolved")
    queues = tuple(sorted({item.queue_kind for item in packet.items}))
    return assemble_review_bundle(
        plan_id=packet.plan_id,
        queues=queues,
        items=tuple(item.item_id for item in packet.items),
        verdicts=tuple(sorted(item.decision_id for item in packet.decisions)),
        waivers=packet.waivers,
        corrections=packet.corrections,
    )
