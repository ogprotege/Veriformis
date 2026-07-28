# tests/chunkers/test_strategies.py
from veriformis.chunkers.strategies import (
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
from veriformis.ir import Heading, HorizontalRule, Paragraph, Span, Text


def _blocks(texts):
    blocks, pos = [], 0
    for i, t in enumerate(texts):
        blocks.append(Paragraph(children=[Text(t)], span=Span(pos, pos + len(t)), block_index=i))
        pos += len(t) + 2
    return blocks


def test_paragraph_chunks_preserve_coverage_and_provenance():
    blocks = _blocks(["alpha", "beta", "gamma"])
    chunks = chunk_paragraph(blocks, max_size=100, source_id="src-x")
    assert "\n\n".join(c.text for c in chunks) == "\n\n".join(["alpha", "beta", "gamma"])
    assert all(c.source_id == "src-x" for c in chunks)
    assert chunks[0].span.start == 0
    assert chunks[0].tokens_est >= 1


def test_sliding_short_document_yields_one_chunk():
    # regression: tunerepo's sliding window produced zero chunks for short docs
    chunks = chunk_sliding(_blocks(["tiny"]), size=1000, overlap=100)
    assert len(chunks) == 1 and chunks[0].text == "tiny"


def test_fixed_respects_size_and_overlap():
    blocks = _blocks(["a" * 100])
    chunks = chunk_fixed(blocks, size=30, overlap=10)
    assert all(len(c.text) <= 30 for c in chunks)
    assert chunks[1].text[:10] == chunks[0].text[-10:]  # overlap continuity


def test_sentence_splitter_respects_abbreviations():
    text = "Dr. Smith left. He met Ms. Lee at 5 p.m. sharp. It was late."
    chunks = chunk_sentence(_blocks([text]), max_size=1000)
    joined = chunks[0].text
    assert "Dr. Smith left." in joined
    assert "5 p.m. sharp." in joined


def test_structure_chunks_attach_heading_path():
    blocks = [
        Heading(level=1, children=[Text("Intro")], span=Span(0, 5), block_index=0),
        Paragraph(children=[Text("body one")], span=Span(7, 15), block_index=1),
        Heading(level=2, children=[Text("Scope")], span=Span(17, 22), block_index=2),
        Paragraph(children=[Text("body two")], span=Span(24, 32), block_index=3),
    ]
    chunks = chunk_structure(blocks, max_size=100, source_id="s")
    assert chunks[0].heading_path == ["Intro"]
    assert chunks[-1].heading_path == ["Intro", "Scope"]
    assert any("body two" in c.text for c in chunks)


def test_transformed_flag_marks_only_chunks_containing_edited_blocks():
    blocks = _blocks(["aaa", "bbb", "ccc"])
    chunks = chunk_paragraph(blocks, max_size=5, transformed=(1,))
    assert [c.transformed for c in chunks] == [False, True, False]


def test_stream_chunks_attribute_transformed_by_window_intersection():
    blocks = _blocks(["x" * 40, "y" * 40])
    chunks = chunk_fixed(blocks, size=30, overlap=10, transformed=(0,))
    assert chunks[0].transformed is True
    assert chunks[-1].transformed is False  # last window covers only block 1


def test_sentence_chunks_accumulate_contributing_blocks_for_transformed():
    blocks = _blocks(["Alpha one. Alpha two.", "Beta one."])
    chunks = chunk_sentence(blocks, max_size=1000, transformed=(1,))
    assert len(chunks) == 1
    assert chunks[0].transformed is True  # edited block 1 contributes mid-buffer


def test_fixed_chunks_gate_clean_on_irregular_text_separators(tmp_path):
    # Final-review amendment: parse_text registers the canonical stream, so
    # fixed windows and the provenance gate agree even on irregular input.
    from veriformis.parsers.text import parse_text
    from veriformis.validate.gates import gate_provenance

    p = tmp_path / "irregular.txt"
    p.write_text("alpha\n\n\nbeta\n \ngamma", encoding="utf-8")
    result = parse_text(p)
    chunks = chunk_fixed(result.document.children, size=10, overlap=2, source_id=result.source.id)
    assert gate_provenance(chunks, {result.source.id: result.source}).passed


def test_paragraph_chunks_never_empty_for_isolated_empty_blocks():
    # Final-review amendment: an isolated empty-text block (e.g. `---` between
    # two oversized paragraphs) must not become a zero-length chunk.
    blocks = [
        Paragraph(children=[Text("a" * 1500)], span=Span(0, 1500), block_index=0),
        HorizontalRule(span=Span(1502, 1502), block_index=1),
        Paragraph(children=[Text("b" * 1500)], span=Span(1504, 3004), block_index=2),
    ]
    chunks = chunk_paragraph(blocks, max_size=1000)
    assert len(chunks) == 2
    assert all(c.text for c in chunks)
    assert chunks[0].span.start == 0 and chunks[0].span.end == 1502  # HR coalesced
