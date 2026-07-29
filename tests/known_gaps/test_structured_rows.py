import json

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.workspace import Workspace


@pytest.mark.xfail(strict=True, reason="roadmap-step-14: Aptus chat rows remain structured messages")
def test_chat_handoff_preserves_messages_and_masking_boundary(tmp_path):
    runner = CliRunner()
    source = tmp_path / "source.txt"
    source.write_text("source-grounded answer", encoding="utf-8")
    workspace_path = tmp_path / "workspace"
    commands = [
        [
            "parse",
            str(source),
            "-o",
            str(workspace_path),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace_path)],
        ["chunk", str(workspace_path), "--strategy", "paragraph"],
        ["format", str(workspace_path), "--format", "chat", "--template", "qwen"],
    ]
    for command in commands:
        prepared = runner.invoke(app, command)
        assert prepared.exit_code == 0, prepared.output

    workspace = Workspace.open(workspace_path)
    revision = workspace.head()
    records_id = revision.stages["format"].outputs["records"]
    rows = [
        json.loads(line)
        for line in workspace.read_artifact(records_id, revision=revision)
        .decode("utf-8")
        .splitlines()
    ]

    assert set(rows[0]) == {"messages"}
    assert rows[0]["messages"][-1]["role"] == "assistant"
    assert rows[0]["messages"][-1]["content"]
