from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.workspace import Workspace


def test_unchanged_chunk_cannot_claim_summary_objective(tmp_path):
    runner = CliRunner()
    source = tmp_path / "source.txt"
    source.write_text("This is unchanged source text.", encoding="utf-8")
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
    ]
    for command in commands:
        prepared = runner.invoke(app, command)
        assert prepared.exit_code == 0, prepared.output

    workspace = Workspace.open(workspace_path)
    before_construct = workspace.head_id
    result = runner.invoke(
        app,
        [
            "construct",
            str(workspace_path),
            "--objective",
            "summary",
            "--target-row-schema",
            "messages",
        ],
    )

    assert result.exit_code != 0
    assert "objective" in result.output.lower()
    assert workspace.head_id == before_construct
