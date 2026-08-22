"""Focused contract tests for deterministic generic export-pack transport."""

from __future__ import annotations

import base64
import json
import zipfile
from pathlib import Path

import pytest

from veriformis._archive_transport import write_deterministic_archive
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    EXPORT_PACK_ARCHIVE_SUFFIX,
    EXPORT_PACK_TRANSPORT_PROFILE,
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportContainerProfile,
    ExportDestinationFileBinding,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportFilePlan,
    ExportPackArchiveReceipt,
    ExportPlan,
    ExportReceipt,
    ExportService,
    verify_export_pack_archive,
    write_export_pack_archive,
)
from veriformis.identity import sha256_digest

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


def _materialize_bundle(root: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _published_export(
    root: Path,
    *,
    container_id: str = "split-jsonl-directory",
) -> tuple[Path, object, bytes]:
    bundle = _materialize_bundle(root)
    selection = {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": container_id,
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }
    service = ExportService()
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **selection)
    )
    destination = root / f"{container_id}-export"
    publication = service.execute_export(
        ExportExecuteRequest(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **selection,
        )
    )
    receipt_bytes = (destination / "export-receipt.json").read_bytes()
    assert receipt_bytes == publication.receipt.canonical_bytes()
    return destination, publication, receipt_bytes


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _rewrite_as_semantic_only_export(
    export_root: Path,
    receipt: ExportReceipt,
) -> tuple[ExportReceipt, bytes]:
    source_plan = receipt.export_plan
    container = ExportContainerProfile.create(
        container_id=source_plan.container_profile.container_id,
        container_version=source_plan.container_profile.container_version,
        determinism_claim="semantic_content_only",
    )
    file_plans = tuple(
        ExportFilePlan.create(
            path=item.path,
            role=item.role,
            media_type=item.media_type,
            membership_scope=item.membership_scope,
            record_count=item.record_count,
            semantic_content_sha256=sha256_digest(
                f"semantic content for {item.path}".encode()
            ),
            expected_sha256=None,
            expected_byte_size=None,
        )
        for item in source_plan.file_plans
    )
    plan = ExportPlan.create(
        source_bundle_id=source_plan.source_bundle_id,
        source_manifest_sha256=source_plan.source_manifest_sha256,
        source_content_root_sha256=source_plan.source_content_root_sha256,
        source_verification_id=source_plan.source_verification_id,
        source_trust_policy=source_plan.source_trust_policy,
        source_trust_grade=source_plan.source_trust_grade,
        dataset_snapshot_id=source_plan.dataset_snapshot_id,
        validation_report_id=source_plan.validation_report_id,
        finished_dataset_plan_id=source_plan.finished_dataset_plan_id,
        recipe_id=source_plan.recipe_id,
        objective_id=source_plan.objective_id,
        construction_result_id=source_plan.construction_result_id,
        curation_result_id=source_plan.curation_result_id,
        serialization_plan_id=source_plan.serialization_plan_id,
        split_result_id=source_plan.split_result_id,
        row_set_id=source_plan.row_set_id,
        source_ids=source_plan.source_ids,
        row_schema=source_plan.row_schema,
        container_profile=container,
        consumer_profile=source_plan.consumer_profile,
        dependencies=source_plan.dependencies,
        membership_projection=source_plan.membership_projection,
        file_plans=file_plans,
    )
    source_bindings = {item.path: item for item in receipt.files}
    semantic_bindings = tuple(
        ExportDestinationFileBinding.create(
            file_plan_id=item.file_plan_id,
            path=item.path,
            role=item.role,
            media_type=item.media_type,
            membership_scope=item.membership_scope,
            record_count=item.record_count,
            semantic_content_sha256=item.semantic_content_sha256,
            sha256=source_bindings[item.path].sha256,
            byte_size=source_bindings[item.path].byte_size,
        )
        for item in file_plans
    )
    semantic_receipt = ExportReceipt.create(
        export_plan=plan,
        files=semantic_bindings,
    )
    receipt_bytes = semantic_receipt.canonical_bytes()
    (export_root / "export-receipt.json").write_bytes(receipt_bytes)
    return semantic_receipt, receipt_bytes


def test_export_pack_archive_is_exact_deterministic_and_receipt_bound(
    tmp_path: Path,
) -> None:
    export_root, publication, receipt_bytes = _published_export(tmp_path)
    receipt_sha256 = sha256_digest(receipt_bytes)
    first = tmp_path / f"first{EXPORT_PACK_ARCHIVE_SUFFIX}"
    second = tmp_path / f"second{EXPORT_PACK_ARCHIVE_SUFFIX}"

    first_result = write_export_pack_archive(
        export_root,
        first,
        expected_export_receipt_sha256=receipt_sha256,
    )
    second_result = write_export_pack_archive(
        export_root,
        second,
        expected_export_receipt_sha256=receipt_sha256,
    )
    verified = verify_export_pack_archive(
        first,
        expected_export_receipt_sha256=receipt_sha256,
    )

    assert EXPORT_PACK_TRANSPORT_PROFILE == "deterministic-export-pack-zip-v1"
    assert isinstance(first_result, ExportPackArchiveReceipt)
    assert first.read_bytes() == second.read_bytes()
    assert first_result.archive_sha256 == second_result.archive_sha256
    assert verified.archive_sha256 == first_result.archive_sha256
    assert verified.export_receipt_sha256 == receipt_sha256
    assert verified.export_receipt_id == publication.receipt.export_receipt_id
    assert verified.export_plan_id == publication.receipt.export_plan_id
    assert verified.source_trust_grade == "external_digest"
    with zipfile.ZipFile(first, mode="r") as archive:
        names = tuple(info.filename for info in archive.infolist())
        assert names == tuple(sorted(_tree(export_root)))
        assert {name: archive.read(name) for name in names} == _tree(export_root)


