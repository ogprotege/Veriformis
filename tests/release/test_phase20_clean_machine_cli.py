"""Phase 20.5: retained clean-machine CLI evidence. Primary path has no Aptus."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "dev/active/independent-product/phase-20-stable-1.0/evidence/clean-machine-cli"
)


def test_clean_machine_cli_evidence_is_retained_without_aptus() -> None:
    summary = (EVIDENCE / "SUMMARY.txt").read_text(encoding="utf-8")
    assert "status=PASS" in summary
    assert "isolated wheel install" in summary
    version = (EVIDENCE / "installed_version.txt").read_text(encoding="utf-8").strip()
    assert version == "0.1.0"
    packages = (EVIDENCE / "installed_packages.txt").read_text(encoding="utf-8").casefold()
    assert "veriformis" in packages
    assert "\naptus " not in f"\n{packages}"
    assert "aptus==" not in packages
    wheel = (EVIDENCE / "wheel_identity.txt").read_text(encoding="utf-8")
    assert "veriformis-0.1.0-py3-none-any.whl" in wheel
    assert "wheel_sha256=" in wheel
    assert not list(EVIDENCE.rglob("*.whl"))
    log = (EVIDENCE / "golden_compile.log").read_text(encoding="utf-8")
    assert "golden_compile: PASS" in log
    assert "automatic_handoff=absent" in log or "aptus-handoff.json" not in log
    for objective in ("full_text", "continuation"):
        evidence = (EVIDENCE / "golden" / f"{objective}.evidence.txt").read_text(
            encoding="utf-8"
        )
        assert f"objective={objective}" in evidence
        assert "automatic_handoff=absent" in evidence
        assert "verification grade: external_digest" in evidence
        assert "transport archive status: accepted" in evidence
        assert "manifest_sha256=" in evidence
