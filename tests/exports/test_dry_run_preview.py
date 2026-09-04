"""Phase 5.6 exact, destination-free dry-run preview contracts."""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent
from typer.testing import CliRunner

import veriformis.cli as cli_module
from veriformis.cli import app
from veriformis.datasets import (
    ProductRow,
    RowSet,
    row_provenance_from_json_bytes,
)
from veriformis.errors import ExportContractError
from veriformis.exports import (
    CANONICAL_JSON_CONTAINER_ID,
    CANONICAL_JSON_CONTAINER_VERSION,
    CANONICAL_JSON_DATASET_PATH,
    CANONICAL_JSON_PROVENANCE_PATH,
    CANONICAL_JSON_README_PATH,
    CONSTRAINED_CSV_CONTAINER_ID,
    CONSTRAINED_CSV_CONTAINER_VERSION,
    CONSTRAINED_CSV_DATA_CARD_PATH,
    CONSTRAINED_CSV_EVALUATION_PATH,
    CONSTRAINED_CSV_PROVENANCE_PATH,
    CONSTRAINED_CSV_README_PATH,
    CONSTRAINED_CSV_TRAIN_PATH,
    EXPORT_DRY_RUN_PREVIEW_SCHEMA,
    EXPORT_RECEIPT_PATH,
    EXPORT_SURFACE_REQUEST_SCHEMA,
    EXPORT_SURFACE_REQUEST_SCHEMA_V2,
    EXPORT_SURFACE_RESPONSE_SCHEMA,
    EXPORT_SURFACE_RESPONSE_SCHEMA_V2,
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
    SPLIT_JSONL_DATA_CARD_PATH,
    SPLIT_JSONL_README_PATH,
    ExportDryRunPreview,
    ExportDryRunRequest,
    ExportDryRunRequestV2,
    ExportExecuteRequest,
    ExportExecuteRequestV2,
    ExportFilePlan,
    ExportPlan,
    ExportService,
    SplitJsonlOptions,
    export_dry_run_preview_response,
    export_dry_run_response,
    export_error_response,
    export_response_json,
)
from veriformis.exports import api as api_module
from veriformis.exports import service as service_module
from veriformis.identity import derive_id, lossless_json_bytes, sha256_digest
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import ExportPlanOutcome

from test_api import (
    EXPECTED_MANIFEST_SHA256,
    _dry_run_request,
    _materialize_bundle,
    _service,
    _tree_bytes,
)
from test_constrained_csv import (
    _dry as _csv_dry_run_request,
    _payload as _schema_payload,
    _row_set_for_schema,
)
from test_semantic_round_trip import (
    ROUND_TRIP_FIXTURE,
    ROUND_TRIP_FIXTURE_SHA256,
    SUCCESSFUL_PAIRS,
    _strict_fixture_object,
    _reload_export,
    _row_set_for_schema as _semantic_row_set_for_schema,
)


def _selection(
    bundle: Path,
    *,
    container_id: str,
    container_version: int,
) -> dict[str, object]:
    return {
        "bundle": str(bundle),
        "container_id": container_id,
        "container_version": container_version,
        "consumer_id": None,
        "consumer_profile_version": None,
        "source_trust_policy": "require_external_digest",
        "expected_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "overwrite_policy": "refuse",
    }


def _dry_request(
    bundle: Path,
    *,
    container_id: str,
    container_version: int,
) -> ExportDryRunRequest:
    return ExportDryRunRequest(
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
        operation="dry_run",
        **_selection(
            bundle,
            container_id=container_id,
            container_version=container_version,
        ),
    )


def _source_row_set(bundle: Path) -> RowSet:
    return ExportService().verified_source(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    ).row_set


