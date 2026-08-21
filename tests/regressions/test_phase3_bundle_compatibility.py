"""Backward-compatibility proof for one sealed pre-taxonomy bundle.

The frozen fixture stores each bundle file as base64 because canonical JSON
metadata intentionally has no trailing LF, while ``apply_patch`` text files do.
Decoding only under pytest's ``tmp_path`` preserves the exact historical bytes
without teaching production readers about a test-fixture encoding.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from veriformis.bundle import BundleAttestation, FinishedBundleManifest
from veriformis.datasets.validation import (
    dataset_validation_report_from_json_bytes,
)
from veriformis.identity import sha256_digest
from veriformis.pipeline import PipelineService

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
EXPECTED_MANIFEST_SHA256 = (
    "2394aea09bf8140c7f0626688f85fe2f387cd519c736b15ffc9382b9d3006733"
)
EXPECTED_BUNDLE_ID = (
    "bundle-v1-49a6b50ed50218b8a22ce834dc69a64eb8d47f0605267bc029b3f938a6b13b4a"
)
EXPECTED_PATHS = {
    "attestation.json",
    "data/evaluation.jsonl",
    "data/train.jsonl",
    "manifest.json",
    "metadata/row-provenance.jsonl",
    "validation.json",
}


def _materialize_frozen_bundle(tmp_path: Path) -> Path:
    encoded_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert encoded_fixture["manifest_sha256"] == EXPECTED_MANIFEST_SHA256
    assert set(encoded_fixture["file_sha256"]) == EXPECTED_PATHS
    assert set(encoded_fixture["files_base64"]) == EXPECTED_PATHS

    bundle = tmp_path / "pre-taxonomy-full-text.vfbundle"
    for relative_path in sorted(EXPECTED_PATHS):
        content = base64.b64decode(
            encoded_fixture["files_base64"][relative_path],
            validate=True,
        )
        assert sha256_digest(content) == encoded_fixture["file_sha256"][relative_path]
        destination = bundle.joinpath(*relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return bundle


def test_pre_taxonomy_finished_bundle_v1_still_loads_and_verifies(tmp_path: Path):
    bundle = _materialize_frozen_bundle(tmp_path)
    manifest_bytes = (bundle / "manifest.json").read_bytes()
    assert sha256_digest(manifest_bytes) == EXPECTED_MANIFEST_SHA256

    manifest = FinishedBundleManifest.from_json_bytes(manifest_bytes)
    attestation = BundleAttestation.from_json_bytes(
        (bundle / "attestation.json").read_bytes()
    )
    validation = dataset_validation_report_from_json_bytes(
        (bundle / "validation.json").read_bytes()
    )
    assert manifest.schema_version == "veriformis.finished-bundle-manifest/v1"
    assert {file.schema_version for file in manifest.files} == {
        "veriformis.finished-bundle-file/v1"
    }
    assert attestation.schema_version == "veriformis.bundle-attestation/v1"
    assert validation.schema_version == "veriformis.dataset-validation-report/v1"
    assert validation.snapshot.schema_version == "veriformis.dataset-snapshot/v1"
    assert manifest.bundle_id == EXPECTED_BUNDLE_ID
    assert len(manifest.files) == 4

    outcome = PipelineService().verify(
        bundle,
        manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    assert outcome.exit_status == 0
    assert outcome.verification is not None
    assert outcome.verification.schema_version == "veriformis.bundle-verification/v1"
    assert outcome.verification.trust_grade == "external_digest"
    assert outcome.verification.manifest_sha256 == EXPECTED_MANIFEST_SHA256
    assert outcome.verification.bundle_id == EXPECTED_BUNDLE_ID
    assert outcome.verification.payload_file_count == 4
    assert outcome.verification.declared_record_count == 3
