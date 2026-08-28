"""Runtime selection of migrated built-ins through the internal protocol."""

from __future__ import annotations

from pathlib import Path

from veriformis.contracts import (
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
    EXTENSION_PROTOCOL_SCHEMA_ID,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.exports._implementation import _ExportImplementation
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


def bound_split_jsonl_exporter(
    *,
    catalog: tuple[_ExportImplementation, ...] | None = None,
    declaration: CapabilityDeclaration | None = None,
) -> _ExportImplementation:
    """Return the generic split-JSONL catalog entry after protocol checks.

    The catalog argument is required on the export-service path so this helper
    never imports ``ExportService`` while that module is still initializing.
    """
    from veriformis.exports.split_jsonl import SPLIT_JSONL_CONTAINER_ID
    from veriformis.extensions.protocol import create_capability_declaration

    if catalog is None:
        from veriformis.exports.service import DEFAULT_EXPORT_SERVICE

        implementations = DEFAULT_EXPORT_SERVICE._catalog()
    else:
        implementations = catalog
    if declaration is None:
        declaration = create_capability_declaration(
            kind="container-exporter",
            origin="builtin",
            lifecycle="supported",
            extra=None,
            selector=SPLIT_JSONL_CONTAINER_ID,
            title="split-jsonl-directory exporter",
        )
    if (
        declaration.kind != "container-exporter"
        or declaration.discovery.selector != SPLIT_JSONL_CONTAINER_ID
        or declaration.origin != "builtin"
    ):
        raise ExtensionProtocolError(
            "split-jsonl-directory selection requires a builtin "
            "container-exporter declaration"
        )
    if declaration.contract_version != EXTENSION_PROTOCOL_CONTRACT_VERSION:
        raise ExtensionProtocolError(
            "unknown extension contract version: requested "
            f"{declaration.contract_version}, supported "
            f"{EXTENSION_PROTOCOL_CONTRACT_VERSION} "
            f"({EXTENSION_PROTOCOL_SCHEMA_ID})"
        )
    for item in implementations:
        consumer = item.descriptor.consumer_profile
        if (
            item.descriptor.container_profile.container_id == SPLIT_JSONL_CONTAINER_ID
            and consumer is None
        ):
            return item
    raise ExtensionProtocolError(
        "split-jsonl-directory is missing from the internal export catalog"
    )


def parse_text_via_protocol(
    path: str | Path,
    *,
    logical_path: str,
    raw_bytes: bytes,
) -> ParseResult:
    """Parse `.txt` only through the internal protocol."""
    parser = bound_text_parser()
    return parser(path, logical_path=logical_path, raw_bytes=raw_bytes)
