from pathlib import Path

from veriformis.contracts import (
    VERIFIED_EXPORT_CONTRACT_ID,
    VERIFIED_EXPORT_CONTRACT_VERSION,
    VERIFIED_EXPORT_ERROR_CODES,
    VERIFIED_EXPORT_SCHEMA_IDS,
)
from veriformis.exports.models import (
    EXPORT_CONTAINER_PROFILE_SCHEMA,
    EXPORT_CONSUMER_PROFILE_SCHEMA,
    EXPORT_DEPENDENCY_BINDING_SCHEMA,
    EXPORT_DESTINATION_FILE_BINDING_SCHEMA,
    EXPORT_FILE_PLAN_SCHEMA,
    EXPORT_MEMBERSHIP_ENTRY_SCHEMA,
    EXPORT_MEMBERSHIP_PROJECTION_SCHEMA,
    EXPORT_PLAN_SCHEMA,
    EXPORT_RECEIPT_PATH,
    EXPORT_RECEIPT_SCHEMA,
    EXPORT_VERIFICATION_SCHEMA,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportDestinationFileBinding,
    ExportFilePlan,
    ExportMembershipEntry,
    ExportMembershipProjection,
    ExportPlan,
    ExportReceipt,
    ExportVerification,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.taxonomy import (
    IMPLEMENTED_CONSUMER_PROFILES,
    IMPLEMENTED_PHYSICAL_CONTAINERS,
)


CONTRACT_PATH = (
    Path(__file__).parents[2] / "docs" / "contracts" / "verified-export-v1.md"
)

MODELS = (
    ExportContainerProfile,
    ExportConsumerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportDestinationFileBinding,
    ExportMembershipEntry,
    ExportMembershipProjection,
    ExportPlan,
    ExportReceipt,
    ExportVerification,
)


def test_verified_export_contract_constants_and_model_schemas_are_exact() -> None:
    assert VERIFIED_EXPORT_CONTRACT_ID == "veriformis.verified-export"
    assert VERIFIED_EXPORT_CONTRACT_VERSION == 1
    assert VERIFIED_EXPORT_ERROR_CODES == (
        "export-contract-invalid",
        "export-verification-invalid",
    )
    assert tuple(
        error.code for error in (ExportContractError, ExportVerificationError)
    ) == VERIFIED_EXPORT_ERROR_CODES
    assert VERIFIED_EXPORT_SCHEMA_IDS == (
        EXPORT_CONTAINER_PROFILE_SCHEMA,
        EXPORT_CONSUMER_PROFILE_SCHEMA,
        EXPORT_DEPENDENCY_BINDING_SCHEMA,
        EXPORT_FILE_PLAN_SCHEMA,
        EXPORT_DESTINATION_FILE_BINDING_SCHEMA,
        EXPORT_MEMBERSHIP_ENTRY_SCHEMA,
        EXPORT_MEMBERSHIP_PROJECTION_SCHEMA,
        EXPORT_PLAN_SCHEMA,
        EXPORT_RECEIPT_SCHEMA,
        EXPORT_VERIFICATION_SCHEMA,
    )
    assert tuple(
        model.model_fields["schema_version"].annotation.__args__[0]
        for model in MODELS
    ) == VERIFIED_EXPORT_SCHEMA_IDS
    assert EXPORT_RECEIPT_PATH == "export-receipt.json"


def test_verified_export_identity_domains_are_exact() -> None:
    assert tuple(
        (model._identity_field, model._identity_kind) for model in MODELS
    ) == (
        ("container_profile_id", "export-container"),
        ("consumer_profile_id", "export-consumer"),
        ("dependency_id", "export-dependency"),
        ("file_plan_id", "export-file-plan"),
        ("destination_file_id", "export-file"),
        ("membership_entry_id", "export-membership-entry"),
        ("membership_projection_id", "export-membership"),
        ("export_plan_id", "export-plan"),
        ("export_receipt_id", "export-receipt"),
        ("export_verification_id", "export-verification"),
    )


def test_verified_export_persisted_field_graph_is_exact() -> None:
    assert {model.__name__: tuple(model.model_fields) for model in MODELS} == {
        "ExportContainerProfile": (
            "schema_version",
            "container_profile_id",
            "container_id",
            "container_version",
            "determinism_claim",
        ),
        "ExportConsumerProfile": (
            "schema_version",
            "consumer_profile_id",
            "consumer_id",
            "profile_version",
            "accepted_row_schemas",
        ),
        "ExportDependencyBinding": (
            "schema_version",
            "dependency_id",
            "dependency_name",
            "dependency_version",
            "dependency_role",
        ),
        "ExportFilePlan": (
            "schema_version",
            "file_plan_id",
            "path",
            "role",
            "media_type",
            "membership_scope",
            "record_count",
            "semantic_content_sha256",
            "expected_sha256",
            "expected_byte_size",
        ),
        "ExportDestinationFileBinding": (
            "schema_version",
            "destination_file_id",
            "file_plan_id",
            "path",
            "role",
            "media_type",
            "membership_scope",
            "record_count",
            "semantic_content_sha256",
            "sha256",
            "byte_size",
        ),
        "ExportMembershipEntry": (
            "schema_version",
            "membership_entry_id",
            "record_id",
            "row_id",
            "provenance_id",
            "assignment_id",
            "leakage_group_id",
            "partition",
            "ordinal",
            "payload_sha256",
        ),
        "ExportMembershipProjection": (
            "schema_version",
            "membership_projection_id",
            "split_result_id",
            "row_set_id",
            "row_schema",
            "assignment_projection_sha256",
            "entries",
        ),
        "ExportPlan": (
            "schema_version",
            "export_plan_id",
            "source_bundle_id",
            "source_manifest_sha256",
            "source_content_root_sha256",
            "source_verification_id",
            "source_trust_policy",
            "source_trust_grade",
            "dataset_snapshot_id",
            "validation_report_id",
            "finished_dataset_plan_id",
            "recipe_id",
            "objective_id",
            "construction_result_id",
            "curation_result_id",
            "serialization_plan_id",
            "split_result_id",
            "row_set_id",
            "source_ids",
            "row_schema",
            "loss_policy",
            "derivative_policy",
            "container_profile",
            "consumer_profile",
            "dependencies",
            "membership_projection",
            "file_plans",
            "overwrite_policy",
        ),
        "ExportReceipt": (
            "schema_version",
            "export_receipt_id",
            "export_plan_id",
            "export_plan",
            "output_content_root_sha256",
            "files",
        ),
        "ExportVerification": (
            "schema_version",
            "export_verification_id",
            "export_receipt_id",
            "export_plan_id",
            "source_bundle_id",
            "source_manifest_sha256",
            "source_content_root_sha256",
            "source_verification_id",
            "source_trust_grade",
            "dataset_snapshot_id",
            "validation_report_id",
            "split_result_id",
            "row_set_id",
            "row_schema",
            "container_profile_id",
            "consumer_profile_id",
            "membership_projection_id",
            "determinism_claim",
            "output_content_root_sha256",
            "output_file_count",
            "declared_record_count",
        ),
    }


def test_normative_contract_names_every_schema_identity_and_current_boundary() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")

    assert f"**Contract ID:** `{VERIFIED_EXPORT_CONTRACT_ID}`" in contract
    assert f"**Contract version:** `{VERIFIED_EXPORT_CONTRACT_VERSION}`" in contract
    for schema_id in VERIFIED_EXPORT_SCHEMA_IDS:
        assert f"`{schema_id}`" in contract
    for identity_kind in (
        "export-container",
        "export-consumer",
        "export-dependency",
        "export-file-plan",
        "export-file",
        "export-membership-entry",
        "export-membership",
        "export-plan",
        "export-receipt",
        "export-verification",
    ):
        assert f"`{identity_kind}`" in contract

    assert "Phase 4.2 implementation establishes exact models" in contract
    assert "default `source_trust_policy` is exactly" in contract
    assert "absence fails before the source" in contract
    assert "fails without retry, downgrade, trimming, or coercion" in contract
    assert "records the observed grade, not the requested policy" in contract
    assert "`ExportService.create_plan` is the only implemented" in contract
    assert "derive every source fact" in contract
    assert "`ExportService.validate_derivative_membership` accepts exactly" in contract
    assert "normalized in-memory semantic evidence" in contract
    assert "arbitrary destination bytes encode the checked semantics" in contract
    assert "`ExportService.publish` accepts one strict" in contract
    assert "invoke the renderer twice before destination access" in contract
    assert "For `semantic_content_only`, exact bytes" in contract
    assert "descriptor-reread staged bytes" in contract
    assert "MUST NOT be used as its own external trust anchor" in contract
    assert "There is no cancellation checkpoint after promotion" in contract
    assert "schemas contain no rerender count" in contract
    assert "`PipelineService` export operations" in contract
    assert "is not a supported product container" in contract
    assert "MUST NOT add a generic export container" in contract
    assert "no trailing line feed" in contract
    assert "duplicate JSON keys" in contract
    assert "NFKC plus case folding" in contract
    assert "preserve_membership_and_semantics" in contract
    assert "leakage group that appears in both train and evaluation" in contract
    assert "source_verification_id` MUST equal that recomputed identity" in contract
    assert "positive `output_file_count`" in contract
    assert "export-receipt.json" in contract
    assert "veriformis.export-assignment-projection/v1" in contract
    assert "veriformis.export-content-root/v1" in contract
    assert "`record_id`, `assignment_id`" in contract
    assert "complete `ExportDestinationFileBinding` JSON object" in contract


def test_phase5_generic_containers_are_the_only_promoted_exports() -> None:
    assert IMPLEMENTED_PHYSICAL_CONTAINERS == (
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "split-jsonl-directory",
        "json",
        "constrained-csv",
    )
    assert IMPLEMENTED_CONSUMER_PROFILES == (
        "veriformis-canonical-v1",
        "aptus-handoff-v1",
    )
