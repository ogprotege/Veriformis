from __future__ import annotations

from copy import deepcopy
import json

import pytest

from veriformis.construction import (
    V1_CONSTRUCTION_DIAGNOSTIC_CODES,
    V1_PROMOTION_REASON_CODES,
    CandidateRecord,
    ConstructionDiagnostic,
    ConstructionInputs,
    ConstructionPass,
    ConstructionResult,
    DatasetRecord,
    IRFieldEvidence,
    PromotionDecision,
    construct_dataset,
    construction_result_from_dict,
    construction_result_from_json_bytes,
    construction_result_to_dict,
    dataset_recipe_from_dict,
    dataset_recipe_from_json_bytes,
    dataset_recipe_to_dict,
    make_ir_field_evidence,
    resolve_ir_field_evidence,
)
from veriformis.construction.models import construction_payload_digest
from veriformis.errors import (
    ConstructionError,
    DuplicateIdentityError,
    EvidenceError,
)
from veriformis.identity import canonical_digest, derive_id, lossless_json_bytes
from veriformis.ir import Link, Paragraph, Text

from .helpers import inputs_for, recipe_for, source_bundle


def _full_text_case(tmp_path, *, two_sources: bool = False):
    bundles = [
        source_bundle(
            tmp_path,
            logical_path="alpha.txt",
            blocks=[Paragraph(children=[Text("alpha source text")])],
        )
    ]
    if two_sources:
        bundles.append(
            source_bundle(
                tmp_path,
                logical_path="beta.txt",
                blocks=[Paragraph(children=[Text("beta source text")])],
            )
        )
    recipe = recipe_for(
        tuple(bundle.source for bundle in bundles),
        "full_text",
    )
    result = construct_dataset(recipe, inputs_for(tuple(bundles)))
    return tuple(bundles), recipe, result


def _replace_id(value: dict, *, field: str, kind: str) -> dict:
    payload = {key: item for key, item in value.items() if key != field}
    value[field] = derive_id(kind, payload)
    return value


def _canonical_artifacts(tmp_path, kind: str):
    _, recipe, result = _full_text_case(tmp_path)
    if kind == "recipe":
        value = dataset_recipe_to_dict(recipe)
        return recipe, value, dataset_recipe_from_json_bytes
    value = construction_result_to_dict(result)
    return result, value, construction_result_from_json_bytes


def test_duplicate_identity_error_code_is_stable():
    assert DuplicateIdentityError.code == "duplicate-identity"


def test_recipe_loader_preserves_duplicate_identity_error(tmp_path):
    _, recipe, _ = _full_text_case(tmp_path)
    value = dataset_recipe_to_dict(recipe)
    value["source_ids"] = [recipe.source_ids[0], recipe.source_ids[0]]
    _replace_id(value, field="recipe_id", kind="rcp")

    with pytest.raises(DuplicateIdentityError) as raised:
        dataset_recipe_from_dict(value)

    assert raised.value.code == "duplicate-identity"


def test_result_loader_preserves_duplicate_identity_error(tmp_path):
    _, _, result = _full_text_case(tmp_path)
    value = construction_result_to_dict(result)
    value["candidates"].append(deepcopy(value["candidates"][0]))
    _replace_id(value, field="result_id", kind="run")

    with pytest.raises(DuplicateIdentityError) as raised:
        construction_result_from_dict(value)

    assert raised.value.code == "duplicate-identity"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("source_ids", "candidate record requires at least one source"),
        ("chunk_ids", "candidate record requires at least one input chunk"),
        ("fields", "candidate record requires at least one field"),
    ],
)
def test_candidate_requires_nonempty_semantic_sets(tmp_path, field, message):
    _, _, result = _full_text_case(tmp_path)
    value = result.candidates[0].model_dump(mode="json")
    value[field] = []
    _replace_id(value, field="candidate_id", kind="cand")

    with pytest.raises(ValueError, match=message):
        CandidateRecord.model_validate_json(lossless_json_bytes(value))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("source_ids", "dataset record requires at least one source"),
        ("chunk_ids", "dataset record requires at least one input chunk"),
        ("fields", "dataset record requires at least one field"),
    ],
)
def test_dataset_record_requires_nonempty_semantic_sets(tmp_path, field, message):
    _, _, result = _full_text_case(tmp_path)
    value = result.records[0].model_dump(mode="json")
    value[field] = []
    _replace_id(value, field="record_id", kind="rec")

    with pytest.raises(ValueError, match=message):
        DatasetRecord.model_validate_json(lossless_json_bytes(value))


