# tests/chunkers/test_defectclose_sentence.py
"""Defect closure: sentence chunking must not strip a buffer its evidence
components cannot reconstruct. Cleaning (e.g. the stock urls rule deleting a
trailing token) leaves edge whitespace inside a block; sentence spans now
exclude leading/trailing whitespace so chunk text is the exact " ".join of
its evidence slices by construction."""
from __future__ import annotations

from veriformis.chunkers.strategies import chunk_sentence
from veriformis.evidence import resolve_evidence
from veriformis.ir import Paragraph, Span, Text
from veriformis.parsers.text import parse_text
from veriformis.pipeline import PipelineService
from veriformis.rules.cleaning import plan_cleaning
from veriformis.rules.derivations import build_block_derivations
from veriformis.rules.library import RULES

# Long enough that deleting the URL stays under the cleaning safety budget.
_PARAGRAPH = (
    "Alpha keeps this corpus well beyond the cleaning safety limit today. "
    "Beta adds more grounded filler text for the removal budget as well. "
    "First sentence is here. Second sentence cites https://example.com/x"
)


def _para(text: str) -> list[Paragraph]:
    return [
        Paragraph(children=[Text(text)], span=Span(0, len(text)), block_index=0)
    ]


def _cleaned(tmp_path):
    path = tmp_path / "doc.txt"
    path.write_text(_PARAGRAPH, encoding="utf-8")
    parsed = parse_text(path, logical_path=path.name)
    preview = plan_cleaning(parsed.document, [RULES["urls"]()])
    derivations = build_block_derivations(
        parsed.source,
        preview.document,
        cleaning_plan_id=preview.plan.id,
    )
    return parsed.source, preview.document, derivations


def test_sentence_evidence_survives_cleaned_trailing_whitespace(tmp_path):
    source, document, derivations = _cleaned(tmp_path)
    from veriformis.ir import block_text

    cleaned_text = block_text(document.children[0])
    assert cleaned_text.endswith(" ")  # guard: cleaning left edge whitespace

    chunks = chunk_sentence(
        document.children,
        max_size=1000,
        source=source,
        block_derivations=derivations,
    )
    assert len(chunks) == 1
    assert chunks[0].text.endswith("Second sentence cites")
    assert not chunks[0].text.endswith(" ")
    assert (
        resolve_evidence(chunks[0].evidence, {source.id: source})
        == chunks[0].text
    )


def test_pipeline_parse_clean_urls_chunk_sentence(tmp_path):
    """End-to-end trigger: parse -> clean(urls) -> chunk(sentence) on a
    paragraph ending in a URL must not kill the chunk stage."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc.txt").write_text(_PARAGRAPH, encoding="utf-8")
    workspace = tmp_path / "ws"
    service = PipelineService()
    service.parse([raw / "doc.txt"], workspace, source_root=raw)
    service.clean(workspace, rules="urls")
    outcome = service.chunk(workspace, strategy="sentence")
    assert outcome.exit_status == 0
    assert outcome.chunk_count >= 1


def test_single_sentence_trailing_whitespace_trimmed():
    chunks = chunk_sentence(_para("Gamma delta "), max_size=1000)
    assert [chunk.text for chunk in chunks] == ["Gamma delta"]
    assert chunks[0].evidence is None  # evidence-less path unchanged


def test_split_buffers_never_carry_edge_whitespace():
    chunks = chunk_sentence(_para("One two.   Three four. "), max_size=10)
    assert [chunk.text for chunk in chunks] == ["One two.", "Three four."]


def test_single_sentence_and_no_evidence_paths_still_behave():
    chunks = chunk_sentence(_para("Hello world."), max_size=1000)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
    assert chunks[0].evidence is None

    # Whitespace-only blocks emit nothing rather than whitespace chunks.
    assert chunk_sentence(_para("   "), max_size=1000) == []
