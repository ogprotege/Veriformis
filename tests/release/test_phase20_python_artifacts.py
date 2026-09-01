"""Phase 20.7: inspected sdist and wheel. Binaries are not retained."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "dev/active/independent-product/phase-20-stable-1.0/evidence/python-artifacts"
)
SCRIPT = ROOT / "scripts/release/inspect_python_artifacts.sh"


def test_python_artifacts_were_inspected_without_retaining_binaries() -> None:
    assert SCRIPT.is_file()
    summary = (EVIDENCE / "SUMMARY.txt").read_text(encoding="utf-8")
    assert "status=PASS" in summary
    identities = (EVIDENCE / "identities.txt").read_text(encoding="utf-8")
    assert "veriformis-0.1.0-py3-none-any.whl" in identities
    assert "veriformis-0.1.0.tar.gz" in identities
    metadata = (EVIDENCE / "wheel_METADATA.txt").read_text(encoding="utf-8")
    assert "Name: veriformis" in metadata
    assert "Version: 0.1.0" in metadata
    assert "Requires-Python: >=3.11" in metadata
    assert "License-Expression: MIT" in metadata
    entry = (EVIDENCE / "wheel_entry_points.txt").read_text(encoding="utf-8")
    assert "veriformis = veriformis.cli:main" in entry
    members = (EVIDENCE / "wheel_members.txt").read_text(encoding="utf-8")
    assert "veriformis/release/support-matrix-v1.json" in members
    sdist = (EVIDENCE / "sdist_members.txt").read_text(encoding="utf-8")
    assert any(line.endswith("LICENSE") for line in sdist.splitlines())
    assert any(line.endswith("pyproject.toml") for line in sdist.splitlines())
    assert not list(EVIDENCE.rglob("*.whl"))
    assert not list(EVIDENCE.rglob("*.tar.gz"))
    blob = metadata + entry + members
    assert "HF_TOKEN" not in blob
    assert "BEGIN RSA PRIVATE KEY" not in blob
