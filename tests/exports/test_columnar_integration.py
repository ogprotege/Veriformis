"""Phase 9.8: load columnar exports through PyArrow and Hugging Face Datasets."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from veriformis.datasets import ProductRow, RowSet, row_provenance_from_json_bytes
from veriformis.errors import ExportVerificationError, RowSourceError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
    ExportService,
    ExportVerifyRequest,
)
from veriformis.exports import arrow as arrow_module
from veriformis.exports import hugging_face_dataset as hf_module
from veriformis.exports import parquet as parquet_module
from veriformis.exports.arrow import ARROW_EVALUATION_PATH, ARROW_TRAIN_PATH
from veriformis.exports.columnar_fingerprint import columnar_partition_fingerprint
from veriformis.exports.hugging_face_dataset import (
    HF_DATASET_ROOT,
    HF_EVALUATION_ARROW_PATH,
    HF_TRAIN_ARROW_PATH,
)
from veriformis.exports.parquet import PARQUET_EVALUATION_PATH, PARQUET_TRAIN_PATH
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest
from veriformis.mapping import capture_row_source

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
ROW_SCHEMAS = ("instruction_output", "messages", "prompt_completion", "text")
UNICODE = 'quoted \\ composed=\u00e9 decomposed=e\u0301 \U0001f600'


def _require_pyarrow() -> Any:
    return pytest.importorskip("pyarrow")


def _require_datasets() -> Any:
    datasets = pytest.importorskip("datasets")
    if not all(
        callable(getattr(datasets, name, None))
        for name in ("Dataset", "DatasetDict", "Features", "Sequence", "Value")
    ):
        pytest.skip("huggingface datasets extra is not installed")
    return datasets


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


def _publish(tmp_path: Path, container_id: str) -> tuple[Path, Path, Any]:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    plan = service.dry_run_export(
        ExportDryRunRequest(operation="dry_run", **_selection(bundle, container_id))
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
    verified = service.verify_export(
        ExportVerifyRequest(
            operation="verify",
            destination_root=str(destination),
            expected_export_plan_id=plan.export_plan_id,
            **_selection(bundle, container_id),
        )
    )
    return bundle, destination, verified


def _source_row_set(bundle: Path) -> RowSet:
    return ExportService().verified_source(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    ).row_set


def _payload(row_schema: str, value: str) -> dict[str, Any]:
    exact = f"{value}\n{UNICODE}"
    if row_schema == "text":
        return {"text": exact}
    if row_schema == "prompt_completion":
        return {"prompt": f"context:{exact}", "completion": f"target:{exact}"}
    if row_schema == "instruction_output":
        return {
            "instruction": "Preserve the exact value.",
            "input": f"context:{exact}",
            "output": f"target:{exact}",
        }
    assert row_schema == "messages"
    return {
        "messages": [
            {"role": "user", "content": f"context:{exact}"},
            {"role": "assistant", "content": f"target:{exact}"},
        ]
    }


def _row_set_for_schema(source: RowSet, row_schema: str) -> RowSet:
    source_rows = (*source.train_rows, *source.evaluation_rows)
    converted = tuple(
        ProductRow.create(
            record_id=row.record_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            payload=_payload(row_schema, str(index)),
        )
        for index, row in enumerate(source_rows)
    )
    converted_by_record = {row.record_id: row for row in converted}
    provenance = []
    for item in source.provenance:
        row = converted_by_record[item.record_id]
        body = item.model_dump(mode="json", exclude={"provenance_id"})
        body.update(row_id=row.row_id, payload_sha256=row.payload_sha256)
        provenance.append(
            row_provenance_from_json_bytes(
                lossless_json_bytes({"provenance_id": derive_id("prv", body), **body})
            )
        )
    train_count = source.train_row_count
    return RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=row_schema,  # type: ignore[arg-type]
        train_rows=converted[:train_count],
        evaluation_rows=converted[train_count:],
        provenance=provenance,
    )


def test_parquet_and_arrow_reload_through_pyarrow(tmp_path: Path) -> None:
    pa = _require_pyarrow()
    pq = pytest.importorskip("pyarrow.parquet")
    ipc = pytest.importorskip("pyarrow.ipc")
    bundle, parquet_root, _verified = _publish(tmp_path / "parquet", "parquet")
    _, arrow_root, _ = _publish(tmp_path / "arrow", "arrow")
    source = _source_row_set(bundle)
    expected_train = [dict(row.payload) for row in source.train_rows]
    expected_eval = [dict(row.payload) for row in source.evaluation_rows]
    parquet_train = pq.read_table(parquet_root / PARQUET_TRAIN_PATH).to_pylist()
    parquet_eval = pq.read_table(parquet_root / PARQUET_EVALUATION_PATH).to_pylist()
    arrow_train = ipc.open_file(arrow_root / ARROW_TRAIN_PATH).read_all().to_pylist()
    arrow_eval = ipc.open_file(arrow_root / ARROW_EVALUATION_PATH).read_all().to_pylist()
    assert parquet_train == expected_train == arrow_train
    assert parquet_eval == expected_eval == arrow_eval
    digest = columnar_partition_fingerprint(
        row_schema="text",
        partition="train",
        payloads=tuple(expected_train),
    )
    assert (
        columnar_partition_fingerprint(
            row_schema="text",
            partition="train",
            payloads=tuple(parquet_train),
        )
        == digest
    )
    assert pa.schema([]) is not None


def test_hugging_face_dataset_reloads_through_load_from_disk(tmp_path: Path) -> None:
    datasets = _require_datasets()
    bundle, destination, _verified = _publish(
        tmp_path, "hugging-face-dataset"
    )
    source = _source_row_set(bundle)
    loaded = datasets.load_from_disk(str(destination / HF_DATASET_ROOT))
    assert set(loaded) == {"train", "evaluation"}
    assert [dict(row) for row in loaded["train"]] == [
        dict(row.payload) for row in source.train_rows
    ]
    assert [dict(row) for row in loaded["evaluation"]] == [
        dict(row.payload) for row in source.evaluation_rows
    ]
    train_files = sorted((destination / "dataset" / "train").glob("data-*.arrow"))
    assert [path.name for path in train_files] == ["data-00000-of-00001.arrow"]
    assert (destination / HF_TRAIN_ARROW_PATH).is_file()
    assert (destination / HF_EVALUATION_ARROW_PATH).is_file()


@pytest.mark.parametrize("row_schema", ROW_SCHEMAS)
def test_every_row_schema_round_trips_with_identical_fingerprints(
    tmp_path: Path, row_schema: str
) -> None:
    _require_pyarrow()
    _require_datasets()
    bundle = _materialize_bundle(tmp_path)
    row_set = _row_set_for_schema(_source_row_set(bundle), row_schema)
    train = tuple(dict(row.payload) for row in row_set.train_rows)
    evaluation = tuple(dict(row.payload) for row in row_set.evaluation_rows)
    digest = columnar_partition_fingerprint(
        row_schema=row_schema,  # type: ignore[arg-type]
        partition="train",
        payloads=train,
    )
    parquet_train = parquet_module._read_partition_payloads(
        parquet_module._partition_parquet_bytes(row_set.train_rows, row_schema),
        row_schema,
    )
    arrow_train = arrow_module._read_partition_payloads(
        arrow_module._partition_arrow_bytes(row_set.train_rows, row_schema),
        row_schema,
    )
    hf_files = hf_module._dataset_dict_files(row_set)
    hf_train = hf_module._read_partition_payloads(hf_files[HF_TRAIN_ARROW_PATH])
    hf_eval = hf_module._read_partition_payloads(hf_files[HF_EVALUATION_ARROW_PATH])
    parquet_eval = parquet_module._read_partition_payloads(
        parquet_module._partition_parquet_bytes(row_set.evaluation_rows, row_schema),
        row_schema,
    )
    arrow_eval = arrow_module._read_partition_payloads(
        arrow_module._partition_arrow_bytes(row_set.evaluation_rows, row_schema),
        row_schema,
    )
    assert parquet_train == train == arrow_train == hf_train
    assert evaluation == parquet_eval == arrow_eval == hf_eval
    assert (
        columnar_partition_fingerprint(
            row_schema=row_schema,  # type: ignore[arg-type]
            partition="train",
            payloads=parquet_train,
        )
        == digest
    )
    if row_schema == "messages":
        for payload in (*hf_train, *parquet_train, *arrow_train):
            turns = payload["messages"]
            assert [turn["role"] for turn in turns] == ["user", "assistant"]
            assert list(turns[0]) == ["role", "content"]


def test_empty_evaluation_and_large_unicode_values_round_trip(tmp_path: Path) -> None:
    _require_pyarrow()
    _require_datasets()
    huge = ("α" * 80_000) + UNICODE
    row = ProductRow.create(
        record_id="rec-v1-" + ("a" * 64),
        row_schema="text",
        payload={"text": huge},
    )
    encoded = parquet_module._partition_parquet_bytes((row,), "text")
    empty = parquet_module._partition_parquet_bytes((), "text")
    assert parquet_module._read_partition_payloads(encoded, "text") == (
        {"text": huge},
    )
    assert parquet_module._read_partition_payloads(empty, "text") == ()
    arrow_empty = arrow_module._read_partition_payloads(
        arrow_module._partition_arrow_bytes((), "text"),
        "text",
    )
    assert arrow_empty == ()
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    for row_schema in ("text", "messages"):
        row_set = _row_set_for_schema(source, row_schema)
        train_only = RowSet.create(
            plan_id=row_set.plan_id,
            serialization_plan_id=row_set.serialization_plan_id,
            recipe_id=row_set.recipe_id,
            construction_result_id=row_set.construction_result_id,
            curation_result_id=row_set.curation_result_id,
            split_result_id=row_set.split_result_id,
            row_schema=row_schema,  # type: ignore[arg-type]
            train_rows=row_set.train_rows,
            evaluation_rows=(),
            provenance=tuple(
                item
                for item in row_set.provenance
                if item.record_id in {row.record_id for row in row_set.train_rows}
            ),
        )
        files = hf_module._dataset_dict_files(train_only)
        assert HF_EVALUATION_ARROW_PATH in files
        assert hf_module._read_partition_payloads(files[HF_EVALUATION_ARROW_PATH]) == ()
        assert hf_module._read_partition_payloads(files[HF_TRAIN_ARROW_PATH]) == tuple(
            dict(item.payload) for item in train_only.train_rows
        )


def test_null_column_fails_in_veriformis_before_mapping(tmp_path: Path) -> None:
    pa = _require_pyarrow()
    pq = pytest.importorskip("pyarrow.parquet")
    schema = pa.schema([pa.field("text", pa.string(), nullable=True)])
    table = pa.Table.from_pylist([{"text": None}], schema=schema)
    path = tmp_path / "nulls.parquet"
    pq.write_table(table, path)
    with pytest.raises(RowSourceError, match="null is unrepresentable"):
        capture_row_source(path, logical_path="nulls.parquet")


def test_schema_evolution_fails_closed_on_reload() -> None:
    pa = _require_pyarrow()
    pq = pytest.importorskip("pyarrow.parquet")
    schema = pa.schema(
        [
            pa.field("text", pa.string(), nullable=False),
            pa.field("extra", pa.string(), nullable=False),
        ]
    )
    table = pa.Table.from_pylist([{"text": "alpha", "extra": "beta"}], schema=schema)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink, compression="none")
    with pytest.raises(ExportVerificationError, match="schema differs"):
        parquet_module._read_partition_payloads(bytes(sink.getvalue()), "text")


def test_extra_dataset_shard_fails_verify(tmp_path: Path) -> None:
    _require_datasets()
    bundle, destination, verified = _publish(tmp_path, "hugging-face-dataset")
    extra = destination / "dataset" / "train" / "data-00001-of-00002.arrow"
    extra.write_bytes((destination / HF_TRAIN_ARROW_PATH).read_bytes())
    service = ExportService()
    with pytest.raises(ExportVerificationError):
        service.verify_export(
            ExportVerifyRequest(
                operation="verify",
                destination_root=str(destination),
                expected_export_plan_id=verified.verification.export_plan_id,
                **_selection(bundle, "hugging-face-dataset"),
            )
        )


def test_parquet_mapping_capture_round_trips_payloads(tmp_path: Path) -> None:
    _require_pyarrow()
    bundle, destination, _verified = _publish(tmp_path, "parquet")
    source = _source_row_set(bundle)
    captured = capture_row_source(
        destination / PARQUET_TRAIN_PATH,
        logical_path="data/train.parquet",
    )
    assert [record.payload for record in captured.records] == [
        dict(row.payload) for row in source.train_rows
    ]
    assert captured.row_source.container_kind == "parquet"
