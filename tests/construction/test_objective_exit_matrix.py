from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from veriformis.construction import (
    ConstructionInputs,
    ConstructionResult,
    DatasetRecipe,
    ReviewEvidence,
    construct_dataset,
    construction_result_from_dict,
    construction_result_to_dict,
    validate_construction_result,
)
from veriformis.errors import ConstructionError
from veriformis.ir import Heading, Link, Paragraph, Text

from .helpers import (
    cleaned_source_bundle,
    inputs_for,
    recipe_for,
    source_bundle,
)


ObjectiveKind = Literal[
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
]

OBJECTIVE_KINDS: tuple[ObjectiveKind, ...] = (
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
)


@dataclass(frozen=True)
class PositiveCase:
    recipe: DatasetRecipe
    inputs: ConstructionInputs
    expected_source_ids: frozenset[str]
    expected_field_names: tuple[str, ...]
    expected_rows: frozenset[tuple[str, ...]]


@dataclass(frozen=True)
class NegativeCase:
    recipe: DatasetRecipe
    inputs: ConstructionInputs
    affected_source_id: str
    diagnostic_code: str


def _positive_case(tmp_path: Path, objective_kind: ObjectiveKind) -> PositiveCase:
    if objective_kind == "full_text":
        alpha = source_bundle(
            tmp_path,
            logical_path="matrix-full-alpha.txt",
            blocks=[Paragraph(children=[Text("Alpha source remains complete.")])],
        )
        beta = source_bundle(
            tmp_path,
            logical_path="matrix-full-beta.txt",
            blocks=[Paragraph(children=[Text("Beta source remains complete.")])],
        )
        bundles = (alpha, beta)
        recipe = recipe_for(tuple(item.source for item in bundles), objective_kind)
        inputs = inputs_for(bundles)
        expected_fields = ("text",)
        expected_rows = frozenset(
            {
                ("Alpha source remains complete.",),
                ("Beta source remains complete.",),
            }
        )
    elif objective_kind == "continuation":
        alpha = source_bundle(
            tmp_path,
            logical_path="matrix-continuation-alpha.txt",
            blocks=[Paragraph(children=[Text("abcdefghij")])],
        )
        beta = source_bundle(
            tmp_path,
            logical_path="matrix-continuation-beta.txt",
            blocks=[Paragraph(children=[Text("klmnopqrst")])],
        )
        bundles = (alpha, beta)
        recipe = recipe_for(tuple(item.source for item in bundles), objective_kind)
        inputs = inputs_for(bundles)
        expected_fields = ("prompt", "completion")
        expected_rows = frozenset({("abcde", "fghij"), ("klmno", "pqrst")})
    elif objective_kind == "section_reconstruction":
        alpha = source_bundle(
            tmp_path,
            logical_path="matrix-section-alpha.md",
            blocks=[
                Heading(level=1, children=[Text("Alpha Heading")]),
                Paragraph(children=[Text("Alpha section body remains complete.")]),
            ],
            strategy="structure",
        )
        beta = source_bundle(
            tmp_path,
            logical_path="matrix-section-beta.md",
            blocks=[
                Heading(level=1, children=[Text("Beta Heading")]),
                Paragraph(children=[Text("Beta section body remains complete.")]),
            ],
            strategy="structure",
        )
        bundles = (alpha, beta)
        recipe = recipe_for(
            tuple(item.source for item in bundles),
            objective_kind,
            strategy="structure",
        )
        inputs = inputs_for(bundles)
        expected_fields = ("heading", "section")
        expected_rows = frozenset(
            {
                ("Alpha Heading", "Alpha section body remains complete."),
                ("Beta Heading", "Beta section body remains complete."),
            }
        )
    elif objective_kind == "before_after_transformation":
        alpha, alpha_transforms = cleaned_source_bundle(
            tmp_path,
            logical_path="matrix-transform-alpha.txt",
            text="Alpha   source before cleaning.",
        )
        beta, beta_transforms = cleaned_source_bundle(
            tmp_path,
            logical_path="matrix-transform-beta.txt",
            text="Beta   source before cleaning.",
        )
        bundles = (alpha, beta)
        recipe = recipe_for(tuple(item.source for item in bundles), objective_kind)
        inputs = inputs_for(
            bundles,
            transforms=(*alpha_transforms, *beta_transforms),
        )
        expected_fields = ("before", "after")
        expected_rows = frozenset(
            {
                (
                    "Alpha   source before cleaning.",
                    "Alpha source before cleaning.",
                ),
                (
                    "Beta   source before cleaning.",
                    "Beta source before cleaning.",
                ),
            }
        )
    else:
        alpha = source_bundle(
            tmp_path,
            logical_path="matrix-structured-alpha.md",
            blocks=[
                Paragraph(
                    children=[
                        Text("See "),
                        Link(
                            children=[Text("Alpha source")],
                            href="https://example.test/alpha",
                            title="Alpha primary",
                        ),
                    ]
                )
            ],
        )
        beta = source_bundle(
            tmp_path,
            logical_path="matrix-structured-beta.md",
            blocks=[
                Paragraph(
                    children=[
                        Text("See "),
                        Link(
                            children=[Text("Beta source")],
                            href="https://example.test/beta",
                            title="Beta primary",
                        ),
                    ]
                )
            ],
        )
        bundles = (alpha, beta)
        recipe = recipe_for(tuple(item.source for item in bundles), objective_kind)
        inputs = inputs_for(bundles)
        expected_fields = ("input", "fields")
        expected_rows = frozenset(
            {
                ("See Alpha source", "https://example.test/alpha"),
                ("See Alpha source", "Alpha primary"),
                ("See Beta source", "https://example.test/beta"),
                ("See Beta source", "Beta primary"),
            }
        )

    return PositiveCase(
        recipe=recipe,
        inputs=inputs,
        expected_source_ids=frozenset(item.source.id for item in bundles),
        expected_field_names=expected_fields,
        expected_rows=expected_rows,
    )


