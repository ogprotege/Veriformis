"""D-29 through D-31: release gates must carry independent failure signal."""
from __future__ import annotations

import asyncio
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from support.mcp import call_registered

ROOT = Path(__file__).resolve().parents[2]


def test_golden_script_refuses_a_wrong_committed_anchor(tmp_path):
    release = tmp_path / "scripts/release"
    release.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/release/golden_compile.sh", release)
    pins = json.loads((ROOT / "scripts/release/golden-manifests.json").read_text())
    pins["full_text"]["manifest_sha256"] = "0" * 64
    (release / "golden-manifests.json").write_text(json.dumps(pins))
    shutil.copytree(
        ROOT / "tests/fixtures/acceptance/v1/raw/corpus",
        tmp_path / "tests/fixtures/acceptance/v1/raw/corpus",
    )
    result = subprocess.run(
        ["bash", str(release / "golden_compile.sh")],
        env={**os.environ, "VERIFORMIS_CMD": shlex.join([sys.executable, "-c", "from veriformis.cli import main; main()"])},
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "expected external digest" in output
    assert "golden_compile: PASS" not in output


def test_ci_actions_are_immutable_and_matrices_are_required():
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    jobs = workflow["jobs"]
    for job in jobs.values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", step["uses"])
    matrix = jobs["acceptance-matrix"]
    assert matrix.get("continue-on-error", False) is False
    matrix_runs = "\n".join(step.get("run", "") for step in matrix["steps"])
    assert '-m "matrix and not aptus_integration' in matrix_runs
    core_runs = "\n".join(step.get("run", "") for step in jobs["test"]["steps"])
    assert 'and not matrix"' in core_runs
    for name in ("aptus-integration", "profile-integration", "columnar-integration"):
        assert jobs[name]["continue-on-error"] is True


def test_shared_helpers_do_not_import_collected_test_modules():
    for path in (ROOT / "tests").rglob("*.py"):
        if "fixtures" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(part.startswith("test_") for part in node.module.split(".")), path
            elif isinstance(node, ast.Import):
                assert not any(part.startswith("test_") for alias in node.names for part in alias.name.split(".")), path


def test_mcp_harness_owns_each_async_loop_after_a_previous_loop_closed():
    async def value():
        return "resolved"
    assert asyncio.run(value()) == "resolved"
    assert call_registered(value) == "resolved"
    assert call_registered(value) == "resolved"
    assert call_registered(lambda: "sync") == "sync"
