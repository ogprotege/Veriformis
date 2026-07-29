from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pytest

from veriformis.construction import (
    BUILTIN_CONSTRUCTOR_IDS,
    OBJECTIVE_FIELD_CONTRACTS,
    ConstructionInputs,
    ConstructionPass,
    DatasetRecipe,
    DatasetRecord,
    IRArtifactInput,
    ReviewEvidence,
    SegmentationPolicy,
    TrainingObjective,
    construct_dataset,
    dataset_recipe_from_json_bytes,
    dataset_recipe_to_dict,
    validate_construction_result,
)
from veriformis.errors import ConstructionError, DuplicateIdentityError, VeriformisError
from veriformis.identity import canonical_digest, derive_id, lossless_json_bytes
from veriformis.ir import Link, Paragraph, Text
from veriformis.ir.serde import document_to_dict

from .helpers import cleaned_source_bundle, inputs_for, recipe_for, source_bundle


def _unchecked_inputs(
    inputs: ConstructionInputs,
    *,
    use_construct: bool = False,
    **updates: Any,
) -> ConstructionInputs:
    if not use_construct:
        return inputs.model_copy(update=updates)
    values = {
        name: getattr(inputs, name)
        for name in ConstructionInputs.model_fields
    }
    values.update(updates)
    return ConstructionInputs.model_construct(**values)


def _assert_both_boundaries_reject(
    recipe: DatasetRecipe,
    valid_inputs: ConstructionInputs,
    unsafe_inputs: ConstructionInputs,
    *,
    code: str,
) -> None:
    valid_result = construct_dataset(recipe, valid_inputs)
    boundaries = (
        lambda: construct_dataset(recipe, unsafe_inputs),
        lambda: validate_construction_result(recipe, unsafe_inputs, valid_result),
    )
    for boundary in boundaries:
        with pytest.raises(VeriformisError) as raised:
            boundary()
        assert raised.value.code == code


