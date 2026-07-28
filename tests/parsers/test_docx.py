from docx import Document as DocxBuilder

from veriformis.ir import Heading, ListBlock, Paragraph, Table, block_text
from veriformis.parsers.docx import parse_docx_file


def _build(path):
    d = DocxBuilder()
    d.add_heading("Report", level=1)
    d.add_paragraph("Opening paragraph.")
    p = d.add_paragraph()
    p.add_run("Mixed ").bold = False
    run = p.add_run("bold")
    run.bold = True
    p.add_run(" text.")
    d.add_paragraph("First item", style="List Bullet")
    d.add_paragraph("Second item", style="List Bullet")
    table = d.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "H1"
    table.cell(0, 1).text = "H2"
    table.cell(1, 0).text = "a"
    table.cell(1, 1).text = "b"
    d.save(path)


def test_docx_structure_and_provenance(tmp_path):
    path = tmp_path / "sample.docx"
    _build(path)
    result = parse_docx_file(path)
    doc = result.document
    assert result.source.parser == "docx"
    types = [type(b) for b in doc.children]
    assert Heading in types and Paragraph in types
    assert ListBlock in types and Table in types
    heading = next(b for b in doc.children if isinstance(b, Heading))
    assert heading.level == 1 and block_text(heading) == "Report"
    # provenance: every span indexes into the extracted stream
    stream = result.source.extracted_text
    for block in doc.children:
        assert block.span is not None
        assert block.span.start < block.span.end <= len(stream)
    para = next(
        b for b in doc.children
        if isinstance(b, Paragraph) and "Opening" in block_text(b)
    )
    assert "Opening paragraph." in stream[para.span.start:para.span.end]
