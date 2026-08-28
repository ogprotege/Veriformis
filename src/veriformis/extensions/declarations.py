"""Read-only built-in capability declarations over the 16.3 registry.

Declarations are metadata. They do not change dispatch, lookup, or the export
catalog. Third-party origin is refused.
"""

from __future__ import annotations

from typing import Any

from veriformis.contracts import (
    EXTENSION_DISCOVERY_SCHEMA_ID,
    EXTENSION_PROTOCOL_CONTRACT_ID,
    EXTENSION_PROTOCOL_CONTRACT_VERSION,
)
from veriformis.errors import ExtensionProtocolError
from veriformis.extensions.protocol import (
    EXTENSION_KINDS,
    CapabilityDeclaration,
    create_capability_declaration,
)
from veriformis.extensions.registry import BuiltinBinding, BuiltinExtensionRegistry

_PARSER_TITLES: dict[str, str] = {
    "text": "Plain text parser",
    "markdown": "Markdown parser",
    "docx": "Word document parser",
    "html": "HTML parser",
    "pdf": "PDF text parser",
    "csv": "CSV parser",
    "json": "JSON parser",
    "jsonl": "JSONL parser",
}
_PROFILE_EXTRAS = {
    "aptus": "aptus",
    "axolotl": "axolotl",
    "llama-factory": "llama-factory",
    "mlx-lm": "mlx-lm",
    "trl": "trl",
}


def declaration_selector(binding: BuiltinBinding) -> str:
    """Map a registry selector onto a protocol token."""
    if binding.kind != "deterministic-constructor":
        return binding.selector
    constructor_id, version = binding.selector.split("/", 1)
    return f"{constructor_id.rsplit('.', 1)[-1]}-{version}"


def _declare_binding(
    binding: BuiltinBinding,
    *,
    title: str,
    extra: str | None = None,
    consumer_id: str | None = None,
    diagnostic_ids: tuple[str, ...] = (),
    fixture_ids: tuple[str, ...] = (),
) -> CapabilityDeclaration:
    return create_capability_declaration(
        kind=binding.kind,  # type: ignore[arg-type]
        origin="builtin",
        lifecycle="supported",
        extra=extra if extra is not None else binding.extra,
        selector=declaration_selector(binding),
        title=title,
        diagnostic_ids=diagnostic_ids,
        fixture_ids=fixture_ids,
        consumer_id=consumer_id,
    )


def _export_declaration(item: object) -> CapabilityDeclaration:
    descriptor = getattr(item, "descriptor")
    consumer = descriptor.consumer_profile
    container_id = descriptor.container_profile.container_id
    if consumer is None:
        return create_capability_declaration(
            kind="container-exporter",
            origin="builtin",
            lifecycle="supported",
            extra=None,
            selector=container_id,
            title=f"{container_id} exporter",
        )
    consumer_id = consumer.consumer_id
    extra = _PROFILE_EXTRAS.get(consumer_id)
    if extra is None:
        raise ExtensionProtocolError(
            "consumer-profile declaration extra is unknown for "
            f"{consumer_id!r}"
        )
    return create_capability_declaration(
        kind="consumer-profile",
        origin="builtin",
        lifecycle="supported",
        extra=extra,
        selector=consumer_id,
        title=f"{consumer_id} adapter",
        consumer_id=consumer_id,
    )


def builtin_declarations(
    registry: BuiltinExtensionRegistry,
) -> tuple[CapabilityDeclaration, ...]:
    """One supported built-in declaration per registry binding."""
    declarations: list[CapabilityDeclaration] = [
        _declare_binding(
            binding,
            title=_PARSER_TITLES[binding.selector],
            fixture_ids=("phase16-text",) if binding.selector == "text" else (),
        )
        for binding in registry.parsers
    ]
    declarations.append(
        _declare_binding(registry.mapper, title="Confirmed row mapping")
    )
    declarations.extend(
        _declare_binding(
            binding,
            title=declaration_selector(binding),
        )
        for binding in registry.constructors
    )
    declarations.extend(
        _declare_binding(
            binding,
            title=binding.selector,
        )
        for binding in registry.quality_checks
    )
    declarations.extend(_export_declaration(item) for item in registry.exporters)
    ordered = tuple(
        sorted(
            declarations,
            key=lambda item: (EXTENSION_KINDS.index(item.kind), item.discovery.selector),
        )
    )
    _require_declarations_match_registry(ordered, registry)
    return ordered


def _require_declarations_match_registry(
    declarations: tuple[CapabilityDeclaration, ...],
    registry: BuiltinExtensionRegistry,
) -> None:
    for item in declarations:
        if item.origin != "builtin":
            raise ExtensionProtocolError(
                "internal registry admits origin builtin only; "
                f"requested {item.origin}"
            )
        if item.lifecycle != "supported":
            raise ExtensionProtocolError(
                "built-in declarations must use lifecycle supported; "
                f"requested {item.lifecycle}"
            )
        if item.contract_version != EXTENSION_PROTOCOL_CONTRACT_VERSION:
            raise ExtensionProtocolError(
                "unknown extension contract version: requested "
                f"{item.contract_version}, supported "
                f"{EXTENSION_PROTOCOL_CONTRACT_VERSION} "
                f"({item.schema_id})"
            )
    expected: list[tuple[str, str]] = [
        (binding.kind, declaration_selector(binding)) for binding in registry.parsers
    ]
    expected.append(
        (registry.mapper.kind, declaration_selector(registry.mapper))
    )
    expected.extend(
        (binding.kind, declaration_selector(binding))
        for binding in registry.constructors
    )
    expected.extend(
        (binding.kind, declaration_selector(binding))
        for binding in registry.quality_checks
    )
    for item in registry.exporters:
        consumer = item.descriptor.consumer_profile
        if consumer is None:
            expected.append(
                ("container-exporter", item.descriptor.container_profile.container_id)
            )
        else:
            expected.append(("consumer-profile", consumer.consumer_id))
    observed = [(item.kind, item.discovery.selector) for item in declarations]
    if sorted(observed) != sorted(expected):
        raise ExtensionProtocolError(
            "built-in declarations must match the internal registry exactly"
        )


def discover_extensions(registry: BuiltinExtensionRegistry) -> dict[str, Any]:
    """Read-only built-in discovery. No third-party loading claim."""
    declarations = builtin_declarations(registry)
    return {
        "contract_id": EXTENSION_PROTOCOL_CONTRACT_ID,
        "contract_version": EXTENSION_PROTOCOL_CONTRACT_VERSION,
        "declarations": [item.model_dump(mode="json") for item in declarations],
        "public_plugin_api": False,
        "schema_id": EXTENSION_DISCOVERY_SCHEMA_ID,
        "third_party_loading": False,
    }
