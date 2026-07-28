# tests/chunkers/test_strategies.py
from veriformis.chunkers.strategies import (
    chunk_fixed, chunk_paragraph, chunk_sentence, chunk_sliding, chunk_structure,
)
from veriformis.ir import Heading, Paragraph, Span, Text


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
