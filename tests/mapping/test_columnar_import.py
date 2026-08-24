"""Phase 9.7: Parquet/Arrow mapping admission without importing PyArrow."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from veriformis.errors import ParseError, RowSourceError, UnsupportedInputError
from veriformis.identity import sha256_digest
from veriformis.mapping import (
    ADMITTED_CONTAINERS,
    FieldMapping,
    MappingPlan,
    ROW_ARROW_PARSER_ID,
    ROW_PARQUET_PARSER_ID,
    capture_row_source,
    row_parser_id,
)
from veriformis.pipeline import PipelineService

SERVICE = PipelineService()
CONFIRM = sha256_digest("phase9-07-confirmation")
ROOT = Path(__file__).resolve().parents[2]


def test_parquet_and_arrow_are_admitted_mapping_containers() -> None:
    assert ADMITTED_CONTAINERS == ("jsonl", "json", "csv", "parquet", "arrow")
    assert row_parser_id("parquet") == ROW_PARQUET_PARSER_ID
    assert row_parser_id("arrow") == ROW_ARROW_PARSER_ID
    for container in ("parquet", "arrow"):
        plan = MappingPlan.create(
            goal_id="learn-the-text",
            representation_id="whole-text",
            row_schema="text",
            container_kind=container,
            confirmation_digest=CONFIRM,
            field_mappings=[
                FieldMapping.create(source_path="text", target_key="text"),
            ],
        )
        assert plan.container_kind == container
        messages = MappingPlan.create(
            goal_id="continue-a-passage",
            representation_id="conversation",
            row_schema="messages",
            container_kind=container,
            confirmation_digest=CONFIRM,
            field_mappings=[
                FieldMapping.create(source_path="messages", target_key="messages"),
            ],
        )
        assert messages.row_schema == "messages"


def test_columnar_capture_fails_closed_without_pyarrow(tmp_path: Path) -> None:
    assert "pyarrow" not in sys.modules
    parquet = tmp_path / "rows.parquet"
    arrow = tmp_path / "rows.arrow"
    parquet.write_bytes(b"PAR1")
    arrow.write_bytes(b"ARROW1")
    with pytest.raises(RowSourceError, match="require PyArrow.*columnar"):
        capture_row_source(parquet, logical_path="rows.parquet")
    with pytest.raises(RowSourceError, match="require PyArrow.*columnar"):
        capture_row_source(arrow, logical_path="rows.arrow")
    assert "pyarrow" not in sys.modules
    toml = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in toml


def test_suffix_does_not_switch_document_source_to_dataset_row(
    tmp_path: Path,
) -> None:
    source = tmp_path / "rows.parquet"
    source.write_bytes(b"PAR1")
    workspace = tmp_path / "ws"
    with pytest.raises(UnsupportedInputError, match="unsupported input type"):
        SERVICE.parse(
            [source],
            workspace,
            source_root=tmp_path,
        )
    assert not workspace.exists()
    with pytest.raises(RowSourceError, match="require PyArrow.*columnar"):
        SERVICE.parse(
            [source],
            workspace,
            source_root=tmp_path,
            mode="dataset-row",
        )
    assert not workspace.exists()
    assert "pyarrow" not in sys.modules


@pytest.mark.parametrize("suffix", [".parquet", ".arrow"])
def test_mixed_parse_refuses_fused_document_and_columnar(
    tmp_path: Path,
    suffix: str,
) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("A document paragraph.\n", encoding="utf-8")
    rows = tmp_path / f"rows{suffix}"
    rows.write_bytes(b"PAR1")
    with pytest.raises(ParseError, match="distinct"):
        SERVICE.parse(
            [doc, rows],
            tmp_path / "ws",
            source_root=tmp_path,
            mode="mixed",
        )
    assert not (tmp_path / "ws").exists()
    assert "pyarrow" not in sys.modules
