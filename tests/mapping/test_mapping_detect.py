"""Phase 7.4: mapping detectors propose plans and map requires confirmation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import MappingError
from veriformis.mapping import detect_mapping, mapping_detector_catalog_json
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

RUNNER = CliRunner()
SERVICE = PipelineService()
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "veriformis" / "mapping" / "detectors-v1.json"
DATASET_ROW = ROOT / "tests/fixtures/matrix/dataset-row"


def test_detector_catalog_is_canonical() -> None:
    stored = DATA.read_text(encoding="utf-8")
    payload = json.loads(stored)
    canonical = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    assert stored == canonical
    assert mapping_detector_catalog_json() == stored


def test_detect_unique_text_still_requires_confirmation(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_text('{"text":"Alpha"}\n{"text":"Beta"}\n', encoding="utf-8")
    detected = SERVICE.detect_mapping(source, source_root=tmp_path)
    assert detected["refusal"] is None
    assert len(detected["proposals"]) == 1
    proposal = detected["proposals"][0]
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    with pytest.raises(MappingError, match="not confirmed"):
        from veriformis.mapping.models import FieldMapping, MappingPlan

        plan = MappingPlan.create(
            goal_id=proposal["goal_id"],
            representation_id=proposal["representation_id"],
            row_schema=proposal["row_schema"],
            container_kind="jsonl",
            confirmation_digest="a" * 64,
            field_mappings=[
                FieldMapping.model_validate(item)
                for item in proposal["field_mappings"]
            ],
        )
        SERVICE.map_rows(
            workspace,
            goal=plan.goal_id,
            representation=plan.representation_id,
            mapping_plan=plan,
        )
    mapped = SERVICE.map_rows(
        workspace,
        goal=proposal["goal_id"],
        representation=proposal["representation_id"],
        mapping_plan=proposal,
    )
    assert mapped.record_count == 2


def test_ambiguous_text_or_prompt_completion_does_not_auto_map(tmp_path: Path) -> None:
    source = tmp_path / "both.jsonl"
    source.write_text(
        '{"text":"Alpha","prompt":"P","completion":"C"}\n'
        '{"text":"Beta","prompt":"Q","completion":"D"}\n',
        encoding="utf-8",
    )
    detected = detect_mapping(source, logical_path="both.jsonl")
    schemas = {item["row_schema"] for item in detected["proposals"]}
    assert schemas == {"text", "prompt_completion"}
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path, mode="dataset-row")
    text_proposal = next(
        item for item in detected["proposals"] if item["row_schema"] == "text"
    )
    with pytest.raises(MappingError, match="unmapped keys"):
        SERVICE.map_rows(
            workspace,
            goal=text_proposal["goal_id"],
            representation=text_proposal["representation_id"],
            mapping_plan=text_proposal,
        )


def test_detect_refuses_to_invent_a_summary(tmp_path: Path) -> None:
    source = tmp_path / "odd.jsonl"
    source.write_text('{"summary":"nope","body":"still nope"}\n', encoding="utf-8")
    detected = SERVICE.detect_mapping(source, source_root=tmp_path)
    assert detected["proposals"] == []
    assert detected["refusal"]
    assert "summary" in detected["refusal"] or "will not invent" in detected["refusal"]
    cli = RUNNER.invoke(app, ["mapping-detect", str(source), "--source-root", str(tmp_path)])
    assert cli.exit_code == 2
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = json.loads(tools["mapping_detect"](str(source), str(tmp_path)))
    assert mcp["proposals"] == []


@pytest.mark.parametrize(
    ("filename", "row_schema", "goal_id", "representation"),
    [
        (
            "tool-call-a.jsonl",
            "tool-call-conversation",
            "use-provided-tool-traces",
            "conversation-and-tool-trace",
        ),
        (
            "stepwise-a.jsonl",
            "stepwise-trace",
            "use-provided-steps",
            "prompt-and-steps",
        ),
    ],
)
def test_detect_matches_list_valued_turns_and_steps_that_map_binds(
    tmp_path: Path,
    filename: str,
    row_schema: str,
    goal_id: str,
    representation: str,
) -> None:
    source = DATASET_ROW / filename
    detected = SERVICE.detect_mapping(source, source_root=ROOT)
    assert detected["refusal"] is None
    schemas = {item["row_schema"] for item in detected["proposals"]}
    assert schemas == {row_schema}
    proposal = detected["proposals"][0]
    assert proposal["goal_id"] == goal_id
    assert proposal["representation_id"] == representation
    workspace = tmp_path / "workspace"
    SERVICE.parse([source], workspace, source_root=ROOT, mode="dataset-row")
    mapped = SERVICE.map_rows(
        workspace,
        goal=proposal["goal_id"],
        representation=proposal["representation_id"],
        mapping_plan=proposal,
    )
    assert mapped.record_count == 1
    cli = RUNNER.invoke(
        app, ["mapping-detect", str(source), "--source-root", str(ROOT)]
    )
    assert cli.exit_code == 0, cli.output
    payload = json.loads(cli.stdout)
    assert payload["refusal"] is None
    assert {item["row_schema"] for item in payload["proposals"]} == {row_schema}
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = json.loads(tools["mapping_detect"](str(source), str(ROOT)))
    assert mcp["refusal"] is None
    assert {item["row_schema"] for item in mcp["proposals"]} == {row_schema}


@pytest.mark.parametrize(
    ("name", "line"),
    [
        (
            "string-turns.jsonl",
            '{"conversation_id":"tool-call-string","turns":"user then tool then assistant"}\n',
        ),
        (
            "string-steps.jsonl",
            '{"prompt":"What color is a ripe lemon?","steps":"name the color then yellow"}\n',
        ),
    ],
)
def test_detect_refuses_string_valued_turns_or_steps(
    tmp_path: Path,
    name: str,
    line: str,
) -> None:
    source = tmp_path / name
    source.write_text(line, encoding="utf-8")
    detected = SERVICE.detect_mapping(source, source_root=tmp_path)
    assert detected["proposals"] == []
    assert detected["refusal"]
    assert "will not invent" in detected["refusal"]
    cli = RUNNER.invoke(
        app, ["mapping-detect", str(source), "--source-root", str(tmp_path)]
    )
    assert cli.exit_code == 2, cli.output
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }
    mcp = json.loads(tools["mapping_detect"](str(source), str(tmp_path)))
    assert mcp["proposals"] == []
