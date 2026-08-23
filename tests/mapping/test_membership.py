"""Phase 7.7: authoritative membership honors imported partitions."""

from __future__ import annotations

from pathlib import Path

import pytest

from veriformis.errors import SplitError
from veriformis.mapping import mapping_confirmation_digest
from veriformis.mapping.models import FieldMapping, MappingPlan
from veriformis.pipeline import PipelineService

SERVICE = PipelineService()


def test_authoritative_membership_fails_closed_on_source_leakage(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text(
        '{"text":"Alpha","partition":"train"}\n'
        '{"text":"Beta","partition":"evaluation"}\n',
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    from veriformis.workspace import Workspace

    head = Workspace.open(workspace).head()
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        membership_policy="authoritative",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=tuple(
                (item.logical_path, item.sha256) for item in head.sources.values()
            ),
        ),
        field_mappings=mappings,
    )
    SERVICE.map_rows(
        workspace,
        goal="learn-the-text",
        representation="whole-text",
        mapping_plan=plan,
    )
    SERVICE.curate(workspace, goal="learn-the-text")
    with pytest.raises(SplitError, match="leakage"):
        SERVICE.split(workspace)
