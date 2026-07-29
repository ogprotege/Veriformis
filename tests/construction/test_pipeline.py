from __future__ import annotations

import pytest

from veriformis.construction import (
    CandidateRecord,
    ConstructionError,
    ConstructionInputs,
    ConstructionPass,
    DatasetRecipe,
    ReviewEvidence,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
    construction_result_from_dict,
    construction_result_to_dict,
    validate_construction_result,
)
from veriformis.identity import canonical_digest
from veriformis.ir import Paragraph, Text

from .helpers import inputs_for, recipe_for, source_bundle


def test_default_promotion_and_exact_replay(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="auto.txt",
        blocks=[Paragraph(children=[Text("Automatically accepted source text")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for((bundle,))

    result = construct_dataset(recipe, inputs)

    assert [item.status for item in result.decisions] == ["accepted"]
    assert [item.candidate_id for item in result.records] == [
        result.candidates[0].candidate_id
    ]
    assert validate_construction_result(recipe, inputs, result) == result
    assert construction_result_from_dict(construction_result_to_dict(result)) == result


def test_required_review_blocks_then_promotes_with_separate_evidence(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="review.txt",
        blocks=[Paragraph(children=[Text("Review this exact record")])],
    )
    recipe = recipe_for(
        (bundle.source,),
        "full_text",
        review_policy="required",
    )
    initial_inputs = inputs_for((bundle,))

    pending = construct_dataset(recipe, initial_inputs)

    assert [item.status for item in pending.decisions] == ["pending_review"]
    assert not pending.records
    review = ReviewEvidence.create(
        candidate_id=pending.candidates[0].candidate_id,
        reviewer_id="local-reviewer-1",
        verdict="accepted",
        rationale="source and field evidence verified",
    )
    reviewed_inputs = inputs_for((bundle,), reviews=(review,))
    accepted = construct_dataset(recipe, reviewed_inputs)

    assert accepted.candidates == pending.candidates
    assert accepted.decisions[0].status == "accepted"
    assert accepted.decisions[0].review == review
    assert accepted.records[0].candidate_id == pending.candidates[0].candidate_id
    assert accepted.records[0].fields == pending.candidates[0].fields
    assert review.review_id.startswith("rvw-v1-")


def test_input_order_does_not_change_result(tmp_path):
    alpha = source_bundle(
        tmp_path,
        logical_path="alpha.txt",
        blocks=[Paragraph(children=[Text("alpha source")])],
    )
    beta = source_bundle(
        tmp_path,
        logical_path="beta.txt",
        blocks=[Paragraph(children=[Text("beta source")])],
    )
    # Existing structural chunk configuration persists overlap even though the
    # paragraph chunker does not operationally consume it.
    recipe = recipe_for(
        (beta.source, alpha.source),
        "full_text",
        strategy="paragraph",
        overlap=100,
    )
    forward = inputs_for((alpha, beta))
    reverse = ConstructionInputs.create(
        cleaning_config_digest=forward.cleaning_config_digest,
        sources=tuple(reversed(forward.sources)),
        chunks=tuple(reversed(forward.chunks)),
        transforms=tuple(reversed(forward.transforms)),
        ir_artifacts=tuple(reversed(forward.ir_artifacts)),
        reviews=tuple(reversed(forward.reviews)),
    )

    assert construct_dataset(recipe, forward) == construct_dataset(recipe, reverse)


def test_cleaning_config_mismatch_fails_closed(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="cleaning.txt",
        blocks=[Paragraph(children=[Text("bound clean state")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for(
        (bundle,),
        cleaning_config_digest=canonical_digest({"cleaning": "different"}),
    )

    with pytest.raises(ConstructionError, match="cleaning config"):
        construct_dataset(recipe, inputs)


def test_unsupported_constructor_version_fails_closed(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="version.txt",
        blocks=[Paragraph(children=[Text("version-bound")])],
    )
    objective = TrainingObjective.create("full_text")
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind="full_text",
        constructor_version="2",
    )
    recipe = DatasetRecipe.create(
        objective=objective,
        source_ids=(bundle.source.id,),
        cleaning_config_digest=canonical_digest({"cleaning": "fixture-v1"}),
        segmentation=SegmentationPolicy(
            schema_version="veriformis.segmentation-policy/v1",
            strategy="paragraph",
            size=1_000,
            overlap=100,
        ),
        passes=(construction_pass,),
        target_row_schema="text",
    )

    with pytest.raises(ConstructionError, match="unsupported constructor"):
        construct_dataset(recipe, inputs_for((bundle,)))


def test_result_tamper_and_replay_tamper_are_rejected(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="tamper.txt",
        blocks=[Paragraph(children=[Text("unaltered")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for((bundle,))
    result = construct_dataset(recipe, inputs)
    value = construction_result_to_dict(result)
    value["records"][0]["fields"][0]["value"] = "forged"

    with pytest.raises(ConstructionError):
        construction_result_from_dict(value)

    unsafe = result.model_copy(update={"input_digest": "0" * 64})
    with pytest.raises(ConstructionError, match="identity mismatch"):
        validate_construction_result(recipe, inputs, unsafe)


def test_candidate_model_rejects_cross_source_nested_evidence(tmp_path):
    first = source_bundle(
        tmp_path,
        logical_path="first.txt",
        blocks=[Paragraph(children=[Text("first")])],
    )
    second = source_bundle(
        tmp_path,
        logical_path="second.txt",
        blocks=[Paragraph(children=[Text("second")])],
    )
    recipe = recipe_for((first.source,), "full_text")
    result = construct_dataset(recipe, inputs_for((first,)))
    candidate = result.candidates[0]

    with pytest.raises(ValueError, match="another source"):
        CandidateRecord.create(
            ordinal=candidate.ordinal,
            recipe_id=candidate.recipe_id,
            objective_id=candidate.objective_id,
            pass_id=candidate.pass_id,
            source_ids=(second.source.id,),
            chunk_ids=(second.chunks[0].id,),
            transform_ids=(),
            fields=candidate.fields,
        )
