"""Phase 7.3: JSONL capture, mapping execution, workspace v4, and seal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import (
    ConstructionError,
    MappingError,
    RowSourceError,
    UnsupportedWorkspaceVersionError,
)
from veriformis.identity import sha256_digest
from veriformis.mapping import (
    FieldMapping,
    MappingPlan,
    capture_jsonl,
    execute_mapping,
)
from veriformis.mapping.result import MappingRecipe
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.workspace import IMPORT_REVISION_SCHEMA_VERSION, Workspace, is_import_revision

FIXTURES = Path(__file__).parents[1] / "regressions" / "fixtures" / "phase7"
RUNNER = CliRunner()
SERVICE = PipelineService()
CONFIRM = sha256_digest("phase7-03-confirmation")

SCHEMA_CASES = (
    (
        "text.jsonl",
        "learn-the-text",
        "whole-text",
        "text",
        (("text", "text"),),
    ),
    (
        "prompt_completion.jsonl",
        "continue-a-passage",
        "prompt-and-completion",
        "prompt_completion",
        (("prompt", "prompt"), ("completion", "completion")),
    ),
    (
        "instruction_output.jsonl",
        "continue-a-passage",
        "instruction-and-output",
        "instruction_output",
        (
            ("instruction", "instruction"),
            ("input", "input"),
            ("output", "output"),
        ),
    ),
    (
        "messages.jsonl",
        "continue-a-passage",
        "conversation",
        "messages",
        (("messages", "messages"),),
    ),
)


def _plan(goal: str, representation: str, row_schema: str, pairs: tuple) -> MappingPlan:
    return MappingPlan.create(
        goal_id=goal,
        representation_id=representation,
        row_schema=row_schema,
        container_kind="jsonl",
        confirmation_digest=CONFIRM,
        field_mappings=[
            FieldMapping.create(source_path=source, target_key=target)
            for source, target in pairs
        ],
    )


def test_capture_keeps_unicode_and_refuses_empty_or_invalid(tmp_path: Path) -> None:
    source = tmp_path / "rows.jsonl"
    source.write_bytes('{"text":"café"}\n{"text":""}\n'.encode("utf-8"))
    capture = capture_jsonl(source, logical_path="rows.jsonl")
    assert capture.row_source.record_count == 2
    assert capture.records[0].payload["text"] == "café"
    assert capture.records[1].payload["text"] == ""
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n\n", encoding="utf-8")
    with pytest.raises(RowSourceError, match="no objects"):
        capture_jsonl(empty, logical_path="empty.jsonl")
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes(b"\xff\xfe not utf-8\n")
    with pytest.raises(RowSourceError, match="UTF-8"):
        capture_jsonl(bad, logical_path="bad.jsonl")


def test_execute_refuses_unmapped_keys_and_three_turn_messages(tmp_path: Path) -> None:
    extra = tmp_path / "extra.jsonl"
    extra.write_text('{"text":"keep","note":"drop"}\n', encoding="utf-8")
    capture = capture_jsonl(extra, logical_path="extra.jsonl")
    plan = _plan("learn-the-text", "whole-text", "text", (("text", "text"),))
    recipe = MappingRecipe.create(
        plan=plan,
        source_ids=("src-v1-" + "0" * 64,),
    )
    # Recipe source must match execute source_id; use a real derived id.
    from veriformis.identity import derive_source_id

    source_id = derive_source_id("extra.jsonl", capture.row_source.sha256)
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    with pytest.raises(MappingError, match="unmapped keys"):
        execute_mapping(plan, capture, source_id=source_id, recipe=recipe)

    three = tmp_path / "three.jsonl"
    three.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "a"},
                    {"role": "assistant", "content": "b"},
                    {"role": "user", "content": "c"},
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    capture = capture_jsonl(three, logical_path="three.jsonl")
    plan = _plan(
        "continue-a-passage",
        "conversation",
        "messages",
        (("messages", "messages"),),
    )
    source_id = derive_source_id("three.jsonl", capture.row_source.sha256)
    recipe = MappingRecipe.create(plan=plan, source_ids=(source_id,))
    with pytest.raises(MappingError, match="exactly two"):
        execute_mapping(plan, capture, source_id=source_id, recipe=recipe)


def _compile_import(
    tmp_path: Path,
    fixture_name: str,
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple,
    *,
    service: PipelineService | None = None,
) -> dict[str, str]:
    service = service or SERVICE
    source = tmp_path / fixture_name
    source.write_bytes((FIXTURES / fixture_name).read_bytes())
    workspace = tmp_path / "ws"
    bundle = tmp_path / "bundle"
    parse = service.parse(
        [source],
        workspace,
        source_root=tmp_path,
        mode="dataset-row",
    )
    assert is_import_revision(
        Workspace.open(workspace).head().schema_version
    )
    plan = _plan(goal, representation, row_schema, pairs)
    mapped = service.map_rows(
        workspace,
        goal=goal,
        representation=representation,
        mapping_plan=plan,
    )
    service.curate(workspace, goal=goal)
    service.split(workspace)
    service.format(workspace)
    validated = service.validate(workspace)
    assert validated.exit_status == 0
    sealed = service.seal(workspace, bundle)
    assert sealed.publication is not None
    return {
        "revision_id": parse.revision_id or "",
        "mapping_plan_id": mapped.mapping_plan_id or "",
        "result_id": mapped.result_id or "",
        "imported_record_ids": json.dumps(mapped.imported_record_ids),
        "row_set_id": Workspace.open(workspace)
        .head()
        .stages["format"]
        .outputs["row-set"],
        "manifest_sha256": sealed.publication.manifest_sha256,
        "schema_version": str(Workspace.open(workspace).head().schema_version),
    }


@pytest.mark.parametrize(
    ("fixture", "goal", "representation", "row_schema", "pairs"),
    SCHEMA_CASES,
)
def test_jsonl_maps_and_seals_four_schemas(
    tmp_path: Path,
    fixture: str,
    goal: str,
    representation: str,
    row_schema: str,
    pairs: tuple,
) -> None:
    ids = _compile_import(tmp_path, fixture, goal, representation, row_schema, pairs)
    assert ids["schema_version"] == str(IMPORT_REVISION_SCHEMA_VERSION)
    assert ids["mapping_plan_id"].startswith("mpl-")
    assert ids["manifest_sha256"]
    store = Workspace.open(tmp_path / "ws")
    head = store.head()
    assert set(head.stages) == {
        "parse",
        "map",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    }
    with pytest.raises(UnsupportedWorkspaceVersionError, match="dataset-row"):
        service = PipelineService()
        service.clean(tmp_path / "ws")
    with pytest.raises(UnsupportedWorkspaceVersionError):
        service.construct(tmp_path / "ws", goal=goal)


def test_python_cli_mcp_parity_on_text_fixture(tmp_path: Path) -> None:
    fixture, goal, representation, row_schema, pairs = SCHEMA_CASES[0]
    python_dir = tmp_path / "py"
    python_dir.mkdir()
    python_ids = _compile_import(
        python_dir,
        fixture,
        goal,
        representation,
        row_schema,
        pairs,
        service=PipelineService(),
    )

    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    source = cli_dir / fixture
    source.write_bytes((FIXTURES / fixture).read_bytes())
    workspace = cli_dir / "ws"
    bundle = cli_dir / "bundle"
    plan = _plan(goal, representation, row_schema, pairs)
    plan_path = cli_dir / "plan.json"
    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    assert (
        RUNNER.invoke(
            app,
            [
                "parse",
                str(source),
                "-o",
                str(workspace),
                "--source-root",
                str(cli_dir),
                "--mode",
                "dataset-row",
            ],
        ).exit_code
        == 0
    )
    mapped = RUNNER.invoke(
        app,
        [
            "map",
            str(workspace),
            "--goal",
            goal,
            "--representation",
            representation,
            "--plan",
            str(plan_path),
        ],
    )
    assert mapped.exit_code == 0, mapped.output
    assert RUNNER.invoke(app, ["curate", str(workspace), "--goal", goal]).exit_code == 0
    assert RUNNER.invoke(app, ["split", str(workspace)]).exit_code == 0
    assert RUNNER.invoke(app, ["format", str(workspace)]).exit_code == 0
    assert RUNNER.invoke(app, ["validate", str(workspace)]).exit_code == 0
    sealed = RUNNER.invoke(app, ["seal", str(workspace), "-o", str(bundle)])
    assert sealed.exit_code == 0, sealed.output
    assert python_ids["mapping_plan_id"] in mapped.output
    assert python_ids["manifest_sha256"] in sealed.output

    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    mcp_source = mcp_dir / fixture
    mcp_source.write_bytes((FIXTURES / fixture).read_bytes())
    mcp_ws = mcp_dir / "ws"
    mcp_bundle = mcp_dir / "bundle"
    tools = {
        tool.name: tool.fn
        for tool in create_mcp_server(PipelineService())._tool_manager.list_tools()
    }
    tools["parse"](
        [str(mcp_source)],
        str(mcp_ws),
        str(mcp_dir),
        "dataset-row",
    )
    mapped_mcp = json.loads(
        tools["map_rows"](
            str(mcp_ws),
            goal,
            representation,
            json.dumps(plan.model_dump(mode="json")),
        )
    )
    tools["curate"](str(mcp_ws), goal=goal)
    tools["split"](str(mcp_ws))
    tools["format_rows"](str(mcp_ws))
    tools["validate"](str(mcp_ws))
    sealed_mcp = json.loads(tools["seal"](str(mcp_ws), str(mcp_bundle)))
    assert mapped_mcp["mapping_plan_id"] == python_ids["mapping_plan_id"]
    assert mapped_mcp["imported_record_ids"] == json.loads(
        python_ids["imported_record_ids"]
    )
    assert (
        sealed_mcp["publication"]["manifest_sha256"] == python_ids["manifest_sha256"]
    )


def test_construct_and_preflight_refuse_dataset_row_as_construction(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("A document paragraph.\n", encoding="utf-8")
    with pytest.raises(ConstructionError, match="does not run constructors"):
        SERVICE.construct(tmp_path / "ws", mode="dataset-row", goal="learn-the-text")
    with pytest.raises(MappingError, match="item 7.6"):
        SERVICE.preflight([source], mode="dataset-row")


def test_map_refuses_document_workspace(tmp_path: Path) -> None:
    source = tmp_path / "doc.txt"
    source.write_text("A document paragraph.\n", encoding="utf-8")
    workspace = tmp_path / "ws"
    SERVICE.parse([source], workspace, source_root=tmp_path)
    plan = _plan("learn-the-text", "whole-text", "text", (("text", "text"),))
    with pytest.raises(UnsupportedWorkspaceVersionError, match="dataset-row"):
        SERVICE.map_rows(
            workspace,
            goal="learn-the-text",
            representation="whole-text",
            mapping_plan=plan,
        )
