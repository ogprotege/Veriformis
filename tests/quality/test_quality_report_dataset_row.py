"""Dataset-row quality-report preview. Not a gate. Does not invent construction."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import pytest

from veriformis.cli import app
from veriformis.errors import MissingStageInputError
from veriformis.identity import derive_id, sha256_digest
from veriformis.mapping import FieldMapping, MappingPlan, mapping_confirmation_digest
from veriformis.pipeline import PipelineService
from veriformis.quality import V1_QUALITY_GATES, require_quality_report_not_enforcing
from veriformis.quality.report import QualityReport, empty_quality_report
from veriformis.workspace import IMPORT_REVISION_SCHEMA_VERSION, Workspace


ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
SERVICE = PipelineService()
DOCUMENT_SOURCE_GOLDEN_SHA256 = (
    "54e4616afe9bd8151aef9336831b1d094fbcfbba2fd96dca3c6216665cc15c53"
)
PREFERENCE_GOAL = "prefer-chosen-over-rejected"
PREFERENCE_REPRESENTATION = "prompt-chosen-rejected"
PREFERENCE_SCHEMA = "preference-pair"
PREFERENCE_PAIRS = (
    ("prompt", "prompt"),
    ("chosen", "chosen"),
    ("rejected", "rejected"),
)
CLASSIFICATION_GOAL = "classify-with-provided-labels"
CLASSIFICATION_REPRESENTATION = "context-and-label"
CLASSIFICATION_SCHEMA = "label-classification"
CLASSIFICATION_PAIRS = (
    ("context", "context"),
    ("label", "label"),
    ("annotator", "annotator"),
)


def _mapping_plan(
    workspace: Path,
    *,
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple[tuple[str, str], ...],
) -> MappingPlan:
    head = Workspace.open(workspace).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in head.sources.values()
    )
    mappings = [
        FieldMapping.create(source_path=source, target_key=target)
        for source, target in pairs
    ]
    return MappingPlan.create(
        goal_id=goal,
        representation_id=representation,
        row_schema=row_schema,
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id=goal,
            representation_id=representation,
            row_schema=row_schema,
            field_mappings=mappings,
            source_digests=source_digests,
        ),
        field_mappings=mappings,
    )


def _compile_import(
    tmp_path: Path,
    first: Path,
    second: Path,
    *,
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple[tuple[str, str], ...],
) -> Path:
    workspace = tmp_path / "workspace"
    SERVICE.parse(
        [first, second],
        workspace,
        source_root=ROOT,
        mode="dataset-row",
    )
    SERVICE.map_rows(
        workspace,
        goal=goal,
        representation=representation,
        mapping_plan=_mapping_plan(
            workspace,
            goal=goal,
            representation=representation,
            row_schema=row_schema,
            pairs=pairs,
        ),
    )
    SERVICE.curate(workspace, goal=goal)
    SERVICE.split(workspace)
    return workspace


def _compile_document_source(tmp_path: Path) -> Path:
    sources = tmp_path / "src"
    sources.mkdir()
    (sources / "alpha.txt").write_text(
        "Contact alpha@example.test for the first independent source.\n",
        encoding="utf-8",
    )
    (sources / "beta.txt").write_text(
        "Key AKIAIOSFODNN7EXAMPLE stays a finding only in source two.\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    SERVICE.parse([sources], workspace, source_root=tmp_path)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace)
    SERVICE.construct(workspace, objective="full_text")
    SERVICE.curate(workspace, evaluation_required=False)
    SERVICE.split(workspace)
    return workspace


def _fact_int(report: QualityReport, name: str) -> int:
    return next(item.integer_value for item in report.facts if item.name == name)


def _fact_text(report: QualityReport, name: str):
    value = next(item.text_value for item in report.facts if item.name == name)
    assert value is not None
    return json.loads(value)


def test_empty_report_accepts_finished_import_plan_id() -> None:
    plan_id = derive_id("fip", {"lane": "quality-report-dataset-row"})
    report = empty_quality_report(plan_id=plan_id)
    assert report.plan_id == plan_id
    assert report.enforcing is False
    require_quality_report_not_enforcing(report)


def test_preference_workspace_emits_preview_with_fip_plan(tmp_path: Path) -> None:
    workspace = _compile_import(
        tmp_path,
        ROOT / "tests/fixtures/matrix/dataset-row/preference-a.jsonl",
        ROOT / "tests/fixtures/matrix/dataset-row/preference-b.jsonl",
        goal=PREFERENCE_GOAL,
        representation=PREFERENCE_REPRESENTATION,
        row_schema=PREFERENCE_SCHEMA,
        pairs=PREFERENCE_PAIRS,
    )
    python = SERVICE.quality_report(workspace)
    assert python.report is not None
    require_quality_report_not_enforcing(python.report)
    assert python.report.schema_id == "veriformis.quality-report/v1"
    assert python.report.enforcing is False
    assert python.report.plan_id.startswith("fip-v")
    assert _fact_int(python.report, "included-record-count") == 2
    assert _fact_int(python.report, "train-record-count") == 1
    assert _fact_int(python.report, "evaluation-record-count") == 1
    assert _fact_int(python.report, "quality-admitted-blocking-count") == 0
    preview = _fact_text(python.report, "quality-gate-preview")
    assert all(row["admitted-to-block"] is False for row in preview)
    assert _fact_text(python.report, "quality-gate-plan-id") == python.report.plan_id
    cli = RUNNER.invoke(app, ["quality-report", str(workspace)])
    assert cli.exit_code == 0, cli.output
    assert cli.stdout == python.report.transport_text() + "\n"


def test_classification_workspace_has_supplied_labels(tmp_path: Path) -> None:
    workspace = _compile_import(
        tmp_path,
        ROOT / "tests/fixtures/matrix/dataset-row/labels-a.jsonl",
        ROOT / "tests/fixtures/matrix/dataset-row/labels-b.jsonl",
        goal=CLASSIFICATION_GOAL,
        representation=CLASSIFICATION_REPRESENTATION,
        row_schema=CLASSIFICATION_SCHEMA,
        pairs=CLASSIFICATION_PAIRS,
    )
    report = SERVICE.quality_report(workspace).report
    assert report is not None
    require_quality_report_not_enforcing(report)
    assert report.plan_id.startswith("fip-v")
    assert _fact_int(report, "family-missing-label-count") == 0
    assert _fact_int(report, "included-record-count") == 2


def test_document_source_preview_bytes_stay_identical(tmp_path: Path) -> None:
    workspace = _compile_document_source(tmp_path)
    report = SERVICE.quality_report(workspace).report
    assert report is not None
    assert report.plan_id.startswith("fdp-v")
    digest = sha256_digest(report.transport_text().encode("utf-8"))
    assert digest == DOCUMENT_SOURCE_GOLDEN_SHA256


def test_admitted_to_block_stays_false_on_every_v1_gate() -> None:
    assert all(item.admitted_to_block is False for item in V1_QUALITY_GATES)


def test_dataset_row_map_only_names_curate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    first = ROOT / "tests/fixtures/matrix/dataset-row/preference-a.jsonl"
    second = ROOT / "tests/fixtures/matrix/dataset-row/preference-b.jsonl"
    SERVICE.parse(
        [first, second],
        workspace,
        source_root=ROOT,
        mode="dataset-row",
    )
    SERVICE.map_rows(
        workspace,
        goal=PREFERENCE_GOAL,
        representation=PREFERENCE_REPRESENTATION,
        mapping_plan=_mapping_plan(
            workspace,
            goal=PREFERENCE_GOAL,
            representation=PREFERENCE_REPRESENTATION,
            row_schema=PREFERENCE_SCHEMA,
            pairs=PREFERENCE_PAIRS,
        ),
    )
    with pytest.raises(MissingStageInputError) as exc:
        SERVICE.quality_report(workspace)
    message = str(exc.value)
    assert "curate" in message
    assert "construct" not in message
    assert "upgrade-workspace" not in message


def test_dataset_row_parse_only_names_map_not_construct(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    SERVICE.parse(
        [
            ROOT / "tests/fixtures/matrix/dataset-row/preference-a.jsonl",
            ROOT / "tests/fixtures/matrix/dataset-row/preference-b.jsonl",
        ],
        workspace,
        source_root=ROOT,
        mode="dataset-row",
    )
    with pytest.raises(MissingStageInputError) as exc:
        SERVICE.quality_report(workspace)
    message = str(exc.value)
    assert "map" in message
    assert "construct" not in message
    assert "schema 3" not in message
    assert "upgrade-workspace" not in message


def test_empty_import_workspace_does_not_ask_for_schema_3(tmp_path: Path) -> None:
    workspace = tmp_path / "import-ws"
    Workspace.create(workspace, schema_version=IMPORT_REVISION_SCHEMA_VERSION)
    with pytest.raises(Exception) as exc:
        SERVICE.quality_report(workspace)
    message = str(exc.value)
    assert "schema 3" not in message
    assert "upgrade-workspace" not in message
    assert "dataset-row revision 4 is not loaded" not in message
