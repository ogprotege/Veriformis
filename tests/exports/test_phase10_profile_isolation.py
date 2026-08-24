"""Phase 10.1: candidate profiles refuse; extras stay empty; implemented selectors stay."""

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
from veriformis.taxonomy import CANDIDATE_CONSUMER_PROFILES, catalog

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "regressions"
    / "fixtures"
    / "phase3"
    / "pre-taxonomy-full-text.vfbundle.json"
)
RUNNER = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def _candidate_request(consumer_id: str) -> ExportDryRunRequest:
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


def test_taxonomy_keeps_phase_10_profiles_as_candidates() -> None:
    assert CANDIDATE_CONSUMER_PROFILES == ("axolotl", "llama-factory", "unsloth")
    entries = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    for identifier in CANDIDATE_CONSUMER_PROFILES:
        assert entries[("consumer_profile", identifier)] == "candidate"
    assert entries[("consumer_profile", "trl")] == "implemented"
    assert entries[("consumer_profile", "mlx-lm")] == "implemented"


def test_implemented_generic_and_profile_selectors_remain_discoverable() -> None:
    profiles = {
        profile.selector: profile
        for profile in ExportService().discover_exports().profiles
    }
    generic = {
        profile.container_profile.container_id
        for profile in profiles.values()
        if profile.consumer_profile is None
    }
    assert generic == {
        "arrow",
        "constrained-csv",
        "hugging-face-dataset",
        "json",
        "parquet",
        "split-jsonl-directory",
    }
    named = {
        profile.consumer_profile.consumer_id
        for profile in profiles.values()
        if profile.consumer_profile is not None
    }
    assert named == {"mlx-lm", "trl"}
    for identifier in CANDIDATE_CONSUMER_PROFILES:
        assert all(profile.selector[2] != identifier for profile in profiles.values())


def test_null_consumer_discovery_still_lists_generics() -> None:
    discovery = PipelineService().discover_exports().discovery
    assert discovery is not None
    generic = [
        profile for profile in discovery.profiles if profile.consumer_profile is None
    ]
    assert {profile.container_profile.container_id for profile in generic} == {
        "arrow",
        "constrained-csv",
        "hugging-face-dataset",
        "json",
        "parquet",
        "split-jsonl-directory",
    }


@pytest.mark.parametrize("consumer_id", CANDIDATE_CONSUMER_PROFILES)
def test_candidate_consumer_id_refuses_as_phase_10(consumer_id: str) -> None:
    with pytest.raises(ExportContractError, match="Phase 10 candidate"):
        ExportService().dry_run_export(_candidate_request(consumer_id))


@pytest.mark.parametrize("consumer_id", CANDIDATE_CONSUMER_PROFILES)
def test_candidate_refusal_is_visible_on_the_cli(consumer_id: str) -> None:
    payload = _candidate_request(consumer_id).canonical_bytes().decode("utf-8")
    result = RUNNER.invoke(app, ["export", "dry-run", "--request-json", payload])
    assert result.exit_code != 0
    assert "Phase 10 candidate" in result.output
    assert consumer_id in result.output


def test_candidate_pins_do_not_make_export_executable() -> None:
    from veriformis.profiles import candidate_profile_admission_catalog

    catalog = candidate_profile_admission_catalog()
    emit_eligible = {
        record.profile_id for record in catalog.records if record.emit_eligible
    }
    assert emit_eligible == {"axolotl", "llama-factory"}
    for consumer_id in CANDIDATE_CONSUMER_PROFILES:
        with pytest.raises(ExportContractError, match="Phase 10 candidate"):
            ExportService().dry_run_export(_candidate_request(consumer_id))


def test_phase_10_extras_are_declared_empty() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "axolotl = []" in text
    assert "llama-factory = []" in text
    assert "unsloth = []" in text
    assert "trl = []" in text
    assert "mlx-lm = []" in text
    assert "columnar = []" in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "axolotl"\n' not in lock
    assert 'name = "unsloth"\n' not in lock
    assert 'name = "llamafactory"\n' not in lock
    assert 'name = "llama-factory"\n' not in lock
    assert 'name = "torch"\n' not in lock
    assert 'provides-extras = ["test", "trl", "mlx-lm", "columnar", "axolotl", "llama-factory", "unsloth"]' in lock
