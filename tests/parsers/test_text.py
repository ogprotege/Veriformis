import hashlib

from veriformis.parsers.text import parse_text


def test_parse_text_paragraphs_and_spans(tmp_path):
    p = tmp_path / "sample.txt"
    p.write_text("First para.\n\nSecond para.\n\nThird para.", encoding="utf-8")
    result = parse_text(p)
    assert result.source.parser == "text"
    assert result.source.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()
    assert result.document.source_id == result.source.id
    blocks = result.document.children
    assert len(blocks) == 3
    for block in blocks:
        assert result.source.extracted_text[block.span.start:block.span.end] == block_text_of(block)


def test_parse_text_code_language(tmp_path):
    p = tmp_path / "snippet.py"
    p.write_text("print('hi')\n", encoding="utf-8")
    result = parse_text(p, language="python")
    assert result.document.children[0].language == "python"


def block_text_of(block):
    from veriformis.ir import block_text

    return block_text(block)