def _negative_case(tmp_path: Path, objective_kind: ObjectiveKind) -> NegativeCase:
    if objective_kind == "full_text":
        included = source_bundle(
            tmp_path,
            logical_path="matrix-negative-full-included.txt",
            blocks=[Paragraph(children=[Text("This source has a chunk.")])],
        )
        omitted = source_bundle(
            tmp_path,
            logical_path="matrix-negative-full-omitted.txt",
            blocks=[Paragraph(children=[Text("This source has no supplied chunk.")])],
        )
        recipe = recipe_for((included.source, omitted.source), objective_kind)
        complete_inputs = inputs_for((included, omitted))
        inputs = ConstructionInputs.create(
            cleaning_config_digest=complete_inputs.cleaning_config_digest,
            sources=complete_inputs.sources,
            chunks=included.chunks,
            ir_artifacts=complete_inputs.ir_artifacts,
        )
        affected_source_id = omitted.source.id
        diagnostic_code = "source-chunks-unavailable"
    elif objective_kind == "continuation":
        bundle = source_bundle(
            tmp_path,
            logical_path="matrix-negative-continuation.txt",
            blocks=[Paragraph(children=[Text("x")])],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        affected_source_id = bundle.source.id
        diagnostic_code = "continuation-boundary-unavailable"
    elif objective_kind == "section_reconstruction":
        bundle = source_bundle(
            tmp_path,
            logical_path="matrix-negative-section.txt",
            blocks=[Paragraph(children=[Text("Body without a heading.")])],
            strategy="structure",
        )
        recipe = recipe_for(
            (bundle.source,),
            objective_kind,
            strategy="structure",
        )
        inputs = inputs_for((bundle,))
        affected_source_id = bundle.source.id
        diagnostic_code = "section-structure-unavailable"
    elif objective_kind == "before_after_transformation":
        bundle = source_bundle(
            tmp_path,
            logical_path="matrix-negative-transform.txt",
            blocks=[Paragraph(children=[Text("No replayable cleaning transform.")])],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        affected_source_id = bundle.source.id
        diagnostic_code = "transformation-pair-unavailable"
    else:
        bundle = source_bundle(
            tmp_path,
            logical_path="matrix-negative-structured.txt",
            blocks=[Paragraph(children=[Text("No structured metadata scalar.")])],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        affected_source_id = bundle.source.id
        diagnostic_code = "structured-field-unavailable"

    return NegativeCase(
        recipe=recipe,
        inputs=inputs,
        affected_source_id=affected_source_id,
        diagnostic_code=diagnostic_code,
    )


def _identity_snapshot(result: ConstructionResult) -> tuple[object, ...]:
    return (
        result.result_id,
        tuple(item.candidate_id for item in result.candidates),
        tuple(item.decision_id for item in result.decisions),
        tuple(item.record_id for item in result.records),
        tuple(item.diagnostic_id for item in result.diagnostics),
    )


@pytest.mark.parametrize("objective_kind", OBJECTIVE_KINDS)
def test_group2_exit_matrix_constructs_multisource_deterministically(
    tmp_path: Path,
    objective_kind: ObjectiveKind,
) -> None:
    case = _positive_case(tmp_path, objective_kind)

    first = construct_dataset(case.recipe, case.inputs)
    repeated = construct_dataset(case.recipe, case.inputs)
    reordered_inputs = ConstructionInputs.create(
        cleaning_config_digest=case.inputs.cleaning_config_digest,
        sources=tuple(reversed(case.inputs.sources)),
        chunks=tuple(reversed(case.inputs.chunks)),
        transforms=tuple(reversed(case.inputs.transforms)),
        ir_artifacts=tuple(reversed(case.inputs.ir_artifacts)),
        reviews=tuple(reversed(case.inputs.reviews)),
    )
    reordered = construct_dataset(case.recipe, reordered_inputs)

    assert first.candidates
    assert first.records
    assert not first.diagnostics
    assert all(item.status == "accepted" for item in first.decisions)
    assert all(
        tuple(field.name for field in candidate.fields)
        == case.expected_field_names
        for candidate in first.candidates
    )
    assert {
        tuple(field.value for field in candidate.fields)
        for candidate in first.candidates
    } == case.expected_rows
    assert {
        source_id
        for record in first.records
        for source_id in record.source_ids
    } == case.expected_source_ids
    assert len(case.expected_source_ids) == 2
    assert first == repeated == reordered
    assert _identity_snapshot(first) == _identity_snapshot(repeated)
    assert _identity_snapshot(first) == _identity_snapshot(reordered)
    assert validate_construction_result(case.recipe, case.inputs, first) == first


@pytest.mark.parametrize("objective_kind", OBJECTIVE_KINDS)
def test_group2_exit_matrix_records_meaningful_non_output(
    tmp_path: Path,
    objective_kind: ObjectiveKind,
) -> None:
    case = _negative_case(tmp_path, objective_kind)

    result = construct_dataset(case.recipe, case.inputs)
    affected = tuple(
        item
        for item in result.diagnostics
        if case.affected_source_id in item.source_ids
    )

    assert [item.code for item in affected] == [case.diagnostic_code]
    assert all(
        case.affected_source_id not in candidate.source_ids
        for candidate in result.candidates
    )
    assert all(
        case.affected_source_id not in record.source_ids for record in result.records
    )
    assert construct_dataset(case.recipe, case.inputs) == result
    assert validate_construction_result(case.recipe, case.inputs, result) == result


@pytest.mark.parametrize("objective_kind", OBJECTIVE_KINDS)
def test_group2_exit_matrix_rejects_output_and_omission_tampering(
    tmp_path: Path,
    objective_kind: ObjectiveKind,
) -> None:
    case = _positive_case(tmp_path, objective_kind)
    result = construct_dataset(case.recipe, case.inputs)
    assert len(result.candidates) >= 2

    serialized = construction_result_to_dict(result)
    serialized["records"][0]["fields"][0]["value"] += " forged"
    with pytest.raises(ConstructionError):
        construction_result_from_dict(serialized)

    retained_candidate = result.candidates[0]
    retained_decision = result.decisions[0]
    retained_records = tuple(
        record
        for record in result.records
        if record.candidate_id == retained_candidate.candidate_id
    )
    omitted = ConstructionResult.create(
        recipe_id=result.recipe_id,
        input_digest=result.input_digest,
        executed_pass_ids=result.executed_pass_ids,
        candidates=(retained_candidate,),
        decisions=(retained_decision,),
        records=retained_records,
        diagnostics=result.diagnostics,
    )

    assert omitted.result_id != result.result_id
    with pytest.raises(ConstructionError, match="does not match exact replay"):
        validate_construction_result(case.recipe, case.inputs, omitted)


@pytest.mark.parametrize("objective_kind", OBJECTIVE_KINDS)
def test_group2_exit_matrix_preserves_unicode_exactly(
    tmp_path: Path,
    objective_kind: ObjectiveKind,
) -> None:
    if objective_kind == "full_text":
        text = "Cafe\u0301 and café 漢字"
        bundle = source_bundle(
            tmp_path,
            logical_path="unicode-full.txt",
            blocks=[Paragraph(children=[Text(text)])],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        expected = {(text,)}
    elif objective_kind == "continuation":
        text = "e\u0301Ω漢字"
        bundle = source_bundle(
            tmp_path,
            logical_path="unicode-continuation.txt",
            blocks=[Paragraph(children=[Text(text)])],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        expected = {("e\u0301", "Ω漢字")}
    elif objective_kind == "section_reconstruction":
        heading = "Cafe\u0301 café"
        section = "Corps naïf Ω漢字"
        bundle = source_bundle(
            tmp_path,
            logical_path="unicode-section.md",
            blocks=[
                Heading(level=1, children=[Text(heading)]),
                Paragraph(children=[Text(section)]),
            ],
            strategy="structure",
        )
        recipe = recipe_for(
            (bundle.source,),
            objective_kind,
            strategy="structure",
        )
        inputs = inputs_for((bundle,))
        expected = {(heading, section)}
    elif objective_kind == "before_after_transformation":
        before = "Cafe\u0301   Ω漢字"
        after = "Cafe\u0301 Ω漢字"
        bundle, transforms = cleaned_source_bundle(
            tmp_path,
            logical_path="unicode-transform.txt",
            text=before,
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,), transforms=transforms)
        expected = {(before, after)}
    else:
        input_text = "Entrée 漢字"
        href = "https://example.test/Cafe\u0301/漢字"
        title = "Titre café Ω"
        bundle = source_bundle(
            tmp_path,
            logical_path="unicode-structured.md",
            blocks=[
                Paragraph(
                    children=[
                        Link(
                            children=[Text(input_text)],
                            href=href,
                            title=title,
                        )
                    ]
                )
            ],
        )
        recipe = recipe_for((bundle.source,), objective_kind)
        inputs = inputs_for((bundle,))
        expected = {(input_text, href), (input_text, title)}

    result = construct_dataset(recipe, inputs)

    assert {
        tuple(field.value for field in candidate.fields)
        for candidate in result.candidates
    } == expected
    assert construct_dataset(recipe, inputs) == result
    assert validate_construction_result(recipe, inputs, result) == result


def test_required_review_rejection_is_bound_and_replayable(tmp_path: Path) -> None:
    bundle = source_bundle(
        tmp_path,
        logical_path="matrix-review-rejection.txt",
        blocks=[Paragraph(children=[Text("Reject this exact candidate.")])],
    )
    recipe = recipe_for(
        (bundle.source,),
        "full_text",
        review_policy="required",
    )
    pending_inputs = inputs_for((bundle,))
    pending = construct_dataset(recipe, pending_inputs)
    candidate = pending.candidates[0]
    review = ReviewEvidence.create(
        candidate_id=candidate.candidate_id,
        reviewer_id="matrix-reviewer",
        verdict="rejected",
        rationale="The source binding is valid, but this row is unsuitable.",
    )
    reviewed_inputs = inputs_for((bundle,), reviews=(review,))

    rejected = construct_dataset(recipe, reviewed_inputs)
    decision = rejected.decisions[0]

    assert rejected.candidates == pending.candidates
    assert decision.candidate_id == candidate.candidate_id
    assert decision.status == "rejected"
    assert decision.reason_codes == ("review-rejected",)
    assert decision.review == review
    assert decision.review.review_id == review.review_id
    assert decision.review.candidate_id == candidate.candidate_id
    assert not tuple(
        record
        for record in rejected.records
        if record.candidate_id == candidate.candidate_id
    )
    assert construct_dataset(recipe, reviewed_inputs) == rejected
    assert validate_construction_result(recipe, reviewed_inputs, rejected) == rejected
