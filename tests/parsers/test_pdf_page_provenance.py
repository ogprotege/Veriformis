"""Post-20 defect D-11: PDF recovery fabricates no text; pages ride on spans.

Before the fix every page contributed a synthetic ``Page N`` heading to the
canonical stream, so text that did not exist in the source became source of
truth and was chunked, evidence-bound, and trained on like any other text.
"""

from __future__ import annotations

from pathlib import Path

from veriformis.ir import Heading, Paragraph
from veriformis.parsers.pdf import PARSER_VERSION, parse_pdf_file

FIXTURES = Path(__file__).parents[1] / "fixtures" / "group5"


def test_two_page_text_layer_yields_paragraphs_with_page_provenance() -> None:
    path = FIXTURES / "two-page-text.pdf"
    result = parse_pdf_file(path, logical_path=path.name)
    assert result.diagnostics.status == "complete"
    assert result.source.parser_version == PARSER_VERSION == "1.1.0"
    assert result.source.extracted_text == (
        "First page line one.\nFirst page line two.\n\nSecond page text."
    )
    assert "Page 1" not in result.source.extracted_text
    blocks = result.document.children
    assert all(isinstance(block, Paragraph) for block in blocks)
    assert not any(isinstance(block, Heading) for block in blocks)
    assert [(block.span.start, block.span.end, block.span.page) for block in blocks] == [
        (0, 41, 1),
        (43, 60, 2),
    ]


def test_single_page_fixture_keeps_only_source_text() -> None:
    path = FIXTURES / "minimal-text.pdf"
    result = parse_pdf_file(path, logical_path=path.name)
    assert result.source.extracted_text == "Hello PDF text layer"
    assert [block.span.page for block in result.document.children] == [1]


def test_whitespace_normalization_is_diagnosed(tmp_path: Path, monkeypatch) -> None:
    import veriformis.parsers.pdf as pdf_module

    monkeypatch.setattr(
        pdf_module,
        "_pdf_page_texts",
        lambda document: ["  Leading space and trailing blank line.\n\n\n"],
    )
    path = FIXTURES / "minimal-text.pdf"
    result = parse_pdf_file(path, logical_path=path.name)
    assert result.source.extracted_text == "Leading space and trailing blank line."
    normalized = next(
        item
        for item in result.diagnostics.diagnostics
        if item.code == "pdf.text-layer-normalized"
    )
    assert normalized.disposition == "normalized"
    assert normalized.loss_kind == "presentation"
    assert normalized.details == {"pages": [1]}


def test_page_count_limit_refuses(monkeypatch) -> None:
    import veriformis.parsers.pdf as pdf_module

    monkeypatch.setattr(pdf_module, "PDF_MAX_PAGES", 1)
    path = FIXTURES / "two-page-text.pdf"
    result = parse_pdf_file(path, logical_path=path.name)
    assert result.diagnostics.status == "refused"
    codes = {item.code for item in result.diagnostics.diagnostics}
    assert "pdf.page-unreadable" in codes
