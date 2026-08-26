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

FINISHED_DATASET_CONTRACT_ID: Final = "veriformis.finished-dataset"
FINISHED_DATASET_CONTRACT_VERSION: Final = 1

TAXONOMY_CONTRACT_ID: Final = "veriformis.taxonomy"
TAXONOMY_CONTRACT_VERSION: Final = 1
TAXONOMY_SCHEMA_ID: Final = "veriformis.taxonomy/v1"

GOAL_CATALOG_CONTRACT_ID: Final = "veriformis.goal-catalog"
GOAL_CATALOG_CONTRACT_VERSION: Final = 1
GOAL_CATALOG_SCHEMA_ID: Final = "veriformis.goal-catalog/v1"

RECIPE_PRESET_CONTRACT_ID: Final = "veriformis.recipe-preset"
RECIPE_PRESET_CONTRACT_VERSION: Final = 1
RECIPE_PRESET_SCHEMA_ID: Final = "veriformis.recipe-preset/v1"

INPUT_MODE_CONTRACT_ID: Final = "veriformis.input-mode"
INPUT_MODE_CONTRACT_VERSION: Final = 1
INPUT_MODE_SCHEMA_ID: Final = "veriformis.input-mode-discovery/v1"

MAPPING_CONTRACT_ID: Final = "veriformis.row-mapping"
MAPPING_CONTRACT_VERSION: Final = 1
MAPPING_DISCOVERY_SCHEMA_ID: Final = "veriformis.mapping-contract-discovery/v1"

PROFILE_ADMISSION_CONTRACT_ID: Final = "veriformis.consumer-profile-admission"
PROFILE_ADMISSION_CONTRACT_VERSION: Final = 1
PROFILE_ADMISSION_SCHEMA_ID: Final = "veriformis.profile-admission-discovery/v1"
CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID: Final = (
    "veriformis.candidate-profile-admission-discovery/v1"
)

COLUMNAR_SCHEMA_CONTRACT_ID: Final = "veriformis.columnar-schema-pin"
COLUMNAR_SCHEMA_CONTRACT_VERSION: Final = 1
COLUMNAR_SCHEMA_SCHEMA_ID: Final = "veriformis.columnar-schema-discovery/v1"

COLUMNAR_FINGERPRINT_CONTRACT_ID: Final = "veriformis.columnar-semantic-fingerprint"
COLUMNAR_FINGERPRINT_CONTRACT_VERSION: Final = 1
COLUMNAR_FINGERPRINT_SCHEMA_ID: Final = "veriformis.columnar-semantic-fingerprint/v1"

OCR_RECOVERY_IDENTITY_CONTRACT_ID: Final = "veriformis.ocr-recovery-identity"
OCR_RECOVERY_IDENTITY_CONTRACT_VERSION: Final = 1
OCR_RECOVERY_IDENTITY_SCHEMA_ID: Final = "veriformis.ocr-recovery-identity/v1"

QUALITY_REPORT_CONTRACT_ID: Final = "veriformis.quality-report"
QUALITY_REPORT_CONTRACT_VERSION: Final = 1
QUALITY_REPORT_SCHEMA_ID: Final = "veriformis.quality-report/v1"

REVIEW_CONTRACT_ID: Final = "veriformis.review"
REVIEW_CONTRACT_VERSION: Final = 1
REVIEW_BUNDLE_SCHEMA_ID: Final = "veriformis.review-bundle/v1"
REVIEW_PACKET_SCHEMA_ID: Final = "veriformis.review-packet/v1"

SCALE_CORPUS_CONTRACT_ID: Final = "veriformis.scale-corpus"
SCALE_CORPUS_CONTRACT_VERSION: Final = 1
SCALE_CORPUS_SPEC_SCHEMA_ID: Final = "veriformis.scale-corpus-spec/v1"
SCALE_CORPUS_SCHEMA_ID: Final = "veriformis.scale-corpus/v1"
SCALE_BASELINE_REPORT_SCHEMA_ID: Final = "veriformis.scale-baseline-report/v1"

VERIFIED_EXPORT_CONTRACT_ID: Final = "veriformis.verified-export"
VERIFIED_EXPORT_CONTRACT_VERSION: Final = 1

VERIFIED_EXPORT_SCHEMA_IDS: Final = (
    "veriformis.export-container-profile/v1",
    "veriformis.export-consumer-profile/v1",
    "veriformis.export-dependency-binding/v1",
    "veriformis.export-file-plan/v1",
    "veriformis.export-destination-file-binding/v1",
    "veriformis.export-membership-entry/v1",
    "veriformis.export-membership-projection/v1",
    "veriformis.export-plan/v1",
    "veriformis.export-receipt/v1",
    "veriformis.export-verification/v1",
)

