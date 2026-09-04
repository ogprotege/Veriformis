"""Phase 19.3: project-spec schema, dry-run, lockfile, and env inspect."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.automation import (
    create_project_lock,
    create_project_spec,
    dry_run_project_spec,
    inspect_environment,
    load_project_lock,
    load_project_spec_document,
    project_spec_json_schema,
)
from veriformis.automation.spec import ProjectSpec
from veriformis.cli import app
from veriformis.identity import derive_id
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION


RUNNER = CliRunner()
DIGEST = "a" * 64
MAPPING_PLAN_ID = derive_id("mpl", {"confirmation_digest": DIGEST, "goal_id": "learn-the-text"})
PIPELINE = {
    "schema_version": PIPELINE_SCHEMA_VERSION,
    "workspace": "/tmp/veriformis-project-spec-ws",
    "sources": ["source.md"],
    "stages": {
        "parse": {},
        "seal": {"out": "/tmp/veriformis-project-spec.vfbundle"},
    },
}


def _spec(**overrides: object) -> ProjectSpec:
    defaults: dict[str, object] = {
        "mode": "document-source",
        "goal_id": "learn-the-text",
        "pipeline": PIPELINE,
    }
    defaults.update(overrides)
    return create_project_spec(**defaults)


def _write_spec(tmp_path: Path, spec: ProjectSpec, name: str = "spec.json") -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(spec.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_schema_is_generated_from_the_model() -> None:
    schema = project_spec_json_schema()
    expected = json.loads(json.dumps(ProjectSpec.model_json_schema(), sort_keys=True))
    assert schema == expected
    assert "spec_id" in json.dumps(schema)
    assert schema != {"type": "object"}


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _spec())
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    preview = dry_run_project_spec(load_project_spec_document(path))
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    assert after == before
    assert preview.writes_workspace is False
    assert preview.writes_bundle is False
    assert preview.writes_destination is False
    assert preview.mode == "document-source"
    assert preview.mapping_required is False
    assert "parse" in preview.stages
    assert "map" not in preview.stages
    assert preview.stages[-1] == "seal"
    assert preview.stages == (
        "parse",
        "clean",
        "chunk",
        "construct",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    )


def test_dataset_row_dry_run_inserts_map() -> None:
    spec = _spec(
        mode="dataset-row",
        mapping={
            "mapping_plan_id": MAPPING_PLAN_ID,
            "confirmation_digest": DIGEST,
        },
        pipeline={**PIPELINE, "sources": ["rows.jsonl"]},
    )
    preview = dry_run_project_spec(spec)
    assert preview.mapping_required is True
    assert preview.mapping_confirmed is True
    assert preview.stages[:2] == ("parse", "map")
    assert preview.stages == (
        "parse",
        "map",
        "curate",
        "split",
        "format",
        "validate",
        "seal",
    )


def test_lockfile_pins_digest_version_and_empty_extras() -> None:
    spec = _spec()
    lock = create_project_lock(spec)
    loaded = load_project_lock(lock.model_dump(mode="json"))
    assert loaded == lock
    assert loaded.spec_id == spec.spec_id
    assert loaded.veriformis_version == "0.1.0"
    assert loaded.python_version.count(".") == 1
    assert loaded.extras["trl"] == "empty"
    assert loaded.extras["ocr"] == "empty"
    assert loaded.extras["test"] == "present"
    blob = json.dumps(loaded.model_dump(mode="json"))
    assert "HF_TOKEN" not in blob
    assert "AWS" not in blob


def test_environment_inspect_omits_secrets(monkeypatch: object) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws_secret")
    packet = inspect_environment()
    dumped = json.dumps(packet.model_dump(mode="json"))
    assert "hf_secret" not in dumped
    assert "aws_secret" not in dumped
    assert "HF_TOKEN" not in dumped
    assert packet.taxonomy_implemented_counts["training_family"] > 0
    assert packet.extras["columnar"] == "present"


def test_cli_schema_dry_run_lock_and_env(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _spec())
    schema = RUNNER.invoke(app, ["spec-schema"])
    assert schema.exit_code == 0, schema.output
    assert json.loads(schema.output) == project_spec_json_schema()
    dry = RUNNER.invoke(app, ["spec-dry-run", str(path)])
    assert dry.exit_code == 0, dry.output
    payload = json.loads(dry.output)
    assert payload["writes_workspace"] is False
    lock_path = tmp_path / "spec.lock.json"
    locked = RUNNER.invoke(app, ["spec-lock", str(path), "--out", str(lock_path)])
    assert locked.exit_code == 0, locked.output
    assert lock_path.is_file()
    env = RUNNER.invoke(app, ["env-inspect"])
    assert env.exit_code == 0, env.output
    assert "HF_TOKEN" not in env.output


def test_pipeline_ref_dry_run_does_not_invent_stages() -> None:
    spec = _spec(pipeline=None, pipeline_ref="compile.yaml")
    from veriformis.errors import ProjectSpecError

    with pytest.raises(ProjectSpecError, match="unresolved pipeline_ref"):
        dry_run_project_spec(spec)


def test_lock_rejects_malformed_digest() -> None:
    from veriformis.errors import ProjectSpecError

    spec = _spec()
    payload = create_project_lock(spec).model_dump(mode="json")
    payload["spec_digest"] = "not-a-digest"
    payload["lock_id"] = derive_id(
        "plk",
        {key: value for key, value in payload.items() if key != "lock_id"},
    )
    with pytest.raises(ProjectSpecError):
        load_project_lock(payload)


def test_spec_lock_refuses_existing_out(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _spec())
    lock_path = tmp_path / "spec.lock.json"
    first = RUNNER.invoke(app, ["spec-lock", str(path), "--out", str(lock_path)])
    assert first.exit_code == 0, first.output
    second = RUNNER.invoke(app, ["spec-lock", str(path), "--out", str(lock_path)])
    assert second.exit_code == 2
    assert "already exists" in second.output


def test_create_project_spec_runs_in_fresh_interpreter() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from veriformis.automation import create_project_spec;"
                "spec=create_project_spec(mode='document-source', goal_id='learn-the-text');"
                "print(spec.spec_id)"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("psp-v1-")


def test_invalid_spec_dry_run_exits_2(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"schema_id": "nope"}\n', encoding="utf-8")
    result = RUNNER.invoke(app, ["spec-dry-run", str(path)])
    assert result.exit_code == 2


def test_pipeline_service_owns_the_new_surfaces() -> None:
    service = PipelineService()
    spec = _spec()
    assert service.project_spec_schema() == project_spec_json_schema()
    preview = service.dry_run_project_spec(spec.model_dump(mode="json"))
    assert preview["writes_destination"] is False
    lock = service.lock_project_spec(spec.model_dump(mode="json"))
    assert lock["spec_id"] == spec.spec_id
    env = service.inspect_environment()
    assert "taxonomy_implemented_counts" in env


def test_mcp_still_has_no_hub_tools() -> None:
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert "spec_dry_run" in mcp_names
    assert "spec_lock" in mcp_names
    assert "env_inspect" in mcp_names
    assert "hub_upload" not in mcp_names
    assert "package_verify" not in mcp_names