def _rebuild_row_set(
    source: RowSet,
    *,
    train: tuple[tuple[ProductRow, dict[str, Any]], ...],
    evaluation: tuple[tuple[ProductRow, dict[str, Any]], ...],
) -> RowSet:
    provenance_by_record = {item.record_id: item for item in source.provenance}
    rebuilt_rows: list[ProductRow] = []
    rebuilt_provenance = []
    for partition, pairs in (("train", train), ("evaluation", evaluation)):
        for ordinal, (prior_row, payload) in enumerate(pairs):
            row = ProductRow.create(
                record_id=prior_row.record_id,
                row_schema=source.row_schema,
                payload=payload,
            )
            prior = provenance_by_record[row.record_id]
            body = prior.model_dump(mode="json", exclude={"provenance_id"})
            body.update(
                partition=partition,
                ordinal=ordinal,
                row_id=row.row_id,
                payload_sha256=row.payload_sha256,
            )
            rebuilt_rows.append(row)
            rebuilt_provenance.append(
                row_provenance_from_json_bytes(
                    lossless_json_bytes(
                        {"provenance_id": derive_id("prv", body), **body}
                    )
                )
            )

    train_count = len(train)
    return RowSet.create(
        plan_id=source.plan_id,
        serialization_plan_id=source.serialization_plan_id,
        recipe_id=source.recipe_id,
        construction_result_id=source.construction_result_id,
        curation_result_id=source.curation_result_id,
        split_result_id=source.split_result_id,
        row_schema=source.row_schema,
        train_rows=rebuilt_rows[:train_count],
        evaluation_rows=rebuilt_rows[train_count:],
        provenance=rebuilt_provenance,
    )


def _plan_for_row_set(base: ExportPlan, row_set: RowSet) -> ExportPlan:
    membership = service_module._membership_projection_from_row_set(row_set)
    counts = {
        "all": row_set.total_row_count,
        "evaluation": row_set.evaluation_row_count,
        "train": row_set.train_row_count,
    }
    file_plans = tuple(
        ExportFilePlan.create(
            path=item.path,
            role=item.role,
            media_type=item.media_type,
            membership_scope=item.membership_scope,
            record_count=(
                None
                if item.membership_scope == "none"
                else counts[item.membership_scope]
            ),
            semantic_content_sha256=item.semantic_content_sha256,
            expected_sha256=item.expected_sha256,
            expected_byte_size=item.expected_byte_size,
        )
        for item in base.file_plans
    )
    return ExportPlan.create(
        source_bundle_id=base.source_bundle_id,
        source_manifest_sha256=base.source_manifest_sha256,
        source_content_root_sha256=base.source_content_root_sha256,
        source_verification_id=base.source_verification_id,
        source_trust_policy=base.source_trust_policy,
        source_trust_grade=base.source_trust_grade,
        dataset_snapshot_id=base.dataset_snapshot_id,
        validation_report_id=base.validation_report_id,
        finished_dataset_plan_id=base.finished_dataset_plan_id,
        recipe_id=base.recipe_id,
        objective_id=base.objective_id,
        construction_result_id=base.construction_result_id,
        curation_result_id=base.curation_result_id,
        serialization_plan_id=row_set.serialization_plan_id,
        split_result_id=row_set.split_result_id,
        row_set_id=row_set.row_set_id,
        source_ids=base.source_ids,
        row_schema=row_set.row_schema,
        container_profile=base.container_profile,
        consumer_profile=base.consumer_profile,
        dependencies=base.dependencies,
        membership_projection=membership,
        file_plans=file_plans,
    )


def _sample_payloads(preview: ExportDryRunPreview) -> list[dict[str, Any]]:
    return [item["payload"] for item in preview.to_dict()["sample_rows"]]


def _published_relative_files(destination: Path) -> list[str]:
    return sorted(
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    )


@pytest.fixture(scope="module")
def semantic_round_trip_fixture() -> dict[str, Any]:
    data = ROUND_TRIP_FIXTURE.read_bytes()
    assert sha256_digest(data) == ROUND_TRIP_FIXTURE_SHA256
    return _strict_fixture_object(data)


async def _call_tool_async(server, name: str, arguments: dict[str, str]) -> str:
    result = await server.call_tool(name, arguments)
    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, TextContent)
    return content.text


def _call_tool(server, name: str, arguments: dict[str, str]) -> str:
    return asyncio.run(_call_tool_async(server, name, arguments))


