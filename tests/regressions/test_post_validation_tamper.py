import json

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.workspace import Workspace


def test_post_validation_record_mutation_refuses_seal(tmp_path):
    runner = CliRunner()
    source = tmp_path / "source.txt"
    source.write_text("alpha source text", encoding="utf-8")
    workspace = tmp_path / "workspace"

    commands = [
        [
            "parse",
            str(source),
            "-o",
            str(workspace),
            "--source-root",
            str(tmp_path),
        ],
        ["clean", str(workspace)],
        ["chunk", str(workspace), "--strategy", "paragraph"],
        ["construct", str(workspace), "--objective", "full_text"],
        ["curate", str(workspace), "--allow-empty-evaluation"],
        ["split", str(workspace)],
        ["format", str(workspace)],
        ["validate", str(workspace)],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output

    store = Workspace.open(workspace)
    revision = store.head()
    train_id = revision.stages["format"].outputs["train"]
    train_ref = revision.artifacts[train_id]
    train_path = store._object_path(train_ref.sha256)
    train_path.chmod(0o600)
    train_path.write_text(
        json.dumps(
            {"text": "fabricated after validation"},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "stale.vfbundle"
    result = runner.invoke(app, ["seal", str(workspace), "-o", str(bundle)])

    assert result.exit_code != 0
    assert "artifact-digest-mismatch" in result.output.lower()
    assert not bundle.exists()
