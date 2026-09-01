"""Phase 20.9: support-lifecycle docs stay honest to the frozen matrix."""

from __future__ import annotations

from pathlib import Path

from veriformis import __version__
from veriformis.release import support_matrix


ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE = ROOT / "docs/support-lifecycle.md"
TROUBLE = ROOT / "docs/troubleshooting.md"
INDEX = ROOT / "docs/README.md"


def test_support_lifecycle_docs_name_required_policy() -> None:
    text = LIFECYCLE.read_text(encoding="utf-8")
    for required in (
        "Semantic versioning",
        "Compatibility windows",
        "Upstream profile review cadence",
        "Deprecation notice",
        "Vulnerability response",
        "Release rollback",
        "This page is not a version bump",
        "Unknown versions fail closed",
        "The exporter does not train.",
    ):
        assert required in text, required
    assert __version__ == "0.1.0"
    assert "0.1.0" in text
    matrix = support_matrix()
    assert matrix.product_version == "0.1.0"
    assert matrix.maturity == "development-alpha"
    trouble = TROUBLE.read_text(encoding="utf-8")
    for required in (
        "Unknown suffix",
        "ocr-image",
        "The exporter does not train.",
        "Hub execute",
        "Public signed Mac",
        "quality-report command",
    ):
        assert required in trouble, required
    index = INDEX.read_text(encoding="utf-8")
    assert "support-lifecycle.md" in index
    assert "troubleshooting.md" in index
    mapping = (ROOT / "docs/mapping.md").read_text(encoding="utf-8")
    assert "No trainer, spreadsheet, or Hub compatibility." in mapping
    exports = (ROOT / "docs/generic-exports.md").read_text(encoding="utf-8")
    assert "There is no Hub" in exports
    profiles = (ROOT / "docs/consumer-profiles.md").read_text(encoding="utf-8")
    assert "The exporter does not train." in profiles
    security = (ROOT / "docs/security.md").read_text(encoding="utf-8")
    assert "## Privacy" in security
    migration = (ROOT / "docs/migration.md").read_text(encoding="utf-8")
    assert "Unknown versions fail closed" in migration
    goals = (ROOT / "docs/cli.md").read_text(encoding="utf-8")
    assert "veriformis.goal-catalog/v1" in goals
    install = (ROOT / "docs/install.md").read_text(encoding="utf-8")
    assert "support-lifecycle.md" in install
