"""Deterministic review sampling with a named seed.

The algorithm ranks a complete recorded population by HMAC-SHA256 of the
seed and subject token, then takes ``size`` members. It does not claim
statistical meaning. Sample-acceptance items are not required reviews.
"""

from __future__ import annotations

from collections.abc import Sequence

from veriformis.errors import ReviewError
from veriformis.review.models import (
    CORE_QUEUE_KINDS,
    SAMPLING_QUEUE_KIND,
    ReviewItem,
    ReviewSample,
    assemble_review_bundle,
)


def sample_subjects(
    *,
    seed: str,
    population: Sequence[str],
    size: int,
) -> ReviewSample:
    """Select ``size`` subjects from a complete population under a named seed."""
    items = tuple(population)
    if len(items) != len(set(items)):
        raise ReviewError("sample population must be unique")
    return ReviewSample.create(seed=seed, population=items, size=size)


def report_sample_queue(
    *,
    plan_id: str,
    seed: str,
    population: Sequence[str],
    size: int,
):
    """Fill sample-acceptance items from a deterministic named-seed draw."""
    sample = sample_subjects(seed=seed, population=population, size=size)
    collected = tuple(
        ReviewItem.create(
            queue_kind="sample-acceptance",
            subject_id=subject,
            required=False,
        )
        for subject in sample.selected
    )
    queues = tuple(sorted((*CORE_QUEUE_KINDS, SAMPLING_QUEUE_KIND)))
    items = tuple(sorted(item.item_id for item in collected))
    bundle = assemble_review_bundle(plan_id=plan_id, queues=queues, items=items)
    return sample, bundle
