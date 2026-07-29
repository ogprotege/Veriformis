import json

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import (
    construction_result_from_dict,
    dataset_recipe_from_dict,
)
from veriformis.workspace import Workspace


runner = CliRunner()


def _succeeded(result):
    assert result.exit_code == 0, result.output


def _workspace_with_sources(tmp_path, values):
    paths = []
    for name, text in values:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    root = tmp_path / "workspace"
    _succeeded(
        runner.invoke(
            app,
            [
                "parse",
                *(str(path) for path in paths),
                "-o",
                str(root),
                "--source-root",
                str(tmp_path),
            ],
        )
    )
    _succeeded(runner.invoke(app, ["clean", str(root)]))
    _succeeded(runner.invoke(app, ["chunk", str(root)]))
    return root, Workspace.open(root)


def _construct_values(workspace, revision):
    state = revision.stages["construct"]
    recipe = dataset_recipe_from_dict(
        json.loads(
            workspace.read_artifact(
                state.outputs["recipe"],
                revision=revision,
            )
        )
    )
    result = construction_result_from_dict(
        json.loads(
            workspace.read_artifact(
                state.outputs["result"],
                revision=revision,
            )
        )
    )
    return recipe, result


def test_construct_cli_commits_real_full_text_result_and_repeats_as_noop(tmp_path):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [("source.txt", "First retained paragraph.\n\nSecond paragraph.")],
    )

    first = runner.invoke(
        app,
        ["construct", str(root), "--objective", "full_text"],
    )
    _succeeded(first)
    constructed = workspace.head()
    recipe, result = _construct_values(workspace, constructed)

    assert constructed.committed_stage == "construct"
    assert set(constructed.stages["construct"].outputs) == {"recipe", "result"}
    assert recipe.objective.kind == "full_text"
    assert recipe.target_row_schema == "text"
    assert result.candidates
    assert result.records
    assert all(record.fields[0].name == "text" for record in result.records)

    second = runner.invoke(
        app,
        ["construct", str(root), "--objective", "full_text"],
    )
    _succeeded(second)
    assert workspace.head().revision_id == constructed.revision_id


def test_construct_cli_selects_exact_source_subset(tmp_path):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [
            ("alpha/source.txt", "Alpha source text."),
            ("beta/source.txt", "Beta source text."),
        ],
    )
    source_id = next(
        source_id
        for source_id, descriptor in workspace.head().sources.items()
        if descriptor.logical_path == "beta/source.txt"
    )

    command = runner.invoke(
        app,
        [
            "construct",
            str(root),
            "--objective",
            "full_text",
            "--source",
            "beta/source.txt",
        ],
    )
    _succeeded(command)
    revision = workspace.head()
    recipe, result = _construct_values(workspace, revision)

    assert recipe.source_ids == (source_id,)
    assert {source for record in result.records for source in record.source_ids} == {
        source_id
    }
    for artifact_id in revision.stages["construct"].outputs.values():
        assert revision.artifacts[artifact_id].source_ids == (source_id,)


def test_construct_cli_required_review_keeps_candidates_pending(tmp_path):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [("review.txt", "Prompt and completion source material.")],
    )

    command = runner.invoke(
        app,
        [
            "construct",
            str(root),
            "--objective",
            "continuation",
            "--require-review",
        ],
    )
    _succeeded(command)
    recipe, result = _construct_values(workspace, workspace.head())

    assert recipe.review_policy == "required"
    assert result.candidates
    assert not result.records
    assert {decision.status for decision in result.decisions} == {"pending_review"}


def test_rerunning_chunk_invalidates_construct_but_not_legacy_format(tmp_path):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [("source.txt", "One paragraph with enough source text for construction.")],
    )
    _succeeded(
        runner.invoke(
            app,
            ["format", str(root), "--format", "completion"],
        )
    )
    _succeeded(
        runner.invoke(
            app,
            ["construct", str(root), "--objective", "full_text"],
        )
    )
    before = workspace.head()
    legacy_format = before.stages["format"]

    _succeeded(
        runner.invoke(
            app,
            [
                "chunk",
                str(root),
                "--strategy",
                "paragraph",
                "--size",
                "500",
                "--overlap",
                "50",
            ],
        )
    )
    revision = workspace.head()

    assert revision.stages["construct"].status == "stale"
    assert revision.stages["construct"].invalidated_by == "chunk"
    assert revision.stages["format"].status == "stale"
    assert legacy_format.status == "complete"


def test_construct_cli_failure_leaves_head_unchanged(tmp_path):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [("source.txt", "Source text.")],
    )
    before = workspace.head()

    result = runner.invoke(
        app,
        [
            "construct",
            str(root),
            "--objective",
            "full_text",
            "--source",
            "missing.txt",
        ],
    )

    assert result.exit_code == 2
    assert "unknown construction source" in result.output
    assert workspace.head() == before


@pytest.mark.parametrize(
    "arguments",
    [
        ["--objective", "summary"],
        ["--objective", "full_text", "--target-row-schema", "unknown"],
        ["--objective", "full_text", "--target-row-schema", "messages"],
        ["--objective", "section_reconstruction"],
    ],
)
def test_construct_cli_contract_errors_use_stable_machine_code(tmp_path, arguments):
    root, workspace = _workspace_with_sources(
        tmp_path,
        [("source.txt", "Source text remains unchanged.")],
    )
    before = workspace.head()

    result = runner.invoke(app, ["construct", str(root), *arguments])

    assert result.exit_code == 2
    assert "error[construction-invalid]" in result.output
    assert workspace.head() == before