def test_construction_result_requires_contiguous_candidate_ordinals(tmp_path):
    _, _, result = _full_text_case(tmp_path, two_sources=True)
    assert len(result.candidates) == 2
    first, second = result.candidates
    noncontiguous = CandidateRecord.create(
        ordinal=3,
        recipe_id=second.recipe_id,
        objective_id=second.objective_id,
        pass_id=second.pass_id,
        source_ids=second.source_ids,
        chunk_ids=second.chunk_ids,
        transform_ids=second.transform_ids,
        fields=second.fields,
    )
    candidates = (first, noncontiguous)
    decisions = tuple(
        PromotionDecision.create(
            candidate_id=candidate.candidate_id,
            status="accepted",
            reason_codes=("construction-integrity-v1",),
        )
        for candidate in candidates
    )
    records = tuple(
        DatasetRecord.promote(candidate, decision)
        for candidate, decision in zip(candidates, decisions, strict=True)
    )

    with pytest.raises(ValueError, match="candidate ordinals must be contiguous"):
        ConstructionResult.create(
            recipe_id=result.recipe_id,
            input_digest=result.input_digest,
            executed_pass_ids=result.executed_pass_ids,
            candidates=candidates,
            decisions=decisions,
            records=records,
        )


def test_diagnostic_must_name_an_executed_pass(tmp_path):
    _, recipe, result = _full_text_case(tmp_path)
    other_pass = ConstructionPass.create(
        sequence=2,
        objective_kind="full_text",
    )
    candidate = result.candidates[0]
    diagnostic = ConstructionDiagnostic.create(
        code="continuation-boundary-unavailable",
        message="fixture diagnostic",
        pass_id=other_pass.pass_id,
        source_ids=candidate.source_ids,
        chunk_ids=candidate.chunk_ids,
    )

    with pytest.raises(ValueError, match="diagnostic names an unexecuted pass"):
        ConstructionResult.create(
            recipe_id=recipe.recipe_id,
            input_digest=result.input_digest,
            executed_pass_ids=result.executed_pass_ids,
            candidates=result.candidates,
            decisions=result.decisions,
            records=result.records,
            diagnostics=(diagnostic,),
        )


def test_every_executed_pass_has_candidate_or_diagnostic_coverage(tmp_path):
    _, recipe, result = _full_text_case(tmp_path)
    uncovered_pass = ConstructionPass.create(
        sequence=2,
        objective_kind="full_text",
    )

    with pytest.raises(
        ValueError,
        match="every executed construction pass requires a candidate or diagnostic",
    ):
        ConstructionResult.create(
            recipe_id=recipe.recipe_id,
            input_digest=result.input_digest,
            executed_pass_ids=(recipe.passes[0].pass_id, uncovered_pass.pass_id),
            candidates=result.candidates,
            decisions=result.decisions,
            records=result.records,
            diagnostics=(),
        )


def test_v1_diagnostic_and_promotion_reason_registries_are_exact():
    assert V1_CONSTRUCTION_DIAGNOSTIC_CODES == (
        "continuation-boundary-unavailable",
        "section-structure-unavailable",
        "source-chunks-unavailable",
        "structured-field-chunk-unavailable",
        "structured-field-empty-value",
        "structured-field-unavailable",
        "structured-ir-artifact-unavailable",
        "transformation-pair-empty-or-unchanged",
        "transformation-pair-unavailable",
    )
    assert V1_PROMOTION_REASON_CODES == (
        "construction-integrity-v1",
        "review-approved",
        "review-rejected",
        "review-required",
    )


