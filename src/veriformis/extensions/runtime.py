"""Runtime selection of migrated built-ins through the internal protocol."""

from __future__ import annotations

from pathlib import Path

from veriformis.contracts import (
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
    EXTENSION_PROTOCOL_SCHEMA_ID,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.extensions.protocol import CapabilityDeclaration
from veriformis.sources import ParseResult


def bound_text_parser(
    *,
    declaration: CapabilityDeclaration | None = None,
):
    """Return the built-in text parser after protocol version checks."""
    from veriformis.exports.service import DEFAULT_EXPORT_SERVICE
    from veriformis.extensions.declarations import builtin_declarations
    from veriformis.extensions.registry import builtin_registry

    registry = builtin_registry(export_catalog=DEFAULT_EXPORT_SERVICE._catalog())
    if declaration is None:
        declaration = next(
            item
            for item in builtin_declarations(registry)
            if item.kind == "source-parser" and item.discovery.selector == "text"
        )
    if (
        declaration.kind != "source-parser"
        or declaration.discovery.selector != "text"
        or declaration.origin != "builtin"
    ):
        raise ExtensionProtocolError(
            "text parser selection requires a builtin source-parser declaration"
        )
    if declaration.contract_version != EXTENSION_PROTOCOL_CONTRACT_VERSION:
        raise ExtensionProtocolError(
            "unknown extension contract version: requested "
            f"{declaration.contract_version}, supported "
            f"{EXTENSION_PROTOCOL_CONTRACT_VERSION} "
            f"({EXTENSION_PROTOCOL_SCHEMA_ID})"
        )
    return registry.parser("text").target


def parse_text_via_protocol(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes,
) -> ParseResult:
    """Parse `.txt` only through the internal protocol."""
    parser = bound_text_parser()
    return parser(path, logical_path=logical_path, raw_bytes=raw_bytes)