@pytest.mark.parametrize(
    "container_id",
    ("split-jsonl-directory", "json", "constrained-csv"),
)
def test_every_shipped_container_packages_twice_and_verifies_without_change(
    tmp_path: Path,
    container_id: str,
) -> None:
    export_root, publication, receipt_bytes = _published_export(
        tmp_path,
        container_id=container_id,
    )
    before = _tree(export_root)
    receipt_sha256 = sha256_digest(receipt_bytes)
    first = tmp_path / f"{container_id}-first{EXPORT_PACK_ARCHIVE_SUFFIX}"
    second = tmp_path / f"{container_id}-second{EXPORT_PACK_ARCHIVE_SUFFIX}"

    first_result = write_export_pack_archive(
        export_root,
        first,
        expected_export_receipt_sha256=receipt_sha256,
    )
    second_result = write_export_pack_archive(
        export_root,
        second,
        expected_export_receipt_sha256=receipt_sha256,
    )
    verified = verify_export_pack_archive(
        first,
        expected_export_receipt_sha256=receipt_sha256,
    )

    assert first.read_bytes() == second.read_bytes()
    assert first_result.archive_sha256 == second_result.archive_sha256
    assert verified.archive_sha256 == first_result.archive_sha256
    assert verified.export_plan_id == publication.receipt.export_plan_id
    assert verified.export_receipt_id == publication.receipt.export_receipt_id
    assert verified.output_content_root_sha256 == (
        publication.receipt.output_content_root_sha256
    )
    assert _tree(export_root) == before
    with zipfile.ZipFile(first, mode="r") as archive:
        names = tuple(info.filename for info in archive.infolist())
        assert names == tuple(sorted(before))
        assert {name: archive.read(name) for name in names} == before


def test_export_pack_archive_refuses_wrong_anchor_tamper_and_replacement(
    tmp_path: Path,
) -> None:
    export_root, _, receipt_bytes = _published_export(tmp_path)
    receipt_sha256 = sha256_digest(receipt_bytes)
    archive = tmp_path / f"pack{EXPORT_PACK_ARCHIVE_SUFFIX}"
    write_export_pack_archive(
        export_root,
        archive,
        expected_export_receipt_sha256=receipt_sha256,
    )

    with pytest.raises(ExportVerificationError, match="expected digest"):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=sha256_digest(b"another receipt"),
        )
    with pytest.raises(FileExistsError):
        write_export_pack_archive(
            export_root,
            archive,
            expected_export_receipt_sha256=receipt_sha256,
        )
    with zipfile.ZipFile(archive, mode="a") as package:
        package.writestr("unexpected", b"tamper")
    with pytest.raises(ExportVerificationError):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=receipt_sha256,
        )


def test_export_pack_archive_refuses_target_inside_source(tmp_path: Path) -> None:
    export_root, _, receipt_bytes = _published_export(tmp_path)
    target = export_root / f"nested{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportContractError, match="inside its source tree"):
        write_export_pack_archive(
            export_root,
            target,
            expected_export_receipt_sha256=sha256_digest(receipt_bytes),
        )

    assert not target.exists()


def test_export_pack_archive_refuses_semantic_only_source_export(
    tmp_path: Path,
) -> None:
    export_root, publication, _ = _published_export(tmp_path)
    _, receipt_bytes = _rewrite_as_semantic_only_export(
        export_root,
        publication.receipt,
    )
    target = tmp_path / f"semantic{EXPORT_PACK_ARCHIVE_SUFFIX}"

    with pytest.raises(ExportVerificationError, match="portable_exact_bytes"):
        write_export_pack_archive(
            export_root,
            target,
            expected_export_receipt_sha256=sha256_digest(receipt_bytes),
        )

    assert not target.exists()


def test_export_pack_archive_verifier_refuses_semantic_only_plan(
    tmp_path: Path,
) -> None:
    export_root, publication, _ = _published_export(tmp_path)
    receipt, receipt_bytes = _rewrite_as_semantic_only_export(
        export_root,
        publication.receipt,
    )
    archive = tmp_path / f"semantic{EXPORT_PACK_ARCHIVE_SUFFIX}"
    members = tuple(
        sorted((*tuple(item.path for item in receipt.files), "export-receipt.json"))
    )
    write_deterministic_archive(export_root, archive, members=members)

    with pytest.raises(ExportVerificationError, match="portable_exact_bytes"):
        verify_export_pack_archive(
            archive,
            expected_export_receipt_sha256=sha256_digest(receipt_bytes),
        )
