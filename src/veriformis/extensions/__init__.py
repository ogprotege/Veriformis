"""Internal extension protocol. Item 16.2 pins declarations; there is no loader."""

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

__all__ = [
    "EXTENSION_KINDS",
    "EXTENSION_LIFECYCLES",
    "EXTENSION_ORIGINS",
    "OFFLINE_DETERMINISTIC_REQUIREMENTS",
    "PROTOCOL_LIMITATIONS",
    "CapabilityDeclaration",
    "DeterministicRequirements",
    "DiscoveryMetadata",
    "create_capability_declaration",
    "load_capability_declaration",
]