@pytest.mark.parametrize("reason_code", ["", "invented-reason"])
def test_promotion_decision_rejects_unregistered_reason_codes(
    tmp_path,
    reason_code,
):
    _, _, result = _full_text_case(tmp_path)

    with pytest.raises(ValueError):
        PromotionDecision.create(
            candidate_id=result.candidates[0].candidate_id,
            status="accepted",
            reason_codes=(reason_code,),
        )


def test_diagnostic_code_and_input_key_are_strict_and_deterministic(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="short.txt",
        blocks=[Paragraph(children=[Text("x")])],
    )
    recipe = recipe_for((bundle.source,), "continuation")
    inputs = inputs_for((bundle,))

    first = construct_dataset(recipe, inputs).diagnostics[0]
    second = construct_dataset(recipe, inputs).diagnostics[0]

    assert first == second
    assert first.input_key == canonical_digest(
        {
            "schema_version": "veriformis.construction-diagnostic-input/v1",
            "source_ids": first.source_ids,
            "chunk_ids": first.chunk_ids,
        }
    )
    missing = first.model_dump(mode="json")
    del missing["input_key"]
    with pytest.raises(ValueError, match="missing=.*input_key"):
        ConstructionDiagnostic.model_validate_json(lossless_json_bytes(missing))
    with pytest.raises(ValueError):
        ConstructionDiagnostic.create(
            code="invented-diagnostic",
            message="not registered",
            pass_id=recipe.passes[0].pass_id,
            source_ids=first.source_ids,
            chunk_ids=first.chunk_ids,
        )


def test_missing_source_chunks_emit_one_source_scoped_diagnostic_per_pass(tmp_path):
    bundles, recipe, _ = _full_text_case(tmp_path, two_sources=True)
    inputs = inputs_for(bundles)
    partial = ConstructionInputs.create(
        cleaning_config_digest=inputs.cleaning_config_digest,
        sources=inputs.sources,
        chunks=bundles[0].chunks,
        ir_artifacts=inputs.ir_artifacts,
    )

    result = construct_dataset(recipe, partial)

    missing = tuple(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "source-chunks-unavailable"
    )
    assert len(missing) == len(recipe.passes) == 1
    assert missing[0].pass_id == recipe.passes[0].pass_id
    assert missing[0].source_ids == (bundles[1].source.id,)
    assert missing[0].chunk_ids == ()
    assert {candidate.source_ids for candidate in result.candidates} == {
        (bundles[0].source.id,)
    }


def test_all_empty_chunk_input_is_an_explicit_diagnostic_result(tmp_path):
    bundles, recipe, _ = _full_text_case(tmp_path)
    inputs = inputs_for(bundles)
    empty = ConstructionInputs.create(
        cleaning_config_digest=inputs.cleaning_config_digest,
        sources=inputs.sources,
        chunks=(),
        ir_artifacts=inputs.ir_artifacts,
    )

    result = construct_dataset(recipe, empty)

    assert result.candidates == ()
    assert result.decisions == ()
    assert result.records == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "source-chunks-unavailable"
    assert result.diagnostics[0].source_ids == (bundles[0].source.id,)


@pytest.mark.parametrize("kind", ["recipe", "result"])
def test_canonical_recipe_and_result_byte_loaders_accept_exact_bytes(
    tmp_path,
    kind,
):
    expected, value, loader = _canonical_artifacts(tmp_path, kind)
    canonical = lossless_json_bytes(value)

    assert loader(canonical) == expected


@pytest.mark.parametrize("kind", ["recipe", "result"])
def test_canonical_byte_loaders_reject_duplicate_json_keys(tmp_path, kind):
    _, value, loader = _canonical_artifacts(tmp_path, kind)
    canonical = lossless_json_bytes(value)
    duplicate = (
        b'{"schema_version":'
        + json.dumps(value["schema_version"]).encode("utf-8")
        + b","
        + canonical[1:]
    )

    with pytest.raises(DuplicateIdentityError) as raised:
        loader(duplicate)

    assert raised.value.code == "duplicate-identity"


