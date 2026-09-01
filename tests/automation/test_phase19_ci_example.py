"""Phase 19.6: retained project-spec example reproduces committed fingerprints."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from veriformis.automation import load_project_lock, load_project_spec
from veriformis.automation.inspect import spec_digest
from veriformis.cli import app


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "project-spec"
RUNNER = CliRunner()


def test_example_spec_lock_and_fingerprint_are_committed() -> None:
    spec = load_project_spec(json.loads((EXAMPLE / "spec.json").read_text(encoding="utf-8")))
    lock = load_project_lock(json.loads((EXAMPLE / "spec.lock.json").read_text(encoding="utf-8")))
    expected = json.loads((EXAMPLE / "expected-fingerprint.json").read_text(encoding="utf-8"))
    assert spec.spec_id == expected["spec_id"]
    assert spec_digest(spec) == expected["spec_digest"]
    assert lock.spec_id == spec.spec_id
    assert lock.spec_digest == expected["spec_digest"]
    assert "HF_TOKEN" not in (EXAMPLE / "spec.json").read_text(encoding="utf-8")
    assert "HF_TOKEN" not in (EXAMPLE / "spec.lock.json").read_text(encoding="utf-8")
    assert not (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").count("xcodebuild")


def test_example_spec_run_reproduces_committed_manifest(tmp_path: Path) -> None:
    copied = tmp_path / "example"
    shutil.copytree(EXAMPLE, copied)
    before = sorted(p.relative_to(copied).as_posix() for p in copied.rglob("*") if p.is_file())
    dry = RUNNER.invoke(app, ["spec-dry-run", str(copied / "spec.json")])
    assert dry.exit_code == 0, dry.output
    after = sorted(p.relative_to(copied).as_posix() for p in copied.rglob("*") if p.is_file())
    assert after == before
    result = RUNNER.invoke(app, ["spec-run", str(copied / "spec.json")])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected = json.loads((EXAMPLE / "expected-fingerprint.json").read_text(encoding="utf-8"))
    assert payload["spec_id"] == expected["spec_id"]
    manifest = Path(payload["bundle"]) / "manifest.json"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert digest == expected["manifest_sha256"]
    assert not list(copied.glob("**/*.vfexport.zip"))
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "golden_compile.sh" in workflow
    assert "project_spec_example.sh" in workflow
    assert "secrets:" not in workflow.lower()
