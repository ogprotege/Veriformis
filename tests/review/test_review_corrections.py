"""Phase 14.4: corrections create new identities; waivers do not change bytes."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriformis.errors import ReviewError
from veriformis.identity import derive_id, sha256_digest
from veriformis.mapping import FieldMapping, MappingPlan
from veriformis.review import (
    ReviewCorrection,
    ReviewItem,
    assemble_review_bundle,
    overwrite_accepted_record,
    record_mapping_revision,
    record_transform_correction,
    record_waiver,
    revise_mapping_plan,
)


CONFIRM = sha256_digest("phase14-04-unconfirmed")


def _item() -> ReviewItem:
    return ReviewItem.create(
        queue_kind="construction-pending",
        subject_id=derive_id("cand", {"phase14": "correction-subject"}),
        required=True,
    )


def _text_plan(*, source_path: str) -> MappingPlan:
    return MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=CONFIRM,
        field_mappings=(
            FieldMapping.create(source_path=source_path, target_key="text"),
        ),
    )


def test_transform_correction_creates_new_identity() -> None:
    item = _item()
    source_id = derive_id("src", {"phase14": "correction-source"})
    first_transform, first = record_transform_correction(
        item=item,
        source_id=source_id,
        input_bytes="kept café source",
        output_bytes="kept cafe source",
        operation="replace-span",
    )
    second_transform, second = record_transform_correction(
        item=item,
        source_id=source_id,
        input_bytes="kept café source",
        output_bytes="kept cafe source",
        operation="replace-span",
    )
    assert first == second
    assert first_transform == second_transform
    assert first.kind == "transform"
    assert first.result_id == first_transform.transform_id
    assert first.result_id.startswith("trn-v1-")
    assert first_transform.input_sha256 != first_transform.output_sha256
    assert first_transform.input_sha256 == sha256_digest("kept café source")


def test_identical_bytes_cannot_be_a_transform() -> None:
    item = _item()
    with pytest.raises(ReviewError, match="must change bytes"):
        record_transform_correction(
            item=item,
            source_id=derive_id("src", {"phase14": "correction-source"}),
            input_bytes="unchanged",
            output_bytes="unchanged",
            operation="replace-span",
        )


def test_mapping_revision_creates_new_plan_identity() -> None:
    item = _item()
    prior = _text_plan(source_path="text")
    revised, correction = record_mapping_revision(
        item=item,
        prior_plan=prior,
        field_mappings=(
            FieldMapping.create(source_path="body", target_key="text"),
        ),
    )
    assert revised.mapping_plan_id != prior.mapping_plan_id
    assert correction.kind == "mapping-revision"
    assert correction.result_id == revised.mapping_plan_id
    replay = revise_mapping_plan(
        prior,
        field_mappings=(
            FieldMapping.create(source_path="body", target_key="text"),
        ),
    )
    assert replay == revised


def test_unchanged_mapping_is_not_a_revision() -> None:
    prior = _text_plan(source_path="text")
    with pytest.raises(ReviewError, match="new mapping-plan identity"):
        revise_mapping_plan(prior, field_mappings=prior.field_mappings)


def test_waiver_does_not_change_bytes() -> None:
    item = _item()
    waiver = record_waiver(
        item=item,
        reviewer_id="local-operator",
        rationale="Keep the finding. Bytes stay.",
    )
    assert waiver.changes_bytes is False
    assert waiver.item_id == item.item_id
    payload = waiver.model_dump(mode="json")
    payload["changes_bytes"] = True
    with pytest.raises((ReviewError, ValidationError)):
        type(waiver).model_validate(payload)


def test_in_place_mutation_of_accepted_record_is_refused() -> None:
    item = _item()
    with pytest.raises(ReviewError, match="cannot mutate an accepted record"):
        overwrite_accepted_record(item)
    with pytest.raises(ValidationError):
        item.required = False  # type: ignore[misc]


def test_correction_result_kind_must_match() -> None:
    item_id = derive_id("rit", {"phase14": "kind-mismatch"})
    with pytest.raises(ReviewError, match="transform or mapping-plan"):
        ReviewCorrection.create(
            item_id=item_id,
            kind="transform",
            result_id=derive_id("mpl", {"phase14": "not-a-transform"}),
        )
    with pytest.raises(ReviewError, match="transform or mapping-plan"):
        ReviewCorrection.create(
            item_id=item_id,
            kind="mapping-revision",
            result_id=derive_id("trn", {"phase14": "not-a-mapping"}),
        )


def test_bundle_can_hold_correction_without_blocking_seal() -> None:
    item = _item()
    _transform, correction = record_transform_correction(
        item=item,
        source_id=derive_id("src", {"phase14": "correction-source"}),
        input_bytes="alpha",
        output_bytes="beta",
        operation="replace-span",
    )
    plan_id = derive_id("fdp", {"phase14": "correction-bundle"})
    bundle = assemble_review_bundle(
        plan_id=plan_id,
        items=(item.item_id,),
        corrections=(correction,),
    )
    assert bundle.blocks_seal is False
    assert bundle.corrections == (correction,)
    assert bundle.waivers == ()
