"""Phase 7.6: full-file mapping preview is runtime-only."""

from __future__ import annotations

from pathlib import Path

from veriformis.identity import sha256_digest
from veriformis.mapping import mapping_confirmation_digest
from veriformis.mapping.models import FieldMapping, MappingPlan
from veriformis.pipeline import PipelineService

SERVICE = PipelineService()


def test_preview_walks_every_row_including_rejects(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    payload = '{"text":"ok"}\n{"text":""}\n{"text":"also ok"}\n'
    source.write_text(payload, encoding="utf-8")
    mappings = [FieldMapping.create(source_path="text", target_key="text")]
    plan = MappingPlan.create(
        goal_id="learn-the-text",
        representation_id="whole-text",
        row_schema="text",
        container_kind="jsonl",
        confirmation_digest=mapping_confirmation_digest(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            field_mappings=mappings,
            source_digests=(("rows.jsonl", sha256_digest(payload)),),
        ),
        field_mappings=mappings,
    )
    preview = SERVICE.preview_mapping(
        source,
        plan,
        source_root=tmp_path,
    )
    assert preview["schema_version"] == "veriformis.mapping-preview/v1"
    assert preview["record_count"] == 3
    assert preview["accepted_count"] == 2
    assert preview["rejected_count"] == 1
    assert preview["rejected"][0]["row_index"] == 2
    assert not (tmp_path / "ws").exists()
