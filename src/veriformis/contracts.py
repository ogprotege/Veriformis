"""Public, versioned product and acceptance-contract identifiers.

These constants describe the product contract. They do not claim that every
declared v1 capability is implemented in the current package release.
"""
from __future__ import annotations

from typing import Final

PRODUCT_CONTRACT_ID: Final = "veriformis.product"
PRODUCT_CONTRACT_VERSION: Final = 1

GROUP1_ACCEPTANCE_CONTRACT_ID: Final = "veriformis.acceptance.group1"
GROUP1_ACCEPTANCE_CONTRACT_VERSION: Final = 1

CANONICAL_STREAM_CONTRACT_ID: Final = "veriformis.canonical-stream"
CANONICAL_STREAM_CONTRACT_VERSION: Final = 1

DETERMINISM_PROFILE: Final = "offline-deterministic-v1"

M1_SOURCE_KINDS: Final = (
    "text",
    "code",
    "markdown",
    "docx",
)

DETERMINISTIC_V1_OBJECTIVE_KINDS: Final = (
    "full_text",
    "continuation",
    "section_reconstruction",
    "before_after_transformation",
    "structured_field",
)

V1_ROW_SCHEMA_KINDS: Final = (
    "text",
    "prompt_completion",
    "instruction_output",
    "messages",
)

VERIFORMIS_OWNED_STAGES: Final = (
    "raw_capture",
    "canonical_recovery",
    "cleaning",
    "construction",
    "curation",
    "balancing_and_splitting",
    "formatting",
    "validation",
    "seal",
)

M1_1_ACCEPTANCE_OBJECTIVE_KINDS: Final = (
    "full_text",
    "continuation",
)

GROUP1_ERROR_CODES: Final = (
    "workspace-revision-conflict",
    "workspace-corrupt",
    "workspace-locked",
    "stale-stage",
    "duplicate-identity",
    "unsupported-workspace-version",
    "source-evidence-invalid",
    "cleaning-plan-invalid",
)

__all__ = [
    "CANONICAL_STREAM_CONTRACT_ID",
    "CANONICAL_STREAM_CONTRACT_VERSION",
    "DETERMINISM_PROFILE",
    "DETERMINISTIC_V1_OBJECTIVE_KINDS",
    "GROUP1_ACCEPTANCE_CONTRACT_ID",
    "GROUP1_ACCEPTANCE_CONTRACT_VERSION",
    "GROUP1_ERROR_CODES",
    "M1_1_ACCEPTANCE_OBJECTIVE_KINDS",
    "M1_SOURCE_KINDS",
    "PRODUCT_CONTRACT_ID",
    "PRODUCT_CONTRACT_VERSION",
    "V1_ROW_SCHEMA_KINDS",
    "VERIFORMIS_OWNED_STAGES",
]
