"""Single deterministic dispatch for captured raw source bytes."""
from __future__ import annotations

import zipfile
from pathlib import Path

from docx.opc.exceptions import PackageNotFoundError
from lxml import etree

from veriformis.errors import ParseError, UnsupportedInputError
from veriformis.parsers.docx import parse_docx_file
from veriformis.parsers.html import parse_html_file
from veriformis.parsers.markdown import parse_md_file
from veriformis.parsers.pdf import parse_pdf_file
from veriformis.parsers.structured import (
    parse_csv_file,
    parse_json_file,
    parse_jsonl_file,
)
from veriformis.parsers.text import parse_text
from veriformis.sources import ParseResult


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".c",
    ".cpp",
    ".go",
    ".rs",
    ".rb",
    ".sh",
}

# Declared v1 input suffixes. OCR-only PDFs still refuse with a named limitation.
DECLARED_V1_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".docx",
        ".html",
        ".htm",
        ".pdf",
        ".csv",
        ".json",
        ".jsonl",
        *CODE_EXTENSIONS,
    }
)


def parse_captured_source(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes,
) -> ParseResult:
    """Parse one immutable byte capture according to its logical suffix."""
    display_path = Path(path)
    extension = Path(logical_path).suffix.lower()
    if extension == ".txt":
        return parse_text(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension in {".md", ".markdown"}:
        return parse_md_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension == ".docx":
        try:
            return parse_docx_file(
                display_path,
                logical_path=logical_path,
                raw_bytes=raw_bytes,
            )
        except (
            zipfile.BadZipFile,
            PackageNotFoundError,
            etree.XMLSyntaxError,
            KeyError,
            RuntimeError,
            ValueError,
        ) as exc:
            raise ParseError(
                f"DOCX package is malformed or incomplete: {logical_path}"
            ) from exc
    if extension in {".html", ".htm"}:
        return parse_html_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension == ".pdf":
        return parse_pdf_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension == ".csv":
        return parse_csv_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension == ".json":
        return parse_json_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension == ".jsonl":
        return parse_jsonl_file(
            display_path,
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    if extension in CODE_EXTENSIONS:
        return parse_text(
            display_path,
            language=extension.lstrip("."),
            logical_path=logical_path,
            raw_bytes=raw_bytes,
        )
    raise UnsupportedInputError(
        f"unsupported input type: {Path(logical_path).name}"
    )
