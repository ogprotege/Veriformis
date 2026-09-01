"""Phase 19.8: credentials never persist in compiler artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.automation import (
    create_project_spec,
    load_project_lock,
    load_project_spec,
)
from veriformis.cli import app
from veriformis.errors import ProjectSpecError
from veriformis.mcp.server import create_mcp_server
from veriformis.recipes.pipeline_spec import PIPELINE_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "project-spec"
RUNNER = CliRunner()
SECRET = "hf_secret_value_phase19_isolation"
AWS_SECRET = "aws_secret_value_phase19_isolation"


def _scan(root: Path) -> str:
    chunks: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def test_spec_and_lock_refuse_credential_shaped_fields() -> None:
    spec = create_project_spec(
        mode="document-source",
        goal_id="learn-the-text",
        pipeline={
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workspace": "/tmp/ws",
            "sources": ["a.txt"],
            "stages": {"parse": {}, "seal": {"out": "/tmp/out.vfbundle"}},
        },
    )
    payload = spec.model_dump(mode="json")
    payload["hf_token"] = SECRET
    with pytest.raises(ProjectSpecError, match="credential-shaped field"):
        load_project_spec(payload)
    lock = json.loads((EXAMPLE / "spec.lock.json").read_text(encoding="utf-8"))
    lock["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET
    with pytest.raises(ProjectSpecError, match="credential-shaped field"):
        load_project_lock(lock)


def test_injected_env_secrets_do_not_persist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", SECRET)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", AWS_SECRET)
    monkeypatch.setenv("AUTHORIZATION", "Bearer phase19")
    copied = tmp_path / "example"
    shutil.copytree(EXAMPLE, copied)
    result = RUNNER.invoke(app, ["spec-run", str(copied / "spec.json")])
    assert result.exit_code == 0, result.output
    blob = result.output + "\n" + _scan(copied)
    assert SECRET not in blob
    assert AWS_SECRET not in blob
    assert "Bearer phase19" not in blob
    env = RUNNER.invoke(app, ["env-inspect"])
    assert SECRET not in env.output
    assert "HF_TOKEN" not in env.output
    tools = {tool.name: tool.fn for tool in create_mcp_server()._tool_manager.list_tools()}
    mcp_env = tools["env_inspect"]()
    assert SECRET not in mcp_env
    assert "HF_TOKEN" not in mcp_env
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "secrets:" not in workflow.lower()
    assert "HF_TOKEN" not in workflow
