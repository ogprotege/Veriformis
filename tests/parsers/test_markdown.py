from pathlib import Path

from veriformis.ir import (
    Blockquote, CodeBlock, Heading, ListBlock, Paragraph, Table, block_text,
)
from veriformis.parsers.markdown import parse_md, parse_md_file

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample.md"


def test_block_types_and_order():
    doc = parse_md_file(FIXTURE).document
    types = [type(b) for b in doc.children]
    assert types[0] is Heading
    assert Paragraph in types and ListBlock in types
    assert CodeBlock in types and Table in types and Blockquote in types


def test_spans_point_into_source():
    result = parse_md_file(FIXTURE)
    text = result.source.extracted_text
    for block in result.document.children:
        assert block.span is not None
        assert block.span.start < block.span.end <= len(text)
    para = next(b for b in result.document.children if isinstance(b, Paragraph))
    assert "bold" in text[para.span.start:para.span.end]


def test_code_block_language_and_footnotes():
    doc = parse_md_file(FIXTURE).document
    code = next(b for b in doc.children if isinstance(b, CodeBlock))
    assert code.language == "python"
    assert "n" in doc.footnotes


def test_parse_md_library_entry():
    doc = parse_md("# Hi\n\ntext")
    assert isinstance(doc.children[0], Heading)
    assert block_text(doc.children[1]) == "text"
