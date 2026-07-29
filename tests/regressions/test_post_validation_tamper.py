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
        ["format", str(workspace), "--format", "completion"],
        ["validate", str(workspace), "--format", "completion"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output

    store = Workspace.open(workspace)
    revision = store.head()
    records_id = revision.stages["format"].outputs["records"]
    records_ref = revision.artifacts[records_id]
    records_path = store._object_path(records_ref.sha256)
    records_path.chmod(0o600)
    records_path.write_text(
        json.dumps({"text": "fabricated after validation"}) + "\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "stale.vfbundle"
    result = runner.invoke(app, ["seal", str(workspace), "-o", str(bundle)])

    assert result.exit_code != 0
    assert "artifact-digest-mismatch" in result.output.lower()
    assert not bundle.exists()
