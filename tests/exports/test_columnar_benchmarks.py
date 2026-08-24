"""Phase 9.8: measure JSONL versus columnar sizes. No storage recommendation."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportService,
)
from veriformis.identity import sha256_digest

pytestmark = pytest.mark.columnar_integration

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
CONTAINERS = (
    "split-jsonl-directory",
    "parquet",
    "arrow",
    "hugging-face-dataset",
)


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


def _selection(bundle: Path, container_id: str) -> dict[str, object]:
    return {
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


def _tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def test_jsonl_versus_columnar_tree_sizes_are_measured(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    datasets = pytest.importorskip("datasets")
    if not callable(getattr(datasets, "DatasetDict", None)):
        pytest.skip("huggingface datasets extra is not installed")
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    sizes: dict[str, int] = {}
    for container_id in CONTAINERS:
        plan = service.dry_run_export(
            ExportDryRunRequest(
                operation="dry_run", **_selection(bundle, container_id)
            )
        )
        destination = tmp_path / container_id
        service.execute_export(
            ExportExecuteRequest(
                operation="execute",
                destination_root=str(destination),
                expected_export_plan_id=plan.export_plan_id,
                **_selection(bundle, container_id),
            )
        )
        sizes[container_id] = _tree_bytes(destination)
        assert sizes[container_id] > 0
    assert set(sizes) == set(CONTAINERS)
    # Item 9.8 records these sizes. It does not recommend a container by size.
    record = tmp_path / "columnar-benchmark-tree-bytes.json"
    record.write_text(json.dumps(sizes, sort_keys=True) + "\n", encoding="utf-8")
    assert json.loads(record.read_text(encoding="utf-8")) == sizes
