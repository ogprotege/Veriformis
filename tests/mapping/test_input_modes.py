"""Compiler-path input modes: discovery, default, and closed refusals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.contracts import (
    INPUT_MODE_CONTRACT_ID,
    INPUT_MODE_CONTRACT_VERSION,
    INPUT_MODE_SCHEMA_ID,
)
from veriformis.errors import InputModeError
from veriformis.identity import sha256_digest
from veriformis.mapping import (
    DATASET_ROW_MODE,
    DOCUMENT_SOURCE_MODE,
    IMPLEMENTED_INPUT_MODES,
    INPUT_MODE_IDS,
    MIXED_MODE,
    PLANNED_INPUT_MODES,
    discover_modes,
    input_mode_catalog,
    input_mode_catalog_json,
    require_executable_mode,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

DATA_PATH = Path(__file__).parents[2] / "src" / "veriformis" / "mapping" / "modes-v1.json"
RUNNER = CliRunner()
SERVICE = PipelineService()


def test_packaged_modes_are_canonical_and_closed() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    catalog = input_mode_catalog()
    assert catalog.schema_id == INPUT_MODE_SCHEMA_ID
    assert catalog.contract_id == INPUT_MODE_CONTRACT_ID
    assert catalog.contract_version == INPUT_MODE_CONTRACT_VERSION
    assert catalog.default_mode == DOCUMENT_SOURCE_MODE
    assert tuple(mode.mode_id for mode in catalog.modes) == INPUT_MODE_IDS
    assert IMPLEMENTED_INPUT_MODES == (
        DOCUMENT_SOURCE_MODE,
        DATASET_ROW_MODE,
        MIXED_MODE,
    )
    assert PLANNED_INPUT_MODES == ()
    assert sha256_digest(stored) == sha256_digest(input_mode_catalog_json())


def test_discover_modes_is_byte_identical_across_python_cli_and_mcp() -> None:
    expected = input_mode_catalog_json().rstrip("\n")
    python = json.dumps(discover_modes(), ensure_ascii=False, indent=2, sort_keys=True)
    cli = RUNNER.invoke(app, ["modes"])
    assert cli.exit_code == 0, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = tools["modes"]()
    assert python == expected
    assert cli.output == expected + "\n"
    assert mcp == expected + "\n"


@pytest.mark.parametrize("mode", [None, "", DOCUMENT_SOURCE_MODE])
def test_document_source_remains_the_default_executable_mode(mode: str | None) -> None:
    assert require_executable_mode(mode) == DOCUMENT_SOURCE_MODE


def test_dataset_row_and_mixed_modes_are_executable() -> None:
    assert require_executable_mode(DATASET_ROW_MODE) == DATASET_ROW_MODE
    assert require_executable_mode(MIXED_MODE) == MIXED_MODE


def test_mixed_parse_refuses_fused_document_and_jsonl(tmp_path: Path) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("A document paragraph.\n", encoding="utf-8")
    rows = tmp_path / "rows.jsonl"
    rows.write_text('{"text":"Alpha"}\n', encoding="utf-8")
    refused = RUNNER.invoke(
        app,
        [
            "parse",
            str(doc),
            str(rows),
            "-o",
            str(tmp_path / "ws"),
            "--source-root",
            str(tmp_path),
            "--mode",
            "mixed",
        ],
    )
    assert refused.exit_code != 0
    assert "distinct" in refused.output


def test_unknown_mode_refuses() -> None:
    with pytest.raises(InputModeError, match="unknown input mode"):
        require_executable_mode("parquet")


def test_parse_flag_keeps_document_source_and_dataset_row_refuses_documents(
    tmp_path: Path,
) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("Exact document-source paragraph.\n", encoding="utf-8")
    workspace = tmp_path / "ws"
    ok = RUNNER.invoke(
        app,
        [
            "parse",
            str(source),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
        ],
    )
    assert ok.exit_code == 0, ok.output
    refused = RUNNER.invoke(
        app,
        [
            "parse",
            str(source),
            "-o",
            str(tmp_path / "other"),
            "--source-root",
            str(tmp_path),
            "--mode",
            "dataset-row",
        ],
    )
    assert refused.exit_code != 0
    assert "jsonl" in refused.output.lower() or "row-source-invalid" in refused.output
    assert not (tmp_path / "other").exists()
