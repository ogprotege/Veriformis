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

DATASET_CONSTRUCTION_CONTRACT_ID: Final = "veriformis.dataset-construction"
DATASET_CONSTRUCTION_CONTRACT_VERSION: Final = 1

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

V1_CONSTRUCTION_DIAGNOSTIC_CODES: Final = (
    "continuation-boundary-unavailable",
    "section-structure-unavailable",
    "source-chunks-unavailable",
    "structured-field-chunk-unavailable",
    "structured-field-empty-value",
    "structured-field-unavailable",
    "structured-ir-artifact-unavailable",
    "transformation-pair-empty-or-unchanged",
    "transformation-pair-unavailable",
)

V1_PROMOTION_REASON_CODES: Final = (
    "construction-integrity-v1",
    "review-approved",
    "review-rejected",
    "review-required",
)

CONSTRUCTION_SCHEMA_IDS: Final = (
    "veriformis.training-objective/v1",
    "veriformis.dataset-recipe/v1",
    "veriformis.segmentation-policy/v1",
    "veriformis.construction-pass/v1",
    "veriformis.field-evidence/v1",
    "veriformis.ir-field-evidence/v1",
    "veriformis.candidate-record/v1",
    "veriformis.promotion-decision/v1",
    "veriformis.review-evidence/v1",
    "veriformis.dataset-record/v1",
    "veriformis.construction-diagnostic/v1",
    "veriformis.construction-result/v1",
)

CONSTRUCTION_STAGE_SCHEMA_ID: Final = "veriformis.construction-stage/v1"

CONSTRUCTION_OUTPUT_CONTRACTS: Final = (
    (
        "recipe",
        "dataset-recipe",
        "veriformis.construction.recipe",
        "1",
    ),
    (
        "result",
        "construction-result",
        "veriformis.construction.result",
        "1",
    ),
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

GROUP2_ERROR_CODES: Final = (
    "construction-invalid",
    "workspace-revision-conflict",
    "unsupported-workspace-version",
    "workspace-corrupt",
    "missing-stage-input",
    "stale-stage",
    "source-evidence-invalid",
    "duplicate-identity",
)

__all__ = [
    "CANONICAL_STREAM_CONTRACT_ID",
    "CANONICAL_STREAM_CONTRACT_VERSION",
    "CONSTRUCTION_OUTPUT_CONTRACTS",
    "CONSTRUCTION_SCHEMA_IDS",
    "CONSTRUCTION_STAGE_SCHEMA_ID",
    "DATASET_CONSTRUCTION_CONTRACT_ID",
    "DATASET_CONSTRUCTION_CONTRACT_VERSION",
    "DETERMINISM_PROFILE",
    "DETERMINISTIC_V1_OBJECTIVE_KINDS",
    "GROUP1_ACCEPTANCE_CONTRACT_ID",
    "GROUP1_ACCEPTANCE_CONTRACT_VERSION",
    "GROUP1_ERROR_CODES",
    "GROUP2_ERROR_CODES",
    "M1_1_ACCEPTANCE_OBJECTIVE_KINDS",
    "M1_SOURCE_KINDS",
    "PRODUCT_CONTRACT_ID",
    "PRODUCT_CONTRACT_VERSION",
    "V1_CONSTRUCTION_DIAGNOSTIC_CODES",
    "V1_PROMOTION_REASON_CODES",
    "V1_ROW_SCHEMA_KINDS",
    "VERIFORMIS_OWNED_STAGES",
]
