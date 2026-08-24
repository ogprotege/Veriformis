"""Phase 9.6: local Hugging Face DatasetDict plans without importing datasets."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

from veriformis.errors import ExportContractError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportService,
)
from veriformis.exports.hugging_face_dataset import (
    HF_DATASET_CONTAINER_ID,
    HF_DATASET_CONTAINER_VERSION,
    HF_DATA_CARD_PATH,
    HF_DATASET_DICT_PATH,
    HF_EVALUATION_ARROW_PATH,
    HF_EVALUATION_INFO_PATH,
    HF_EVALUATION_STATE_PATH,
    HF_PROVENANCE_PATH,
    HF_README_PATH,
    HF_TRAIN_ARROW_PATH,
    HF_TRAIN_INFO_PATH,
    HF_TRAIN_STATE_PATH,
)
from veriformis.identity import sha256_digest
from veriformis.taxonomy import catalog

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
ROOT = Path(__file__).resolve().parents[2]


def _hugging_face_datasets_loaded() -> bool:
    return callable(getattr(sys.modules.get("datasets"), "DatasetDict", None))


def _materialize_bundle(root: Path) -> Path:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = root / "source.vfbundle"
    for relative_path, encoded in sorted(fixture["files_base64"].items()):
        data = base64.b64decode(encoded, validate=True)
        assert sha256_digest(data) == fixture["file_sha256"][relative_path]
        target = bundle.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return bundle


def _selection(bundle: Path) -> dict[str, object]:
    return {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": HF_DATASET_CONTAINER_ID,
        "container_version": HF_DATASET_CONTAINER_VERSION,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def test_hugging_face_dataset_is_discoverable_as_semantic_generic_export() -> None:
    profiles = {
        profile.selector: profile
        for profile in ExportService().discover_exports().profiles
    }
    hf_dataset = profiles[
        (HF_DATASET_CONTAINER_ID, HF_DATASET_CONTAINER_VERSION, None, None)
    ]
    assert hf_dataset.consumer_profile is None
    assert hf_dataset.container_profile.determinism_claim == "semantic_content_only"
    assert hf_dataset.supported_row_schemas == (
        "instruction_output",
        "messages",
        "prompt_completion",
        "text",
    )
    states = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    assert states[("physical_container", "hugging-face-dataset")] == "planned"


def test_hugging_face_dataset_dry_run_plans_fingerprints_without_datasets(
    tmp_path: Path,
) -> None:
    assert not _hugging_face_datasets_loaded()
    assert "pyarrow" not in sys.modules
    bundle = _materialize_bundle(tmp_path)
    plan = ExportService().dry_run_export(
        ExportDryRunRequest(operation="dry_run", **_selection(bundle))
    )
    assert not _hugging_face_datasets_loaded()
    assert "pyarrow" not in sys.modules
    assert plan.container_profile.determinism_claim == "semantic_content_only"
    assert plan.consumer_profile is None
    by_path = {item.path: item for item in plan.file_plans}
    assert tuple(sorted(by_path)) == (
        HF_README_PATH,
        HF_DATASET_DICT_PATH,
        HF_EVALUATION_ARROW_PATH,
        HF_EVALUATION_INFO_PATH,
        HF_EVALUATION_STATE_PATH,
        HF_TRAIN_ARROW_PATH,
        HF_TRAIN_INFO_PATH,
        HF_TRAIN_STATE_PATH,
        HF_DATA_CARD_PATH,
        HF_PROVENANCE_PATH,
    )
    for item in plan.file_plans:
        assert item.semantic_content_sha256 is not None
        assert item.expected_sha256 is None
        assert item.expected_byte_size is None
    train = by_path[HF_TRAIN_ARROW_PATH]
    assert train.membership_scope == "train"
    assert train.media_type == "application/vnd.apache.arrow.file"
    evaluation = by_path[HF_EVALUATION_ARROW_PATH]
    assert evaluation.membership_scope == "evaluation"


def test_hugging_face_dataset_execute_fails_closed_without_datasets(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **_selection(bundle))
    )
    destination = tmp_path / "out"
    with pytest.raises(
        ExportContractError, match="requires Hugging Face Datasets.*columnar"
    ):
        service.execute_export(
            ExportExecuteRequest(
                operation="execute",
                destination_root=str(destination),
                expected_export_plan_id=plan.export_plan_id,
                **_selection(bundle),
            )
        )
    assert not _hugging_face_datasets_loaded()
    assert "pyarrow" not in sys.modules
    assert not destination.exists()


def test_importing_hf_dataset_module_does_not_import_columnar_libraries() -> None:
    assert not _hugging_face_datasets_loaded()
    assert "pyarrow" not in sys.modules
    from veriformis.exports import hugging_face_dataset as hf_module

    assert hf_module.HF_DATASET_CONTAINER_ID == "hugging-face-dataset"
    assert not _hugging_face_datasets_loaded()
    assert "pyarrow" not in sys.modules
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in toml
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "datasets"\n' not in lock
    assert 'name = "pyarrow"\n' not in lock
