"""Versioned finished-bundle handoffs for training-system consumers."""

from veriformis.handoff.aptus_v1 import (
    APTUS_HANDOFF_SCHEMA_VERSION,
    AptusHandoffDescriptor,
    AptusHandoffError,
    build_aptus_handoff,
    consume_aptus_handoff,
    handoff_path_for_bundle,
    write_aptus_handoff,
)

__all__ = [
    "APTUS_HANDOFF_SCHEMA_VERSION",
    "AptusHandoffDescriptor",
    "AptusHandoffError",
    "build_aptus_handoff",
    "consume_aptus_handoff",
    "handoff_path_for_bundle",
    "write_aptus_handoff",
]
