"""Digitally-born PDF recovery via pypdfium2 text layer.

Empty text-layer pages are classified as OCR recovery. Digital text is
never replaced. Without an OCR provider, image-only PDFs still refuse.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pypdfium2 as pdfium

from veriformis.diagnostics import (
    DiagnosticLocation,
    make_diagnostic,
    make_parse_report,
)
from veriformis.identity import sha256_digest
from veriformis.ir import Document, Heading, Paragraph, Span, Text
from veriformis.ocr.recovery import recover_pages
from veriformis.sources import ParseResult, register_source

if TYPE_CHECKING:
    from veriformis.ocr.recovery import OcrProvider

PARSER_VERSION = "1.0.0"
_PARSER = "pdf"
_OCR_LIMITATION = "ocr-unsupported"


def parse_pdf_file(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes | None = None,
    ocr_provider: OcrProvider | None = None,
) -> ParseResult:
    """Extract page text from a digitally-born PDF into canonical IR."""
    p = Path(path)
    captured = raw_bytes if raw_bytes is not None else p.read_bytes()
    try:
        document = pdfium.PdfDocument(captured)
    except Exception as exc:  # pypdfium2 raises PdfiumError subclasses
        source = register_source(
            p,
            _PARSER,
            "",
            logical_path=logical_path,
            parser_version=PARSER_VERSION,
            raw_bytes=captured,
        )
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=(
                make_diagnostic(
                    source_id=source.id,
                    parser_name=_PARSER,
                    parser_version=PARSER_VERSION,
                    code="pdf.unreadable",
                    severity="error",
                    disposition="refused",
                    loss_kind="structure",
                    location=DiagnosticLocation(kind="source"),
                    message=f"PDF package could not be opened: {exc}",
                    details={"reason": "unreadable"},
                ),
            ),
        )
        return ParseResult(
            document=Document(children=[], source_id=source.id),
            source=source,
            diagnostics=report,
        )

    try:
        page_texts = _pdf_page_texts(document)
    finally:
        document.close()

    if not page_texts:
        page_texts = [""]
    rasters: tuple[bytes, ...] | None = None
    if ocr_provider is not None:
        from veriformis.ocr.raster import render_pdf_page_png

        rendered: list[bytes] = []
        for index, text in enumerate(page_texts, start=1):
            if text.strip():
                rendered.append(b"")
            else:
                rendered.append(render_pdf_page_png(captured, index))
        rasters = tuple(rendered)
    recovery = recover_pages(
        tuple(page_texts),
        source_sha256=sha256_digest(captured),
        provider=ocr_provider,
        rasters=rasters,
    )
    empty_pages = [
        page.page_index
        for page in recovery.pages
        if page.recovery_path == "ocr" and not page.text.strip()
    ]
    recovery_details = {
        "recovery_path": recovery.recovery_path,
        "pages": [
            {"page_index": page.page_index, "recovery_path": page.recovery_path}
            for page in recovery.pages
        ],
    }

    blocks: list = []
    parts: list[str] = []
    pos = 0
    for page in recovery.pages:
        if not page.text.strip():
            continue
        heading = f"Page {page.page_index}"
        if parts:
            pos += 2
        heading_start = pos
        heading_end = heading_start + len(heading)
        blocks.append(
            Heading(
                level=2,
                children=[Text(heading)],
                span=Span(heading_start, heading_end),
                block_index=len(blocks),
            )
        )
        parts.append(heading)
        pos = heading_end
        for paragraph in _split_paragraphs(page.text):
            pos += 2
            start = pos
            end = start + len(paragraph)
            blocks.append(
                Paragraph(
                    children=[Text(paragraph)],
                    span=Span(start, end),
                    block_index=len(blocks),
                )
            )
            parts.append(paragraph)
            pos = end

    stream = "\n\n".join(parts)
    source = register_source(
        p,
        _PARSER,
        stream,
        logical_path=logical_path,
        parser_version=PARSER_VERSION,
        raw_bytes=captured,
    )
    diagnostics = []
    warn_pages = [
        page.page_index
        for page in recovery.pages
        if page.confidence_action == "warn"
    ]
    review_pages = [
        page.page_index
        for page in recovery.pages
        if page.confidence_action == "review"
    ]
    refused_pages = [
        page.page_index
        for page in recovery.pages
        if page.confidence_action == "refuse"
    ]
    if warn_pages:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="pdf.ocr-confidence-warn",
                severity="warning",
                disposition="preserved",
                loss_kind="none",
                location=DiagnosticLocation(kind="source"),
                message=(
                    "OCR confidence is below the warn threshold on pages: "
                    + ", ".join(str(item) for item in warn_pages)
                ),
                details={"pages": warn_pages, **recovery_details},
            )
        )
    if review_pages:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="pdf.ocr-confidence-review",
                severity="warning",
                disposition="preserved",
                loss_kind="none",
                location=DiagnosticLocation(kind="source"),
                message=(
                    "OCR confidence requires review on pages: "
                    + ", ".join(str(item) for item in review_pages)
                ),
                details={
                    "pages": review_pages,
                    "pending_review": True,
                    **recovery_details,
                },
            )
        )
    if refused_pages:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="pdf.ocr-confidence-refuse",
                severity="warning",
                disposition="omitted",
                loss_kind="text",
                location=DiagnosticLocation(kind="source"),
                message=(
                    "OCR confidence is below the refuse threshold; recovered "
                    "text is retained on held_text and omitted from the stream "
                    "on pages: " + ", ".join(str(item) for item in refused_pages)
                ),
                details={"pages": refused_pages, **recovery_details},
            )
        )
    if empty_pages:
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="pdf.empty-text-pages",
                severity="warning",
                disposition="omitted",
                loss_kind="text",
                location=DiagnosticLocation(kind="source"),
                message=(
                    "One or more PDF pages exposed no extractable text layer: "
                    + ", ".join(str(item) for item in empty_pages)
                ),
                details={"empty_pages": empty_pages, **recovery_details},
            )
        )

    if not stream.strip():
        diagnostics.append(
            make_diagnostic(
                source_id=source.id,
                parser_name=_PARSER,
                parser_version=PARSER_VERSION,
                code="pdf.ocr-required",
                severity="error",
                disposition="refused",
                loss_kind="text",
                location=DiagnosticLocation(kind="source"),
                message=(
                    "PDF has no extractable text layer. OCR is unsupported in "
                    "deterministic v1; provide a digitally-born PDF with a text layer."
                ),
                details={
                    "limitation": _OCR_LIMITATION,
                    "page_count": len(page_texts),
                    **recovery_details,
                },
            )
        )
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=tuple(diagnostics),
        )
    else:
        report = make_parse_report(
            source_id=source.id,
            parser_name=_PARSER,
            parser_version=PARSER_VERSION,
            diagnostics=tuple(diagnostics),
        )
    return ParseResult(
        document=Document(children=blocks, source_id=source.id),
        source=source,
        diagnostics=report,
    )


def _pdf_page_texts(document: pdfium.PdfDocument) -> list[str]:
    page_texts: list[str] = []
    for index in range(len(document)):
        page = document[index]
        textpage = page.get_textpage()
        try:
            text = textpage.get_text_bounded() or ""
        finally:
            textpage.close()
            page.close()
        page_texts.append(text.replace("\r\n", "\n").replace("\r", "\n").strip())
    return page_texts


def pdf_page_texts(
    path: str | Path,
    *,
    raw_bytes: bytes | None = None,
) -> tuple[str, ...]:
    """Return per-page digital text layers without running OCR."""
    captured = raw_bytes if raw_bytes is not None else Path(path).read_bytes()
    try:
        document = pdfium.PdfDocument(captured)
    except Exception:
        return ()
    try:
        texts = _pdf_page_texts(document)
    finally:
        document.close()
    return tuple(texts) if texts else ("",)


def _split_paragraphs(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in text.split("\n\n")]
    result = [chunk for chunk in chunks if chunk]
    if result:
        return result
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines if lines else ([text.strip()] if text.strip() else [])
