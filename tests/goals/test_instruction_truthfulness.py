"""Phase 6.7: catalog templates are the only default instruction literals."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import (
    InstructionNotApplicableError,
    InstructionRequiredError,
    InstructionTruthfulnessError,
)
from veriformis.goals import (
    goal_catalog,
    goal_for_objective,
    resolve_operator_instruction,
    validate_instruction_text,
)
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_finished_plan
from veriformis.recipes import load_pipeline_spec, run_pipeline_spec
from veriformis.workspace import Workspace

runner = CliRunner()
SERVICE = PipelineService()
MATRIX = (
    Path(__file__).parents[1]
    / "regressions"
    / "fixtures"
    / "phase6"
    / "goal-acceptance-matrix.json"
)


def _sources(root: Path) -> tuple[Path, list[Path]]:
    source_root = root / "sources"
    source_root.mkdir(parents=True)
    paths = []
    for index, name in enumerate(("alpha.txt", "beta.txt")):
        path = source_root / name
        path.write_text(
            (
                f"Source {index} opening paragraph is long enough to split. "
                "The wording is retained exactly for instruction proofs.\n\n"
                f"Source {index} remainder stays in the same document."
            ),
            encoding="utf-8",
        )
        paths.append(path)
    return source_root, paths


def _constructed(root: Path, *, representation: str = "instruction-and-output") -> Path:
    source_root, paths = _sources(root)
    workspace = root / "workspace"
    SERVICE.parse(paths, workspace, source_root=source_root)
    SERVICE.clean(workspace)
    SERVICE.chunk(workspace, preset="continue-a-passage.safe")
    SERVICE.construct(
        workspace,
        goal="continue-a-passage",
        preset="continue-a-passage.safe",
        representation=representation,
    )
    return workspace


def _tool(name: str):
    return {
        tool.name: tool.fn
        for tool in create_mcp_server(SERVICE)._tool_manager.list_tools()
    }[name]


def test_catalog_templates_are_exactly_the_acceptance_matrix_literals() -> None:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    by_goal = {goal.goal_id: goal for goal in goal_catalog().goals}
    observed: dict[str, set[str]] = {}
    for cell in matrix["cells"]:
        instruction = cell["instruction"]
        if instruction is None:
            continue
        observed.setdefault(cell["goal_id"], set()).add(instruction)
    for goal_id, instructions in observed.items():
        assert instructions == {by_goal[goal_id].instruction_template}
    for goal in goal_catalog().goals:
        assert goal.instruction_task.lower() in goal.instruction_template.lower()
        validate_instruction_text(goal, goal.instruction_template)


def test_omitted_instruction_resolves_to_the_catalog_template() -> None:
    goal = goal_for_objective("continuation")
    assert (
        resolve_operator_instruction(
            goal=goal.goal_id,
            representation="instruction-and-output",
        )
        == goal.instruction_template
    )
    assert (
        resolve_operator_instruction(
            objective="continuation",
            row_schema="instruction_output",
            instruction=goal.instruction_template,
        )
        == goal.instruction_template
    )


@pytest.mark.parametrize(
    ("instruction", "error"),
    [
        ("", InstructionRequiredError),
        ("   ", InstructionRequiredError),
        ("Continue the passage.", InstructionTruthfulnessError),
        (
            "Summarize the passage with its exact source remainder.",
            InstructionTruthfulnessError,
        ),
        (
            "Answer the question with its exact source remainder.",
            InstructionTruthfulnessError,
        ),
        (
            "Translate the passage with its exact source remainder.",
            InstructionTruthfulnessError,
        ),
    ],
)
def test_untruthful_or_empty_operator_instructions_fail_closed(
    instruction: str, error: type[Exception]
) -> None:
    with pytest.raises(error):
        resolve_operator_instruction(
            goal="continue-a-passage",
            representation="instruction-and-output",
            instruction=instruction,
        )


def test_instruction_is_rejected_outside_instruction_and_output() -> None:
    with pytest.raises(InstructionNotApplicableError):
        resolve_operator_instruction(
            goal="continue-a-passage",
            representation="conversation",
            instruction="Continue the passage with its exact source remainder.",
        )
    assert (
        resolve_operator_instruction(
            goal="learn-the-text",
            representation="whole-text",
        )
        is None
    )


def test_messages_user_turns_are_exact_context_for_every_supervised_goal(
    tmp_path: Path,
) -> None:
    for goal in goal_catalog().goals:
        if "conversation" not in goal.compatible_representations:
            continue
        workspace = tmp_path / goal.goal_id
        if goal.goal_id == "continue-a-passage":
            source_root, paths = _sources(workspace)
        elif goal.goal_id == "recover-a-section-from-its-heading":
            source_root = workspace / "sources"
            source_root.mkdir(parents=True)
            paths = []
            for name, heading in (("a.md", "First"), ("b.md", "Second")):
                path = source_root / name
                path.write_text(
                    f"# {heading} heading\n\nBody under {heading.lower()} heading.\n",
                    encoding="utf-8",
                )
                paths.append(path)
        elif goal.goal_id == "reproduce-a-recorded-change":
            source_root = workspace / "sources"
            source_root.mkdir(parents=True)
            paths = []
            for name in ("a.txt", "b.txt"):
                path = source_root / name
                path.write_text("line   one with   extra spaces\n", encoding="utf-8")
                paths.append(path)
        else:
            source_root = workspace / "sources"
            source_root.mkdir(parents=True)
            paths = []
            for name, title in (("a.md", "Alpha"), ("b.md", "Beta")):
                path = source_root / name
                path.write_text(
                    f"# {title}\n\nSee the [site](https://x.test/{name}).\n",
                    encoding="utf-8",
                )
                paths.append(path)
        SERVICE.parse(paths, workspace / "ws", source_root=source_root)
        SERVICE.clean(workspace / "ws")
        SERVICE.chunk(workspace / "ws", preset=f"{goal.goal_id}.safe")
        SERVICE.construct(
            workspace / "ws",
            goal=goal.goal_id,
            preset=f"{goal.goal_id}.safe",
            representation="conversation",
        )
        preview = SERVICE.preview_goal(
            workspace / "ws", representation="conversation"
        ).preview
        assert preview.records
        for entry in preview.records:
            user = entry.rendered_row["messages"][0]
            assert user["role"] == "user"
            context_value = next(iter(entry.context.values()))
            assert user["content"] == context_value
            assert "summar" not in user["content"].lower()
            assert "answer" not in user["content"].lower()
            assert "translat" not in user["content"].lower()


def test_instruction_output_rows_use_only_truthful_templates(tmp_path: Path) -> None:
    workspace = _constructed(tmp_path)
    SERVICE.curate(workspace, evaluation_required=False)
    store = Workspace.open(workspace)
    plan = _load_finished_plan(store, store.head())
    expected = goal_for_objective("continuation").instruction_template
    assert plan.serialization_plan.instruction_text == expected
    preview = SERVICE.preview_goal(workspace).preview
    assert preview.representation_id == "instruction-and-output"
    for entry in preview.records:
        assert entry.rendered_row["instruction"] == expected
        validate_instruction_text(goal_for_objective("continuation"), expected)
        assert entry.rendered_row["input"] == next(iter(entry.context.values()))


def test_curate_rejects_an_untruthful_operator_instruction(tmp_path: Path) -> None:
    workspace = _constructed(tmp_path)
    with pytest.raises(ValueError, match="summar"):
        SERVICE.curate(
            workspace,
            evaluation_required=False,
            instruction="Summarize the passage with its exact source remainder.",
        )


def test_cli_and_mcp_curate_share_the_catalog_template(tmp_path: Path) -> None:
    expected = goal_for_objective("continuation").instruction_template
    cli_ws = _constructed(tmp_path / "cli")
    mcp_ws = _constructed(tmp_path / "mcp")
    cli = runner.invoke(
        app,
        ["curate", str(cli_ws), "--allow-empty-evaluation"],
    )
    assert cli.exit_code == 0, cli.output
    _tool("curate")(str(mcp_ws), evaluation_required=False)
    for workspace in (cli_ws, mcp_ws):
        store = Workspace.open(workspace)
        plan = _load_finished_plan(store, store.head())
        assert plan.serialization_plan.instruction_text == expected


def test_yaml_curate_uses_the_catalog_template(tmp_path: Path) -> None:
    workspace = _constructed(tmp_path / "yaml")
    source_root = tmp_path / "yaml" / "sources"
    spec = tmp_path / "curate.yaml"
    spec.write_text(
        (
            "schema_version: veriformis.pipeline/v1\n"
            f"workspace: {workspace}\n"
            f"source_root: {source_root}\n"
            "sources:\n"
            f"  - {source_root / 'alpha.txt'}\n"
            f"  - {source_root / 'beta.txt'}\n"
            "stages:\n"
            "  curate:\n"
            "    allow_empty_evaluation: true\n"
        ),
        encoding="utf-8",
    )
    run_pipeline_spec(load_pipeline_spec(spec))
    store = Workspace.open(workspace)
    plan = _load_finished_plan(store, store.head())
    assert (
        plan.serialization_plan.instruction_text
        == goal_for_objective("continuation").instruction_template
    )
