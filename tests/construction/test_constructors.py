from __future__ import annotations

import pytest

from veriformis.construction import (
    ConstructionInputs,
    IRFieldEvidence,
    SourceTextEvidence,
    construct_dataset,
    resolve_ir_field_evidence,
)
from veriformis.construction.constructors import construction_field_context
from veriformis.evidence import resolve_evidence
from veriformis.errors import EvidenceError
from veriformis.identity import lossless_json_bytes
from veriformis.ir import Cell, Heading, Link, Math, Paragraph, Table, Text
from veriformis.ir.serde import document_to_dict

from .helpers import (
    cleaned_source_bundle,
    inputs_for,
    recipe_for,
    source_bundle,
)


def _field_map(candidate):
    return {field.name: field for field in candidate.fields}


def test_full_text_constructor_preserves_complete_chunk_and_evidence(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="full.txt",
        blocks=[Paragraph(children=[Text("Café\u0301 source text")])],
    )
    recipe = recipe_for((bundle.source,), "full_text")
    inputs = inputs_for((bundle,))

    result = construct_dataset(recipe, inputs)

    assert len(result.records) == 1
    field = result.records[0].fields[0]
    assert (field.name, field.value) == ("text", "Café\u0301 source text")
    assert isinstance(field.evidence, SourceTextEvidence)
    assert resolve_evidence(
        field.evidence.evidence,
        {bundle.source.id: bundle.source},
    ) == field.value
    assert result.records[0].source_ids == (bundle.source.id,)
    assert result.records[0].chunk_ids == (bundle.chunks[0].id,)


