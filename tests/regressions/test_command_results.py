"""Machine receipts are separate from human diagnostics and bind actual output."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.pipeline import PipelineService


@pytest.fixture
def curated(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    for name, text in [("a.txt", "Alpha evidence has its own immutable source passage."),
                       ("b.txt", "Beta records preserve a distinct independently supplied passage.")]:
        (sources / name).write_text(text * 4)
    service = PipelineService()
    workspace = tmp_path / "workspace"
    service.parse([sources], workspace, source_root=sources)
    service.clean(workspace)
    service.chunk(workspace, goal="learn-the-text")
    service.construct(workspace, goal="learn-the-text")
    service.curate(workspace)
    return service, workspace


def receipt(runner, command, args):
    result = runner.invoke(app, [command, *map(str, args), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload) == {"schema_id", "command", "result"}
    assert payload["schema_id"] == "veriformis.command-result/v1"
    assert payload["command"] == command
    return payload["result"], result


@pytest.mark.parametrize("name", ["sealed.vfbundle", "Café e\u0301.vfbundle"])
def test_split_seal_and_package_receipts_bind_real_bytes(curated, tmp_path, name):
    service, workspace = curated
    runner = CliRunner()
    split, split_process = receipt(runner, "split", [workspace])
    assert len(split["assignment_digest"]) == 64
    assert "split" in split_process.stderr.lower()
    service.format(workspace)
    service.validate(workspace)
    bundle = tmp_path / name
    seal, seal_process = receipt(runner, "seal", [workspace, "-o", bundle])
    manifest = hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest()
    assert seal["manifest_sha256"] == manifest
    assert Path(seal["bundle_path"]) == bundle
    assert seal["handoff_path"] is None
    assert seal["revision_id"]
    assert "manifest SHA-256:" in seal_process.stderr
    archive = tmp_path / (name + ".zip")
    package, process = receipt(runner, "package", [bundle, "-o", archive, "--manifest-sha256", manifest])
    assert package == {
        "archive_path": str(archive),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "manifest_sha256": manifest,
        "export_receipt_sha256": None,
    }
    assert "archive SHA-256:" in process.stderr
    assert service.package_verify(archive, manifest_sha256=manifest).exit_status == 0


def test_machine_failure_has_no_success_receipt(tmp_path):
    result = CliRunner().invoke(app, ["seal", str(tmp_path / "missing"), "-o", str(tmp_path / "bundle"), "--json"])
    assert result.exit_code != 0
    assert not result.stdout
    assert "error[" in result.stderr