VERIFIED_EXPORT_ERROR_CODES: Final = (
    "export-contract-invalid",
    "export-verification-invalid",
)

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
MAPPING_STAGE_SCHEMA_ID: Final = "veriformis.mapping-stage/v1"
CURATION_STAGE_SCHEMA_ID: Final = "veriformis.curation-stage/v1"
SPLIT_STAGE_SCHEMA_ID: Final = "veriformis.split-stage/v1"
FORMAT_STAGE_SCHEMA_ID: Final = "veriformis.finished-format-stage/v1"
VALIDATION_STAGE_SCHEMA_ID: Final = "veriformis.dataset-validation-stage/v1"
SEAL_STAGE_SCHEMA_ID: Final = "veriformis.finished-seal-stage/v1"

V1_DATASET_PARTITIONS: Final = ("train", "evaluation")

V1_CURATION_REASON_CODES: Final = (
    "conflicting-target",
    "exact-duplicate",
    "primary-source-cap",
    "quality-passed",
    "target-too-short",
)

V1_QUALITY_FINDING_CODES: Final = (
    "conflicting-target",
    "exact-duplicate",
    "primary-source-cap",
    "target-too-short",
)

V1_COVERAGE_BLOCKER_CODES: Final = (
    "no-constructed-candidates",
    "no-dataset-records",
    "no-included-contribution",
)

V1_FINISHED_DATASET_GATES: Final = (
    "construction-replay",
    "record-lifecycle",
    "curation",
    "deduplication",
    "quality",
    "balance",
    "coverage",
    "split",
    "leakage",
    "row-binding",
    "objective",
    "schema",
    "encoding",
    "masking",
    "partition-nonempty",
    "aptus-row-shape",
    "snapshot",
)

FINISHED_DATASET_SCHEMA_IDS: Final = (
    "veriformis.finished-dataset-plan/v1",
    "veriformis.curation-policy/v1",
    "veriformis.quality-finding/v1",
    "veriformis.curation-decision/v1",
    "veriformis.coverage-ledger-entry/v1",
    "veriformis.coverage-ledger/v1",
    "veriformis.curation-result/v1",
    "veriformis.exact-record-fingerprint/v1",
    "veriformis.split-policy/v1",
    "veriformis.leakage-group/v1",
    "veriformis.record-assignment/v1",
    "veriformis.split-result/v1",
    "veriformis.serialization-plan/v1",
    "veriformis.product-row/v1",
    "veriformis.row-provenance/v1",
    "veriformis.row-set/v1",
    "veriformis.snapshot-artifact-binding/v1",
    "veriformis.snapshot-file-binding/v1",
    "veriformis.snapshot-validator-binding/v1",
    "veriformis.dataset-snapshot/v1",
    "veriformis.dataset-gate-result/v1",
    "veriformis.dataset-validation-report/v1",
    "veriformis.finished-bundle-file/v1",
    "veriformis.finished-bundle-manifest/v1",
    "veriformis.bundle-attestation/v1",
    "veriformis.bundle-verification/v1",
)

V1_BUNDLE_VERIFICATION_GRADES: Final = (
    "self_consistent",
    "external_digest",
)

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

