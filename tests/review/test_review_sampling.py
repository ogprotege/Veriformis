"""Phase 14.5: named-seed sampling with complete population evidence."""

from __future__ import annotations

import pytest

from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.review import (
    CORE_QUEUE_KINDS,
    SAMPLE_ALGORITHM_ID,
    SAMPLING_QUEUE_KIND,
    ReviewSample,
    report_sample_queue,
    sample_subjects,
)


POPULATION = tuple(f"row-{index:02d}" for index in range(10))
UNICODE_POPULATION = ("alpha", "café-row", "omega", "row-04", "row-05")


def test_named_seed_replays_and_records_the_population() -> None:
    first = sample_subjects(seed="operator-seed", population=POPULATION, size=3)
    second = sample_subjects(seed="operator-seed", population=POPULATION, size=3)
    assert first == second
    assert first.algorithm_id == SAMPLE_ALGORITHM_ID
    assert first.statistical_meaning is False
    assert first.seed == "operator-seed"
    assert first.population == POPULATION
    assert first.size == 3
    assert len(first.selected) == 3
    assert set(first.selected) <= set(POPULATION)
    shuffled = sample_subjects(
        seed="operator-seed",
        population=tuple(reversed(POPULATION)),
        size=3,
    )
    assert shuffled == first


def test_different_seed_changes_selection() -> None:
    first = sample_subjects(seed="seed-alpha", population=POPULATION, size=3)
    second = sample_subjects(seed="seed-beta", population=POPULATION, size=3)
    assert first.selected != second.selected
    assert first.sample_id != second.sample_id


def test_unicode_population_is_exact_and_replayable() -> None:
    first = sample_subjects(seed="unicode-seed", population=UNICODE_POPULATION, size=2)
    second = sample_subjects(seed="unicode-seed", population=UNICODE_POPULATION, size=2)
    assert first == second
    assert "café-row" in first.population
    assert set(first.selected) <= set(UNICODE_POPULATION)


def test_invalid_seed_size_and_duplicates_fail_closed() -> None:
    with pytest.raises(ReviewError, match="lowercase token"):
        sample_subjects(seed="Seed", population=POPULATION, size=1)
    with pytest.raises(ReviewError, match="unique"):
        sample_subjects(seed="operator-seed", population=("a", "a"), size=1)
    with pytest.raises(ReviewError, match="exceed"):
        sample_subjects(seed="operator-seed", population=POPULATION, size=99)
    with pytest.raises(ReviewError, match="positive"):
        sample_subjects(seed="operator-seed", population=POPULATION, size=0)


def test_tampered_selection_fails_closed() -> None:
    sample = sample_subjects(seed="operator-seed", population=POPULATION, size=2)
    payload = sample.model_dump(mode="json")
    payload["selected"] = list(POPULATION[:2])
    with pytest.raises(ReviewError, match="named seed"):
        ReviewSample.model_validate(payload)


def test_sample_queue_items_are_not_required() -> None:
    plan_id = derive_id("fdp", {"phase14": "sampling"})
    sample, bundle = report_sample_queue(
        plan_id=plan_id,
        seed="operator-seed",
        population=POPULATION,
        size=2,
    )
    assert SAMPLING_QUEUE_KIND in bundle.queues
    assert set(CORE_QUEUE_KINDS) <= set(bundle.queues)
    assert bundle.blocks_seal is False
    assert len(bundle.items) == sample.size
    assert sample.statistical_meaning is False
