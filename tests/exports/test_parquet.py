"""Phase 9.4: generic Parquet export plans without importing PyArrow."""

from __future__ import annotations

import base64
import importlib.util
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
from veriformis.exports.parquet import (
    PARQUET_CONTAINER_ID,
    PARQUET_CONTAINER_VERSION,
    PARQUET_EVALUATION_PATH,
    PARQUET_TRAIN_PATH,
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
        "container_id": PARQUET_CONTAINER_ID,
        "container_version": PARQUET_CONTAINER_VERSION,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def test_parquet_is_discoverable_as_semantic_generic_export() -> None:
    profiles = {
        profile.selector: profile
        for profile in ExportService().discover_exports().profiles
    }
    parquet = profiles[(PARQUET_CONTAINER_ID, PARQUET_CONTAINER_VERSION, None, None)]
    assert parquet.consumer_profile is None
    assert parquet.container_profile.determinism_claim == "semantic_content_only"
    assert parquet.supported_row_schemas == (
        "instruction_output",
        "messages",
        "prompt_completion",
        "text",
    )
    states = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    assert states[("physical_container", "parquet")] == "implemented"


def test_parquet_dry_run_plans_semantic_fingerprints_without_pyarrow(
    tmp_path: Path,
) -> None:
    assert "pyarrow" not in sys.modules
    bundle = _materialize_bundle(tmp_path)
    plan = ExportService().dry_run_export(
        ExportDryRunRequest(operation="dry_run", **_selection(bundle))
    )
    assert "pyarrow" not in sys.modules
    assert plan.container_profile.determinism_claim == "semantic_content_only"
    assert plan.consumer_profile is None
    by_path = {item.path: item for item in plan.file_plans}
    assert PARQUET_TRAIN_PATH in by_path
    assert PARQUET_EVALUATION_PATH in by_path
    train = by_path[PARQUET_TRAIN_PATH]
    assert train.membership_scope == "train"
    assert train.semantic_content_sha256 is not None
    assert train.expected_sha256 is None
    assert train.media_type == "application/vnd.apache.parquet"
    evaluation = by_path[PARQUET_EVALUATION_PATH]
    assert evaluation.membership_scope == "evaluation"
    assert evaluation.semantic_content_sha256 is not None
    assert evaluation.expected_sha256 is None


def test_parquet_execute_fails_closed_without_pyarrow(tmp_path: Path) -> None:
    if importlib.util.find_spec("pyarrow") is not None:
        pytest.skip("PyArrow is installed")
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **_selection(bundle))
    )
    destination = tmp_path / "out"
    with pytest.raises(ExportContractError, match="requires PyArrow.*columnar"):
        service.execute_export(
            ExportExecuteRequest(
                operation="execute",
                destination_root=str(destination),
                expected_export_plan_id=plan.export_plan_id,
                **_selection(bundle),
            )
        )
    assert "pyarrow" not in sys.modules
    assert not destination.exists()


def test_importing_parquet_module_does_not_import_pyarrow() -> None:
    assert "pyarrow" not in sys.modules
    from veriformis.exports import parquet as parquet_module

    assert parquet_module.PARQUET_CONTAINER_ID == "parquet"
    assert "pyarrow" not in sys.modules
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in toml
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pyarrow"\n' not in lock