FINISHED_DATASET_OUTPUT_CONTRACTS: Final = (
    ("curate", "plan", "finished-dataset-plan", "veriformis.curation.plan", "1"),
    (
        "curate",
        "result",
        "curation-result",
        "veriformis.curation.result",
        "1",
    ),
    ("split", "result", "split-result", "veriformis.splitting.result", "1"),
    (
        "format",
        "row-set",
        "formatted-row-set",
        "veriformis.dataset-serializer.row-set",
        "1",
    ),
    (
        "format",
        "train",
        "training-partition",
        "veriformis.dataset-serializer.train",
        "1",
    ),
    (
        "format",
        "evaluation",
        "evaluation-partition",
        "veriformis.dataset-serializer.evaluation",
        "1",
    ),
    (
        "format",
        "provenance",
        "row-provenance",
        "veriformis.dataset-serializer.provenance",
        "1",
    ),
    (
        "validate",
        "snapshot",
        "dataset-snapshot",
        "veriformis.dataset-validation.snapshot",
        "1",
    ),
    (
        "validate",
        "report",
        "dataset-validation-report",
        "veriformis.dataset-validation.report",
        "1",
    ),
    (
        "seal",
        "manifest",
        "finished-bundle-manifest",
        "veriformis.bundle.manifest",
        "1",
    ),
    (
        "seal",
        "attestation",
        "finished-bundle-attestation",
        "veriformis.bundle.attestation",
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

GROUP3_ERROR_CODES: Final = (
    "curation-invalid",
    "split-invalid",
    "serialization-invalid",
    "dataset-validation-invalid",
    "gate-failure",
    "seal-invalid",
    "bundle-invalid",
    "artifact-digest-mismatch",
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
    "MAPPING_STAGE_SCHEMA_ID",
    "CURATION_STAGE_SCHEMA_ID",
    "DATASET_CONSTRUCTION_CONTRACT_ID",
    "DATASET_CONSTRUCTION_CONTRACT_VERSION",
    "DETERMINISM_PROFILE",
    "DETERMINISTIC_V1_OBJECTIVE_KINDS",
    "GOAL_CATALOG_CONTRACT_ID",
    "GOAL_CATALOG_CONTRACT_VERSION",
    "GOAL_CATALOG_SCHEMA_ID",
    "INPUT_MODE_CONTRACT_ID",
    "INPUT_MODE_CONTRACT_VERSION",
    "INPUT_MODE_SCHEMA_ID",
    "MAPPING_CONTRACT_ID",
    "MAPPING_CONTRACT_VERSION",
    "MAPPING_DISCOVERY_SCHEMA_ID",
    "PROFILE_ADMISSION_CONTRACT_ID",
    "PROFILE_ADMISSION_CONTRACT_VERSION",
    "PROFILE_ADMISSION_SCHEMA_ID",
    "CANDIDATE_PROFILE_ADMISSION_SCHEMA_ID",
    "COLUMNAR_SCHEMA_CONTRACT_ID",
    "COLUMNAR_SCHEMA_CONTRACT_VERSION",
    "COLUMNAR_SCHEMA_SCHEMA_ID",
    "COLUMNAR_FINGERPRINT_CONTRACT_ID",
    "COLUMNAR_FINGERPRINT_CONTRACT_VERSION",
    "COLUMNAR_FINGERPRINT_SCHEMA_ID",
    "OCR_RECOVERY_IDENTITY_CONTRACT_ID",
    "OCR_RECOVERY_IDENTITY_CONTRACT_VERSION",
    "OCR_RECOVERY_IDENTITY_SCHEMA_ID",
    "QUALITY_REPORT_CONTRACT_ID",
    "QUALITY_REPORT_CONTRACT_VERSION",
    "QUALITY_REPORT_SCHEMA_ID",
    "REVIEW_BUNDLE_SCHEMA_ID",
    "REVIEW_CONTRACT_ID",
    "REVIEW_CONTRACT_VERSION",
    "REVIEW_PACKET_SCHEMA_ID",
    "SCALE_BASELINE_REPORT_SCHEMA_ID",
    "SCALE_CORPUS_CONTRACT_ID",
    "SCALE_CORPUS_CONTRACT_VERSION",
    "SCALE_CORPUS_SCHEMA_ID",
    "SCALE_CORPUS_SPEC_SCHEMA_ID",
    "RECIPE_PRESET_CONTRACT_ID",
    "RECIPE_PRESET_CONTRACT_VERSION",
    "RECIPE_PRESET_SCHEMA_ID",
    "FINISHED_DATASET_CONTRACT_ID",
    "FINISHED_DATASET_CONTRACT_VERSION",
    "FINISHED_DATASET_OUTPUT_CONTRACTS",
    "FINISHED_DATASET_SCHEMA_IDS",
    "FORMAT_STAGE_SCHEMA_ID",
    "GROUP1_ACCEPTANCE_CONTRACT_ID",
    "GROUP1_ACCEPTANCE_CONTRACT_VERSION",
    "GROUP1_ERROR_CODES",
    "GROUP2_ERROR_CODES",
    "GROUP3_ERROR_CODES",
    "M1_1_ACCEPTANCE_OBJECTIVE_KINDS",
    "M1_SOURCE_KINDS",
    "PRODUCT_CONTRACT_ID",
    "PRODUCT_CONTRACT_VERSION",
    "SEAL_STAGE_SCHEMA_ID",
    "SPLIT_STAGE_SCHEMA_ID",
    "TAXONOMY_CONTRACT_ID",
    "TAXONOMY_CONTRACT_VERSION",
    "TAXONOMY_SCHEMA_ID",
    "VALIDATION_STAGE_SCHEMA_ID",
    "V1_CONSTRUCTION_DIAGNOSTIC_CODES",
    "V1_BUNDLE_VERIFICATION_GRADES",
    "V1_COVERAGE_BLOCKER_CODES",
    "V1_CURATION_REASON_CODES",
    "V1_DATASET_PARTITIONS",
    "V1_FINISHED_DATASET_GATES",
    "V1_PROMOTION_REASON_CODES",
    "V1_QUALITY_FINDING_CODES",
    "V1_ROW_SCHEMA_KINDS",
    "VERIFIED_EXPORT_CONTRACT_ID",
    "VERIFIED_EXPORT_CONTRACT_VERSION",
    "VERIFIED_EXPORT_ERROR_CODES",
    "VERIFIED_EXPORT_SCHEMA_IDS",
    "VERIFORMIS_OWNED_STAGES",
]
