from __future__ import annotations

from copy import deepcopy

import pytest

from veriformis.construction import (
    OBJECTIVE_FIELD_CONTRACTS,
    ConstructionError,
    ConstructionPass,
    IRFieldEvidence,
    TrainingObjective,
    construct_dataset,
    construction_result_from_dict,
    construction_result_to_dict,
    dataset_recipe_from_dict,
    dataset_recipe_to_dict,
    make_ir_field_evidence,
    resolve_ir_field_evidence,
)
from veriformis.errors import EvidenceError
from veriformis.identity import lossless_json_bytes
from veriformis.ir import Link, Paragraph, Text
from veriformis.ir.serde import document_to_dict

from .helpers import inputs_for, recipe_for, source_bundle


def _without_path(value, path):
    copied = deepcopy(value)
    parent = copied
    for item in path[:-1]:
        parent = parent[item]
    del parent[path[-1]]
    return copied


def test_objective_contracts_use_semantic_fields_only():
    expected = {
        "full_text": ("text",),
        "continuation": ("prompt", "completion"),
        "section_reconstruction": ("heading", "section"),
        "before_after_transformation": ("before", "after"),
        "structured_field": ("input", "fields"),
    }

    assert OBJECTIVE_FIELD_CONTRACTS == expected
    assert {
        kind: TrainingObjective.create(kind).field_names for kind in expected
    } == expected
    assert "summary" not in OBJECTIVE_FIELD_CONTRACTS


def test_public_factories_reject_unsupported_objectives_with_typed_error():
    with pytest.raises(ConstructionError, match="unsupported deterministic objective"):
        TrainingObjective.create("summary")
    with pytest.raises(ConstructionError, match="unsupported deterministic objective"):
        ConstructionPass.create(sequence=1, objective_kind="summary")


def test_recipe_round_trip_binds_cleaning_and_deferred_policies(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="unicode.txt",
        blocks=[Paragraph(children=[Text("Cafe\u0301 and café")])],
    )
    recipe = recipe_for((bundle.source,), "continuation")

    value = dataset_recipe_to_dict(recipe)

    assert dataset_recipe_from_dict(value) == recipe
    assert value["cleaning_config_digest"] == recipe.cleaning_config_digest
    assert value["curation_policy"] == "deferred"
    assert value["split_policy"] == "deferred"
    tampered = deepcopy(value)
    tampered["cleaning_config_digest"] = "0" * 64
    with pytest.raises(ConstructionError, match="identity mismatch"):
        dataset_recipe_from_dict(tampered)


def test_recipe_loader_rejects_taxonomy_incompatible_objective_and_row(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="incompatible-row.txt",
        blocks=[Paragraph(children=[Text("Canonical recipe source.")])],
    )
    value = dataset_recipe_to_dict(recipe_for((bundle.source,), "full_text"))
    value["target_row_schema"] = "prompt_completion"

    with pytest.raises(
        ConstructionError,
        match="full_text recipes require the product 'text' row schema",
    ):
        dataset_recipe_from_dict(value)


@pytest.mark.parametrize(
    "path",
    [
        ("curation_policy",),
        ("objective", "schema_version"),
        ("segmentation", "schema_version"),
        ("passes", 0, "parameters"),
    ],
)
def test_recipe_loader_rejects_recursively_missing_fields(tmp_path, path):
    bundle = source_bundle(
        tmp_path,
        logical_path="missing-recipe-field.txt",
        blocks=[Paragraph(children=[Text("complete recipe")])],
    )
    value = dataset_recipe_to_dict(recipe_for((bundle.source,), "full_text"))

    with pytest.raises(ConstructionError, match="missing"):
        dataset_recipe_from_dict(_without_path(value, path))


@pytest.mark.parametrize(
    "path",
    [
        ("diagnostics",),
        ("candidates", 0, "schema_version"),
        ("candidates", 0, "fields", 0, "evidence", "kind"),
        ("decisions", 0, "review"),
        ("records", 0, "schema_version"),
    ],
)
def test_result_loader_rejects_recursively_missing_fields(tmp_path, path):
    bundle = source_bundle(
        tmp_path,
        logical_path="missing-result-field.txt",
        blocks=[Paragraph(children=[Text("complete result")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    value = construction_result_to_dict(
        construct_dataset(recipe, inputs_for((bundle,)))
    )

    with pytest.raises(ConstructionError):
        construction_result_from_dict(_without_path(value, path))


def test_ir_field_evidence_resolves_exact_unicode_and_rejects_tamper(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="links.md",
        blocks=[
            Paragraph(
                children=[
                    Link(
                        children=[Text("Café")],
                        href="https://example.test/Cafe\u0301",
                        title="Exact",
                    )
                ]
            )
        ],
    )
    pointer = "/document/children/0/children/0/href"
    context = {"field": "fields", "normalization": "none"}

    value, evidence = make_ir_field_evidence(
        source_id=bundle.source.id,
        artifact_id=bundle.artifact.artifact_id,
        artifact_kind=bundle.artifact.artifact_kind,
        document_json=bundle.artifact.document_json,
        json_pointer=pointer,
        context=context,
    )

    assert value == "https://example.test/Cafe\u0301"
    assert resolve_ir_field_evidence(
        evidence,
        source_id=bundle.source.id,
        artifact_id=bundle.artifact.artifact_id,
        artifact_kind=bundle.artifact.artifact_kind,
        document_json=bundle.artifact.document_json,
        context=context,
    ) == value

    document_value = document_to_dict(bundle.document)
    document_value["document"]["children"][0]["children"][0]["href"] = (
        "https://evil.test"
    )
    tampered_json = lossless_json_bytes(document_value)
    with pytest.raises(EvidenceError, match="content digest"):
        resolve_ir_field_evidence(
            evidence,
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=tampered_json,
            context=context,
        )

    unsafe = evidence.model_copy(update={"json_pointer": "/document/source_id"})
    with pytest.raises(EvidenceError, match="identity mismatch"):
        resolve_ir_field_evidence(
            unsafe,
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            context=context,
        )

    missing = evidence.model_dump(mode="json")
    del missing["context_digest"]
    with pytest.raises(ValueError, match="missing"):
        IRFieldEvidence.model_validate_json(lossless_json_bytes(missing))


def test_ir_field_evidence_rejects_noncanonical_pointer(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="pointer.md",
        blocks=[Paragraph(children=[Text("text")])],
    )

    with pytest.raises(EvidenceError, match="leading zero"):
        make_ir_field_evidence(
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=bundle.artifact.document_json,
            json_pointer="/document/children/00/type",
            context={},
        )

    payload = {
        "schema_version": "veriformis.ir-field-evidence/v1",
        "kind": "ir_field",
        "evidence_id": "evd-v1-" + "0" * 64,
        "source_id": bundle.source.id,
        "artifact_id": bundle.artifact.artifact_id,
        "artifact_kind": bundle.artifact.artifact_kind,
        "document_sha256": bundle.artifact.document_sha256,
        "ir_schema_version": "veriformis.ir/v1",
        "json_pointer": "document/source_id",
        "source_value_digest": "0" * 64,
        "encoding": "identity-string",
        "output_sha256": "0" * 64,
        "context_digest": "0" * 64,
    }
    with pytest.raises(ValueError, match="RFC 6901"):
        IRFieldEvidence.model_validate_json(lossless_json_bytes(payload))
