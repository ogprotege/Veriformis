"""Phase 14.7: required unresolved reviews block seal; default recipes stay none."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.construction import DatasetRecipe
from veriformis.errors import ReviewError
from veriformis.identity import derive_id
from veriformis.quality import V1_QUALITY_GATES
from veriformis.recipes.library import RECIPE_LIBRARY_IDS, build_named_recipe
from veriformis.review import (
    assert_required_reviews_resolved,
    report_core_queues,
    required_reviews_block_seal,
)

from .test_review_queues import _construct


def test_required_pending_review_blocks_seal(tmp_path: Path) -> None:
    construction = _construct(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
        review_policy="required",
    )
    assert required_reviews_block_seal(construction) is True
    with pytest.raises(ReviewError, match="unresolved"):
        assert_required_reviews_resolved(construction)
    plan_id = derive_id("fdp", {"phase14": construction.result_id})
    report = report_core_queues(plan_id=plan_id, construction=construction)
    assert report.blocks_seal is True


def test_default_none_review_does_not_block_seal(tmp_path: Path) -> None:
    construction = _construct(
        tmp_path,
        (
            ("a.txt", "Alpha exact kept text for source one."),
            ("b.txt", "Beta completely different omega text."),
        ),
    )
    assert required_reviews_block_seal(construction) is False
    assert_required_reviews_resolved(construction)
    plan_id = derive_id("fdp", {"phase14": construction.result_id})
    report = report_core_queues(plan_id=plan_id, construction=construction)
    assert report.blocks_seal is False


def test_default_recipes_stay_none() -> None:
    assert DatasetRecipe.model_fields["review_policy"].default == "none"
    source_ids = ("src-v1-" + "0" * 64,)
    digest = "0" * 64
    for recipe_id in RECIPE_LIBRARY_IDS:
        recipe = build_named_recipe(
            recipe_id,
            source_ids=source_ids,
            cleaning_config_digest=digest,
        )
        assert recipe.review_policy == "none"


def test_quality_heuristics_still_do_not_block_seal() -> None:
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)
