"""Adversarial contract tests for verified-export v1 persisted models."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from pydantic import BaseModel, ValidationError

from veriformis.bundle import VerificationResult
from veriformis.contracts import VERIFIED_EXPORT_SCHEMA_IDS
from veriformis.errors import ExportContractError, ExportVerificationError
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
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest


def _id(kind: str, label: str) -> str:
    return derive_id(kind, {"fixture": label})


def _sha(label: str) -> str:
    return sha256_digest(f"verified-export-fixture:{label}")


def _reidentify(
    value: dict[str, Any],
    *,
    identity_field: str,
    identity_kind: str,
) -> dict[str, Any]:
    value[identity_field] = derive_id(
        identity_kind,
        {key: item for key, item in value.items() if key != identity_field},
    )
    return value


def _entry_kwargs(entry: ExportMembershipEntry) -> dict[str, Any]:
    return {
        "record_id": entry.record_id,
        "row_id": entry.row_id,
        "provenance_id": entry.provenance_id,
        "assignment_id": entry.assignment_id,
        "leakage_group_id": entry.leakage_group_id,
        "partition": entry.partition,
        "ordinal": entry.ordinal,
        "payload_sha256": entry.payload_sha256,
    }


def _plan_kwargs(plan: ExportPlan) -> dict[str, Any]:
    return {
        "source_bundle_id": plan.source_bundle_id,
        "source_manifest_sha256": plan.source_manifest_sha256,
        "source_content_root_sha256": plan.source_content_root_sha256,
        "source_verification_id": plan.source_verification_id,
        "source_trust_policy": plan.source_trust_policy,
        "source_trust_grade": plan.source_trust_grade,
        "dataset_snapshot_id": plan.dataset_snapshot_id,
        "validation_report_id": plan.validation_report_id,
        "finished_dataset_plan_id": plan.finished_dataset_plan_id,
        "recipe_id": plan.recipe_id,
        "objective_id": plan.objective_id,
        "construction_result_id": plan.construction_result_id,
        "curation_result_id": plan.curation_result_id,
        "serialization_plan_id": plan.serialization_plan_id,
        "split_result_id": plan.split_result_id,
        "row_set_id": plan.row_set_id,
        "source_ids": plan.source_ids,
        "row_schema": plan.row_schema,
        "container_profile": plan.container_profile,
        "consumer_profile": plan.consumer_profile,
        "dependencies": plan.dependencies,
        "membership_projection": plan.membership_projection,
        "file_plans": plan.file_plans,
    }


def _source_verification_id(
    plan: ExportPlan,
    *,
    trust_grade: Literal["external_digest", "self_consistent"],
) -> str:
    return VerificationResult.create(
        bundle_id=plan.source_bundle_id,
        dataset_snapshot_id=plan.dataset_snapshot_id,
        validation_report_id=plan.validation_report_id,
        manifest_sha256=plan.source_manifest_sha256,
        content_root_sha256=plan.source_content_root_sha256,
        trust_grade=trust_grade,
        payload_file_count=4,
        declared_record_count=plan.membership_projection.total_record_count,
    ).verification_id


@dataclass(frozen=True)
class ExportGraph:
    container: ExportContainerProfile
    consumer: ExportConsumerProfile
    dependencies: tuple[ExportDependencyBinding, ...]
    file_plans: tuple[ExportFilePlan, ...]
    destination_files: tuple[ExportDestinationFileBinding, ...]
    entries: tuple[ExportMembershipEntry, ...]
    projection: ExportMembershipProjection
    plan: ExportPlan
    receipt: ExportReceipt
    verification: ExportVerification

    @property
    def models(self) -> tuple[BaseModel, ...]:
        """Return one valid instance of every one of the ten v1 schemas."""
        return (
            self.container,
            self.consumer,
            self.dependencies[0],
            self.file_plans[0],
            self.destination_files[0],
            self.entries[0],
            self.projection,
            self.plan,
            self.receipt,
            self.verification,
        )


@pytest.fixture
def graph() -> ExportGraph:
    container = ExportContainerProfile.create(
        container_id="test-directory",
        container_version=1,
        determinism_claim="portable_exact_bytes",
    )
    consumer = ExportConsumerProfile.create(
        consumer_id="test-consumer",
        profile_version=1,
        accepted_row_schemas=("prompt_completion", "messages"),
    )
    dependencies = tuple(
        sorted(
            (
                ExportDependencyBinding.create(
                    dependency_name="renderer-beta",
                    dependency_version="rélease-2",
                    dependency_role="renderer",
                ),
                ExportDependencyBinding.create(
                    dependency_name="renderer-alpha",
                    dependency_version="1.0.0",
                    dependency_role="runtime",
                ),
            ),
            key=lambda item: item.dependency_id,
        )
    )

    # Deliberately use reverse identity order. Membership is authoritative
    # partition/ordinal order, not an identity-sorted registry.
    record_ids = tuple(
        sorted((_id("rec", f"record-{index}") for index in range(3)), reverse=True)
    )
    row_ids = tuple(
        sorted((_id("row", f"row-{index}") for index in range(3)), reverse=True)
    )
    provenance_ids = tuple(
        sorted((_id("prv", f"provenance-{index}") for index in range(3)), reverse=True)
    )
    assignment_ids = tuple(
        sorted((_id("asg", f"assignment-{index}") for index in range(3)), reverse=True)
    )
    train_group = _id("lkg", "shared-train-group")
    evaluation_group = _id("lkg", "evaluation-group")
    entries = (
        ExportMembershipEntry.create(
            record_id=record_ids[0],
            row_id=row_ids[0],
            provenance_id=provenance_ids[0],
            assignment_id=assignment_ids[0],
            leakage_group_id=train_group,
            partition="train",
            ordinal=0,
            payload_sha256=_sha("payload-0"),
        ),
        ExportMembershipEntry.create(
            record_id=record_ids[1],
            row_id=row_ids[1],
            provenance_id=provenance_ids[1],
            assignment_id=assignment_ids[1],
            leakage_group_id=train_group,
            partition="train",
            ordinal=1,
            payload_sha256=_sha("payload-1"),
        ),
        ExportMembershipEntry.create(
            record_id=record_ids[2],
            row_id=row_ids[2],
            provenance_id=provenance_ids[2],
            assignment_id=assignment_ids[2],
            leakage_group_id=evaluation_group,
            partition="evaluation",
            ordinal=0,
            payload_sha256=_sha("payload-2"),
        ),
    )
    split_result_id = _id("spt", "split")
    row_set_id = _id("rws", "row-set")
    projection = ExportMembershipProjection.create(
        split_result_id=split_result_id,
        row_set_id=row_set_id,
        row_schema="prompt_completion",
        entries=entries,
    )

    train_bytes = (
        b'{"completion":"b","prompt":"a"}\n'
        b'{"completion":"d","prompt":"c"}\n'
    )
    evaluation_bytes = b'{"completion":"f","prompt":"e"}\n'
    file_plans = tuple(
        sorted(
            (
                ExportFilePlan.create(
                    path="data/train.jsonl",
                    role="training-partition",
                    media_type="application/jsonl",
                    membership_scope="train",
                    record_count=2,
                    semantic_content_sha256=None,
                    expected_sha256=sha256_digest(train_bytes),
                    expected_byte_size=len(train_bytes),
                ),
                ExportFilePlan.create(
                    path="data/evaluation.jsonl",
                    role="evaluation-partition",
                    media_type="application/jsonl",
                    membership_scope="evaluation",
                    record_count=1,
                    semantic_content_sha256=None,
                    expected_sha256=sha256_digest(evaluation_bytes),
                    expected_byte_size=len(evaluation_bytes),
                ),
            ),
            key=lambda item: item.path,
        )
    )
    data_by_path = {
        "data/evaluation.jsonl": evaluation_bytes,
        "data/train.jsonl": train_bytes,
    }
    destination_files = tuple(
        ExportDestinationFileBinding.create(
            file_plan_id=file_plan.file_plan_id,
            path=file_plan.path,
            role=file_plan.role,
            media_type=file_plan.media_type,
            membership_scope=file_plan.membership_scope,
            record_count=file_plan.record_count,
            semantic_content_sha256=None,
            sha256=sha256_digest(data_by_path[file_plan.path]),
            byte_size=len(data_by_path[file_plan.path]),
        )
        for file_plan in file_plans
    )
    source_bundle_id = _id("bundle", "source-bundle")
    source_manifest_sha256 = _sha("source-manifest")
    source_content_root_sha256 = _sha("source-content-root")
    dataset_snapshot_id = _id("dss", "snapshot")
    validation_report_id = _id("dvr", "validation")
    source_verification_id = VerificationResult.create(
        bundle_id=source_bundle_id,
        dataset_snapshot_id=dataset_snapshot_id,
        validation_report_id=validation_report_id,
        manifest_sha256=source_manifest_sha256,
        content_root_sha256=source_content_root_sha256,
        trust_grade="external_digest",
        payload_file_count=4,
        declared_record_count=len(entries),
    ).verification_id
    plan = ExportPlan.create(
        source_bundle_id=source_bundle_id,
        source_manifest_sha256=source_manifest_sha256,
        source_content_root_sha256=source_content_root_sha256,
        source_verification_id=source_verification_id,
        source_trust_policy="require_external_digest",
        source_trust_grade="external_digest",
        dataset_snapshot_id=dataset_snapshot_id,
        validation_report_id=validation_report_id,
        finished_dataset_plan_id=_id("fdp", "finished-plan"),
        recipe_id=_id("rcp", "recipe"),
        objective_id=_id("obj", "objective"),
        construction_result_id=_id("run", "construction"),
        curation_result_id=_id("cur", "curation"),
        serialization_plan_id=_id("srp", "serialization"),
        split_result_id=split_result_id,
        row_set_id=row_set_id,
        source_ids=(_id("src", "source-b"), _id("src", "source-a")),
        row_schema="prompt_completion",
        container_profile=container,
        consumer_profile=consumer,
        dependencies=tuple(reversed(dependencies)),
        membership_projection=projection,
        file_plans=tuple(reversed(file_plans)),
    )
    receipt = ExportReceipt.create(
        export_plan=plan,
        files=tuple(reversed(destination_files)),
    )
    verification = ExportVerification.create(receipt=receipt)
    return ExportGraph(
        container=container,
        consumer=consumer,
        dependencies=dependencies,
        file_plans=file_plans,
        destination_files=destination_files,
        entries=entries,
        projection=projection,
        plan=plan,
        receipt=receipt,
        verification=verification,
    )


IDENTITY_CONTRACTS: dict[type[BaseModel], tuple[str, str]] = {
    ExportContainerProfile: ("container_profile_id", "export-container"),
    ExportConsumerProfile: ("consumer_profile_id", "export-consumer"),
    ExportDependencyBinding: ("dependency_id", "export-dependency"),
    ExportFilePlan: ("file_plan_id", "export-file-plan"),
    ExportDestinationFileBinding: ("destination_file_id", "export-file"),
    ExportMembershipEntry: ("membership_entry_id", "export-membership-entry"),
    ExportMembershipProjection: ("membership_projection_id", "export-membership"),
    ExportPlan: ("export_plan_id", "export-plan"),
    ExportReceipt: ("export_receipt_id", "export-receipt"),
    ExportVerification: ("export_verification_id", "export-verification"),
}


def test_schema_registry_error_codes_and_exact_fields_are_pinned() -> None:
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
    assert ExportContractError.code == "export-contract-invalid"
    assert ExportVerificationError.code == "export-verification-invalid"
    assert set(ExportContainerProfile.model_fields) == {
        "schema_version",
        "container_profile_id",
        "container_id",
        "container_version",
        "determinism_claim",
    }
    assert set(ExportConsumerProfile.model_fields) == {
        "schema_version",
        "consumer_profile_id",
        "consumer_id",
        "profile_version",
        "accepted_row_schemas",
    }
    assert set(ExportDependencyBinding.model_fields) == {
        "schema_version",
        "dependency_id",
        "dependency_name",
        "dependency_version",
        "dependency_role",
    }
    assert set(ExportFilePlan.model_fields) == {
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
    }
    assert set(ExportDestinationFileBinding.model_fields) == {
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
    }
    assert set(ExportMembershipEntry.model_fields) == {
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
    }
    assert set(ExportMembershipProjection.model_fields) == {
        "schema_version",
        "membership_projection_id",
        "split_result_id",
        "row_set_id",
        "row_schema",
        "assignment_projection_sha256",
        "entries",
    }
    assert set(ExportPlan.model_fields) == {
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
    }
    assert set(ExportReceipt.model_fields) == {
        "schema_version",
        "export_receipt_id",
        "export_plan_id",
        "export_plan",
        "output_content_root_sha256",
        "files",
    }
    assert set(ExportVerification.model_fields) == {
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
    }


def test_every_model_has_one_canonical_round_trip_and_recomputed_identity(
    graph: ExportGraph,
) -> None:
    for model in graph.models:
        model_type = type(model)
        canonical = model.canonical_bytes()
        assert canonical == lossless_json_bytes(model.model_dump(mode="json"))
        loaded = model_type.from_json_bytes(canonical)
        assert loaded == model
        assert loaded.canonical_bytes() == canonical

        identity_field, identity_kind = IDENTITY_CONTRACTS[model_type]
        value = model.model_dump(mode="json")
        expected = derive_id(
            identity_kind,
            {key: item for key, item in value.items() if key != identity_field},
        )
        assert value[identity_field] == expected

        forged = deepcopy(value)
        forged[identity_field] = _id(identity_kind, f"forged-{model_type.__name__}")
        with pytest.raises(ExportVerificationError, match="identity mismatch"):
            model_type.from_json_bytes(lossless_json_bytes(forged))

    with pytest.raises(ValidationError, match="frozen"):
        graph.container.container_version = 2


def test_every_model_rejects_each_missing_field_and_unknown_fields(
    graph: ExportGraph,
) -> None:
    for model in graph.models:
        model_type = type(model)
        original = model.model_dump(mode="json")
        for field_name in tuple(original):
            missing = deepcopy(original)
            del missing[field_name]
            with pytest.raises(ExportVerificationError, match="missing"):
                model_type.from_json_bytes(lossless_json_bytes(missing))

        extra = deepcopy(original)
        extra["unexpected_runtime_path"] = "/private/tmp/not-portable"
        with pytest.raises(ExportVerificationError, match="extra"):
            model_type.from_json_bytes(lossless_json_bytes(extra))


def test_every_model_rejects_unsupported_schema_versions(graph: ExportGraph) -> None:
    for model in graph.models:
        model_type = type(model)
        value = model.model_dump(mode="json")
        value["schema_version"] = value["schema_version"].replace("/v1", "/v999")
        with pytest.raises(ExportVerificationError):
            model_type.from_json_bytes(lossless_json_bytes(value))

    nested = graph.receipt.model_dump(mode="json")
    nested["export_plan"]["membership_projection"]["entries"][0][
        "schema_version"
    ] = "veriformis.export-membership-entry/v999"
    with pytest.raises(ExportVerificationError):
        ExportReceipt.from_json_bytes(lossless_json_bytes(nested))


def test_duplicate_json_keys_fail_at_root_and_nested_depth(graph: ExportGraph) -> None:
    for model in graph.models:
        model_type = type(model)
        canonical = model.canonical_bytes()
        schema = model.model_dump(mode="json")["schema_version"]
        duplicate = (
            b'{"schema_version":'
            + json.dumps(schema).encode("utf-8")
            + b","
            + canonical[1:]
        )
        with pytest.raises(ExportVerificationError, match="duplicate key"):
            model_type.from_json_bytes(duplicate)

    receipt = graph.receipt.canonical_bytes()
    nested_duplicate = receipt.replace(
        b'"path":"data/evaluation.jsonl"',
        b'"path":"data/evaluation.jsonl","path":"data/evaluation.jsonl"',
        1,
    )
    assert nested_duplicate != receipt
    with pytest.raises(ExportVerificationError, match="duplicate key"):
        ExportReceipt.from_json_bytes(nested_duplicate)


def test_float_nonfinite_and_bool_as_int_are_rejected_recursively(
    graph: ExportGraph,
) -> None:
    for model in graph.models:
        canonical = model.canonical_bytes()
        for token in (b"1.0", b"1e0", b"NaN", b"Infinity", b"-Infinity"):
            malformed = canonical[:-1] + b',"numeric_probe":' + token + b"}"
            with pytest.raises(ExportVerificationError):
                type(model).from_json_bytes(malformed)

    numeric_fields = (
        (graph.container, "container_version"),
        (graph.consumer, "profile_version"),
        (graph.file_plans[0], "record_count"),
        (graph.file_plans[0], "expected_byte_size"),
        (graph.destination_files[0], "record_count"),
        (graph.destination_files[0], "byte_size"),
        (graph.entries[0], "ordinal"),
        (graph.verification, "output_file_count"),
        (graph.verification, "declared_record_count"),
    )
    for model, field_name in numeric_fields:
        model_type = type(model)
        for invalid in (True, 1.5):
            value = model.model_dump(mode="json")
            value[field_name] = invalid
            with pytest.raises(ExportVerificationError):
                model_type.from_json_bytes(lossless_json_bytes(value))
            with pytest.raises(ValidationError):
                model_type.model_validate(value)


def test_unicode_is_lossless_but_paths_require_preexisting_nfc(
    graph: ExportGraph,
) -> None:
    nfc = ExportDependencyBinding.create(
        dependency_name="unicode-renderer",
        dependency_version="café",
        dependency_role="renderer",
    )
    nfd = ExportDependencyBinding.create(
        dependency_name="unicode-renderer",
        dependency_version="cafe\N{COMBINING ACUTE ACCENT}",
        dependency_role="renderer",
    )
    assert nfc.dependency_version != nfd.dependency_version
    assert nfc.dependency_id != nfd.dependency_id
    assert "café".encode() in nfc.canonical_bytes()
    assert "cafe\N{COMBINING ACUTE ACCENT}".encode() in nfd.canonical_bytes()

    escaped = nfc.canonical_bytes().replace("é".encode(), b"\\u00e9")
    with pytest.raises(ExportVerificationError, match="not canonical"):
        ExportDependencyBinding.from_json_bytes(escaped)

    nfc_path = ExportFilePlan.create(
        path="data/café.jsonl",
        role="unicode-data",
        media_type="application/jsonl",
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        expected_sha256=_sha("unicode-file"),
        expected_byte_size=1,
    )
    assert nfc_path.path == "data/café.jsonl"
    with pytest.raises(ValidationError, match="NFC"):
        ExportFilePlan.create(
            path="data/cafe\N{COMBINING ACUTE ACCENT}.jsonl",
            role="unicode-data",
            media_type="application/jsonl",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            expected_sha256=_sha("unicode-file"),
            expected_byte_size=1,
        )

    # Ensure the complete graph retained the non-ASCII dependency exactly.
    loaded = ExportReceipt.from_json_bytes(graph.receipt.canonical_bytes())
    assert any(item.dependency_version == "rélease-2" for item in loaded.export_plan.dependencies)


@pytest.mark.parametrize(
    "unsafe_path",
    (
        "．．/evil.json",
        "．/evil.json",
        "data／evil.json",
        "data＼evil.json",
        "Ｃ：/evil.json",
        "ＣＯＮ.txt",
        "ＮＵＬ",
        "COM¹.txt",
        "CON .txt",
        "COM1 .log",
        "AUX .txt",
        "LPT9 .json",
        "NUL .bin",
        "CON\N{NO-BREAK SPACE}.txt",
        "COM¹ .txt",
        "data/*.json",
        "data/?.json",
        'data/"quote.json',
        "data/<input>.json",
        "data/pipe|name.json",
        "CONIN$",
        "CONOUT$.txt",
        "safe\N{RIGHT-TO-LEFT OVERRIDE}json",
    ),
)
def test_paths_reject_compatibility_traversal_aliases_and_format_controls(
    unsafe_path: str,
) -> None:
    with pytest.raises(ValidationError):
        ExportFilePlan.create(
            path=unsafe_path,
            role="unsafe",
            media_type="application/json",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            expected_sha256=_sha("unsafe"),
            expected_byte_size=1,
        )


def test_exact_text_rejects_unicode_format_controls() -> None:
    with pytest.raises(ValidationError, match="format characters"):
        ExportDependencyBinding.create(
            dependency_name="renderer",
            dependency_version="1\N{RIGHT-TO-LEFT OVERRIDE}exe",
            dependency_role="runtime",
        )


def test_noncanonical_and_invalid_byte_forms_are_rejected(graph: ExportGraph) -> None:
    model = graph.dependencies[0]
    canonical = model.canonical_bytes()
    value = model.model_dump(mode="json")
    reversed_keys = dict(reversed(tuple(value.items())))
    malformed = (
        b" " + canonical,
        canonical + b"\n",
        b"\xef\xbb\xbf" + canonical,
        canonical + b"\xff",
        json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"),
        json.dumps(
            reversed_keys,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        b"[]",
        b"null",
    )
    for data in malformed:
        with pytest.raises(ExportVerificationError):
            ExportDependencyBinding.from_json_bytes(data)


def test_profile_dependency_source_and_file_registries_are_canonical(
    graph: ExportGraph,
) -> None:
    consumer = graph.consumer.model_dump(mode="json")
    consumer["accepted_row_schemas"] = list(
        reversed(consumer["accepted_row_schemas"])
    )
    _reidentify(
        consumer,
        identity_field="consumer_profile_id",
        identity_kind="export-consumer",
    )
    with pytest.raises(ExportVerificationError, match="sorted and unique"):
        ExportConsumerProfile.from_json_bytes(lossless_json_bytes(consumer))

    consumer["accepted_row_schemas"] = ["messages", "messages"]
    _reidentify(
        consumer,
        identity_field="consumer_profile_id",
        identity_kind="export-consumer",
    )
    with pytest.raises(ExportVerificationError, match="sorted and unique"):
        ExportConsumerProfile.from_json_bytes(lossless_json_bytes(consumer))

    plan = graph.plan.model_dump(mode="json")
    plan["dependencies"] = list(reversed(plan["dependencies"]))
    _reidentify(plan, identity_field="export_plan_id", identity_kind="export-plan")
    with pytest.raises(ExportVerificationError, match="sorted by dependency_id"):
        ExportPlan.from_json_bytes(lossless_json_bytes(plan))

    with pytest.raises(ValidationError, match="duplicate dependencies"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "dependencies": (graph.dependencies[0], graph.dependencies[0]),
            }
        )

    same_name = ExportDependencyBinding.create(
        dependency_name=graph.dependencies[0].dependency_name,
        dependency_version="different-version",
        dependency_role="runtime",
    )
    with pytest.raises(ValidationError, match="duplicate dependency names"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "dependencies": (*graph.dependencies, same_name),
            }
        )

    with pytest.raises(ValidationError, match="at least one dependency"):
        ExportPlan.create(**{**_plan_kwargs(graph.plan), "dependencies": ()})

    plan = graph.plan.model_dump(mode="json")
    plan["source_ids"] = list(reversed(plan["source_ids"]))
    _reidentify(plan, identity_field="export_plan_id", identity_kind="export-plan")
    with pytest.raises(ExportVerificationError, match="sorted, and unique"):
        ExportPlan.from_json_bytes(lossless_json_bytes(plan))

    plan = graph.plan.model_dump(mode="json")
    plan["file_plans"] = list(reversed(plan["file_plans"]))
    _reidentify(plan, identity_field="export_plan_id", identity_kind="export-plan")
    with pytest.raises(ExportVerificationError, match="sorted by exact path"):
        ExportPlan.from_json_bytes(lossless_json_bytes(plan))

    receipt = graph.receipt.model_dump(mode="json")
    receipt["files"] = list(reversed(receipt["files"]))
    _reidentify(
        receipt,
        identity_field="export_receipt_id",
        identity_kind="export-receipt",
    )
    with pytest.raises(ExportVerificationError, match="sorted by exact path"):
        ExportReceipt.from_json_bytes(lossless_json_bytes(receipt))


def test_export_tree_rejects_duplicate_alias_ancestor_and_receipt_paths(
    graph: ExportGraph,
) -> None:
    with pytest.raises(ValidationError, match="duplicate paths"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (graph.file_plans[0], graph.file_plans[0]),
            }
        )

    case_alias = ExportFilePlan.create(
        path="DATA/evaluation.jsonl",
        role="alias",
        media_type="application/jsonl",
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        expected_sha256=_sha("alias"),
        expected_byte_size=1,
    )
    with pytest.raises(ValidationError, match="collide by case or Unicode"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (*graph.file_plans, case_alias),
            }
        )

    ancestor = ExportFilePlan.create(
        path="data",
        role="ancestor",
        media_type="application/json",
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        expected_sha256=_sha("ancestor"),
        expected_byte_size=1,
    )
    with pytest.raises(ValidationError, match="both a file and a directory"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (*graph.file_plans, ancestor),
            }
        )

    receipt_collision = ExportFilePlan.create(
        path=EXPORT_RECEIPT_PATH,
        role="self-reference",
        media_type="application/json",
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        expected_sha256=_sha("receipt-collision"),
        expected_byte_size=1,
    )
    with pytest.raises(ValidationError, match="duplicate paths"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (*graph.file_plans, receipt_collision),
            }
        )


def test_membership_preserves_partition_ordinals_not_identity_order(
    graph: ExportGraph,
) -> None:
    assert tuple(entry.record_id for entry in graph.entries) != tuple(
        sorted(entry.record_id for entry in graph.entries)
    )
    assert graph.entries[0].leakage_group_id == graph.entries[1].leakage_group_id
    assert graph.projection.train_record_count == 2
    assert graph.projection.evaluation_record_count == 1
    assert graph.projection.total_record_count == 3

    with pytest.raises(ValidationError, match="train membership cannot follow"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=tuple(reversed(graph.entries)),
        )

    gap = ExportMembershipEntry.create(
        **{**_entry_kwargs(graph.entries[1]), "ordinal": 2}
    )
    with pytest.raises(ValidationError, match="contiguous from zero"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=(graph.entries[0], gap, graph.entries[2]),
        )

    evaluation_only = ExportMembershipEntry.create(
        **{
            **_entry_kwargs(graph.entries[0]),
            "partition": "evaluation",
            "ordinal": 0,
        }
    )
    with pytest.raises(ValidationError, match="non-empty train"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=(evaluation_only,),
        )


def test_membership_rejects_a_leakage_group_crossing_partitions(
    graph: ExportGraph,
) -> None:
    crossing = ExportMembershipEntry.create(
        **{
            **_entry_kwargs(graph.entries[2]),
            "leakage_group_id": graph.entries[0].leakage_group_id,
        }
    )
    with pytest.raises(ValidationError, match="leakage group cannot cross"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=(*graph.entries[:2], crossing),
        )


@pytest.mark.parametrize(
    "duplicate_field",
    ["record_id", "row_id", "provenance_id", "assignment_id"],
)
def test_membership_rejects_each_cross_entry_duplicate(
    graph: ExportGraph,
    duplicate_field: str,
) -> None:
    second = _entry_kwargs(graph.entries[1])
    second[duplicate_field] = getattr(graph.entries[0], duplicate_field)
    duplicate = ExportMembershipEntry.create(**second)
    with pytest.raises(ValidationError, match=f"duplicate {duplicate_field}"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=(graph.entries[0], duplicate, graph.entries[2]),
        )


def test_membership_digest_and_nested_forgery_fail_closed(graph: ExportGraph) -> None:
    projection = graph.projection.model_dump(mode="json")
    projection["assignment_projection_sha256"] = "0" * 64
    _reidentify(
        projection,
        identity_field="membership_projection_id",
        identity_kind="export-membership",
    )
    with pytest.raises(ExportVerificationError, match="projection digest mismatch"):
        ExportMembershipProjection.from_json_bytes(lossless_json_bytes(projection))

    unsafe_entry = graph.entries[0].model_copy(
        update={"payload_sha256": "0" * 64}
    )
    with pytest.raises(ValidationError, match="identity mismatch"):
        ExportMembershipProjection.create(
            split_result_id=graph.projection.split_result_id,
            row_set_id=graph.projection.row_set_id,
            row_schema=graph.projection.row_schema,
            entries=(unsafe_entry, *graph.entries[1:]),
        )

    unsafe_container = graph.container.model_copy(
        update={"determinism_claim": "semantic_content_only"}
    )
    with pytest.raises(ValidationError, match="identity mismatch"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "container_profile": unsafe_container,
            }
        )

    unsafe_file = graph.destination_files[0].model_copy(
        update={"byte_size": graph.destination_files[0].byte_size + 1}
    )
    with pytest.raises(ValidationError, match="identity mismatch"):
        ExportReceipt.create(
            export_plan=graph.plan,
            files=(unsafe_file, *graph.destination_files[1:]),
        )


def test_plan_cross_references_trust_and_derivative_policy(graph: ExportGraph) -> None:
    with pytest.raises(ValidationError, match="external_digest source trust"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "source_trust_grade": "self_consistent",
            }
        )

    lower_trust = ExportPlan.create(
        **{
            **_plan_kwargs(graph.plan),
            "source_trust_policy": "allow_self_consistent",
            "source_trust_grade": "self_consistent",
            "source_verification_id": _source_verification_id(
                graph.plan,
                trust_grade="self_consistent",
            ),
        }
    )
    assert lower_trust.source_trust_grade == "self_consistent"

    with pytest.raises(ValidationError, match="source verification identity"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "source_verification_id": _id(
                    "verification",
                    "unrelated-source-verification",
                ),
            }
        )

    refusing_consumer = ExportConsumerProfile.create(
        consumer_id="refusing-consumer",
        profile_version=1,
        accepted_row_schemas=("text",),
    )
    with pytest.raises(ValidationError, match="refuses"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "consumer_profile": refusing_consumer,
            }
        )

    wrong_projection = ExportMembershipProjection.create(
        split_result_id=_id("spt", "other-split"),
        row_set_id=graph.projection.row_set_id,
        row_schema=graph.projection.row_schema,
        entries=graph.entries,
    )
    with pytest.raises(ValidationError, match="another source row set"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "membership_projection": wrong_projection,
            }
        )

    plan = graph.plan.model_dump(mode="json")
    plan["loss_policy"] = "full-sequence"
    _reidentify(plan, identity_field="export_plan_id", identity_kind="export-plan")
    with pytest.raises(ExportVerificationError, match="loss policy differs"):
        ExportPlan.from_json_bytes(lossless_json_bytes(plan))

    for field_name, invalid in (
        ("derivative_policy", "filter-membership"),
        ("overwrite_policy", "replace"),
    ):
        plan = graph.plan.model_dump(mode="json")
        plan[field_name] = invalid
        _reidentify(
            plan,
            identity_field="export_plan_id",
            identity_kind="export-plan",
        )
        with pytest.raises(ExportVerificationError):
            ExportPlan.from_json_bytes(lossless_json_bytes(plan))


def test_exact_and_semantic_evidence_modes_are_closed(graph: ExportGraph) -> None:
    exact_with_semantics = ExportFilePlan.create(
        path="data/all.jsonl",
        role="all-records",
        media_type="application/jsonl",
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=_sha("semantic-all"),
        expected_sha256=_sha("exact-all"),
        expected_byte_size=10,
    )
    with pytest.raises(ValidationError, match="byte expectations only"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (exact_with_semantics,),
            }
        )

    semantic_container = ExportContainerProfile.create(
        container_id="semantic-container",
        container_version=1,
        determinism_claim="semantic_content_only",
    )
    semantic_plan_file = ExportFilePlan.create(
        path="data/all.bin",
        role="all-records",
        media_type="application/octet-stream",
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=_sha("semantic-all"),
        expected_sha256=None,
        expected_byte_size=None,
    )
    semantic_plan = ExportPlan.create(
        **{
            **_plan_kwargs(graph.plan),
            "container_profile": semantic_container,
            "file_plans": (semantic_plan_file,),
        }
    )
    semantic_file = ExportDestinationFileBinding.create(
        file_plan_id=semantic_plan_file.file_plan_id,
        path=semantic_plan_file.path,
        role=semantic_plan_file.role,
        media_type=semantic_plan_file.media_type,
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=semantic_plan_file.semantic_content_sha256,
        sha256=_sha("one-nondeterministic-rendering"),
        byte_size=99,
    )
    semantic_receipt = ExportReceipt.create(
        export_plan=semantic_plan,
        files=(semantic_file,),
    )
    assert semantic_receipt.files[0].sha256 == _sha("one-nondeterministic-rendering")

    semantic_with_bytes = ExportFilePlan.create(
        path="data/all.bin",
        role="all-records",
        media_type="application/octet-stream",
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=_sha("semantic-all"),
        expected_sha256=_sha("forbidden-exact"),
        expected_byte_size=99,
    )
    with pytest.raises(ValidationError, match="semantic evidence only"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "container_profile": semantic_container,
                "file_plans": (semantic_with_bytes,),
            }
        )


def test_file_counts_and_membership_scope_must_close(graph: ExportGraph) -> None:
    wrong_train_count = ExportFilePlan.create(
        path="data/train.jsonl",
        role="training-partition",
        media_type="application/jsonl",
        membership_scope="train",
        record_count=3,
        semantic_content_sha256=None,
        expected_sha256=_sha("wrong-count"),
        expected_byte_size=1,
    )
    with pytest.raises(ValidationError, match="record count differs"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (wrong_train_count, graph.file_plans[0]),
            }
        )

    all_file = ExportFilePlan.create(
        path="data/all.jsonl",
        role="all-records",
        media_type="application/jsonl",
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=None,
        expected_sha256=_sha("all-records"),
        expected_byte_size=1,
    )
    all_plan = ExportPlan.create(
        **{**_plan_kwargs(graph.plan), "file_plans": (all_file,)}
    )
    assert all_plan.file_plans[0].membership_scope == "all"

    with pytest.raises(ValidationError, match="one all file"):
        ExportPlan.create(
            **{
                **_plan_kwargs(graph.plan),
                "file_plans": (all_file, graph.file_plans[1]),
            }
        )


def test_zero_byte_bindings_are_locally_closed() -> None:
    empty_sha256 = sha256_digest(b"")
    with pytest.raises(ValidationError, match="SHA-256 of empty bytes"):
        ExportFilePlan.create(
            path="empty.bin",
            role="sidecar",
            media_type="application/octet-stream",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            expected_sha256=_sha("not-empty"),
            expected_byte_size=0,
        )
    with pytest.raises(ValidationError, match="cannot occupy zero bytes"):
        ExportFilePlan.create(
            path="data/all.jsonl",
            role="all-records",
            media_type="application/jsonl",
            membership_scope="all",
            record_count=1,
            semantic_content_sha256=None,
            expected_sha256=empty_sha256,
            expected_byte_size=0,
        )
    with pytest.raises(ValidationError, match="SHA-256 of empty bytes"):
        ExportDestinationFileBinding.create(
            file_plan_id=_id("export-file-plan", "empty"),
            path="empty.bin",
            role="sidecar",
            media_type="application/octet-stream",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            sha256=_sha("not-empty"),
            byte_size=0,
        )


def test_receipt_is_self_describing_closed_and_exactly_plan_bound(
    graph: ExportGraph,
) -> None:
    with pytest.raises(ValidationError, match="complete planned file set"):
        ExportReceipt.create(
            export_plan=graph.plan,
            files=(graph.destination_files[0],),
        )

    extra_plan = ExportFilePlan.create(
        path="metadata/info.json",
        role="metadata",
        media_type="application/json",
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        expected_sha256=_sha("extra"),
        expected_byte_size=1,
    )
    extra_file = ExportDestinationFileBinding.create(
        file_plan_id=extra_plan.file_plan_id,
        path=extra_plan.path,
        role=extra_plan.role,
        media_type=extra_plan.media_type,
        membership_scope="none",
        record_count=None,
        semantic_content_sha256=None,
        sha256=_sha("extra"),
        byte_size=1,
    )
    with pytest.raises(ValidationError, match="complete planned file set"):
        ExportReceipt.create(
            export_plan=graph.plan,
            files=(*graph.destination_files, extra_file),
        )

    planned = graph.file_plans[0]
    wrong_role = ExportDestinationFileBinding.create(
        file_plan_id=planned.file_plan_id,
        path=planned.path,
        role="wrong-role",
        media_type=planned.media_type,
        membership_scope=planned.membership_scope,
        record_count=planned.record_count,
        semantic_content_sha256=None,
        sha256=planned.expected_sha256,
        byte_size=planned.expected_byte_size,
    )
    with pytest.raises(ValidationError, match="differs from plan"):
        ExportReceipt.create(
            export_plan=graph.plan,
            files=(wrong_role, graph.destination_files[1]),
        )

    wrong_bytes = ExportDestinationFileBinding.create(
        file_plan_id=planned.file_plan_id,
        path=planned.path,
        role=planned.role,
        media_type=planned.media_type,
        membership_scope=planned.membership_scope,
        record_count=planned.record_count,
        semantic_content_sha256=None,
        sha256=_sha("wrong-bytes"),
        byte_size=planned.expected_byte_size,
    )
    with pytest.raises(ValidationError, match="exact destination bytes differ"):
        ExportReceipt.create(
            export_plan=graph.plan,
            files=(wrong_bytes, graph.destination_files[1]),
        )

    receipt = graph.receipt.model_dump(mode="json")
    receipt["export_plan_id"] = _id("export-plan", "other-plan")
    _reidentify(
        receipt,
        identity_field="export_receipt_id",
        identity_kind="export-receipt",
    )
    with pytest.raises(ExportVerificationError, match="embeds another"):
        ExportReceipt.from_json_bytes(lossless_json_bytes(receipt))

    receipt = graph.receipt.model_dump(mode="json")
    receipt["output_content_root_sha256"] = "0" * 64
    _reidentify(
        receipt,
        identity_field="export_receipt_id",
        identity_kind="export-receipt",
    )
    with pytest.raises(ExportVerificationError, match="content root mismatch"):
        ExportReceipt.from_json_bytes(lossless_json_bytes(receipt))


def test_verification_repeats_the_receipt_graph_without_runtime_state(
    graph: ExportGraph,
) -> None:
    verification = graph.verification
    plan = graph.plan
    assert verification.export_receipt_id == graph.receipt.export_receipt_id
    assert verification.export_plan_id == plan.export_plan_id
    assert verification.source_bundle_id == plan.source_bundle_id
    assert verification.source_manifest_sha256 == plan.source_manifest_sha256
    assert verification.source_content_root_sha256 == plan.source_content_root_sha256
    assert verification.source_verification_id == plan.source_verification_id
    assert verification.source_trust_grade == plan.source_trust_grade
    assert verification.dataset_snapshot_id == plan.dataset_snapshot_id
    assert verification.validation_report_id == plan.validation_report_id
    assert verification.split_result_id == plan.split_result_id
    assert verification.row_set_id == plan.row_set_id
    assert verification.row_schema == plan.row_schema
    assert verification.container_profile_id == plan.container_profile.container_profile_id
    assert verification.consumer_profile_id == plan.consumer_profile.consumer_profile_id
    assert (
        verification.membership_projection_id
        == plan.membership_projection.membership_projection_id
    )
    assert verification.output_content_root_sha256 == graph.receipt.output_content_root_sha256
    assert verification.output_file_count == len(graph.receipt.files)
    assert verification.declared_record_count == len(graph.entries)

    forbidden_runtime_fields = {
        "destination_root",
        "absolute_path",
        "timestamp",
        "pid",
        "temporary_name",
        "durability_warning",
    }
    for model in graph.models:
        assert not (forbidden_runtime_fields & set(type(model).model_fields))

    forged_receipt = graph.receipt.model_copy(
        update={"export_receipt_id": _id("export-receipt", "forged")}
    )
    with pytest.raises(ExportContractError, match="identity mismatch"):
        ExportVerification.create(receipt=forged_receipt)


@pytest.mark.parametrize("field_name", ["output_file_count", "declared_record_count"])
def test_standalone_verification_rejects_zero_counts(
    graph: ExportGraph,
    field_name: str,
) -> None:
    value = graph.verification.model_dump(mode="json")
    value[field_name] = 0
    _reidentify(
        value,
        identity_field="export_verification_id",
        identity_kind="export-verification",
    )
    with pytest.raises(ExportVerificationError, match="positive integer"):
        ExportVerification.from_json_bytes(lossless_json_bytes(value))


def test_standalone_verification_rejects_unrelated_source_verification(
    graph: ExportGraph,
) -> None:
    value = graph.verification.model_dump(mode="json")
    value["source_verification_id"] = _id("verification", "unrelated")
    _reidentify(
        value,
        identity_field="export_verification_id",
        identity_kind="export-verification",
    )
    with pytest.raises(ExportVerificationError, match="bound source facts"):
        ExportVerification.from_json_bytes(lossless_json_bytes(value))
