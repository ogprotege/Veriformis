import json
from pathlib import Path

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.construction import construction_result_from_dict
from veriformis.workspace import Workspace


FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "acceptance" / "v1"
runner = CliRunner()


def _succeeded(result):
    assert result.exit_code == 0, result.output


def _result(workspace):
    revision = workspace.head()
    artifact_id = revision.stages["construct"].outputs["result"]
    return construction_result_from_dict(
        json.loads(workspace.read_artifact(artifact_id, revision=revision))
    )


def test_raw_multisource_acceptance_corpus_constructs_two_objectives(tmp_path):
    sources = sorted((FIXTURE_ROOT / "raw").rglob("*"))
    sources = [path for path in sources if path.is_file()]
    root = tmp_path / "workspace"

    _succeeded(
        runner.invoke(
            app,
            [
                "parse",
                *(str(path) for path in sources),
                "-o",
                str(root),
                "--source-root",
                str(FIXTURE_ROOT),
            ],
        )
    )
    _succeeded(runner.invoke(app, ["clean", str(root)]))
    _succeeded(runner.invoke(app, ["chunk", str(root)]))
    workspace = Workspace.open(root)

    _succeeded(
        runner.invoke(
            app,
            ["construct", str(root), "--objective", "full_text"],
        )
    )
    full_text = _result(workspace)
    assert full_text.records
    assert {field.name for record in full_text.records for field in record.fields} == {
        "text"
    }
    record_sources = {
        source_id for record in full_text.records for source_id in record.source_ids
    }
    missing_sources = set(workspace.head().sources) - record_sources
    missing_diagnostics = tuple(
        diagnostic
        for diagnostic in full_text.diagnostics
        if diagnostic.code == "source-chunks-unavailable"
    )
    assert record_sources | missing_sources == set(workspace.head().sources)
    assert {diagnostic.source_ids for diagnostic in missing_diagnostics} == {
        (source_id,) for source_id in missing_sources
    }
    assert len(missing_diagnostics) == len(missing_sources)

    _succeeded(
        runner.invoke(
            app,
            [
                "construct",
                str(root),
                "--objective",
                "continuation",
                "--split-ratio-ppm",
                "400000",
            ],
        )
    )
    continuation = _result(workspace)
    assert continuation.records
    assert {
        tuple(field.name for field in record.fields)
        for record in continuation.records
    } == {("prompt", "completion")}

    repeated_revision = workspace.head().revision_id
    _succeeded(
        runner.invoke(
            app,
            [
                "construct",
                str(root),
                "--objective",
                "continuation",
                "--split-ratio-ppm",
                "400000",
            ],
        )
    )
    assert workspace.head().revision_id == repeated_revision
    assert _result(workspace).result_id == continuation.result_id

    _succeeded(
        runner.invoke(
            app,
            ["construct", str(root), "--objective", "full_text"],
        )
    )
    assert _result(workspace).result_id == full_text.result_id
