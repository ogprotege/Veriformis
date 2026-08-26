"""Core review queues over existing construction and curation facts.

Item 14.3 lists the five core queue kinds on every bundle. Construction
`pending_review` decisions and curation `conflicting-target` quarantines
become items. Opt-in near-duplicate and detector queues stay off unless
requested. The bundle does not block seal.
"""

from __future__ import annotations

from veriformis.construction import ConstructionResult
from veriformis.datasets.models import CurationResult
from veriformis.review.models import (
    CORE_QUEUE_KINDS,
    OPT_IN_QUEUE_KINDS,
    ReviewItem,
    assemble_review_bundle,
)


def report_core_queues(
    *,
    plan_id: str,
    construction: ConstructionResult,
    curation: CurationResult | None = None,
    include_opt_in: bool = False,
):
    """Fill core queue kinds and items from construction and optional curation."""
    collected: list[ReviewItem] = []
    for decision in construction.decisions:
        if decision.status == "pending_review":
            collected.append(
                ReviewItem.create(
                    queue_kind="construction-pending",
                    subject_id=decision.candidate_id,
                    required=True,
                )
            )
    if curation is not None:
        for decision in curation.decisions:
            if (
                decision.status == "quarantined"
                and "conflicting-target" in decision.reason_codes
            ):
                collected.append(
                    ReviewItem.create(
                        queue_kind="conflict",
                        subject_id=decision.record_id,
                        required=False,
                    )
                )
    queues = CORE_QUEUE_KINDS
    if include_opt_in:
        queues = tuple(sorted((*CORE_QUEUE_KINDS, *OPT_IN_QUEUE_KINDS)))
    items = tuple(sorted(item.item_id for item in collected))
    return assemble_review_bundle(plan_id=plan_id, queues=queues, items=items)
