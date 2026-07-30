import json

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.workspace import Workspace


def test_chat_handoff_preserves_messages_and_masking_boundary(tmp_path):
    runner = CliRunner()
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text(
        "First source prompt material continues into its exact grounded answer.",
        encoding="utf-8",
    )
    second.write_text(
        "Second source prompt material continues into another grounded answer.",
        encoding="utf-8",
    )
    workspace_path = tmp_path / "workspace"
    commands = [
        [
            "parse",
            str(first),
            str(second),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
        [
            "construct",
            str(workspace_path),
            "--objective",
            "continuation",
            "--target-row-schema",
            "messages",
        ],
        ["curate", str(workspace_path)],
        ["split", str(workspace_path)],
        ["format", str(workspace_path)],
        ["validate", str(workspace_path)],
    ]
    for command in commands:
        prepared = runner.invoke(app, command)
        assert prepared.exit_code == 0, prepared.output

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    rows = []
    for partition in ("train", "evaluation"):
        artifact_id = revision.stages["format"].outputs[partition]
        rows.extend(
            json.loads(line)
            for line in workspace.read_artifact(
                artifact_id,
                revision=revision,
            )
            .decode("utf-8")
            .splitlines()
        )

    assert len(rows) == 2
    assert all(set(row) == {"messages"} for row in rows)
    assert all(row["messages"][0]["role"] == "user" for row in rows)
    assert all(row["messages"][-1]["role"] == "assistant" for row in rows)
    assert all(row["messages"][-1]["content"] for row in rows)
    assert all(
        not row["messages"][0]["content"].startswith("Summarize") for row in rows
    )
