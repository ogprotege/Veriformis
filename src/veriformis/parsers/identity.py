"""Pinned parser identities and recovery-quality vocabulary.

Parser version strings already travel on ``SourceRef`` and parse reports.
This module names those pins and the library versions they execute with,
without changing persisted parse-report bytes.
"""

from __future__ import annotations

from importlib import metadata
from typing import Mapping

from veriformis.parsers.docx import PARSER_VERSION as DOCX_PARSER_VERSION
from veriformis.parsers.html import PARSER_VERSION as HTML_PARSER_VERSION
from veriformis.parsers.markdown import PARSER_VERSION as MARKDOWN_PARSER_VERSION
from veriformis.parsers.pdf import PARSER_VERSION as PDF_PARSER_VERSION
from veriformis.parsers.structured import (
    CSV_PARSER_VERSION,
    JSON_PARSER_VERSION,
    JSONL_PARSER_VERSION,
)
from veriformis.parsers.text import PARSER_VERSION as TEXT_PARSER_VERSION

RECOVERY_QUALITY_STATUSES = ("complete", "degraded", "refused")

PARSER_KIND_VERSIONS: Mapping[str, str] = {
    "text": TEXT_PARSER_VERSION,
    "markdown": MARKDOWN_PARSER_VERSION,
    "docx": DOCX_PARSER_VERSION,
    "html": HTML_PARSER_VERSION,
    "pdf": PDF_PARSER_VERSION,
    "csv": CSV_PARSER_VERSION,
    "json": JSON_PARSER_VERSION,
    "jsonl": JSONL_PARSER_VERSION,
}

PARSER_LIBRARIES: Mapping[str, tuple[str, ...]] = {
    "text": (),
    "markdown": ("markdown-it-py", "mdit-py-plugins"),
    "docx": ("python-docx", "lxml"),
    "html": ("lxml",),
    "pdf": ("pypdfium2",),
    "csv": (),
    "json": (),
    "jsonl": (),
}


def _distribution_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "absent"


def parser_identities() -> dict[str, dict[str, object]]:
    """Return pinned parser kinds, versions, and runtime library versions."""
    identities: dict[str, dict[str, object]] = {}
    for kind, version in PARSER_KIND_VERSIONS.items():
        libraries = {
            name: _distribution_version(name) for name in PARSER_LIBRARIES[kind]
        }
        identities[kind] = {
            "parser": kind,
            "parser_version": version,
            "libraries": libraries,
            "recovery_quality_status": list(RECOVERY_QUALITY_STATUSES),
        }
    return identities
