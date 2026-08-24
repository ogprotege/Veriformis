"""Phase 8 isolation: generic exports stay null; candidates refuse as Phase 10."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from veriformis.cli import app
from veriformis.errors import ExportContractError
from veriformis.exports import (
    EXPORT_SURFACE_REQUEST_SCHEMA,
    ExportDryRunRequest,
    ExportService,
)
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
)
from veriformis.pipeline import PipelineService
from veriformis.taxonomy import (
    CANDIDATE_CONSUMER_PROFILES,
    IMPLEMENTED_EXPORT_CONSUMER_PROFILES,
    PLANNED_CONSUMER_PROFILE_ITEMS,
    PLANNED_CONSUMER_PROFILES,
    UNEXECUTABLE_CONSUMER_PROFILE_ITEMS,
    catalog,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
RUNNER = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _planned_request(consumer_id: str) -> ExportDryRunRequest:
    return ExportDryRunRequest(
        operation="dry_run",
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
        bundle=str(FIXTURE),
        container_id=SPLIT_JSONL_CONTAINER_ID,
        container_version=SPLIT_JSONL_CONTAINER_VERSION,
        consumer_id=consumer_id,
        consumer_profile_version=1,
        source_trust_policy="allow_self_consistent",
        expected_manifest_sha256=None,
        overwrite_policy="refuse",
    )


def test_planned_profile_item_map_is_empty_after_promotion() -> None:
    assert PLANNED_CONSUMER_PROFILES == ()
    assert dict(PLANNED_CONSUMER_PROFILE_ITEMS) == {}
    assert IMPLEMENTED_EXPORT_CONSUMER_PROFILES == (
        "trl",
        "mlx-lm",
        "axolotl",
        "llama-factory",
        "aptus",
    )
    assert UNEXECUTABLE_CONSUMER_PROFILE_ITEMS == {}


def test_taxonomy_lists_trl_and_mlx_lm_as_implemented() -> None:
    entries = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    assert entries[("consumer_profile", "trl")] == "implemented"
    assert entries[("consumer_profile", "mlx-lm")] == "implemented"
    assert entries[("consumer_profile", "axolotl")] == "implemented"
    assert entries[("consumer_profile", "llama-factory")] == "implemented"
    assert entries[("consumer_profile", "aptus")] == "implemented"
    for identifier in CANDIDATE_CONSUMER_PROFILES:
        assert entries[("consumer_profile", identifier)] == "candidate"


def test_generic_export_discovery_keeps_a_null_consumer_profile() -> None:
    discovery = PipelineService().discover_exports().discovery
    assert discovery is not None
    generic = [
        profile for profile in discovery.profiles if profile.consumer_profile is None
    ]
    named = [
        profile for profile in discovery.profiles if profile.consumer_profile is not None
    ]
    assert generic
    assert all(profile.consumer_profile is None for profile in generic)
    assert {
        profile.consumer_profile.consumer_id
        for profile in named
        if profile.consumer_profile is not None
    } == {"aptus", "axolotl", "llama-factory", "mlx-lm", "trl"}


def test_emitted_profiles_are_not_refused_as_planned() -> None:
    selectors = {
        profile.selector[2] for profile in ExportService().discover_exports().profiles
    }
    assert {"aptus", "axolotl", "llama-factory", "mlx-lm", "trl"} <= selectors


def test_candidate_consumer_id_refuses_as_phase_10() -> None:
    with pytest.raises(ExportContractError, match="Phase 10 candidate"):
        ExportService().dry_run_export(_planned_request("unsloth"))


def test_candidate_consumer_id_refusal_is_visible_on_the_cli() -> None:
    payload = _planned_request("unsloth").canonical_bytes().decode("utf-8")
    result = RUNNER.invoke(app, ["export", "dry-run", "--request-json", payload])
    assert result.exit_code != 0
    assert "Phase 10 candidate" in result.output


def test_optional_profile_extras_are_declared_empty() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "trl = []" in text
    assert "mlx-lm = []" in text
    assert 'test = ["pytest>=8.0", "ruff==0.16.0"]' in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "trl"\n' not in lock
    assert 'name = "mlx-lm"\n' not in lock
    assert 'name = "torch"\n' not in lock
    assert 'name = "mlx"\n' not in lock
