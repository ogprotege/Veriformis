"""Post-20 defect D-10: DOCX recovery is hardened and names every text loss.

- Note parts are parsed with entity resolution and network access off.
- A package whose central directory declares an unsafe inflated size or member
  count is refused before any member is inflated.
- Text carried inside a drawing (text box, callout, caption) is diagnosed as
  text loss, not as a structural omission.
- Accepted moved text (``w:moveTo``) is retained once, at its destination.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from docx import Document
from lxml import etree

from veriformis.errors import ParseError
from veriformis.parsers.dispatch import parse_captured_source
from veriformis.parsers.docx import (
    DOCX_MAX_INFLATED_BYTES,
    DOCX_MAX_MEMBERS,
    PARSER_VERSION,
    parse_docx_file,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"


def _docx_bytes(build) -> bytes:
    document = Document()
    build(document)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _parse(tmp_path: Path, raw: bytes):
    path = tmp_path / "source.docx"
    path.write_bytes(raw)
    return parse_docx_file(path, logical_path=path.name, raw_bytes=raw)


def _codes(result) -> dict[str, list]:
    codes: dict[str, list] = {}
    for item in result.diagnostics.diagnostics:
        codes.setdefault(item.code, []).append(item)
    return codes


def _replace_member(raw: bytes, name: str, data: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            payload = data if info.filename == name else source.read(info.filename)
            target.writestr(info, payload)
        if name not in source.namelist():
            target.writestr(name, data)
    return out.getvalue()


def test_parser_pin_advanced_for_hardening() -> None:
    assert PARSER_VERSION == "1.3.0"


def test_moved_text_is_retained_once_at_its_destination(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("Plain paragraph before.")
        source = document.add_paragraph()
        source._p.append(
            etree.fromstring(
                f'<w:moveFrom xmlns:w="{W}" w:id="1" w:author="a" '
                f'w:date="2020-01-01T00:00:00Z"><w:r><w:t>moved sentence</w:t></w:r>'
                "</w:moveFrom>"
            )
        )
        destination = document.add_paragraph()
        destination._p.append(
            etree.fromstring(
                f'<w:moveTo xmlns:w="{W}" w:id="2" w:author="a" '
                f'w:date="2020-01-01T00:00:00Z"><w:r><w:t>moved sentence</w:t></w:r>'
                "</w:moveTo>"
            )
        )

    result = _parse(tmp_path, _docx_bytes(build))
    assert result.source.extracted_text == "Plain paragraph before.\n\nmoved sentence"
    codes = _codes(result)
    assert "docx.revision-move-normalized" in codes
    assert "docx.revision-move-source-omitted" in codes
    assert "docx.unsupported-run-element" not in codes
    assert "docx.unsupported-paragraph-element" not in codes


def test_text_box_text_is_diagnosed_as_text_loss(tmp_path: Path) -> None:
    def build(document) -> None:
        paragraph = document.add_paragraph("Before box.")
        run = paragraph.add_run()
        run._r.append(
            etree.fromstring(
                f'<w:drawing xmlns:w="{W}" xmlns:wp="{WP}" xmlns:a="{A}" xmlns:wps="{WPS}">'
                "<wp:inline><a:graphic><a:graphicData uri=\"" + WPS + "\">"
                "<wps:wsp><wps:txbx><w:txbxContent><w:p><w:r><w:t>Text box content</w:t>"
                "</w:r></w:p></w:txbxContent></wps:txbx></wps:wsp>"
                "</a:graphicData></a:graphic></wp:inline></w:drawing>"
            )
        )

    result = _parse(tmp_path, _docx_bytes(build))
    assert "Text box content" not in result.source.extracted_text
    codes = _codes(result)
    omitted = codes["docx.drawing-text-omitted"]
    assert len(omitted) == 1
    assert omitted[0].loss_kind == "text"
    assert omitted[0].disposition == "omitted"
    assert omitted[0].details["image_recovered"] is False
    assert codes["docx.drawing-omitted"][0].loss_kind == "text"
    assert result.diagnostics.status == "degraded"


def test_footnote_part_does_not_resolve_entities(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text("LEAKED-LOCAL-FILE", encoding="utf-8")
    footnotes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<!DOCTYPE w:footnotes [ <!ENTITY leak SYSTEM "file://' + secret.as_posix() + '"> ]>\n'
        f'<w:footnotes xmlns:w="{W}">'
        '<w:footnote w:id="1"><w:p><w:r><w:t>&leak;</w:t></w:r></w:p></w:footnote>'
        "</w:footnotes>"
    )

    def build(document) -> None:
        document.add_paragraph("Body text with a note reference.")

    raw = _replace_member(_docx_bytes(build), "word/footnotes.xml", footnotes.encode("utf-8"))
    path = tmp_path / "entity.docx"
    path.write_bytes(raw)
    try:
        result = parse_docx_file(path, logical_path=path.name, raw_bytes=raw)
    except (ParseError, ValueError, etree.XMLSyntaxError):
        return  # refusing the part is acceptable; leaking is not
    text = result.source.extracted_text + "".join(
        str(item.message) for item in result.diagnostics.diagnostics
    )
    assert "LEAKED-LOCAL-FILE" not in text


def test_oversized_declared_inflation_is_refused_before_inflating(tmp_path: Path) -> None:
    def build(document) -> None:
        document.add_paragraph("Small document.")

    raw = _docx_bytes(build)
    # Rewrite the central directory to claim a huge member without storing it.
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
    forged = bytearray(out.getvalue())
    with zipfile.ZipFile(io.BytesIO(bytes(forged))) as check:
        assert sum(info.file_size for info in check.infolist()) < DOCX_MAX_INFLATED_BYTES

    class HugeZip(zipfile.ZipFile):
        def infolist(self):
            infos = super().infolist()
            infos[0].file_size = DOCX_MAX_INFLATED_BYTES + 1
            return infos

    import veriformis.parsers.docx as docx_module

    original = docx_module.zipfile.ZipFile
    docx_module.zipfile.ZipFile = HugeZip
    try:
        with pytest.raises(ValueError, match="inflated bytes"):
            parse_docx_file(tmp_path / "x.docx", logical_path="x.docx", raw_bytes=bytes(forged))
    finally:
        docx_module.zipfile.ZipFile = original


def test_member_count_limit_is_refused(tmp_path: Path, monkeypatch) -> None:
    def build(document) -> None:
        document.add_paragraph("Small document.")

    raw = _docx_bytes(build)
    import veriformis.parsers.docx as docx_module

    monkeypatch.setattr(docx_module, "DOCX_MAX_MEMBERS", 2)
    with pytest.raises(ValueError, match="member limit"):
        parse_docx_file(tmp_path / "x.docx", logical_path="x.docx", raw_bytes=raw)


def test_dispatch_turns_the_refusal_into_a_typed_parse_error(tmp_path: Path, monkeypatch) -> None:
    def build(document) -> None:
        document.add_paragraph("Small document.")

    raw = _docx_bytes(build)
    path = tmp_path / "x.docx"
    path.write_bytes(raw)
    import veriformis.parsers.docx as docx_module

    monkeypatch.setattr(docx_module, "DOCX_MAX_MEMBERS", 2)
    with pytest.raises(ParseError):
        parse_captured_source(path, logical_path="x.docx", raw_bytes=raw)