def test_service_preview_uses_one_snapshot_and_neither_renders_nor_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source_before = _tree_bytes(bundle)
    destination = tmp_path / "preview-must-not-exist"
    service, runtime = _service()
    original = service_module._source_plan_evidence
    captured: list[RowSet] = []

    def capture(source):
        evidence = original(source)
        captured.append(evidence[1])
        return evidence

    monkeypatch.setattr(service_module, "_source_plan_evidence", capture)
    preview = service.dry_run_export_preview(_dry_run_request(bundle))

    assert len(captured) == 1
    assert runtime.planner_calls == 1
    assert runtime.render_calls == 0
    assert not destination.exists()
    assert _tree_bytes(bundle) == source_before

    row_set = captured[0]
    rows = (row_set.train_rows[0], row_set.evaluation_rows[0])
    response = export_dry_run_preview_response(preview)
    assert response["schema_version"] == EXPORT_SURFACE_RESPONSE_SCHEMA_V2
    assert set(response["result"]) == {"plan", "preview"}
    body = response["result"]["preview"]
    assert set(body) == {
        "container_profile_id",
        "destination_tree",
        "export_plan_id",
        "maximum_sample_payload_bytes",
        "row_schema",
        "row_set_id",
        "sample_policy",
        "sample_rows",
        "schema_version",
    }
    assert body["schema_version"] == EXPORT_DRY_RUN_PREVIEW_SCHEMA
    assert body["export_plan_id"] == preview.plan.export_plan_id
    assert body["container_profile_id"] == (
        preview.plan.container_profile.container_profile_id
    )
    assert body["row_set_id"] == preview.plan.row_set_id
    assert body["row_schema"] == "text"
    assert body["sample_policy"] == "first-row-per-non-empty-partition"
    assert body["maximum_sample_payload_bytes"] == 65536
    assert body["destination_tree"] == {
        "directories": ["data", "metadata"],
        "files": [
            "data/evaluation.jsonl",
            "data/train.jsonl",
            EXPORT_RECEIPT_PATH,
            "metadata/schema.json",
        ],
    }
    assert [item["partition"] for item in body["sample_rows"]] == [
        "train",
        "evaluation",
    ]
    for sample, row in zip(body["sample_rows"], rows, strict=True):
        assert set(sample) == {
            "omission_reason",
            "ordinal",
            "partition",
            "payload",
            "payload_byte_size",
            "payload_sha256",
        }
        assert sample["ordinal"] == 0
        assert sample["payload"] == row.payload
        assert set(sample["payload"]) == {"text"}
        assert sample["payload_sha256"] == row.payload_sha256
        assert sample["payload_byte_size"] == len(lossless_json_bytes(row.payload))
        assert sample["omission_reason"] is None

    frozen_response = export_dry_run_preview_response(preview)
    row_set.train_rows[0].payload["text"] = "post-preview mutation"
    assert export_dry_run_preview_response(preview) == frozen_response


