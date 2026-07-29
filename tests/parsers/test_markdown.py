from pathlib import Path

from veriformis.ir import (
    Blockquote,
    CodeBlock,
    Heading,
    Image,
    ListBlock,
    Paragraph,
    Table,
    block_text,
)
from veriformis.parsers.markdown import parse_md, parse_md_file as _parse_md_file

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample.md"


def parse_md_file(path: str | Path):
    return _parse_md_file(path, logical_path=Path(path).name)


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
    assert "bold" in text[para.span.start : para.span.end]


def test_code_block_language_and_footnotes():
    result = parse_md_file(FIXTURE)
    doc = result.document
    code = next(b for b in doc.children if isinstance(b, CodeBlock))
    assert code.language == "python"
    assert "n" in doc.footnotes
    note_block = doc.footnotes["n"].children[0]
    assert note_block.span is not None
    assert note_block.block_index >= len(doc.children)
    assert result.source.extracted_text[
        note_block.span.start : note_block.span.end
    ] == block_text(note_block)


def test_parse_md_library_entry():
    doc = parse_md("# Hi\n\ntext")
    assert isinstance(doc.children[0], Heading)
    assert block_text(doc.children[1]) == "text"


def test_literal_star_only_paragraph_is_preserved(tmp_path):
    path = tmp_path / "literal-stars.md"
    path.write_text("before\n\n**\n\nafter", encoding="utf-8")

    result = parse_md_file(path)

    assert result.source.extracted_text == "before\n\n**\n\nafter"


def test_fenced_code_preserves_intentional_trailing_blank_line(tmp_path):
    path = tmp_path / "trailing-code.md"
    path.write_text("```text\nline\n\n```", encoding="utf-8")

    result = parse_md_file(path)
    code = next(
        block for block in result.document.children if isinstance(block, CodeBlock)
    )

    assert code.text == "line\n"
    assert result.source.extracted_text == "line\n"


def test_pandoc_cleanup_is_narrow_and_preserves_unrelated_spacing(tmp_path):
    path = tmp_path / "pandoc-scope.md"
    path.write_text(
        "# Heading {#heading .major key=value}\n\n"
        "literal {.not-an-attribute}  spacing\n\n"
        "left []{#anchor .target} right",
        encoding="utf-8",
    )

    result = parse_md_file(path)

    assert result.source.extracted_text == (
        "Heading\n\nliteral {.not-an-attribute}  spacing\n\nleft right"
    )
    pandoc = [
        item
        for item in result.diagnostics.diagnostics
        if item.code.startswith("markdown.pandoc-")
    ]
    assert {item.code for item in pandoc} == {
        "markdown.pandoc-anchor-omitted",
        "markdown.pandoc-attributes-omitted",
    }


def test_heading_attributes_are_removed_only_at_heading_scope(tmp_path):
    path = tmp_path / "heading-attribute-scope.md"
    path.write_text(
        "# **literal {#inside}** {#heading}",
        encoding="utf-8",
    )

    result = parse_md_file(path)
    attributes = [
        item
        for item in result.diagnostics.diagnostics
        if item.code == "markdown.pandoc-attributes-omitted"
    ]

    assert result.source.extracted_text == "literal {#inside}"
    assert len(attributes) == 1


def test_pandoc_like_image_alt_is_preserved_without_false_diagnostic(tmp_path):
    path = tmp_path / "image-alt-attribute.md"
    path.write_text("# ![{#literal}](image.png)", encoding="utf-8")

    result = parse_md_file(path)
    heading = result.document.children[0]
    image = next(node for node in heading.children if isinstance(node, Image))

    assert image.alt == "{#literal}"
    assert not any(
        item.code.startswith("markdown.pandoc-")
        for item in result.diagnostics.diagnostics
    )


def test_definition_loss_is_detected_before_markdown_tokenization(tmp_path):
    path = tmp_path / "definitions.md"
    path.write_text(
        "[^note]: first body\n"
        "[^note]: replacement body\n\n"
        "[target]: https://first.example\n"
        "[target]: https://second.example\n"
        "[unused]: https://unused.example\n\n"
        "Body[^note] and [link][target].",
        encoding="utf-8",
    )

    result = parse_md_file(path)
    by_code = {item.code: item for item in result.diagnostics.diagnostics}

    assert result.diagnostics.status == "refused"
    assert by_code["markdown.duplicate-footnote-definition"].location.line_start == 2
    assert by_code["markdown.duplicate-reference-definition"].location.line_start == 5
    assert (
        by_code["markdown.unused-reference-definition-omitted"].location.line_start == 6
    )
    assert by_code["markdown.duplicate-footnote-definition"].loss_kind == "text"


def test_case_distinct_footnote_ids_are_not_treated_as_duplicates(tmp_path):
    path = tmp_path / "case-distinct-notes.md"
    path.write_text(
        "[^Note]: upper\n[^note]: lower\n\nBody[^Note] and body[^note].",
        encoding="utf-8",
    )

    result = parse_md_file(path)

    assert set(result.document.footnotes) == {"Note", "note"}
    assert not any(
        item.code == "markdown.duplicate-footnote-definition"
        for item in result.diagnostics.diagnostics
    )


def test_unreferenced_footnote_text_is_refused_not_silently_lost(tmp_path):
    path = tmp_path / "unused-note.md"
    path.write_text("[^unused]: Whole note body\n\nVisible body", encoding="utf-8")

    result = parse_md_file(path)
    item = next(
        diagnostic
        for diagnostic in result.diagnostics.diagnostics
        if diagnostic.code == "markdown.unused-footnote-definition-refused"
    )

    assert result.diagnostics.status == "refused"
    assert item.loss_kind == "text"
    assert item.location.line_start == 1


def test_definition_inventory_ignores_literal_code_blocks(tmp_path):
    path = tmp_path / "literal-definitions.md"
    path.write_text(
        "```markdown\n"
        "[^note]: first literal\n"
        "[^note]: second literal\n"
        "[unused]: https://literal.example\n"
        "```",
        encoding="utf-8",
    )

    result = parse_md_file(path)

    assert result.diagnostics.status == "complete"
    assert result.document.children[0].text.startswith("[^note]: first literal")


def test_reference_text_inside_inline_code_does_not_mark_definition_used(tmp_path):
    path = tmp_path / "inline-code-reference.md"
    path.write_text("[target]: /destination\n\n`[target]`", encoding="utf-8")

    result = parse_md_file(path)

    item = next(
        diagnostic
        for diagnostic in result.diagnostics.diagnostics
        if diagnostic.code == "markdown.unused-reference-definition-omitted"
    )
    assert item.location.line_start == 1


def test_reference_definition_used_by_image_is_not_reported_unused(tmp_path):
    path = tmp_path / "reference-image.md"
    path.write_text("[asset]: /image.png\n\n![alt][asset]", encoding="utf-8")

    result = parse_md_file(path)

    assert not any(
        item.code == "markdown.unused-reference-definition-omitted"
        for item in result.diagnostics.diagnostics
    )


def test_list_start_softbreak_and_image_alt_are_explicit(tmp_path):
    path = tmp_path / "normalizations.md"
    path.write_text(
        "3. first\n4. second\n\nline one\nline two\n\nbefore ![  padded  ](image.png) after",
        encoding="utf-8",
    )

    result = parse_md_file(path)
    codes = {item.code for item in result.diagnostics.diagnostics}
    paragraph = result.document.children[-1]
    image = next(node for node in paragraph.children if isinstance(node, Image))

    assert "markdown.ordered-list-start-omitted" in codes
    assert "markdown.softbreak-normalized" in codes
    assert image.alt == "  padded  "
