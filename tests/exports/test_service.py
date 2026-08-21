"""Phase 4 opening contracts for the verified export composition service."""

from __future__ import annotations

import base64
import json
import typing
from pathlib import Path

import pytest

from veriformis.bundle import BundleVerificationError, VerifiedFinishedBundle
from veriformis.bundle import verifier as verifier_module
from veriformis.exports import DEFAULT_EXPORT_SERVICE, ExportService
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


def test_export_source_records_lower_self_consistent_trust_explicitly(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)

    source = ExportService().verified_source(bundle)

    assert source.verification.trust_grade == "self_consistent"
    assert source.verification.manifest_sha256 == EXPECTED_MANIFEST_SHA256


def test_export_source_fails_closed_on_post_fixture_tampering(tmp_path: Path):
    bundle = _materialize_bundle(tmp_path)
    train = bundle / "data" / "train.jsonl"
    train.write_bytes(train.read_bytes().replace(b"HEADER", b"TAMPER", 1))

    with pytest.raises(BundleVerificationError, match="digest mismatch"):
        ExportService().verified_source(
            bundle,
            expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
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
    hints = typing.get_type_hints(VerifiedFinishedBundle)

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
