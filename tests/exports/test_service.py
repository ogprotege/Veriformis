"""Phase 4 source and trust contracts for the export composition service."""

from __future__ import annotations

import base64
import inspect
import json
import typing
from dataclasses import replace
from pathlib import Path

import pytest

from veriformis.bundle import (
    BundleFile,
    BundleVerificationError,
    FinishedBundleManifest,
    VerificationResult,
    VerifiedFinishedBundle,
)
from veriformis.bundle import verifier as verifier_module
from veriformis.datasets import (
    ProductRow,
    RowProvenance,
    row_provenance_from_json_bytes,
)
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    DEFAULT_EXPORT_SERVICE,
    ExportConsumerProfile,
    ExportContainerProfile,
    ExportDependencyBinding,
    ExportFilePlan,
    ExportMembershipEntry,
    ExportMembershipProjection,
    ExportPlan,
    ExportService,
    SourceTrustGrade,
    SourceTrustPolicy,
)
from veriformis.exports import service as service_module
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import loss_policy_for_row

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)


def _materialize_bundle(tmp_path: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = tmp_path / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _bundle_file_bytes(bundle: Path) -> dict[str, bytes]:
    return {
        path.relative_to(bundle).as_posix(): path.read_bytes()
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    }


def _exact_plan_evidence() -> tuple[
    ExportContainerProfile,
    ExportConsumerProfile,
    tuple[ExportDependencyBinding, ...],
    tuple[ExportFilePlan, ...],
]:
    container = ExportContainerProfile.create(
        container_id="phase4-conformance-directory",
        container_version=7,
        determinism_claim="portable_exact_bytes",
    )
    consumer = ExportConsumerProfile.create(
        consumer_id="phase4-conformance-consumer",
        profile_version=3,
        accepted_row_schemas=("text", "messages"),
    )
    dependencies = (
        ExportDependencyBinding.create(
            dependency_name="phase4-renderer",
            dependency_version="rélease-2",
            dependency_role="renderer",
        ),
        ExportDependencyBinding.create(
            dependency_name="canonical-json",
            dependency_version="1.0.0",
            dependency_role="runtime",
        ),
    )
    file_bytes = {
        "data/train.jsonl": b'{"text":"train"}\n',
        "data/evaluation.jsonl": (
            b'{"text":"evaluation-a"}\n'
            b'{"text":"evaluation-b"}\n'
        ),
        "metadata/schema.json": b'{"row_schema":"text"}',
    }
    files = (
        ExportFilePlan.create(
            path="metadata/schema.json",
            role="schema-metadata",
            media_type="application/json",
            membership_scope="none",
            record_count=None,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(file_bytes["metadata/schema.json"]),
            expected_byte_size=len(file_bytes["metadata/schema.json"]),
        ),
        ExportFilePlan.create(
            path="data/train.jsonl",
            role="training-partition",
            media_type="application/jsonl",
            membership_scope="train",
            record_count=1,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(file_bytes["data/train.jsonl"]),
            expected_byte_size=len(file_bytes["data/train.jsonl"]),
        ),
        ExportFilePlan.create(
            path="data/evaluation.jsonl",
            role="evaluation-partition",
            media_type="application/jsonl",
            membership_scope="evaluation",
            record_count=2,
            semantic_content_sha256=None,
            expected_sha256=sha256_digest(file_bytes["data/evaluation.jsonl"]),
            expected_byte_size=len(file_bytes["data/evaluation.jsonl"]),
        ),
    )
    return container, consumer, dependencies, files


def _semantic_plan_evidence() -> tuple[
    ExportContainerProfile,
    tuple[ExportDependencyBinding, ...],
    tuple[ExportFilePlan, ...],
]:
    container = ExportContainerProfile.create(
        container_id="phase4-semantic-conformance",
        container_version=2,
        determinism_claim="semantic_content_only",
    )
    dependency = ExportDependencyBinding.create(
        dependency_name="semantic-renderer",
        dependency_version="2.1.0",
        dependency_role="renderer",
    )
    file_plan = ExportFilePlan.create(
        path="records/all.rows",
        role="complete-dataset",
        media_type="application/json",
        membership_scope="all",
        record_count=3,
        semantic_content_sha256=sha256_digest(b"three canonical semantic rows"),
        expected_sha256=None,
        expected_byte_size=None,
    )
    return container, (dependency,), (file_plan,)


def _create_exact_plan(
    service: ExportService,
    bundle: Path,
    *,
    source_trust_policy: SourceTrustPolicy = "require_external_digest",
    expected_manifest_sha256: str | None = EXPECTED_MANIFEST_SHA256,
) -> ExportPlan:
    container, consumer, dependencies, file_plans = _exact_plan_evidence()
    return service.create_plan(
        bundle,
        container_profile=container,
        consumer_profile=consumer,
        dependencies=dependencies,
        file_plans=file_plans,
        source_trust_policy=source_trust_policy,
        expected_manifest_sha256=expected_manifest_sha256,
    )


def _reidentified_provenance(
    provenance: RowProvenance,
    **updates: object,
) -> RowProvenance:
    body = provenance.model_dump(mode="json", exclude={"provenance_id"})
    body.update(updates)
    return row_provenance_from_json_bytes(
        lossless_json_bytes({"provenance_id": derive_id("prv", body), **body})
    )


def test_export_service_reconstructs_one_anchored_immutable_source(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)

    source = ExportService().verified_source(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    assert isinstance(source, VerifiedFinishedBundle)
    assert source.bundle_path == bundle.resolve()
    assert source.verification.trust_grade == "external_digest"
    assert source.verification.manifest_sha256 == EXPECTED_MANIFEST_SHA256
    assert source.manifest.bundle_id == source.verification.bundle_id
    assert source.validation_report.report_id == source.verification.validation_report_id
    assert source.row_set.row_set_id == source.validation_report.snapshot.row_set_id
    assert source.row_set.row_schema == "text"
    assert source.row_set.train_row_count == 1
    assert source.row_set.evaluation_row_count == 2


def test_export_source_requires_retained_expected_digest_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    inspected = False

    class UnopenedPath:
        def __fspath__(self) -> str:
            raise AssertionError("source path must not be resolved")

    def inspect(*args: object, **kwargs: object) -> None:
        nonlocal inspected
        inspected = True

    monkeypatch.setattr(service_module, "inspect_finished_bundle", inspect)

    with pytest.raises(ExportContractError, match="retained expected_manifest"):
        ExportService().verified_source(UnopenedPath())

    assert inspected is False


def test_export_source_records_lower_self_consistent_trust_explicitly(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)

    source = ExportService().verified_source(
        bundle,
        source_trust_policy="allow_self_consistent",
    )

    assert source.verification.trust_grade == "self_consistent"
    assert source.verification.manifest_sha256 == EXPECTED_MANIFEST_SHA256


def test_lower_trust_policy_preserves_supplied_external_evidence(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)

    source = ExportService().verified_source(
        bundle,
        source_trust_policy="allow_self_consistent",
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    assert source.verification.trust_grade == "external_digest"
    assert source.verification.manifest_sha256 == EXPECTED_MANIFEST_SHA256


@pytest.mark.parametrize(
    "source_trust_policy",
    ["require_external_digest", "allow_self_consistent"],
)
def test_source_trust_policy_never_falls_back_after_external_digest_mismatch(
    tmp_path: Path,
    source_trust_policy: str,
):
    bundle = _materialize_bundle(tmp_path)
    before = _bundle_file_bytes(bundle)

    with pytest.raises(BundleVerificationError, match="expected external digest"):
        ExportService().verified_source(
            bundle,
            source_trust_policy=source_trust_policy,  # type: ignore[arg-type]
            expected_manifest_sha256="0" * 64,
        )

    assert _bundle_file_bytes(bundle) == before


@pytest.mark.parametrize("source_trust_policy", ["invented", None, False, b"bad"])
def test_export_source_rejects_invalid_trust_policy_before_source_access(
    monkeypatch: pytest.MonkeyPatch,
    source_trust_policy: object,
):
    inspected = False

    class UnopenedPath:
        def __fspath__(self) -> str:
            raise AssertionError("source path must not be resolved")

    def inspect(*args: object, **kwargs: object) -> None:
        nonlocal inspected
        inspected = True

    monkeypatch.setattr(service_module, "inspect_finished_bundle", inspect)

    with pytest.raises(ExportContractError, match="source_trust_policy"):
        ExportService().verified_source(
            UnopenedPath(),
            source_trust_policy=source_trust_policy,  # type: ignore[arg-type]
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )

    assert inspected is False


def test_export_source_rejects_an_overstated_verifier_trust_grade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    self_consistent = verifier_module.inspect_finished_bundle(bundle)
    monkeypatch.setattr(
        service_module,
        "inspect_finished_bundle",
        lambda *args, **kwargs: self_consistent,
    )

    with pytest.raises(ExportVerificationError, match="trust grade"):
        ExportService().verified_source(
            bundle,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )


def test_export_source_rejects_a_silent_trust_upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    externally_anchored = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    monkeypatch.setattr(
        service_module,
        "inspect_finished_bundle",
        lambda *args, **kwargs: externally_anchored,
    )

    with pytest.raises(ExportVerificationError, match="trust grade"):
        ExportService().verified_source(
            bundle,
            source_trust_policy="allow_self_consistent",
        )


def test_export_source_rejects_a_verifier_manifest_digest_disagreement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    anchored_to_another_digest = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    impossible = anchored_to_another_digest.verification.model_copy(
        update={"manifest_sha256": "f" * 64}
    )
    monkeypatch.setattr(
        service_module,
        "inspect_finished_bundle",
        lambda *args, **kwargs: VerifiedFinishedBundle(
            bundle_path=anchored_to_another_digest.bundle_path,
            manifest=anchored_to_another_digest.manifest,
            validation_report=anchored_to_another_digest.validation_report,
            row_set=anchored_to_another_digest.row_set,
            verification=impossible,
        ),
    )

    with pytest.raises(ExportVerificationError, match="manifest digest"):
        ExportService().verified_source(
            bundle,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
        )


@pytest.mark.parametrize(
    "source_trust_policy",
    ["require_external_digest", "allow_self_consistent"],
)
@pytest.mark.parametrize("malformed_digest", ["", "0" * 63, "A" * 64, b"0" * 64])
def test_lower_trust_policy_rejects_malformed_external_evidence_without_fallback(
    source_trust_policy: str,
    malformed_digest: object,
):
    class UnopenedPath:
        def __fspath__(self) -> str:
            raise AssertionError("source path must not be resolved")

    with pytest.raises(BundleVerificationError, match="invalid expected manifest"):
        ExportService().verified_source(
            UnopenedPath(),
            source_trust_policy=source_trust_policy,  # type: ignore[arg-type]
            expected_manifest_sha256=malformed_digest,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("source_trust_policy", "expected_manifest_sha256"),
    [
        ("require_external_digest", EXPECTED_MANIFEST_SHA256),
        ("allow_self_consistent", None),
    ],
)
def test_export_source_fails_closed_on_post_fixture_tampering(
    tmp_path: Path,
    source_trust_policy: str,
    expected_manifest_sha256: str | None,
):
    bundle = _materialize_bundle(tmp_path)
    train = bundle / "data" / "train.jsonl"
    train.write_bytes(train.read_bytes().replace(b"HEADER", b"TAMPER", 1))
    before = _bundle_file_bytes(bundle)

    with pytest.raises(BundleVerificationError, match="digest mismatch"):
        ExportService().verified_source(
            bundle,
            source_trust_policy=source_trust_policy,  # type: ignore[arg-type]
            expected_manifest_sha256=expected_manifest_sha256,
        )

    assert _bundle_file_bytes(bundle) == before


def test_create_plan_binds_the_complete_verified_source_and_output_evidence(
    tmp_path: Path,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    container, consumer, dependencies, file_plans = _exact_plan_evidence()

    plan = ExportService().create_plan(
        bundle,
        container_profile=container,
        consumer_profile=consumer,
        dependencies=dependencies,
        file_plans=file_plans,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    snapshot = source.validation_report.snapshot
    row_set = source.row_set
    assert plan.source_bundle_id == source.manifest.bundle_id
    assert plan.source_manifest_sha256 == source.verification.manifest_sha256
    assert plan.source_content_root_sha256 == source.manifest.content_root_sha256
    assert plan.source_verification_id == source.verification.verification_id
    assert plan.source_trust_policy == "require_external_digest"
    assert plan.source_trust_grade == "external_digest"
    assert plan.dataset_snapshot_id == snapshot.snapshot_id
    assert plan.validation_report_id == source.validation_report.report_id
    assert plan.finished_dataset_plan_id == snapshot.plan_id
    assert plan.recipe_id == snapshot.recipe_id
    assert plan.construction_result_id == snapshot.construction_result_id
    assert plan.curation_result_id == snapshot.curation_result_id
    assert plan.serialization_plan_id == row_set.serialization_plan_id
    assert plan.split_result_id == snapshot.split_result_id
    assert plan.row_set_id == snapshot.row_set_id
    assert plan.source_ids == snapshot.source_ids
    assert plan.row_schema == row_set.row_schema == "text"
    assert plan.loss_policy == loss_policy_for_row(row_set.row_schema)
    assert plan.objective_id == row_set.provenance[0].objective_id
    assert {item.objective_id for item in row_set.provenance} == {
        plan.objective_id
    }
    assert plan.derivative_policy == "preserve_membership_and_semantics"
    assert plan.overwrite_policy == "refuse"

    projection = plan.membership_projection
    rows = (*row_set.train_rows, *row_set.evaluation_rows)
    assert projection.split_result_id == row_set.split_result_id
    assert projection.row_set_id == row_set.row_set_id
    assert projection.row_schema == row_set.row_schema
    assert projection.train_record_count == row_set.train_row_count == 1
    assert projection.evaluation_record_count == row_set.evaluation_row_count == 2
    assert projection.total_record_count == row_set.total_row_count == 3
    assert len(projection.entries) == len(rows) == len(row_set.provenance)
    for entry, row, provenance in zip(
        projection.entries,
        rows,
        row_set.provenance,
        strict=True,
    ):
        assert (
            entry.record_id,
            entry.row_id,
            entry.provenance_id,
            entry.assignment_id,
            entry.leakage_group_id,
            entry.partition,
            entry.ordinal,
            entry.payload_sha256,
        ) == (
            row.record_id,
            row.row_id,
            provenance.provenance_id,
            provenance.assignment_id,
            provenance.leakage_group_id,
            provenance.partition,
            provenance.ordinal,
            row.payload_sha256,
        )

    assert plan.container_profile == container
    assert plan.container_profile.container_version == 7
    assert plan.consumer_profile == consumer
    assert plan.consumer_profile.profile_version == 3
    assert plan.dependencies == tuple(
        sorted(dependencies, key=lambda item: item.dependency_id)
    )
    assert any(
        dependency.dependency_version == "rélease-2"
        for dependency in plan.dependencies
    )
    assert plan.file_plans == tuple(sorted(file_plans, key=lambda item: item.path))
    assert tuple(item.path for item in plan.file_plans) == (
        "data/evaluation.jsonl",
        "data/train.jsonl",
        "metadata/schema.json",
    )
    for file_plan in plan.file_plans:
        assert file_plan.media_type in {"application/json", "application/jsonl"}
        assert file_plan.expected_sha256 is not None
        assert file_plan.expected_byte_size is not None
        assert file_plan.semantic_content_sha256 is None


def test_create_plan_binds_semantic_only_evidence_without_overclaiming_bytes(
    tmp_path: Path,
):
    bundle = _materialize_bundle(tmp_path)
    container, dependencies, file_plans = _semantic_plan_evidence()

    plan = ExportService().create_plan(
        bundle,
        container_profile=container,
        consumer_profile=None,
        dependencies=dependencies,
        file_plans=file_plans,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    assert plan.consumer_profile is None
    assert plan.container_profile.determinism_claim == "semantic_content_only"
    assert len(plan.file_plans) == 1
    planned = plan.file_plans[0]
    assert planned.path == "records/all.rows"
    assert planned.membership_scope == "all"
    assert planned.record_count == 3
    assert planned.semantic_content_sha256 == file_plans[0].semantic_content_sha256
    assert planned.expected_sha256 is None
    assert planned.expected_byte_size is None


@pytest.mark.parametrize(
    ("source_trust_policy", "expected_manifest_sha256", "expected_grade"),
    [
        ("require_external_digest", EXPECTED_MANIFEST_SHA256, "external_digest"),
        ("allow_self_consistent", None, "self_consistent"),
        ("allow_self_consistent", EXPECTED_MANIFEST_SHA256, "external_digest"),
    ],
)
def test_create_plan_persists_requested_policy_and_observed_grade_exactly(
    tmp_path: Path,
    source_trust_policy: SourceTrustPolicy,
    expected_manifest_sha256: str | None,
    expected_grade: SourceTrustGrade,
):
    bundle = _materialize_bundle(tmp_path)

    plan = _create_exact_plan(
        ExportService(),
        bundle,
        source_trust_policy=source_trust_policy,
        expected_manifest_sha256=expected_manifest_sha256,
    )

    assert plan.source_trust_policy == source_trust_policy
    assert plan.source_trust_grade == expected_grade


def test_create_plan_is_order_and_portable_root_independent(tmp_path: Path):
    first_bundle = _materialize_bundle(tmp_path / "first-root")
    second_bundle = _materialize_bundle(tmp_path / "second-root")
    container, consumer, dependencies, file_plans = _exact_plan_evidence()
    service = ExportService()

    first = service.create_plan(
        first_bundle,
        container_profile=container,
        consumer_profile=consumer,
        dependencies=dependencies,
        file_plans=file_plans,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    second = service.create_plan(
        second_bundle,
        container_profile=container,
        consumer_profile=consumer,
        dependencies=tuple(reversed(dependencies)),
        file_plans=tuple(reversed(file_plans)),
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )

    assert first.export_plan_id == second.export_plan_id
    assert first.canonical_bytes() == second.canonical_bytes()
    portable = first.canonical_bytes()
    assert str(first_bundle).encode() not in portable
    assert str(second_bundle).encode() not in portable
    for forbidden_runtime_field in (
        b'"bundle_path"',
        b'"destination_root"',
        b'"created_at"',
        b'"process_id"',
        b'"temporary_path"',
        b'"warning"',
    ):
        assert forbidden_runtime_field not in portable


def test_create_plan_identity_binds_profile_and_dependency_versions(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    container, consumer, dependencies, file_plans = _exact_plan_evidence()
    service = ExportService()
    common = {
        "bundle": bundle,
        "consumer_profile": consumer,
        "dependencies": dependencies,
        "file_plans": file_plans,
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
    }
    baseline = service.create_plan(container_profile=container, **common)
    changed_container = service.create_plan(
        container_profile=ExportContainerProfile.create(
            container_id=container.container_id,
            container_version=container.container_version + 1,
            determinism_claim=container.determinism_claim,
        ),
        **common,
    )
    changed_consumer = service.create_plan(
        container_profile=container,
        **{
            **common,
            "consumer_profile": ExportConsumerProfile.create(
                consumer_id=consumer.consumer_id,
                profile_version=consumer.profile_version + 1,
                accepted_row_schemas=consumer.accepted_row_schemas,
            ),
        },
    )
    changed_dependency = service.create_plan(
        container_profile=container,
        **{
            **common,
            "dependencies": (
                ExportDependencyBinding.create(
                    dependency_name=dependencies[0].dependency_name,
                    dependency_version="rélease-3",
                    dependency_role=dependencies[0].dependency_role,
                ),
                dependencies[1],
            ),
        },
    )

    assert len(
        {
            baseline.export_plan_id,
            changed_container.export_plan_id,
            changed_consumer.export_plan_id,
            changed_dependency.export_plan_id,
        }
    ) == 4


@pytest.mark.parametrize(
    "mismatch",
    (
        "verification-content-root",
        "snapshot-row-set",
        "mixed-objective",
        "coherent-stale-plan",
        "manifest-snapshot-file",
    ),
)
def test_create_plan_rejects_impossible_verified_source_graphs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    if mismatch == "verification-content-root":
        impossible = replace(
            source,
            verification=source.verification.model_copy(
                update={"content_root_sha256": "0" * 64}
            ),
        )
    elif mismatch == "snapshot-row-set":
        impossible = replace(
            source,
            row_set=source.row_set.model_copy(
                update={
                    "split_result_id": derive_id(
                        "spt",
                        {"fixture": "another-split"},
                    )
                }
            ),
        )
    elif mismatch == "mixed-objective":
        provenance = source.row_set.provenance
        impossible = replace(
            source,
            row_set=source.row_set.model_copy(
                update={
                    "provenance": (
                        provenance[0].model_copy(
                            update={
                                "objective_id": derive_id(
                                    "obj",
                                    {"fixture": "another-objective"},
                                )
                            }
                        ),
                        *provenance[1:],
                    )
                }
            ),
        )
    elif mismatch == "coherent-stale-plan":
        alternate_plan_id = derive_id("fdp", {"fixture": "substituted-plan"})
        substituted_provenance = tuple(
            item.model_copy(update={"plan_id": alternate_plan_id})
            for item in source.row_set.provenance
        )
        substituted_row_set = source.row_set.model_copy(
            update={
                "plan_id": alternate_plan_id,
                "provenance": substituted_provenance,
            }
        )
        substituted_snapshot = source.validation_report.snapshot.model_copy(
            update={"plan_id": alternate_plan_id}
        )
        substituted_report = source.validation_report.model_copy(
            update={"snapshot": substituted_snapshot}
        )
        impossible = replace(
            source,
            validation_report=substituted_report,
            row_set=substituted_row_set,
        )
    else:
        train_descriptor = next(
            item for item in source.manifest.files if item.path == "data/train.jsonl"
        )
        substituted_train = BundleFile.create(
            path=train_descriptor.path,
            data=b'{"text":"substituted"}\n',
            role=train_descriptor.role,
            media_type=train_descriptor.media_type,
            record_count=train_descriptor.record_count,
        )
        substituted_files = tuple(
            substituted_train if item.path == substituted_train.path else item
            for item in source.manifest.files
        )
        substituted_manifest = FinishedBundleManifest.create(
            dataset_snapshot_id=source.manifest.dataset_snapshot_id,
            validation_report_id=source.manifest.validation_report_id,
            files=substituted_files,
        )
        substituted_manifest_sha256 = sha256_digest(
            substituted_manifest.canonical_bytes()
        )
        substituted_verification = VerificationResult.create(
            bundle_id=substituted_manifest.bundle_id,
            dataset_snapshot_id=substituted_manifest.dataset_snapshot_id,
            validation_report_id=substituted_manifest.validation_report_id,
            manifest_sha256=substituted_manifest_sha256,
            content_root_sha256=substituted_manifest.content_root_sha256,
            trust_grade=source.verification.trust_grade,
            payload_file_count=source.verification.payload_file_count,
            declared_record_count=source.verification.declared_record_count,
        )
        impossible = replace(
            source,
            manifest=substituted_manifest,
            verification=substituted_verification,
        )
    service = ExportService()
    monkeypatch.setattr(
        service,
        "verified_source",
        lambda *args, **kwargs: impossible,
    )

    with pytest.raises(ExportVerificationError) as caught:
        _create_exact_plan(service, bundle)

    assert caught.value.code == "export-verification-invalid"


def test_create_plan_wraps_invalid_caller_evidence_in_contract_error(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    container, consumer, dependencies, file_plans = _exact_plan_evidence()
    refusing_consumer = ExportConsumerProfile.create(
        consumer_id="refusing-consumer",
        profile_version=1,
        accepted_row_schemas=("prompt_completion",),
    )
    invalid_cases = (
        {
            "container_profile": container.model_copy(
                update={"container_version": 0}
            ),
            "consumer_profile": consumer,
            "dependencies": dependencies,
            "file_plans": file_plans,
        },
        {
            "container_profile": container,
            "consumer_profile": refusing_consumer,
            "dependencies": dependencies,
            "file_plans": file_plans,
        },
        {
            "container_profile": container,
            "consumer_profile": consumer,
            "dependencies": (
                dependencies[0].model_copy(update={"dependency_version": ""}),
                dependencies[1],
            ),
            "file_plans": file_plans,
        },
        {
            "container_profile": container,
            "consumer_profile": consumer,
            "dependencies": dependencies,
            "file_plans": (
                file_plans[0].model_copy(update={"path": "/private/output.json"}),
                *file_plans[1:],
            ),
        },
        {
            "container_profile": container,
            "consumer_profile": consumer,
            "dependencies": dependencies,
            "file_plans": (
                file_plans[0],
                file_plans[1].model_copy(update={"record_count": 99}),
                file_plans[2],
            ),
        },
    )

    for evidence in invalid_cases:
        with pytest.raises(ExportContractError) as caught:
            ExportService().create_plan(
                bundle,
                **evidence,  # type: ignore[arg-type]
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )
        assert caught.value.code == "export-contract-invalid"


def test_create_plan_rejects_a_non_source_admission_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    monkeypatch.setattr(
        service,
        "verified_source",
        lambda *args, **kwargs: object(),
    )

    with pytest.raises(ExportVerificationError, match="source model evidence"):
        _create_exact_plan(service, bundle)


def test_create_plan_exposes_no_membership_or_runtime_destination_controls():
    parameters = set(inspect.signature(ExportService.create_plan).parameters)

    assert {
        "bundle",
        "container_profile",
        "consumer_profile",
        "dependencies",
        "file_plans",
        "source_trust_policy",
        "expected_manifest_sha256",
    } <= parameters
    assert parameters.isdisjoint(
        {
            "source_ids",
            "row_schema",
            "objective_id",
            "membership_projection",
            "entries",
            "include",
            "exclude",
            "filter",
            "balance",
            "partition",
            "resplit",
            "target",
            "destination_root",
            "overwrite_policy",
        }
    )


def test_create_plan_is_read_only_and_admits_the_source_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    before = _bundle_file_bytes(bundle)
    before_paths = tuple(
        path.relative_to(tmp_path).as_posix()
        for path in sorted(tmp_path.rglob("*"))
    )
    service = ExportService()
    original_verified_source = service.verified_source
    admission_count = 0

    def tracked_verified_source(*args: object, **kwargs: object):
        nonlocal admission_count
        admission_count += 1
        return original_verified_source(*args, **kwargs)

    def reject_write(*args: object, **kwargs: object) -> None:
        raise AssertionError("plan population must not write")

    monkeypatch.setattr(service, "verified_source", tracked_verified_source)
    monkeypatch.setattr(Path, "mkdir", reject_write)
    monkeypatch.setattr(Path, "write_bytes", reject_write)
    monkeypatch.setattr(service_module.os, "replace", reject_write)

    plan = _create_exact_plan(service, bundle)

    assert isinstance(plan, ExportPlan)
    assert admission_count == 1
    assert _bundle_file_bytes(bundle) == before
    assert tuple(
        path.relative_to(tmp_path).as_posix()
        for path in sorted(tmp_path.rglob("*"))
    ) == before_paths
    assert not (bundle / "export-receipt.json").exists()


def test_derivative_membership_accepts_only_the_complete_source_semantics(
    tmp_path: Path,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)

    projection = ExportService().validate_derivative_membership(
        plan,
        candidate_train_rows=source.row_set.train_rows,
        candidate_evaluation_rows=source.row_set.evaluation_rows,
        candidate_provenance=source.row_set.provenance,
    )

    assert projection == plan.membership_projection
    assert projection.canonical_bytes() == plan.membership_projection.canonical_bytes()
    assert projection.row_set_id == source.row_set.row_set_id
    assert projection.total_record_count == source.row_set.total_row_count


@pytest.mark.parametrize("mutation", ("omission", "duplicate", "reorder"))
def test_derivative_membership_rejects_structural_membership_mutation(
    tmp_path: Path,
    mutation: str,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    train_rows = source.row_set.train_rows
    evaluation_rows = source.row_set.evaluation_rows
    provenance = source.row_set.provenance
    if mutation == "omission":
        evaluation_rows = evaluation_rows[:-1]
        provenance = provenance[:-1]
    elif mutation == "duplicate":
        evaluation_rows = (*evaluation_rows, evaluation_rows[-1])
        provenance = (*provenance, provenance[-1])
    else:
        evaluation_rows = tuple(reversed(evaluation_rows))
        provenance = (provenance[0], *reversed(provenance[1:]))

    with pytest.raises(ExportVerificationError) as caught:
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )

    assert caught.value.code == "export-verification-invalid"


def test_derivative_membership_rejects_a_coherent_addition(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    evaluation_rows = source.row_set.evaluation_rows
    existing_ids = {row.record_id for row in evaluation_rows}
    final_id = max(existing_ids)
    added_record_id = next(
        candidate
        for index in range(10_000)
        if (candidate := derive_id("rec", {"phase4-addition": index}))
        not in existing_ids
        and candidate > final_id
    )
    added_row = ProductRow.create(
        record_id=added_record_id,
        row_schema=plan.row_schema,
        payload={"text": "coherently added derivative target"},
    )
    added_provenance = _reidentified_provenance(
        source.row_set.provenance[-1],
        ordinal=len(evaluation_rows),
        row_id=added_row.row_id,
        payload_sha256=added_row.payload_sha256,
        record_id=added_record_id,
        assignment_id=derive_id("asg", {"phase4-addition": added_record_id}),
    )

    with pytest.raises(ExportVerificationError, match="changes the source row set"):
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=(*evaluation_rows, added_row),
            candidate_provenance=(*source.row_set.provenance, added_provenance),
        )


def test_derivative_membership_rejects_a_coherently_reidentified_target_mutation(
    tmp_path: Path,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    original = source.row_set.evaluation_rows[0]
    altered = ProductRow.create(
        record_id=original.record_id,
        row_schema=original.row_schema,
        payload={"text": f"{original.payload['text']} — altered"},
    )
    altered_provenance = _reidentified_provenance(
        source.row_set.provenance[1],
        row_id=altered.row_id,
        payload_sha256=altered.payload_sha256,
    )

    with pytest.raises(ExportVerificationError, match="changes the source row set"):
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=(
                altered,
                *source.row_set.evaluation_rows[1:],
            ),
            candidate_provenance=(
                source.row_set.provenance[0],
                altered_provenance,
                *source.row_set.provenance[2:],
            ),
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    (
        ("assignment_id", derive_id("asg", {"phase4": "another-assignment"})),
        ("leakage_group_id", derive_id("lkg", {"phase4": "another-group"})),
    ),
)
def test_derivative_membership_rejects_coherent_assignment_or_group_substitution(
    tmp_path: Path,
    field_name: str,
    replacement: str,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    changed = _reidentified_provenance(
        source.row_set.provenance[-1],
        **{field_name: replacement},
    )

    with pytest.raises(ExportVerificationError, match="changes the source row set"):
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=(*source.row_set.provenance[:-1], changed),
        )


def test_derivative_membership_rejects_coherent_repartitioning(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    moved = source.row_set.evaluation_rows[0]
    train_rows = tuple(
        sorted((*source.row_set.train_rows, moved), key=lambda row: row.record_id)
    )
    evaluation_rows = source.row_set.evaluation_rows[1:]
    by_record_id = {item.record_id: item for item in source.row_set.provenance}
    provenance = tuple(
        _reidentified_provenance(
            by_record_id[row.record_id],
            partition=partition,
            ordinal=ordinal,
        )
        for partition, rows in (
            ("train", train_rows),
            ("evaluation", evaluation_rows),
        )
        for ordinal, row in enumerate(rows)
    )

    with pytest.raises(ExportVerificationError, match="changes the source row set"):
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=train_rows,
            candidate_evaluation_rows=evaluation_rows,
            candidate_provenance=provenance,
        )


def test_derivative_membership_rejects_resplit_provenance(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    replacement_split_id = derive_id("spt", {"phase4": "another-split"})
    provenance = tuple(
        _reidentified_provenance(item, split_result_id=replacement_split_id)
        for item in source.row_set.provenance
    )

    with pytest.raises(ExportVerificationError) as caught:
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=provenance,
        )

    assert caught.value.code == "export-verification-invalid"


def test_derivative_membership_compares_the_complete_projection(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    final = plan.membership_projection.entries[-1]
    altered_final = ExportMembershipEntry.create(
        record_id=final.record_id,
        row_id=final.row_id,
        provenance_id=final.provenance_id,
        assignment_id=derive_id("asg", {"phase4": "forged-plan-assignment"}),
        leakage_group_id=final.leakage_group_id,
        partition=final.partition,
        ordinal=final.ordinal,
        payload_sha256=final.payload_sha256,
    )
    altered_projection = ExportMembershipProjection.create(
        split_result_id=plan.split_result_id,
        row_set_id=plan.row_set_id,
        row_schema=plan.row_schema,
        entries=(*plan.membership_projection.entries[:-1], altered_final),
    )
    plan_body = plan.model_dump(mode="json", exclude={"export_plan_id"})
    plan_body["membership_projection"] = altered_projection.model_dump(mode="json")
    altered_plan = ExportPlan.from_json_bytes(
        lossless_json_bytes(
            {
                "export_plan_id": derive_id("export-plan", plan_body),
                **plan_body,
            }
        )
    )

    with pytest.raises(
        ExportVerificationError,
        match="changes source membership or semantics",
    ):
        ExportService().validate_derivative_membership(
            altered_plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=source.row_set.provenance,
        )


@pytest.mark.parametrize(
    "field_name",
    (
        "objective_id",
        "source_ids",
    ),
)
def test_derivative_membership_rejects_changed_semantic_scope(
    tmp_path: Path,
    field_name: str,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    original = source.row_set.provenance[-1]
    replacement: object = derive_id("obj", {"phase4": "another-objective"})
    if field_name == "source_ids":
        replacement = tuple(
            sorted(
                (
                    *original.source_ids,
                    derive_id("src", {"phase4": "another-source"}),
                )
            )
        )
    changed = _reidentified_provenance(
        original,
        **{field_name: replacement},
    )

    with pytest.raises(ExportVerificationError) as caught:
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=(*source.row_set.provenance[:-1], changed),
        )

    assert caught.value.code == "export-verification-invalid"


def test_derivative_membership_fresh_loads_plan_and_candidate_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    original_projection_helper = service_module._membership_projection_from_row_set
    observed_fresh_models = False

    def capture_fresh_models(row_set):
        nonlocal observed_fresh_models
        observed_fresh_models = True
        assert row_set.train_rows[0] is not source.row_set.train_rows[0]
        assert row_set.train_rows[0].payload is not source.row_set.train_rows[0].payload
        assert row_set.provenance[0] is not source.row_set.provenance[0]
        return original_projection_helper(row_set)

    monkeypatch.setattr(
        service_module,
        "_membership_projection_from_row_set",
        capture_fresh_models,
    )
    ExportService().validate_derivative_membership(
        plan,
        candidate_train_rows=source.row_set.train_rows,
        candidate_evaluation_rows=source.row_set.evaluation_rows,
        candidate_provenance=source.row_set.provenance,
    )
    assert observed_fresh_models is True

    stale_plan = plan.model_copy(update={"row_set_id": derive_id("rws", {"stale": 1})})
    stale_row = source.row_set.train_rows[0].model_copy(
        update={"payload_sha256": "0" * 64}
    )

    with pytest.raises(ExportVerificationError):
        ExportService().validate_derivative_membership(
            stale_plan,
            candidate_train_rows=source.row_set.train_rows,
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=source.row_set.provenance,
        )
    with pytest.raises(ExportVerificationError):
        ExportService().validate_derivative_membership(
            plan,
            candidate_train_rows=(stale_row,),
            candidate_evaluation_rows=source.row_set.evaluation_rows,
            candidate_provenance=source.row_set.provenance,
        )


def test_derivative_membership_is_read_only_and_has_no_mutation_controls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    bundle = _materialize_bundle(tmp_path)
    source = verifier_module.inspect_finished_bundle(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    plan = _create_exact_plan(ExportService(), bundle)
    before = _bundle_file_bytes(bundle)

    def reject_write(*args: object, **kwargs: object) -> None:
        raise AssertionError("membership validation must not write")

    monkeypatch.setattr(Path, "mkdir", reject_write)
    monkeypatch.setattr(Path, "write_bytes", reject_write)
    monkeypatch.setattr(service_module.os, "replace", reject_write)

    result = ExportService().validate_derivative_membership(
        plan,
        candidate_train_rows=source.row_set.train_rows,
        candidate_evaluation_rows=source.row_set.evaluation_rows,
        candidate_provenance=source.row_set.provenance,
    )
    parameters = set(
        inspect.signature(ExportService.validate_derivative_membership).parameters
    )

    assert result == plan.membership_projection
    assert _bundle_file_bytes(bundle) == before
    assert parameters == {
        "self",
        "plan",
        "candidate_train_rows",
        "candidate_evaluation_rows",
        "candidate_provenance",
    }
    assert parameters.isdisjoint(
        {
            "include",
            "exclude",
            "filter",
            "balance",
            "ratio",
            "seed",
            "partition",
            "resplit",
            "target",
            "membership_projection",
            "destination_root",
            "overwrite_policy",
        }
    )


def test_pipeline_composition_root_owns_the_injected_export_service():
    export_service = ExportService()

    pipeline = PipelineService(export_service=export_service)

    assert pipeline.export_service is export_service


def test_pipeline_export_service_preserves_existing_subclass_initialization_pattern():
    class ExistingStyleSubclass(PipelineService):
        def __init__(self) -> None:
            self.adapter_state = "ready"

    assert ExistingStyleSubclass().export_service is DEFAULT_EXPORT_SERVICE


def test_pipeline_export_service_preserves_falsey_injected_service():
    class FalseyExportService(ExportService):
        def __bool__(self) -> bool:
            return False

    export_service = FalseyExportService()

    assert PipelineService(export_service=export_service).export_service is export_service


def test_verified_source_public_type_hints_resolve_at_runtime():
    service_hints = typing.get_type_hints(ExportService.verified_source)
    hints = typing.get_type_hints(VerifiedFinishedBundle)

    assert service_hints["source_trust_policy"] == SourceTrustPolicy
    assert typing.get_args(SourceTrustPolicy) == (
        "require_external_digest",
        "allow_self_consistent",
    )
    assert typing.get_args(SourceTrustGrade) == (
        "external_digest",
        "self_consistent",
    )
    assert hints["validation_report"].__name__ == "DatasetValidationReport"
    assert hints["row_set"].__name__ == "RowSet"


def test_verifier_and_inspector_preserve_their_public_error_envelopes(monkeypatch):
    def fail(*args: object, **kwargs: object) -> None:
        raise ValueError("sentinel")

    monkeypatch.setattr(verifier_module, "_inspect_finished_bundle", fail)

    with pytest.raises(BundleVerificationError, match="bundle verification failed"):
        verifier_module.verify_finished_bundle("unused")
    with pytest.raises(BundleVerificationError, match="bundle inspection failed"):
        verifier_module.inspect_finished_bundle("unused")
