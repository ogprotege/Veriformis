"""Phase 7.8: JSON and CSV capture, refusals, and production round trips."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from veriformis.errors import ParseError, RowSourceError
from veriformis.exports.api import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportExecuteRequest,
)
from veriformis.exports.canonical_json import CanonicalJsonDataset
from veriformis.mapping import (
    FieldMapping,
    MappingPlan,
    capture_csv,
    capture_json,
    capture_jsonl,
    capture_row_source,
    mapping_confirmation_digest,
)
from veriformis.mapping.detect import detect_mapping
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace

FIXTURES = Path(__file__).parents[1] / "regressions" / "fixtures" / "phase7"
SERVICE = PipelineService()

SCHEMA_CASES = (
    (
        "text",
        "learn-the-text",
        "whole-text",
        (("text", "text"),),
    ),
    (
        "prompt_completion",
        "continue-a-passage",
        "prompt-and-completion",
        (("prompt", "prompt"), ("completion", "completion")),
    ),
    (
        "instruction_output",
        "continue-a-passage",
        "instruction-and-output",
        (
            ("instruction", "instruction"),
            ("input", "input"),
            ("output", "output"),
        ),
    ),
    (
        "messages",
        "continue-a-passage",
        "conversation",
        (("messages", "messages"),),
    ),
)

CONTAINER_EXPORT = {
    "jsonl": "split-jsonl-directory",
    "json": "json",
    "csv": "constrained-csv",
}


def _payloads(row_schema: str) -> list[dict[str, object]]:
    capture = capture_jsonl(
        FIXTURES / f"{row_schema}.jsonl",
        logical_path=f"{row_schema}.jsonl",
    )
    return [dict(record.payload) for record in capture.records]


def _write_source(
    tmp_path: Path,
    container: str,
    row_schema: str,
    payloads: list[dict[str, object]],
) -> Path:
    if container == "jsonl":
        path = tmp_path / f"{row_schema}.jsonl"
        path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in payloads),
            encoding="utf-8",
        )
        return path
    if container == "json":
        path = tmp_path / f"{row_schema}.json"
        path.write_text(json.dumps(payloads, ensure_ascii=False), encoding="utf-8")
        return path
    path = tmp_path / f"{row_schema}.csv"
    keys = list(payloads[0])
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=keys, lineterminator="\n")
    writer.writeheader()
    writer.writerows(payloads)
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path


def _plan(
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple,
    container_kind: str,
    source_digests: tuple[tuple[str, str], ...],
) -> MappingPlan:
    mappings = [
        FieldMapping.create(source_path=source, target_key=target)
        for source, target in pairs
    ]
    return MappingPlan.create(
        goal_id=goal,
        representation_id=representation,
        row_schema=row_schema,
        container_kind=container_kind,
        confirmation_digest=mapping_confirmation_digest(
            goal_id=goal,
            representation_id=representation,
            row_schema=row_schema,
            field_mappings=mappings,
            source_digests=source_digests,
        ),
        field_mappings=mappings,
    )


def _compile(
    tmp_path: Path,
    source: Path,
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple,
    container_kind: str,
) -> tuple[Path, str]:
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle"
    SERVICE.parse(
        [source],
        workspace,
        source_root=tmp_path,
        mode="dataset-row",
    )
    head = Workspace.open(workspace).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in head.sources.values()
    )
    plan = _plan(
        goal,
        representation,
        row_schema,
        pairs,
        container_kind,
        source_digests,
    )
    SERVICE.map_rows(
        workspace,
        goal=goal,
        representation=representation,
        mapping_plan=plan,
    )
    SERVICE.curate(workspace, goal=goal)
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    validated = SERVICE.validate(workspace)
    assert validated.exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    return sealed.publication.bundle_path, sealed.publication.manifest_sha256


def _export(
    bundle: Path,
    destination: Path,
    container_id: str,
    manifest_sha256: str,
) -> None:
    selection = {
        "schema_version": EXPORT_SURFACE_REQUEST_SCHEMA,
        "bundle": str(bundle),
        "container_id": container_id,
        "container_version": 1,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": manifest_sha256,
        "overwrite_policy": "refuse",
    }
    dry = SERVICE.dry_run_export(ExportDryRunRequest(operation="dry_run", **selection))
    assert dry.plan is not None
    SERVICE.execute_export(
        ExportExecuteRequest(
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=dry.plan.export_plan_id,
            **selection,
        )
    )


def _bundle_payloads(bundle: Path) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    train = capture_jsonl(bundle / "data" / "train.jsonl", logical_path="data/train.jsonl")
    evaluation = capture_jsonl(
        bundle / "data" / "evaluation.jsonl",
        logical_path="data/evaluation.jsonl",
    )
    return (
        [dict(record.payload) for record in train.records],
        [dict(record.payload) for record in evaluation.records],
    )


def _export_payloads(
    container_id: str,
    destination: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if container_id == "split-jsonl-directory":
        train = capture_jsonl(
            destination / "data" / "train.jsonl",
            logical_path="data/train.jsonl",
        )
        evaluation = capture_jsonl(
            destination / "data" / "evaluation.jsonl",
            logical_path="data/evaluation.jsonl",
        )
        return (
            [dict(record.payload) for record in train.records],
            [dict(record.payload) for record in evaluation.records],
        )
    if container_id == "json":
        dataset = CanonicalJsonDataset.from_json_bytes(
            (destination / "dataset.json").read_bytes()
        )
        return list(dataset.splits.train), list(dataset.splits.evaluation)
    train = capture_csv(destination / "data" / "train.csv", logical_path="data/train.csv")
    evaluation = capture_csv(
        destination / "data" / "evaluation.csv",
        logical_path="data/evaluation.csv",
    )
    return (
        [dict(record.payload) for record in train.records],
        [dict(record.payload) for record in evaluation.records],
    )


def test_json_array_and_records_object_capture(tmp_path: Path) -> None:
    array_path = tmp_path / "rows.json"
    array_path.write_text(
        json.dumps([{"text": "café one"}, {"text": "café two"}], ensure_ascii=False),
        encoding="utf-8",
    )
    array = capture_json(array_path, logical_path="rows.json")
    assert array.row_source.container_kind == "json"
    assert array.row_source.record_count == 2
    assert array.records[0].payload["text"] == "café one"
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(
        json.dumps({"records": [{"text": "Alpha"}, {"text": "Beta"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    records = capture_row_source(wrapped, logical_path="wrapped.json")
    assert [item.payload["text"] for item in records.records] == ["Alpha", "Beta"]
    rows_wrapped = tmp_path / "rows-key.json"
    rows_wrapped.write_text(
        json.dumps({"rows": [{"text": "Gamma"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert capture_json(rows_wrapped, logical_path="rows-key.json").records[0].payload[
        "text"
    ] == "Gamma"


def test_json_refusals(tmp_path: Path) -> None:
    scalar = tmp_path / "scalar.json"
    scalar.write_text('"hello"\n', encoding="utf-8")
    with pytest.raises(RowSourceError, match="scalar"):
        capture_json(scalar, logical_path="scalar.json")
    single = tmp_path / "single.json"
    single.write_text('{"text":"Alpha"}\n', encoding="utf-8")
    with pytest.raises(RowSourceError, match="array of objects"):
        capture_json(single, logical_path="single.json")
    mixed = tmp_path / "mixed.json"
    mixed.write_text('[{"text":"Alpha"}, "nope"]\n', encoding="utf-8")
    with pytest.raises(RowSourceError, match="non-object"):
        capture_json(mixed, logical_path="mixed.json")
    both = tmp_path / "both.json"
    both.write_text(
        json.dumps({"records": [{"text": "A"}], "rows": [{"text": "B"}]}),
        encoding="utf-8",
    )
    with pytest.raises(RowSourceError, match="both records and rows"):
        capture_json(both, logical_path="both.json")


def test_csv_keeps_padding_and_refuses_jagged_nested_and_messages(
    tmp_path: Path,
) -> None:
    padded = tmp_path / "padded.csv"
    padded.write_text("text\n  café \n", encoding="utf-8")
    capture = capture_csv(padded, logical_path="padded.csv")
    assert capture.records[0].payload["text"] == "  café "
    jagged = tmp_path / "jagged.csv"
    jagged.write_text("text,prompt\nonly-one\n", encoding="utf-8")
    with pytest.raises(RowSourceError, match="jagged"):
        capture_csv(jagged, logical_path="jagged.csv")
    nested = tmp_path / "nested.csv"
    nested.write_text('text\n"{""nested"":true}"\n', encoding="utf-8")
    with pytest.raises(RowSourceError, match="nested"):
        capture_csv(nested, logical_path="nested.csv")
    messages = tmp_path / "messages.csv"
    messages.write_text("messages\nuser\n", encoding="utf-8")
    with pytest.raises(RowSourceError, match="split-jsonl-directory or json"):
        capture_csv(messages, logical_path="messages.csv")


def test_json_nested_pointer_maps_text(tmp_path: Path) -> None:
    from veriformis.identity import derive_source_id
    from veriformis.mapping.execute import execute_mapping
    from veriformis.mapping.result import MappingRecipe

    source = tmp_path / "nested.json"
    source.write_text(
        json.dumps([{"user": {"text": "Alpha"}}], ensure_ascii=False),
        encoding="utf-8",
    )
    capture = capture_json(source, logical_path="nested.json")
    source_id = derive_source_id("nested.json", capture.row_source.sha256)
    mappings = [FieldMapping.create(source_path="/user/text", target_key="text")]
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="json",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=(("nested.json", capture.row_source.sha256),),
        ),
        field_mappings=mappings,
    )
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    records = execute_mapping(plan, capture, source_id=source_id, recipe=recipe)
    assert records[0].fields[0].value == "Alpha"


def test_csv_detector_proposes_flat_text(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("text\nAlpha\nBeta\n", encoding="utf-8")
    detected = detect_mapping(source, logical_path="rows.csv")
    assert detected["refusal"] is None
    schemas = {item["row_schema"] for item in detected["proposals"]}
    assert schemas == {"text"}
    assert detected["proposals"][0]["container_kind"] == "csv"


def test_document_mode_does_not_collapse_with_dataset_row(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    source.write_text(
        json.dumps([{"text": "Alpha café one."}, {"text": "Beta café two."}]),
        encoding="utf-8",
    )
    SERVICE.parse([source], tmp_path / "doc", source_root=tmp_path)
    SERVICE.parse(
        [source],
        tmp_path / "row",
        source_root=tmp_path,
        mode="dataset-row",
    )
    document = next(iter(Workspace.open(tmp_path / "doc").head().sources.values()))
    imported = next(iter(Workspace.open(tmp_path / "row").head().sources.values()))
    assert document.parser_id != imported.parser_id
    assert imported.parser_id == "row-json"
    assert document.document_artifact_id is not None
    assert imported.document_artifact_id is None


def test_mixed_parse_refuses_fused_document_and_csv(tmp_path: Path) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("A document paragraph.\n", encoding="utf-8")
    rows = tmp_path / "rows.csv"
    rows.write_text("text\nAlpha\n", encoding="utf-8")
    with pytest.raises(ParseError, match="distinct"):
        SERVICE.parse(
            [doc, rows],
            tmp_path / "ws",
            source_root=tmp_path,
            mode="mixed",
        )


ROUND_TRIP_CASES = [
    ("jsonl", *case)
    for case in SCHEMA_CASES
] + [
    ("json", *case)
    for case in SCHEMA_CASES
] + [
    ("csv", *case)
    for case in SCHEMA_CASES
    if case[0] != "messages"
]


@pytest.mark.parametrize(
    ("container", "row_schema", "goal", "representation", "pairs"),
    ROUND_TRIP_CASES,
)
def test_admitted_pairs_map_seal_and_export_semantically(
    tmp_path: Path,
    container: str,
    row_schema: str,
    goal: str,
    representation: str,
    pairs: tuple,
) -> None:
    payloads = _payloads(row_schema)
    source = _write_source(tmp_path, container, row_schema, payloads)
    bundle, manifest_sha256 = _compile(
        tmp_path,
        source,
        goal,
        representation,
        row_schema,
        pairs,
        container,
    )
    expected_train, expected_evaluation = _bundle_payloads(bundle)
    assert expected_train
    assert expected_evaluation
    destination = tmp_path / "export"
    _export(
        bundle,
        destination,
        CONTAINER_EXPORT[container],
        manifest_sha256,
    )
    exported_train, exported_evaluation = _export_payloads(
        CONTAINER_EXPORT[container],
        destination,
    )
    assert exported_train == expected_train
    assert exported_evaluation == expected_evaluation
