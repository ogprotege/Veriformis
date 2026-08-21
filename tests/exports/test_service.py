"""Phase 4 source and trust contracts for the export composition service."""

from __future__ import annotations

import base64
import json
import typing
from pathlib import Path

import pytest

from veriformis.bundle import BundleVerificationError, VerifiedFinishedBundle
from veriformis.bundle import verifier as verifier_module
from veriformis.errors import ExportContractError, ExportVerificationError
from veriformis.exports import (
    DEFAULT_EXPORT_SERVICE,
    ExportService,
    SourceTrustGrade,
    SourceTrustPolicy,
)
from veriformis.exports import service as service_module
from veriformis.identity import sha256_digest
from veriformis.pipeline import PipelineService

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
