from veriformis.contracts import (
    CONSTRUCTION_OUTPUT_CONTRACTS,
    CONSTRUCTION_SCHEMA_IDS,
    CONSTRUCTION_STAGE_SCHEMA_ID,
    DATASET_CONSTRUCTION_CONTRACT_ID,
    DATASET_CONSTRUCTION_CONTRACT_VERSION,
    GROUP2_ERROR_CODES,
    V1_CONSTRUCTION_DIAGNOSTIC_CODES,
    V1_PROMOTION_REASON_CODES,
)
from veriformis.errors import (
    ConstructionError,
    DuplicateIdentityError,
    EvidenceError,
    MissingStageInputError,
    StaleStageError,
    UnsupportedWorkspaceVersionError,
    WorkspaceCorruptError,
    WorkspaceRevisionConflict,
)


def test_dataset_construction_contract_constants_are_exact():
    assert DATASET_CONSTRUCTION_CONTRACT_ID == "veriformis.dataset-construction"
    assert DATASET_CONSTRUCTION_CONTRACT_VERSION == 1
    assert CONSTRUCTION_STAGE_SCHEMA_ID == "veriformis.construction-stage/v1"
    assert CONSTRUCTION_SCHEMA_IDS == (
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
    assert CONSTRUCTION_OUTPUT_CONTRACTS == (
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
    assert V1_CONSTRUCTION_DIAGNOSTIC_CODES == (
        "continuation-boundary-unavailable",
        "section-structure-unavailable",
        "source-chunks-unavailable",
        "structured-field-chunk-unavailable",
        "structured-field-empty-value",
        "structured-field-unavailable",
        "structured-ir-artifact-unavailable",
        "transformation-pair-empty-or-unchanged",
        "transformation-pair-unavailable",
        "mapped-label-unavailable",
        "mapped-preference-unavailable",
        "mapped-tool-trace-unavailable",
    )
    assert V1_PROMOTION_REASON_CODES == (
        "construction-integrity-v1",
        "review-approved",
        "review-rejected",
        "review-required",
    )


def test_group2_error_codes_match_their_typed_errors():
    assert tuple(
        error.code
        for error in (
            ConstructionError,
            WorkspaceRevisionConflict,
            UnsupportedWorkspaceVersionError,
            WorkspaceCorruptError,
            MissingStageInputError,
            StaleStageError,
            EvidenceError,
            DuplicateIdentityError,
        )
    ) == GROUP2_ERROR_CODES