def _malformed_bytes(value: dict, canonical: bytes, kind: str) -> bytes:
    if kind == "nan":
        return canonical[:-1] + b',"unexpected":NaN}'
    if kind == "infinity":
        return canonical[:-1] + b',"unexpected":Infinity}'
    if kind == "invalid-utf8":
        return canonical + b"\xff"
    if kind == "whitespace":
        return b" " + canonical
    if kind == "key-order":
        reordered = dict(reversed(tuple(value.items())))
        return json.dumps(
            reordered,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    raise AssertionError(f"unknown malformed-byte fixture {kind!r}")


@pytest.mark.parametrize("artifact_kind", ["recipe", "result"])
@pytest.mark.parametrize(
    "malformation",
    ["nan", "infinity", "invalid-utf8", "whitespace", "key-order"],
)
def test_canonical_byte_loaders_reject_noncanonical_or_invalid_bytes(
    tmp_path,
    artifact_kind,
    malformation,
):
    _, value, loader = _canonical_artifacts(tmp_path, artifact_kind)
    canonical = lossless_json_bytes(value)

    with pytest.raises(ConstructionError):
        loader(_malformed_bytes(value, canonical, malformation))


def test_ir_evidence_contexts_reject_floats_recursively(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="link.md",
        blocks=[
            Paragraph(
                children=[
                    Link(
                        children=[Text("link")],
                        href="https://example.test",
                    )
                ]
            )
        ],
    )
    pointer = "/document/children/0/children/0/href"
    valid_context = {"field": "href"}
    invalid_context = {"nested": {"weights": [1, 0.5]}}
    _, evidence = make_ir_field_evidence(
        source_id=bundle.source.id,
        artifact_id=bundle.artifact.artifact_id,
        artifact_kind=bundle.artifact.artifact_kind,
        document_json=bundle.artifact.document_json,
        json_pointer=pointer,
        context=valid_context,
    )

    with pytest.raises(EvidenceError, match="float"):
        make_ir_field_evidence(
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            json_pointer=pointer,
            context=invalid_context,
        )
    with pytest.raises(EvidenceError, match="float"):
        resolve_ir_field_evidence(
            evidence,
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            context=invalid_context,
        )


def test_construction_payload_digest_rejects_floats_recursively():
    with pytest.raises(ConstructionError, match="float"):
        construction_payload_digest(
            {"nested": {"values": ["exact", {"ratio": 0.5}]}}
        )


def test_ir_pointer_error_type_respects_model_and_public_boundaries(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="pointer.md",
        blocks=[
            Paragraph(
                children=[
                    Link(
                        children=[Text("link")],
                        href="https://example.test",
                    )
                ]
            )
        ],
    )
    pointer = "/document/children/0/children/0/href"
    context = {"field": "href"}
    _, evidence = make_ir_field_evidence(
        source_id=bundle.source.id,
        artifact_id=bundle.artifact.artifact_id,
        artifact_kind=bundle.artifact.artifact_kind,
        document_json=bundle.artifact.document_json,
        json_pointer=pointer,
        context=context,
    )
    invalid_pointer = "document/children/0"
    invalid = evidence.model_dump(mode="json")
    invalid["json_pointer"] = invalid_pointer
    _replace_id(invalid, field="evidence_id", kind="evd")

    with pytest.raises(ValueError, match="RFC 6901"):
        IRFieldEvidence.model_validate_json(lossless_json_bytes(invalid))

    unsafe = IRFieldEvidence.model_construct(**invalid)
    with pytest.raises(EvidenceError, match="RFC 6901"):
        resolve_ir_field_evidence(
            unsafe,
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            context=context,
        )
    with pytest.raises(EvidenceError, match="RFC 6901"):
        make_ir_field_evidence(
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            json_pointer=invalid_pointer,
            context=context,
        )
