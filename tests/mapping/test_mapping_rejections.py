"""Phase 7.9: row-level mapping rejection reports."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.identity import sha256_digest
from veriformis.mapping import (
    FieldMapping,
    MappingPlan,
    mapping_confirmation_digest,
)
from veriformis.mapping.reject import MappingRejectionReport
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace

RUNNER = CliRunner()
SERVICE = PipelineService()


def _text_plan(source_digests: tuple[tuple[str, str], ...]) -> MappingPlan:
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    return MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=source_digests,
        ),
        field_mappings=mappings,
    )


def test_accepted_rows_seal_and_rejected_rows_stay_out_of_row_set(
    tmp_path: Path,
) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        '{"text":"Alpha café one."}\n'
        '{"text":"Beta café two."}\n'
        '{"text":"Gamma","note":"drop"}\n',
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    head = Workspace.open(workspace).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in head.sources.values()
    )
    plan = _text_plan(source_digests)
    mapped = SERVICE.map_rows(
        workspace,
        goal="learn-the-text",
        representation="whole-text",
        mapping_plan=plan,
    )
    assert mapped.record_count == 2
    assert mapped.rejected_count == 1
    assert mapped.rejection_report_path is not None
    report_path = Path(mapped.rejection_report_path)
    assert report_path.is_file()
    report = MappingRejectionReport.model_validate_json(
        report_path.read_text(encoding="utf-8")
    )
    assert report.rejected_count == 1
    assert report.rejections[0].reason_code == "unmapped-keys"
    assert report.rejections[0].row_index == 3
    SERVICE.curate(workspace, goal="learn-the-text")
    SERVICE.split(workspace)
    SERVICE.format(workspace)
    assert SERVICE.validate(workspace).exit_status == 0
    sealed = SERVICE.seal(workspace, bundle)
    assert sealed.publication is not None
    train = (bundle / "data" / "train.jsonl").read_text(encoding="utf-8")
    evaluation = (bundle / "data" / "evaluation.jsonl").read_text(encoding="utf-8")
    payloads = train + evaluation
    assert "Gamma" not in payloads
    assert "Alpha" in payloads
    assert "Beta" in payloads
    manifest_digest = sealed.publication.manifest_sha256
    report_path.write_bytes(report_path.read_bytes() + b" ")
    assert sealed.publication.manifest_sha256 == manifest_digest
    assert "Gamma" not in (bundle / "data" / "train.jsonl").read_text(encoding="utf-8")


def test_corrected_source_produces_a_new_plan_id(tmp_path: Path) -> None:
    first = tmp_path / "rows.jsonl"
    first.write_text(
        '{"text":"Alpha café one."}\n{"text":"Beta","note":"drop"}\n',
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    SERVICE.parse([first], workspace, source_root=tmp_path, mode="dataset-row")
    head = Workspace.open(workspace).head()
    first_plan = _text_plan(
        tuple((item.logical_path, item.sha256) for item in head.sources.values())
    )
    first_id = first_plan.mapping_plan_id
    corrected = tmp_path / "fixed.jsonl"
    corrected.write_text(
        '{"text":"Alpha café one."}\n{"text":"Beta café two."}\n',
        encoding="utf-8",
    )
    other = tmp_path / "ws2"
    SERVICE.parse([corrected], other, source_root=tmp_path, mode="dataset-row")
    head2 = Workspace.open(other).head()
    second_plan = _text_plan(
        tuple((item.logical_path, item.sha256) for item in head2.sources.values())
    )
    assert second_plan.mapping_plan_id != first_id


def test_mapping_rejections_python_cli_mcp_write_the_same_report(
    tmp_path: Path,
) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        '{"text":"Alpha"}\n{"text":"Beta","note":"drop"}\n',
        encoding="utf-8",
    )
    plan_path = tmp_path / "plan.json"
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    confirmation = mapping_confirmation_digest(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        field_mappings=mappings,
        source_digests=(("rows.jsonl", sha256_digest(source.read_bytes())),),
    )
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=confirmation,
        field_mappings=mappings,
    )
    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    python = SERVICE.export_mapping_rejections(
        source,
        plan,
        tmp_path / "py",
        source_root=tmp_path,
    )
    cli = RUNNER.invoke(
        app,
        [
            "mapping-rejections",
            str(source),
            "--plan",
            str(plan_path),
            "--output",
            str(tmp_path / "cli"),
            "--source-root",
            str(tmp_path),
        ],
    )
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(PipelineService())._tool_manager.list_tools()
    }
    mcp = json.loads(
        tools["mapping_rejections"](
            str(source),
            json.dumps(plan.model_dump(mode="json")),
            str(tmp_path / "mcp"),
            str(tmp_path),
        )
    )
    assert python["report_id"] == json.loads(cli.output)["report_id"] == mcp["report_id"]
    assert python["rejected_count"] == 1
