"""Post-20 remainder: unsigned Debug xcodebuild is optional, not a public Mac claim."""

from __future__ import annotations

from pathlib import Path

from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"
SCRIPT = ROOT / "scripts/release/xcodebuild_debug.sh"


def _workflows() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / ".github/workflows").glob("*.yml")
    )


def _xcodebuild_job(ci: str) -> str:
    marker = "  xcodebuild-debug:"
    start = ci.index(marker)
    return ci[start:]


def test_unsigned_debug_xcodebuild_is_optional_and_not_a_public_mac_claim() -> None:
    workflows = _workflows()
    ci = CI.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    job = _xcodebuild_job(ci)
    assert "xcodebuild" in workflows
    assert "name: xcodebuild-debug (optional)" in job
    assert "continue-on-error: true" in job
    assert "macos-latest" in job
    assert "xcodebuild_debug.sh" in job
    assert "CODE_SIGNING_ALLOWED=NO" in script
    assert "-scheme Veriformis" in script
    assert "-configuration Debug" in script
    assert "  test \\\n  CODE_SIGNING_ALLOWED=NO" in script
    assert "notarytool" not in workflows
    assert "stapler" not in workflows
    assert "secrets:" not in workflows.lower()
    assert "Signing/notarization remain owner-executed" in ci
    matrix = support_matrix()
    assert matrix.platforms.public_signed_mac is False
    assert matrix.platforms.macos_workbench == "local-dev-thin-adapter"


def test_live_copy_does_not_present_tense_skip_github_xcodebuild() -> None:
    phrase = (
        "GitHub xcodebuild, virtualization, and full localization are skipped"
    )
    for relative in ("docs/current-status.md", "CLAUDE.md", "CONTRIBUTING.md"):
        collapsed = " ".join((ROOT / relative).read_text(encoding="utf-8").split())
        assert phrase not in collapsed, relative


def test_beta_limitations_does_not_claim_no_ocr() -> None:
    text = (ROOT / "docs/beta-limitations.md").read_text(encoding="utf-8")
    assert "**No OCR.**" not in text
    assert "ocr-image" in text
    assert "Last reviewed:** 2026-08-11" not in text
