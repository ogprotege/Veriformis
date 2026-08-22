"""Goal discovery parity: Python, CLI, and MCP emit identical canonical JSON."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.goals import goal_catalog_json
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService

runner = CliRunner()


def _tool_map(server):
    return {tool.name: tool.fn for tool in server._tool_manager.list_tools()}


def test_service_discovery_is_fresh_and_equals_packaged_data() -> None:
    service = PipelineService()
    first = service.discover_goals()
    second = service.discover_goals()
    assert first == second and first is not second
    assert json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True) + "\n" == (
        goal_catalog_json()
    )


def test_cli_goals_prints_exact_catalog_json() -> None:
    first = runner.invoke(app, ["goals"])
    second = runner.invoke(app, ["goals"])
    assert first.exit_code == 0, first.output
    assert first.output == goal_catalog_json()
    assert second.output == first.output
    assert "format" not in json.loads(first.output)


def test_mcp_goals_delegates_to_service_with_exact_json_parity() -> None:
    calls = []

    class Recording(PipelineService):
        def discover_goals(self):
            calls.append("discover")
            return super().discover_goals()

    goals = _tool_map(create_mcp_server(Recording()))["goals"]
    payload = goals()
    assert calls == ["discover"]
    assert payload == goal_catalog_json()
