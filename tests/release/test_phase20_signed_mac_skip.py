"""Phase 20.6: public signed Mac is not in the 1.0 matrix."""

from __future__ import annotations

from pathlib import Path

from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
SKIP = (
    ROOT
    / "dev/active/independent-product/phase-20-stable-1.0"
    / "skipped-signed-mac.md"
)


def test_signed_mac_is_skipped_with_a_record() -> None:
    text = SKIP.read_text(encoding="utf-8")
    assert "signed, notarized, and stapled Mac" in text
    assert "xcodebuild" in text
    assert "public_signed_mac" in text
    matrix = support_matrix()
    assert matrix.platforms.public_signed_mac is False
    assert matrix.platforms.macos_workbench == "local-dev-thin-adapter"
    workflows = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / ".github/workflows").glob("*.yml")
    )
    assert "xcodebuild" not in workflows
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "Signing/notarization remain owner-executed" in ci
