"""Locks standalone imports and default CLI sealing against Aptus coupling."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from veriformis.pipeline import PipelineService

REPO_ROOT = Path(__file__).resolve().parents[2]


def _finished_workspace(tmp_path: Path) -> Path:
    source = tmp_path / "source.txt"
    source.write_text(
        "First paragraph proves standalone compilation and sealing.\n\n"
        "Second paragraph provides a deterministic completion target.",
        encoding="utf-8",
    )
    workspace = tmp_path / "workspace"
    service = PipelineService()
    service.parse([source], workspace, source_root=tmp_path)
    service.clean(workspace)
    service.chunk(workspace)
    service.construct(workspace, objective="continuation", split_ratio_ppm=400_000)
    service.curate(workspace, evaluation_required=False)
    service.split(workspace)
    service.format(workspace)
    assert service.validate(workspace).exit_status == 0
    return workspace


def test_cli_and_mcp_default_path_never_imports_or_writes_aptus(tmp_path):
    """Fresh-process imports, MCP creation, and default seal stay standalone."""
    workspace = _finished_workspace(tmp_path)
    bundle = tmp_path / "standalone.vfbundle"
    handoff = Path(f"{bundle.resolve()}.aptus-handoff.json")
    script = """
import sys
from pathlib import Path
from typer.testing import CliRunner
from veriformis.cli import app

assert "veriformis.handoff" not in sys.modules
from veriformis.mcp.server import create_mcp_server
assert "veriformis.handoff" not in sys.modules
create_mcp_server()
assert "veriformis.handoff" not in sys.modules

workspace = Path(sys.argv[1])
bundle = Path(sys.argv[2])
result = CliRunner().invoke(app, ["seal", str(workspace), "-o", str(bundle)])
assert result.exit_code == 0, result.output
assert "aptus handoff:" not in result.output.lower()
assert "veriformis.handoff" not in sys.modules
assert not Path(f"{bundle.resolve()}.aptus-handoff.json").exists()
"""
    environment = os.environ.copy()
    source_root = str(REPO_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root
        if not existing_pythonpath
        else f"{source_root}{os.pathsep}{existing_pythonpath}"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(workspace), str(bundle)],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert bundle.is_dir()
    assert not handoff.exists()
