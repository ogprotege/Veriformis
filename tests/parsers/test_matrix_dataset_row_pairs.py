"""Matrix dataset-row pairs: parse accepts two independent imported sources."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.mapping import (
    FieldMapping,
    mapping_confirmation_digest,
    mapping_plan_from_template,
    mapping_template_catalog,
)
from veriformis.pipeline import PipelineService
from veriformis.workspace import Workspace

ROOT = Path(__file__).resolve().parents[2]
RUNNER = CliRunner()
SERVICE = PipelineService()
DATASET_ROW = ROOT / "tests/fixtures/matrix/dataset-row"

PAIRS = (
    pytest.param(
        DATASET_ROW / "preference-a.jsonl",
        DATASET_ROW / "preference-b.jsonl",
        id="preference-pair",
    ),
    pytest.param(
        DATASET_ROW / "labels-a.jsonl",
        DATASET_ROW / "labels-b.jsonl",
        id="label-classification",
    ),
    pytest.param(
        DATASET_ROW / "tool-call-a.jsonl",
        DATASET_ROW / "tool-call-b.jsonl",
        id="tool-call-conversation",
    ),
    pytest.param(
        DATASET_ROW / "stepwise-a.jsonl",
        DATASET_ROW / "stepwise-b.jsonl",
        id="stepwise-trace",
    ),
)

MAP_PAIRS = (
    pytest.param(
        DATASET_ROW / "tool-call-a.jsonl",
        DATASET_ROW / "tool-call-b.jsonl",
        "conversation-and-tool-trace",
        id="tool-call-conversation",
    ),
    pytest.param(
        DATASET_ROW / "stepwise-a.jsonl",
        DATASET_ROW / "stepwise-b.jsonl",
        "prompt-and-steps",
        id="stepwise-trace",
    ),
)


@pytest.mark.parametrize("first,second", PAIRS)
def test_dataset_row_parse_accepts_two_independent_sources(
    tmp_path: Path, first: Path, second: Path
) -> None:
    workspace = tmp_path / "workspace"
    result = RUNNER.invoke(
        app,
        [
            "parse",
            str(first),
            str(second),
            "-o",
            str(workspace),
            "--source-root",
            str(ROOT),
            "--mode",
            "dataset-row",
        ],
    )
    assert result.exit_code == 0, result.output


def _plan_from_template(workspace: Path, template_id: str):
    template = next(
        item
        for item in mapping_template_catalog().templates
        if item.template_id == template_id
    )
    mappings = tuple(
        FieldMapping.create(
            source_path=item["source_path"],
            target_key=item["target_key"],
        )
        for item in template.field_mappings
    )
    head = Workspace.open(workspace).head()
    source_digests = tuple(
        (item.logical_path, item.sha256) for item in head.sources.values()
    )
    digest = mapping_confirmation_digest(
        goal_id=template.goal_id,
        representation_id=template.representation_id,
        row_schema=template.row_schema,
        field_mappings=mappings,
        source_digests=source_digests,
    )
    return template, mapping_plan_from_template(template, confirmation_digest=digest)


@pytest.mark.parametrize("first,second,template_id", MAP_PAIRS)
def test_dataset_row_fixture_pair_maps_two_sources(
    tmp_path: Path, first: Path, second: Path, template_id: str
) -> None:
    workspace = tmp_path / "workspace"
    SERVICE.parse(
        [first, second],
        workspace,
        source_root=ROOT,
        mode="dataset-row",
    )
    template, plan = _plan_from_template(workspace, template_id)
    mapped = SERVICE.map_rows(
        workspace,
        goal=template.goal_id,
        representation=template.representation_id,
        mapping_plan=plan,
    )
    assert mapped.record_count == 2
    assert len(mapped.imported_record_ids) == 2