def test_configured_split_tree_uses_exact_names_and_excludes_provenance(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    options = SplitJsonlOptions(
        train_partition_name="learn",
        evaluation_partition_name="score",
        include_provenance=False,
    )
    request = ExportDryRunRequestV2(
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2,
        operation="dry_run",
        container_options=options.model_dump(mode="json"),
        **_selection(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        ),
    )

    service = ExportService()
    preview = service.dry_run_export_preview(request)
    tree = preview.to_dict()["destination_tree"]

    assert tree == {
        "directories": ["data", "metadata"],
        "files": [
            SPLIT_JSONL_README_PATH,
            "data/learn.jsonl",
            "data/score.jsonl",
            EXPORT_RECEIPT_PATH,
            SPLIT_JSONL_DATA_CARD_PATH,
        ],
    }
    assert all("provenance" not in path for path in tree["files"])
    assert all("staging" not in path and "archive" not in path for path in tree["files"])

    destination = tmp_path / "configured-split-output"
    service.execute_export(
        ExportExecuteRequestV2(
            schema_version=EXPORT_SURFACE_REQUEST_SCHEMA_V2,
            operation="execute",
            container_options=options.model_dump(mode="json"),
            destination_root=str(destination),
            expected_export_plan_id=preview.plan.export_plan_id,
            **_selection(
                bundle,
                container_id=SPLIT_JSONL_CONTAINER_ID,
                container_version=SPLIT_JSONL_CONTAINER_VERSION,
            ),
        )
    )
    assert _published_relative_files(destination) == tree["files"]


@pytest.mark.parametrize(("container_id", "row_schema"), SUCCESSFUL_PAIRS)
def test_every_compatible_preview_matches_strictly_reloaded_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    semantic_round_trip_fixture: dict[str, Any],
    container_id: str,
    row_schema: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service = ExportService()
    admitted = service.verified_source(
        bundle,
        expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
    )
    report, source, verification, objective_id, _ = (
        service_module._source_plan_evidence(admitted)
    )
    converted = _semantic_row_set_for_schema(
        source,
        semantic_round_trip_fixture,
        row_schema,
    )
    snapshot = report.snapshot
    closed_snapshot = SimpleNamespace(
        snapshot_id=snapshot.snapshot_id,
        plan_id=snapshot.plan_id,
        recipe_id=snapshot.recipe_id,
        construction_result_id=snapshot.construction_result_id,
        curation_result_id=snapshot.curation_result_id,
        split_result_id=snapshot.split_result_id,
        row_set_id=converted.row_set_id,
        source_ids=snapshot.source_ids,
    )
    closed_report = SimpleNamespace(
        report_id=report.report_id,
        snapshot=closed_snapshot,
    )
    closed_evidence = (
        closed_report,
        converted,
        verification,
        objective_id,
        service_module._membership_projection_from_row_set(converted),
    )
    monkeypatch.setattr(
        service_module,
        "_source_plan_evidence",
        lambda _source: closed_evidence,
    )
    request = _dry_request(
        bundle,
        container_id=container_id,
        container_version=1,
    )
    preview = service.dry_run_export_preview(request)
    preview_body = preview.to_dict()
    destination = tmp_path / f"executed-{container_id}-{row_schema}"

    service.execute_export(
        ExportExecuteRequest(
            schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
            operation="execute",
            destination_root=str(destination),
            expected_export_plan_id=preview.plan.export_plan_id,
            **_selection(
                bundle,
                container_id=container_id,
                container_version=1,
            ),
        )
    )

    assert _published_relative_files(destination) == preview_body[
        "destination_tree"
    ]["files"]
    reloaded = _reload_export(container_id, destination)
    assert reloaded.row_set == converted
    partitions = {
        "train": reloaded.train_payloads,
        "evaluation": reloaded.evaluation_payloads,
    }
    for sample in preview_body["sample_rows"]:
        executed_payload = partitions[sample["partition"]][sample["ordinal"]]
        assert sample["omission_reason"] is None
        assert sample["payload"] == executed_payload
        executed_payload_bytes = lossless_json_bytes(executed_payload)
        assert sample["payload_byte_size"] == len(executed_payload_bytes)
        assert sample["payload_sha256"] == sha256_digest(executed_payload_bytes)


@pytest.mark.parametrize(
    ("container_id", "container_version", "expected_directories", "expected_files"),
    (
        (
            CANONICAL_JSON_CONTAINER_ID,
            CANONICAL_JSON_CONTAINER_VERSION,
            ["metadata"],
            [
                CANONICAL_JSON_README_PATH,
                CANONICAL_JSON_DATASET_PATH,
                EXPORT_RECEIPT_PATH,
                CANONICAL_JSON_PROVENANCE_PATH,
            ],
        ),
        (
            CONSTRAINED_CSV_CONTAINER_ID,
            CONSTRAINED_CSV_CONTAINER_VERSION,
            ["data", "metadata"],
            [
                CONSTRAINED_CSV_README_PATH,
                CONSTRAINED_CSV_EVALUATION_PATH,
                CONSTRAINED_CSV_TRAIN_PATH,
                EXPORT_RECEIPT_PATH,
                CONSTRAINED_CSV_DATA_CARD_PATH,
                CONSTRAINED_CSV_PROVENANCE_PATH,
            ],
        ),
    ),
)
def test_fixed_profile_destination_tree_matches_the_planned_output(
    tmp_path: Path,
    container_id: str,
    container_version: int,
    expected_directories: list[str],
    expected_files: list[str],
) -> None:
    bundle = _materialize_bundle(tmp_path)
    request = _dry_request(
        bundle,
        container_id=container_id,
        container_version=container_version,
    )

    tree = ExportService().dry_run_export_preview(request).to_dict()[
        "destination_tree"
    ]

    assert tree == {
        "directories": expected_directories,
        "files": sorted(expected_files),
    }


@pytest.mark.parametrize(
    "row_schema",
    ("text", "prompt_completion", "instruction_output", "messages"),
)
def test_sample_is_the_complete_payload_for_every_supported_row_schema(
    tmp_path: Path,
    row_schema: str,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    service = ExportService()
    base = service.dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    converted = _row_set_for_schema(source, row_schema)
    plan = _plan_for_row_set(base, converted)

    payloads = _sample_payloads(
        ExportDryRunPreview.create(plan=plan, row_set=converted)
    )

    assert payloads == [
        converted.train_rows[0].payload,
        converted.evaluation_rows[0].payload,
    ]
    assert payloads[0] == _schema_payload(row_schema, "0")


def test_empty_evaluation_emits_only_the_train_sample(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    base = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    all_rows = tuple(
        sorted(
            (*source.train_rows, *source.evaluation_rows),
            key=lambda row: row.record_id,
        )
    )
    train = tuple((row, dict(row.payload)) for row in all_rows)
    row_set = _rebuild_row_set(source, train=train, evaluation=())
    preview = ExportDryRunPreview.create(
        plan=_plan_for_row_set(base, row_set),
        row_set=row_set,
    )

    samples = preview.to_dict()["sample_rows"]
    assert [item["partition"] for item in samples] == ["train"]
    assert samples[0]["payload"] == row_set.train_rows[0].payload


def test_exact_payload_limit_is_included_whole(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    base = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    empty_payload_size = len(lossless_json_bytes({"text": ""}))
    exact_payload = {"text": "x" * (65_536 - empty_payload_size)}
    assert len(lossless_json_bytes(exact_payload)) == 65_536
    row_set = _rebuild_row_set(
        source,
        train=(
            (source.train_rows[0], exact_payload),
            *((row, dict(row.payload)) for row in source.train_rows[1:]),
        ),
        evaluation=tuple(
            (row, dict(row.payload)) for row in source.evaluation_rows
        ),
    )

    sample = ExportDryRunPreview.create(
        plan=_plan_for_row_set(base, row_set),
        row_set=row_set,
    ).to_dict()["sample_rows"][0]

    assert sample["payload"] == exact_payload
    assert sample["payload_byte_size"] == 65_536
    assert sample["payload_sha256"] == row_set.train_rows[0].payload_sha256
    assert sample["omission_reason"] is None


def test_large_samples_are_omitted_whole_by_exact_reason_and_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    base = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    train_source = source.train_rows[0]
    evaluation_source = source.evaluation_rows
    over_limit = {"text": "x" * 65536}
    row_set = _rebuild_row_set(
        source,
        train=((train_source, over_limit),),
        evaluation=tuple((row, dict(row.payload)) for row in evaluation_source),
    )
    preview = ExportDryRunPreview.create(
        plan=_plan_for_row_set(base, row_set),
        row_set=row_set,
    )
    samples = preview.to_dict()["sample_rows"]

    assert [item["partition"] for item in samples] == ["train", "evaluation"]
    assert samples[0]["payload"] is None
    assert samples[0]["payload_byte_size"] == len(lossless_json_bytes(over_limit))
    assert samples[0]["omission_reason"] == "exact-payload-exceeds-preview-limit"
    assert samples[1]["payload"] == row_set.evaluation_rows[0].payload
    assert len(
        export_response_json(export_dry_run_preview_response(preview)).encode(
            "ascii"
        )
    ) <= 256 * 1024

    under_limit_payload = {"text": "y" * 50000}
    response_row_set = _rebuild_row_set(
        source,
        train=((train_source, under_limit_payload),),
        evaluation=(
            (evaluation_source[0], {"text": "z" * 50000}),
            (evaluation_source[1], dict(evaluation_source[1].payload)),
        ),
    )
    response_plan = _plan_for_row_set(base, response_row_set)
    complete = ExportDryRunPreview.create(
        plan=response_plan,
        row_set=response_row_set,
    )
    full_size = len(
        export_response_json(export_dry_run_preview_response(complete)).encode(
            "ascii"
        )
    )
    monkeypatch.setattr(
        api_module,
        "_MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES",
        full_size - 1,
    )

    budgeted = ExportDryRunPreview.create(
        plan=response_plan,
        row_set=response_row_set,
    )
    budgeted_samples = budgeted.to_dict()["sample_rows"]
    budgeted_size = len(
        export_response_json(export_dry_run_preview_response(budgeted)).encode(
            "ascii"
        )
    )

    assert [item["partition"] for item in budgeted_samples] == [
        "train",
        "evaluation",
    ]
    assert budgeted_samples[0]["payload"] == under_limit_payload
    assert budgeted_samples[0]["omission_reason"] is None
    assert budgeted_samples[1]["payload"] is None
    assert budgeted_samples[1]["omission_reason"] == (
        "exact-payload-exceeds-response-budget"
    )
    assert budgeted_size <= full_size - 1


def test_response_budget_falls_back_from_evaluation_to_train_then_refuses_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    base = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    row_set = _rebuild_row_set(
        source,
        train=(
            (source.train_rows[0], {"text": "t" * 50_000}),
            *((row, dict(row.payload)) for row in source.train_rows[1:]),
        ),
        evaluation=(
            (source.evaluation_rows[0], {"text": "e" * 50_000}),
            *(
                (row, dict(row.payload))
                for row in source.evaluation_rows[1:]
            ),
        ),
    )
    plan = _plan_for_row_set(base, row_set)

    complete = ExportDryRunPreview.create(plan=plan, row_set=row_set)
    full_size = len(
        export_response_json(export_dry_run_preview_response(complete)).encode(
            "ascii"
        )
    )
    monkeypatch.setattr(
        api_module,
        "_MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES",
        full_size - 1,
    )
    evaluation_omitted = ExportDryRunPreview.create(plan=plan, row_set=row_set)
    evaluation_omitted_samples = evaluation_omitted.to_dict()["sample_rows"]
    assert evaluation_omitted_samples[0]["payload"] is not None
    assert evaluation_omitted_samples[1]["payload"] is None
    evaluation_omitted_size = len(
        export_response_json(
            export_dry_run_preview_response(evaluation_omitted)
        ).encode("ascii")
    )

    monkeypatch.setattr(
        api_module,
        "_MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES",
        evaluation_omitted_size - 1,
    )
    preview = ExportDryRunPreview.create(plan=plan, row_set=row_set)
    samples = preview.to_dict()["sample_rows"]

    assert [sample["partition"] for sample in samples] == [
        "train",
        "evaluation",
    ]
    assert [sample["payload"] for sample in samples] == [None, None]
    assert [sample["omission_reason"] for sample in samples] == [
        "exact-payload-exceeds-response-budget",
        "exact-payload-exceeds-response-budget",
    ]
    assert [sample["payload_sha256"] for sample in samples] == [
        row_set.train_rows[0].payload_sha256,
        row_set.evaluation_rows[0].payload_sha256,
    ]
    assert [sample["payload_byte_size"] for sample in samples] == [
        len(lossless_json_bytes(row_set.train_rows[0].payload)),
        len(lossless_json_bytes(row_set.evaluation_rows[0].payload)),
    ]
    metadata_size = len(
        export_response_json(export_dry_run_preview_response(preview)).encode(
            "ascii"
        )
    )
    assert metadata_size <= evaluation_omitted_size - 1

    monkeypatch.setattr(
        api_module,
        "_MAX_DRY_RUN_PREVIEW_RESPONSE_BYTES",
        metadata_size - 1,
    )
    with pytest.raises(
        ExportContractError,
        match="plan and preview metadata exceed",
    ):
        ExportDryRunPreview.create(plan=plan, row_set=row_set)


def test_preview_cannot_be_publicly_reconstructed_or_relabelled(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    preview = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    )

    with pytest.raises(TypeError):
        ExportDryRunPreview(  # type: ignore[call-arg]
            plan=preview.plan,
            sample_rows=preview.sample_rows,
        )
    with pytest.raises(TypeError):
        ExportDryRunPreview()
    assert not hasattr(
        preview.sample_rows[0],
        "omitted_for_response_budget",
    )

    relabelled = list(preview.sample_rows)
    relabelled[1] = replace(
        relabelled[1],
        canonical_payload_bytes=None,
        omission_reason="exact-payload-exceeds-response-budget",
    )
    forged = ExportDryRunPreview._from_samples(
        plan=preview.plan,
        sample_rows=tuple(relabelled),
        sample_evidence=preview._sample_evidence,
    )
    with pytest.raises(ExportContractError, match="omission state differs"):
        export_dry_run_preview_response(forged)

    oversized = list(preview.sample_rows)
    oversized[0] = replace(
        oversized[0],
        canonical_payload_bytes=None,
        payload_byte_size=65_537,
        omission_reason="exact-payload-exceeds-preview-limit",
    )
    with pytest.raises(ExportContractError, match="membership binding"):
        ExportDryRunPreview._from_samples(
            plan=preview.plan,
            sample_rows=tuple(oversized),
            sample_evidence=preview._sample_evidence,
        )

    with pytest.raises(ExportContractError, match="wrong runtime type"):
        export_dry_run_preview_response(object())  # type: ignore[arg-type]


def test_v2_is_ascii_safe_and_cli_mcp_preserve_exact_unicode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    source = _source_row_set(bundle)
    base = ExportService().dry_run_export_preview(
        _dry_request(
            bundle,
            container_id=SPLIT_JSONL_CONTAINER_ID,
            container_version=SPLIT_JSONL_CONTAINER_VERSION,
        )
    ).plan
    exact = "esc=\x1b c1=\u009b bidi=\u202e nfc=\u00e9 nfd=e\u0301 nonbmp=\U0001f600"
    row_set = _rebuild_row_set(
        source,
        train=((source.train_rows[0], {"text": exact}),),
        evaluation=tuple(
            (row, dict(row.payload)) for row in source.evaluation_rows
        ),
    )
    preview = ExportDryRunPreview.create(
        plan=_plan_for_row_set(base, row_set),
        row_set=row_set,
    )
    response = export_dry_run_preview_response(preview)
    encoded = export_response_json(response)

    assert encoded.isascii()
    assert all(character not in encoded for character in ("\x1b", "\u009b", "\u202e"))
    decoded_text = json.loads(encoded)["result"]["preview"]["sample_rows"][0][
        "payload"
    ]["text"]
    assert tuple(map(ord, decoded_text)) == tuple(map(ord, exact))

    class PreviewPipeline:
        def dry_run_export(self, _request):
            return ExportPlanOutcome(plan=preview.plan, preview=preview)

    pipeline = PreviewPipeline()
    monkeypatch.setattr(cli_module, "_SERVICE", pipeline)
    request_json = _dry_request(
        bundle,
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
    ).canonical_bytes().decode("utf-8")
    cli_result = CliRunner().invoke(
        app,
        ["export", "dry-run", "--request-json", request_json],
    )
    mcp_result = _call_tool(
        create_mcp_server(pipeline),  # type: ignore[arg-type]
        "export_dry_run",
        {"request_json": request_json},
    )

    assert cli_result.exit_code == 0, cli_result.output
    assert cli_result.stdout == f"{encoded}\n"
    assert mcp_result == encoded


def test_cli_request_json_path_is_not_read_as_a_request_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    request_json = _dry_request(
        bundle,
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
    ).canonical_bytes().decode("utf-8")
    path = tmp_path / "dry-run.request.json"
    path.write_text(request_json, encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8"))["operation"] == "dry_run"

    calls: list[object] = []

    class RecordingPipeline:
        def dry_run_export(self, request: object) -> None:
            calls.append(request)
            raise AssertionError("path must not be loaded as a request")

    monkeypatch.setattr(cli_module, "_SERVICE", RecordingPipeline())
    result = CliRunner().invoke(
        app,
        ["export", "dry-run", "--request-json", str(path)],
    )

    assert result.exit_code == 2
    assert calls == []
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "export-contract-invalid"
    message = str(payload["error"]["message"]).lower()
    assert "invalid export surface request json" in message
    assert "expecting value" in message


def test_legacy_v1_bytes_remain_exact_and_dry_run_errors_are_v2(
    tmp_path: Path,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    service, _ = _service()
    plan = service.dry_run_export(_dry_run_request(bundle))
    legacy = export_dry_run_response(plan)

    assert legacy["schema_version"] == EXPORT_SURFACE_RESPONSE_SCHEMA
    assert export_response_json(legacy).encode("utf-8") == lossless_json_bytes(
        legacy
    )

    error = export_error_response(
        "dry_run",
        ExportContractError("unsafe \u009b \u202e detail"),
    )
    encoded = export_response_json(error)
    assert error["schema_version"] == EXPORT_SURFACE_RESPONSE_SCHEMA_V2
    assert error["status"] == "error"
    assert encoded.isascii()
    assert "\u009b" not in encoded and "\u202e" not in encoded


def test_constrained_csv_refuses_messages_before_preview_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = _materialize_bundle(tmp_path)
    messages = _row_set_for_schema(_source_row_set(bundle), "messages")
    service = ExportService()
    monkeypatch.setattr(service, "verified_source", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        service_module,
        "_source_plan_evidence",
        lambda _source: (
            None,
            messages,
            None,
            messages.provenance[0].objective_id,
            None,
        ),
    )

    with pytest.raises(ExportContractError) as error:
        service.dry_run_export_preview(_csv_dry_run_request(bundle))

    message = str(error.value)
    assert "constrained-csv" in message
    assert "messages" in message
    assert "split-jsonl-directory v1" in message
    assert "json v1" in message
