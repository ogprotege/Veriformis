"""Phase 20.8: optional profiles stay isolated. The exporter does not train."""

from __future__ import annotations

import tomllib
from pathlib import Path

from veriformis.release import support_matrix
from veriformis.taxonomy import (
    CANDIDATE_CONSUMER_PROFILES,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
)


ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "docs/consumer-profiles.md"
CI = ROOT / ".github/workflows/ci.yml"


def test_optional_profiles_are_frozen_and_isolated() -> None:
    text = FREEZE.read_text(encoding="utf-8")
    assert "do not train" in text.lower() or "does not train" in text
    assert "unsloth" in text
    assert "continue-on-error" in text
    matrix = support_matrix()
    assert matrix.profiles.optional_export_adapters == tuple(
        IMPLEMENTED_EXPORT_CONSUMER_PROFILES
    )
    assert matrix.profiles.candidate_not_executable == tuple(CANDIDATE_CONSUMER_PROFILES)
    assert matrix.profiles.extras_required == ("columnar",)
    assert "unsloth" in matrix.profiles.candidate_not_executable
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = project["project"]["optional-dependencies"]
    for name in matrix.profiles.extras_empty:
        assert extras[name] == []
    assert extras["columnar"] == [
        "pyarrow>=19.0.0,<26.0.0",
        "datasets>=3.0.0,<6.0.0",
    ]
    ci = CI.read_text(encoding="utf-8")
    assert "name: profile-integration (optional)" in ci
    assert "name: aptus-integration (optional)" in ci
    assert "name: columnar-integration (optional)" in ci
    assert ci.count("continue-on-error: true") >= 3
    for adapter in ("trl", "mlx-lm", "axolotl", "llama-factory"):
        source = (
            ROOT / "src/veriformis/profiles" / f"{adapter.replace('-', '_')}.py"
        ).read_text(encoding="utf-8")
        assert "does not launch" in source
