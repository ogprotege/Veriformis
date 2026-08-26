"""Corrections as new transforms or mapping revisions.

A correction always creates a new identity. It cannot mutate an accepted
record in place. A waiver records a decision and does not change bytes.
"""

from __future__ import annotations

from veriformis.errors import ReviewError
from veriformis.identity import sha256_digest
from veriformis.mapping.models import FieldMapping, MappingPlan
from veriformis.review.models import (
    ReviewCorrection,
    ReviewItem,
    ReviewTransform,
    ReviewWaiver,
)


def record_transform_correction(
    *,
    item: ReviewItem,
    source_id: str,
    input_bytes: str | bytes,
    output_bytes: str | bytes,
    operation: str,
) -> tuple[ReviewTransform, ReviewCorrection]:
    """Bind a review item to a new source-grounded transform identity."""
    transform = ReviewTransform.create(
        source_id=source_id,
        input_sha256=sha256_digest(input_bytes),
        output_sha256=sha256_digest(output_bytes),
        operation=operation,
    )
    correction = ReviewCorrection.create(
        item_id=item.item_id,
        kind="transform",
        result_id=transform.transform_id,
    )
    return transform, correction


def revise_mapping_plan(
    prior: MappingPlan,
    *,
    field_mappings: tuple[FieldMapping, ...] | list[FieldMapping],
) -> MappingPlan:
    """Create a new mapping-plan identity from prior settings plus new rules."""
    revised = MappingPlan.create(
        goal_id=prior.goal_id,
        representation_id=prior.representation_id,
        row_schema=prior.row_schema,
        container_kind=prior.container_kind,
        confirmation_digest=prior.confirmation_digest,
        field_mappings=field_mappings,
        membership_policy=prior.membership_policy,
        review_policy=prior.review_policy,
    )
    if revised.mapping_plan_id == prior.mapping_plan_id:
        raise ReviewError("mapping revision must create a new mapping-plan identity")
    return revised


def record_mapping_revision(
    *,
    item: ReviewItem,
    prior_plan: MappingPlan,
    field_mappings: tuple[FieldMapping, ...] | list[FieldMapping],
) -> tuple[MappingPlan, ReviewCorrection]:
    """Bind a review item to a new mapping-plan identity."""
    revised = revise_mapping_plan(prior_plan, field_mappings=field_mappings)
    correction = ReviewCorrection.create(
        item_id=item.item_id,
        kind="mapping-revision",
        result_id=revised.mapping_plan_id,
    )
    return revised, correction


def record_waiver(
    *,
    item: ReviewItem,
    reviewer_id: str,
    rationale: str,
) -> ReviewWaiver:
    """Record a waiver. The accepted bytes stay unchanged."""
    return ReviewWaiver.create(
        item_id=item.item_id,
        reviewer_id=reviewer_id,
        rationale=rationale,
    )


def overwrite_accepted_record(record: object) -> None:
    """Fail closed. Accepted records are content-addressed and immutable."""
    raise ReviewError("correction cannot mutate an accepted record in place")
