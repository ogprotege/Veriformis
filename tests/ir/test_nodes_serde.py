from veriformis.ir.nodes import Document, Heading, Paragraph, Span, Text, block_text, set_block_text
from veriformis.ir.serde import document_from_dict, document_to_dict


def _doc():
    return Document(
        children=[
            Heading(level=1, children=[Text("Title")], span=Span(0, 5), block_index=0),
            Paragraph(children=[Text("Body text.")], span=Span(7, 17), block_index=1),
        ],
        source_id="src-1",
    )


def test_serde_roundtrip():
    doc = _doc()
    assert document_from_dict(document_to_dict(doc)) == doc


def test_block_text_and_set_block_text():
    para = _doc().children[1]
    assert block_text(para) == "Body text."
    replaced = set_block_text(para, "Cleaned.")
    assert block_text(replaced) == "Cleaned."
    assert type(replaced) is Paragraph
    assert replaced.span == para.span  # provenance preserved through cleaning
