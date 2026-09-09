"""Staged goal construction matches preflight's explicit segmentation selection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ConstructionError
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService
from veriformis.pipeline.service import _load_constructed_dataset
from veriformis.workspace import Workspace


@pytest.mark.parametrize("surface", ["python", "cli", "mcp"])
def test_custom_chunks_require_matching_explicit_selection(tmp_path: Path, surface: str) -> None:
    service = PipelineService()
    source = tmp_path / "passage.txt"
    source.write_text("Exact source content continues here. " * 8, encoding="utf-8")
    settings = {"strategy": "paragraph", "size": 80, "overlap": 0}
    preflight = service.preflight(
        [source], source_root=tmp_path, goal="learn-the-text", evaluation_required=False, **settings,
    ).preflight
    assert preflight.admitted
    workspace = tmp_path / "workspace"
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace, goal="learn-the-text", **settings)
    before = Workspace.open(workspace).head_id
    tools = {t.name: t.fn for t in create_mcp_server(service)._tool_manager.list_tools()}
    if surface == "cli":
        refused = CliRunner().invoke(app, ["construct", str(workspace), "--goal", "learn-the-text"])
        assert refused.exit_code == 2 and "resolved goal/preset" in refused.output
    else:
        with pytest.raises(ConstructionError, match="resolved goal/preset"):
            if surface == "python":
                service.construct(workspace, goal="learn-the-text")
            else:
                tools["construct"](str(workspace), goal="learn-the-text")
    assert Workspace.open(workspace).head_id == before
    if surface == "python":
        result = service.construct(workspace, goal="learn-the-text", **settings)
        assert result.record_count == preflight.counts.record_count
    elif surface == "cli":
        result = CliRunner().invoke(app, [
            "construct", str(workspace), "--goal", "learn-the-text", "--strategy", "paragraph",
            "--size", "80", "--overlap", "0",
        ])
        assert result.exit_code == 0, result.output
    else:
        assert json.loads(tools["construct"](str(workspace), goal="learn-the-text", **settings))["exit_status"] == 0
    store = Workspace.open(workspace)
    recipe, result, _ = _load_constructed_dataset(store, store.head())
    assert recipe.segmentation.model_dump(exclude={"schema_version"}) == preflight.selection.resolved.segmentation.model_dump()
    assert len(result.records) == preflight.counts.record_count
