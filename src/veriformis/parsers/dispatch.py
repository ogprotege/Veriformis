"""Single deterministic dispatch for captured raw source bytes."""
from __future__ import annotations

import zipfile
from pathlib import Path

from docx.opc.exceptions import PackageNotFoundError
from lxml import etree

from veriformis.errors import ParseError, UnsupportedInputError
from veriformis.parsers.docx import parse_docx_file
from veriformis.parsers.markdown import parse_md_file
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
