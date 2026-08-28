"""Internal extension protocol and built-in-only registry. There is no loader."""

from veriformis.extensions.protocol import (
    EXTENSION_KINDS,
    EXTENSION_LIFECYCLES,
    EXTENSION_ORIGINS,
    OFFLINE_DETERMINISTIC_REQUIREMENTS,
    PROTOCOL_LIMITATIONS,
    CapabilityDeclaration,
    DeterministicRequirements,
    DiscoveryMetadata,
    create_capability_declaration,
    load_capability_declaration,
)
from veriformis.extensions.registry import (
    BuiltinBinding,
    BuiltinExtensionRegistry,
    builtin_registry,
)

__all__ = [
    "EXTENSION_KINDS",
    "EXTENSION_LIFECYCLES",
    "EXTENSION_ORIGINS",
    "OFFLINE_DETERMINISTIC_REQUIREMENTS",
    "PROTOCOL_LIMITATIONS",
    "BuiltinBinding",
    "BuiltinExtensionRegistry",
    "CapabilityDeclaration",
    "DeterministicRequirements",
    "DiscoveryMetadata",
    "builtin_registry",
    "create_capability_declaration",
    "load_capability_declaration",
]
