"""Phase 16.8: ADR-0017 is policy. There is still no untrusted loader."""

from __future__ import annotations

import inspect
import tomllib
from pathlib import Path

from veriformis.cli import app
from veriformis.exports.service import ExportService
from veriformis.mcp.server import create_mcp_server
from veriformis.pipeline import PipelineService


ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr/0017-no-untrusted-extension-loader.md"
_FORBIDDEN_OPERATIONS = frozenset(
    {
        "extension-load",
        "extension_load",
        "install-extension",
        "install_extension",
        "plugin-load",
        "plugin_load",
        "install-plugin",
        "install_plugin",
    }
)


def test_adr_0017_records_decision_a_and_required_threats() -> None:
    text = ADR.read_text(encoding="utf-8")
    assert text.startswith("# ADR-0017 — No Untrusted Extension Loader in Phase 16\n")
    assert "**Status:** Accepted" in text
    assert "**Decision A.** Phase 16 does not install an untrusted loader." in text
    for heading in (
        "Process isolation",
        "Permissions / filesystem",
        "Network policy",
        "Resource limits",
        "Signing / trust",
        "Crash containment",
        "Workspace corruption",
        "Dataset-project code execution",
    ):
        assert heading in text
    assert "Decision B" in text
    assert "Decision C" in text
    assert "This item is policy. It adds no loader." in text


def test_no_loader_entry_points_or_workspace_plugin_path() -> None:
    assert not (ROOT / "src/veriformis/extensions/loader.py").exists()
    assert not (ROOT / "plugins").exists()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["scripts"] == {"veriformis": "veriformis.cli:main"}
    assert "entry-points" not in project
    runtime = (ROOT / "src/veriformis/extensions/runtime.py").read_text(
        encoding="utf-8"
    )
    registry = (ROOT / "src/veriformis/extensions/registry.py").read_text(
        encoding="utf-8"
    )
    for source in (runtime, registry):
        assert "entry_points" not in source
        assert "importlib.metadata" not in source
        assert "plugins/" not in source


def test_public_surfaces_still_have_no_plugin_install_operation() -> None:
    cli_names = {command.name for command in app.registered_commands}
    mcp_names = {tool.name for tool in create_mcp_server()._tool_manager.list_tools()}
    assert cli_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    assert mcp_names.isdisjoint(_FORBIDDEN_OPERATIONS)
    service = PipelineService()
    for name in _FORBIDDEN_OPERATIONS:
        assert not hasattr(service, name.replace("-", "_"))
    resolve = inspect.getsource(ExportService._resolve_implementation)
    assert "entry_point" not in resolve
    assert "plugins" not in resolve
