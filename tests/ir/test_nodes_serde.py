from copy import deepcopy

import pytest

from veriformis.errors import InvalidIRError
from veriformis.identity import derive_id
from veriformis.ir.nodes import (
    Citation,
    Document,
    EndnoteRef,
    FootnoteRef,
    Heading,
    Image,
    Paragraph,
    Span,
    Text,
    block_text,
    set_block_text,
)
from veriformis.ir.serde import (
    IR_SCHEMA_VERSION,
    document_from_dict,
    document_to_dict,
    validate_document_against_stream,
)


SOURCE_ID = derive_id("src", {"fixture": "ir-serde"})


def _doc():
    return Document(
        children=[
            Heading(level=1, children=[Text("Title")], span=Span(0, 5), block_index=0),
            Paragraph(children=[Text("Body text.")], span=Span(7, 17), block_index=1),
        ],
        source_id=SOURCE_ID,
    )


def test_serde_roundtrip():
    document = _doc()
    value = document_to_dict(document)
    assert value["schema_version"] == IR_SCHEMA_VERSION
    assert document_from_dict(value) == document
    validate_document_against_stream(document, "Title\n\nBody text.", exact=True)


def test_block_text_and_set_block_text():
    para = _doc().children[1]
    assert block_text(para) == "Body text."
    replaced = set_block_text(para, "Cleaned.")
    assert block_text(replaced) == "Cleaned."
    assert type(replaced) is Paragraph
    assert replaced.span == para.span  # provenance preserved through cleaning


def test_canonical_projection_keeps_visible_semantic_inline_content():
    paragraph = Paragraph(
        children=[
            Text("See "),
            Image(alt="diagram", src="image.png"),
            Text(" "),
            Citation(key="smith2020", locator="p. 4"),
            Text(" "),
            FootnoteRef(id="n"),
            Text(" "),
            EndnoteRef(id="e"),
        ]
    )

    assert block_text(paragraph) == (
        "See diagram [@smith2020, p. 4] [^n] [^endnote:e]"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version="veriformis.ir/v999"),
        lambda value: value["document"].update(approval="forged"),
        lambda value: value["document"]["children"][0].update(type="object"),
        lambda value: value["document"]["children"][0].update(level="1"),
    ],
)
def test_ir_deserialization_rejects_unknown_schema_fields_nodes_and_types(mutation):
    value = deepcopy(document_to_dict(_doc()))
    mutation(value)

    with pytest.raises(InvalidIRError):
        document_from_dict(value)


def test_ir_provenance_rejects_projection_and_span_drift():
    document = _doc()
    with pytest.raises(InvalidIRError, match="projection"):
        validate_document_against_stream(document, "X" * 17, exact=True)

    document.children[1].span = Span(7, 999)
    with pytest.raises(InvalidIRError, match="exceeds"):
        validate_document_against_stream(document, "Title\n\nBody text.", exact=False)