def test_construction_boundaries_revalidate_sources_chunks_and_transforms(tmp_path):
    bundle, transforms = cleaned_source_bundle(
        tmp_path,
        logical_path="unchecked-collections.txt",
        text="Alpha   beta remains source-grounded.",
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for((bundle,), transforms=transforms)

    forged_source = replace(bundle.source, stream_sha256="0" * 64)
    forged_chunk = replace(bundle.chunks[0], text="forged chunk text")
    forged_transform = replace(transforms[0], rule="forged-rule")
    cases = (
        (
            _unchecked_inputs(inputs, sources=(forged_source,)),
            "construction-invalid",
        ),
        (
            _unchecked_inputs(
                inputs,
                use_construct=True,
                chunks=(forged_chunk,),
            ),
            "source-evidence-invalid",
        ),
        (
            _unchecked_inputs(inputs, transforms=(forged_transform,)),
            "rule-error",
        ),
    )

    for unsafe, code in cases:
        _assert_both_boundaries_reject(
            recipe,
            inputs,
            unsafe,
            code=code,
        )


def test_changed_ir_bytes_cannot_retain_an_old_artifact_id(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="unchecked-ir.md",
        blocks=[
            Paragraph(
                children=[
                    Link(
                        children=[Text("source link")],
                        href="https://source.test",
                    )
                ]
            )
        ],
    )
    recipe = recipe_for((bundle.source,), "structured_field")
    inputs = inputs_for((bundle,))
    valid_result = construct_dataset(recipe, inputs)
    assert valid_result.records
    assert valid_result.records[0].fields[1].value == "https://source.test"

    document = document_to_dict(bundle.document)
    document["document"]["children"][0]["children"][0]["href"] = (
        "https://forged.test"
    )
    artifact_values = bundle.artifact.model_dump(mode="python")
    artifact_values["document_json"] = lossless_json_bytes(document)
    forged_artifact = IRArtifactInput.model_construct(**artifact_values)
    unsafe = _unchecked_inputs(
        inputs,
        use_construct=True,
        ir_artifacts=(forged_artifact,),
    )

    for boundary in (
        lambda: construct_dataset(recipe, unsafe),
        lambda: validate_construction_result(recipe, unsafe, valid_result),
    ):
        with pytest.raises(ConstructionError, match="content digest mismatch"):
            boundary()


def test_construction_boundaries_revalidate_reviews_and_input_schema(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="unchecked-review.txt",
        blocks=[Paragraph(children=[Text("Review-bound source text.")])],
    )
    recipe = recipe_for(
        (bundle.source,),
        "full_text",
        review_policy="required",
    )
    pending = construct_dataset(recipe, inputs_for((bundle,)))
    review = ReviewEvidence.create(
        candidate_id=pending.candidates[0].candidate_id,
        reviewer_id="reviewer-1",
        verdict="accepted",
        rationale="verified against source evidence",
    )
    inputs = inputs_for((bundle,), reviews=(review,))
    forged_review = review.model_construct(
        **{
            **review.model_dump(mode="python"),
            "rationale": "changed without changing the review identity",
        }
    )
    unsafe_review = _unchecked_inputs(inputs, reviews=(forged_review,))
    unsafe_schema = _unchecked_inputs(
        inputs,
        use_construct=True,
        schema_version="veriformis.construction-inputs/v999",
    )

    _assert_both_boundaries_reject(
        recipe,
        inputs,
        unsafe_review,
        code="construction-invalid",
    )
    _assert_both_boundaries_reject(
        recipe,
        inputs,
        unsafe_schema,
        code="construction-invalid",
    )


def test_duplicate_input_identities_keep_their_machine_code_at_both_boundaries(
    tmp_path,
):
    bundle, transforms = cleaned_source_bundle(
        tmp_path,
        logical_path="duplicate-inputs.txt",
        text="Duplicate   identity checks remain typed.",
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for((bundle,), transforms=transforms)
    duplicates = (
        _unchecked_inputs(
            inputs,
            use_construct=True,
            sources=(bundle.source, bundle.source),
        ),
        _unchecked_inputs(
            inputs,
            use_construct=True,
            chunks=(bundle.chunks[0], bundle.chunks[0]),
        ),
        _unchecked_inputs(
            inputs,
            use_construct=True,
            transforms=(transforms[0], transforms[0]),
        ),
        _unchecked_inputs(
            inputs,
            use_construct=True,
            ir_artifacts=(bundle.artifact, bundle.artifact),
        ),
    )
    for unsafe in duplicates:
        _assert_both_boundaries_reject(
            recipe,
            inputs,
            unsafe,
            code="duplicate-identity",
        )

    review_recipe = recipe_for(
        (bundle.source,),
        "full_text",
        review_policy="required",
    )
    pending = construct_dataset(review_recipe, inputs)
    review = ReviewEvidence.create(
        candidate_id=pending.candidates[0].candidate_id,
        reviewer_id="reviewer-1",
        verdict="accepted",
        rationale="reviewed",
    )
    reviewed_inputs = inputs_for((bundle,), transforms=transforms, reviews=(review,))
    duplicate_reviews = _unchecked_inputs(
        reviewed_inputs,
        use_construct=True,
        reviews=(review, review),
    )
    _assert_both_boundaries_reject(
        review_recipe,
        reviewed_inputs,
        duplicate_reviews,
        code="duplicate-identity",
    )


def test_dataset_record_promotion_revalidates_candidate_and_decision(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="promotion.txt",
        blocks=[Paragraph(children=[Text("Promotion stays identity-bound.")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    result = construct_dataset(recipe, inputs_for((bundle,)))
    candidate = result.candidates[0]
    decision = result.decisions[0]
    assert DatasetRecord.promote(candidate, decision) == result.records[0]

    accepted_review = ReviewEvidence.create(
        candidate_id=candidate.candidate_id,
        reviewer_id="reviewer-1",
        verdict="accepted",
        rationale="reviewed",
    )
    forged_candidate_id = derive_id("cand", {"forged": "candidate"})
    forged_decision_id = derive_id("dec", {"forged": "decision"})
    forged_review = accepted_review.model_copy(update={"rationale": "forged"})
    cases = (
        (
            candidate,
            decision.model_construct(
                **{
                    **decision.model_dump(mode="python"),
                    "status": "pending_review",
                }
            ),
        ),
        (
            candidate,
            decision.model_copy(update={"reason_codes": ("review-required",)}),
        ),
        (
            candidate,
            decision.model_copy(
                update={
                    "review": forged_review,
                    "reason_codes": ("review-approved",),
                }
            ),
        ),
        (
            candidate.model_copy(update={"candidate_id": forged_candidate_id}),
            decision,
        ),
        (
            candidate,
            decision.model_copy(update={"candidate_id": forged_candidate_id}),
        ),
        (
            candidate,
            decision.model_copy(update={"decision_id": forged_decision_id}),
        ),
    )

    for unsafe_candidate, unsafe_decision in cases:
        with pytest.raises(ConstructionError) as raised:
            DatasetRecord.promote(unsafe_candidate, unsafe_decision)
        assert raised.value.code == "construction-invalid"


def test_duplicate_pass_ids_precede_sequence_validation_and_remain_typed(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="duplicate-pass.txt",
        blocks=[Paragraph(children=[Text("Duplicate pass fixture.")])],
    )
    objective = TrainingObjective.create("full_text")
    construction_pass = ConstructionPass.create(
        sequence=1,
        objective_kind="full_text",
    )
    segmentation = SegmentationPolicy(
        schema_version="veriformis.segmentation-policy/v1",
        strategy="paragraph",
        size=1_000,
        overlap=100,
    )
    kwargs = {
        "objective": objective,
        "source_ids": (bundle.source.id,),
        "cleaning_config_digest": canonical_digest({"cleaning": "fixture-v1"}),
        "segmentation": segmentation,
        "passes": (construction_pass, construction_pass),
        "target_row_schema": "text",
    }

    with pytest.raises(DuplicateIdentityError) as direct:
        DatasetRecipe.create(**kwargs)
    assert direct.value.code == "duplicate-identity"

    valid = recipe_for((bundle.source,), "full_text")
    value = dataset_recipe_to_dict(valid)
    value["passes"] = [value["passes"][0], value["passes"][0]]
    value["recipe_id"] = derive_id(
        "rcp",
        {key: item for key, item in value.items() if key != "recipe_id"},
    )
    with pytest.raises(DuplicateIdentityError) as loaded:
        dataset_recipe_from_json_bytes(lossless_json_bytes(value))
    assert loaded.value.code == "duplicate-identity"


def test_identity_defining_public_mappings_are_read_only():
    objective_fields = cast(dict[str, tuple[str, ...]], OBJECTIVE_FIELD_CONTRACTS)
    constructor_ids = cast(dict[str, str], BUILTIN_CONSTRUCTOR_IDS)

    with pytest.raises(TypeError):
        objective_fields["full_text"] = ("forged",)
    with pytest.raises(TypeError):
        constructor_ids["full_text"] = "veriformis.constructor.forged"

    assert OBJECTIVE_FIELD_CONTRACTS["full_text"] == ("text",)
    assert BUILTIN_CONSTRUCTOR_IDS["full_text"] == "veriformis.constructor.full-text"


def test_section_reconstruction_recipe_requires_structure_segmentation(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="section-strategy.md",
        blocks=[Paragraph(children=[Text("No structural boundary.")])],
    )

    with pytest.raises(ValueError, match="require structure segmentation"):
        recipe_for(
            (bundle.source,),
            "section_reconstruction",
            strategy="paragraph",
        )

    valid = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
    )
    value = dataset_recipe_to_dict(valid)
    value["segmentation"]["strategy"] = "paragraph"
    value["recipe_id"] = derive_id(
        "rcp",
        {key: item for key, item in value.items() if key != "recipe_id"},
    )
    with pytest.raises(ConstructionError, match="require structure segmentation"):
        dataset_recipe_from_json_bytes(lossless_json_bytes(value))