def test_continuation_constructor_uses_ordered_nonoverlapping_slices(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="continuation.txt",
        blocks=[Paragraph(children=[Text("abcdefghij")])],
    )
    recipe = recipe_for(
        (bundle.source,),
        "continuation",
        parameters={"split_ratio_ppm": 300_000},
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    fields = _field_map(result.candidates[0])
    assert fields["prompt"].value == "abc"
    assert fields["completion"].value == "defghij"
    assert fields["prompt"].value + fields["completion"].value == bundle.chunks[0].text
    for field in fields.values():
        assert isinstance(field.evidence, SourceTextEvidence)
        assert resolve_evidence(
            field.evidence.evidence,
            {bundle.source.id: bundle.source},
        ) == field.value


def test_section_reconstruction_requires_exact_same_chunk_structure(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="section.md",
        blocks=[
            Heading(level=1, children=[Text("Heading")]),
            Paragraph(children=[Text("The complete section body.")]),
        ],
        strategy="structure",
        size=1_000,
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
        size=1_000,
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert bundle.chunks[0].text == "Heading\n\nThe complete section body."
    fields = _field_map(result.candidates[0])
    assert fields["heading"].value == "Heading"
    assert fields["section"].value == "The complete section body."
    assert not result.diagnostics
    for field in fields.values():
        assert resolve_evidence(
            field.evidence.evidence,
            {bundle.source.id: bundle.source},
        ) == field.value


def test_section_reconstruction_reports_ineligible_chunk(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="unheaded.txt",
        blocks=[Paragraph(children=[Text("Body without a heading")])],
        strategy="structure",
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert not result.candidates
    assert not result.records
    assert [item.code for item in result.diagnostics] == [
        "section-structure-unavailable"
    ]


def test_section_reconstruction_requires_cleaned_ir_boundaries(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="parsed-only-section.md",
        blocks=[
            Heading(level=1, children=[Text("Heading")]),
            Paragraph(children=[Text("Body")]),
        ],
        strategy="structure",
        artifact_kind="document-ir",
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert not result.candidates
    assert not result.records
    assert [item.code for item in result.diagnostics] == [
        "section-structure-unavailable"
    ]


def test_section_reconstruction_joins_every_chunk_in_oversized_section(tmp_path):
    first_body = "A" * 20
    second_body = "B" * 20
    bundle = source_bundle(
        tmp_path,
        logical_path="oversized-section.md",
        blocks=[
            Heading(level=1, children=[Text("H")]),
            Paragraph(children=[Text(first_body)]),
            Paragraph(children=[Text(second_body)]),
        ],
        strategy="structure",
        size=25,
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
        size=25,
        overlap=0,
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert len(bundle.chunks) == 2
    assert len(result.candidates) == 1
    assert not result.diagnostics
    candidate = result.candidates[0]
    fields = _field_map(candidate)
    assert fields["heading"].value == "H"
    assert fields["section"].value == f"{first_body}\n\n{second_body}"
    assert set(candidate.chunk_ids) == {chunk.id for chunk in bundle.chunks}
    section_evidence = fields["section"].evidence
    assert isinstance(section_evidence, SourceTextEvidence)
    assert len(section_evidence.evidence.components) == 2
    assert resolve_evidence(
        section_evidence.evidence,
        {bundle.source.id: bundle.source},
    ) == fields["section"].value


def test_section_reconstruction_rejects_an_oversized_section_prefix(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="partial-section.md",
        blocks=[
            Heading(level=1, children=[Text("H")]),
            Paragraph(children=[Text("A" * 20)]),
            Paragraph(children=[Text("B" * 20)]),
        ],
        strategy="structure",
        size=25,
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
        size=25,
        overlap=0,
    )
    complete = inputs_for((bundle,))
    partial = ConstructionInputs.create(
        cleaning_config_digest=complete.cleaning_config_digest,
        sources=complete.sources,
        chunks=(bundle.chunks[0],),
        ir_artifacts=complete.ir_artifacts,
    )

    result = construct_dataset(recipe, partial)

    assert not result.candidates
    assert not result.records
    assert [item.code for item in result.diagnostics] == [
        "section-structure-unavailable"
    ]


def test_section_reconstruction_keeps_repeated_headings_as_distinct_units(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="repeated-headings.md",
        blocks=[
            Heading(level=1, children=[Text("Repeated")]),
            Paragraph(children=[Text("First body")]),
            Heading(level=1, children=[Text("Repeated")]),
            Paragraph(children=[Text("Second body")]),
        ],
        strategy="structure",
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert [
        tuple(field.value for field in candidate.fields)
        for candidate in result.candidates
    ] == [
        ("Repeated", "First body"),
        ("Repeated", "Second body"),
    ]
    assert len({candidate.chunk_ids for candidate in result.candidates}) == 2
    assert not result.diagnostics


def test_section_reconstruction_uses_each_nested_heading_boundary(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="nested-headings.md",
        blocks=[
            Heading(level=1, children=[Text("Parent")]),
            Paragraph(children=[Text("Parent body")]),
            Heading(level=2, children=[Text("Child")]),
            Paragraph(children=[Text("Child body")]),
            Heading(level=1, children=[Text("Next")]),
            Paragraph(children=[Text("Next body")]),
        ],
        strategy="structure",
    )
    recipe = recipe_for(
        (bundle.source,),
        "section_reconstruction",
        strategy="structure",
    )

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert [
        tuple(field.value for field in candidate.fields)
        for candidate in result.candidates
    ] == [
        ("Parent", "Parent body"),
        ("Child", "Child body"),
        ("Next", "Next body"),
    ]
    assert not result.diagnostics


def test_before_after_constructor_binds_replayable_transform(tmp_path):
    bundle, transforms = cleaned_source_bundle(
        tmp_path,
        logical_path="clean.txt",
        text="Alpha   beta and more text",
    )
    recipe = recipe_for((bundle.source,), "before_after_transformation")

    result = construct_dataset(
        recipe,
        inputs_for((bundle,), transforms=transforms),
    )

    fields = _field_map(result.candidates[0])
    assert fields["before"].value == "Alpha   beta and more text"
    assert fields["after"].value == "Alpha beta and more text"
    assert result.candidates[0].transform_ids == tuple(
        sorted(record.id for record in transforms if record.edits)
    )
    for field in fields.values():
        assert resolve_evidence(
            field.evidence.evidence,
            {bundle.source.id: bundle.source},
        ) == field.value


def test_structured_field_constructor_binds_each_ir_metadata_leaf(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="structured.md",
        blocks=[
            Paragraph(
                children=[
                    Text("See "),
                    Link(
                        children=[Text("source")],
                        href="https://example.test/raw",
                        title="Primary",
                    ),
                ]
            )
        ],
    )
    recipe = recipe_for((bundle.source,), "structured_field")
    inputs = inputs_for((bundle,))

    result = construct_dataset(recipe, inputs)

    assert len(result.records) == 2
    outputs = {_field_map(candidate)["fields"].value for candidate in result.candidates}
    assert outputs == {"https://example.test/raw", "Primary"}
    for candidate in result.candidates:
        fields = _field_map(candidate)
        assert fields["input"].value == "See source"
        assert isinstance(fields["input"].evidence, SourceTextEvidence)
        assert isinstance(fields["fields"].evidence, IRFieldEvidence)
        artifact = bundle.artifact
        assert resolve_ir_field_evidence(
            fields["fields"].evidence,
            source_id=bundle.source.id,
            artifact_id=artifact.artifact_id,
            artifact_kind=artifact.artifact_kind,
            document_json=artifact.document_json,
            context=construction_field_context(
                recipe,
                recipe.passes[0],
                "fields",
                candidate.chunk_ids,
                json_pointer=fields["fields"].evidence.json_pointer,
            ),
        ) == fields["fields"].value
        assert candidate.source_ids == (bundle.source.id,)
        assert candidate.chunk_ids == (bundle.chunks[0].id,)


def test_structured_field_without_ir_is_a_diagnostic_not_silent_omission(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="missing-ir.txt",
        blocks=[Paragraph(children=[Text("plain text")])],
    )
    recipe = recipe_for((bundle.source,), "structured_field")

    result = construct_dataset(
        recipe,
        inputs_for((bundle,), include_artifacts=False),
    )

    assert not result.candidates
    assert [item.code for item in result.diagnostics] == [
        "structured-ir-artifact-unavailable"
    ]


def test_structured_field_records_distinct_empty_leaf_diagnostics(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="empty-fields.md",
        blocks=[
            Paragraph(
                children=[
                    Link(
                        children=[Text("source")],
                        href="",
                        title="",
                    )
                ]
            )
        ],
    )
    recipe = recipe_for((bundle.source,), "structured_field")

    result = construct_dataset(recipe, inputs_for((bundle,)))

    assert not result.candidates
    assert [item.code for item in result.diagnostics] == [
        "structured-field-empty-value",
        "structured-field-empty-value",
    ]
    assert len({item.diagnostic_id for item in result.diagnostics}) == 2
    assert {item.message.rsplit(" ", 1)[-1] for item in result.diagnostics} == {
        "/document/children/0/children/0/href",
        "/document/children/0/children/0/title",
    }


def test_structured_field_preserves_present_null_false_and_zero_scalars(tmp_path):
    bundle = source_bundle(
        tmp_path,
        logical_path="typed-scalars.md",
        blocks=[
            Heading(level=0, children=[Text("Zero level")]),
            Math(source="x", display=False),
            Table(
                headers=[Cell(children=[Text("A")]), Cell(children=[Text("B")])],
                rows=[[Cell(children=[Text("1")]), Cell(children=[Text("2")])]],
                alignments=[None, "right"],
            ),
            Paragraph(
                children=[
                    Link(
                        children=[Text("optional title")],
                        href="https://example.test/optional",
                        title=None,
                    )
                ]
            ),
        ],
    )
    recipe = recipe_for((bundle.source,), "structured_field")

    result = construct_dataset(recipe, inputs_for((bundle,)))

    targets = {
        _field_map(candidate)["fields"].value: _field_map(candidate)["fields"]
        for candidate in result.candidates
    }
    assert len(result.candidates) == 5
    assert set(targets) == {
        "0",
        "false",
        "null",
        "right",
        "https://example.test/optional",
    }
    assert targets["0"].evidence.encoding == "json-scalar-v1"
    assert targets["false"].evidence.encoding == "json-scalar-v1"
    assert targets["null"].evidence.encoding == "json-scalar-v1"
    assert all(
        not field.evidence.json_pointer.endswith("/title")
        for field in targets.values()
    )

    null_candidate = next(
        candidate
        for candidate in result.candidates
        if _field_map(candidate)["fields"].value == "null"
    )
    null_field = _field_map(null_candidate)["fields"]
    assert isinstance(null_field.evidence, IRFieldEvidence)
    assert resolve_ir_field_evidence(
        null_field.evidence,
        source_id=bundle.source.id,
        artifact_id=bundle.artifact.artifact_id,
        artifact_kind=bundle.artifact.artifact_kind,
        document_json=bundle.artifact.document_json,
        context=construction_field_context(
            recipe,
            recipe.passes[0],
            "fields",
            null_candidate.chunk_ids,
            json_pointer=null_field.evidence.json_pointer,
        ),
    ) == "null"

    tampered = document_to_dict(bundle.document)
    tampered["document"]["children"][2]["alignments"][0] = "left"
    with pytest.raises(EvidenceError, match="content digest"):
        resolve_ir_field_evidence(
            null_field.evidence,
            source_id=bundle.source.id,
            artifact_id=bundle.artifact.artifact_id,
            artifact_kind=bundle.artifact.artifact_kind,
            document_json=lossless_json_bytes(tampered),
            context=construction_field_context(
                recipe,
                recipe.passes[0],
                "fields",
                null_candidate.chunk_ids,
                json_pointer=null_field.evidence.json_pointer,
            ),
        )
