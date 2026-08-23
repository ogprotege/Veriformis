"""Phase 9.1: planned columnar containers refuse; existing selectors stay."""

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
from veriformis.taxonomy import (
    PLANNED_PHYSICAL_CONTAINERS,
    UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS,
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


def _planned_request(container_id: str) -> ExportDryRunRequest:
    return ExportDryRunRequest(
        operation="dry_run",
        schema_version=EXPORT_SURFACE_REQUEST_SCHEMA,
        bundle=str(FIXTURE),
        container_id=container_id,
        container_version=1,
        consumer_id=None,
        consumer_profile_version=None,
        source_trust_policy="allow_self_consistent",
        expected_manifest_sha256=None,
        overwrite_policy="refuse",
    )


def test_planned_container_item_map_is_closed_over_the_taxonomy() -> None:
    assert PLANNED_PHYSICAL_CONTAINERS == (
        "parquet",
        "arrow",
        "hugging-face-dataset",
    )
    assert PLANNED_PHYSICAL_CONTAINERS == (
        "parquet",
        "arrow",
        "hugging-face-dataset",
    )
    assert "parquet" not in UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS
    assert UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS["arrow"] == "9.5"
    assert UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS["hugging-face-dataset"] == "9.6"


def test_taxonomy_still_lists_columnar_containers_as_planned() -> None:
    entries = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    for identifier in PLANNED_PHYSICAL_CONTAINERS:
        assert entries[("physical_container", identifier)] == "planned"


def test_existing_generic_and_profile_selectors_remain_discoverable() -> None:
    profiles = {
        profile.selector: profile
        for profile in ExportService().discover_exports().profiles
    }
    assert (
        SPLIT_JSONL_CONTAINER_ID,
        SPLIT_JSONL_CONTAINER_VERSION,
        None,
        None,
    ) in profiles
    generic = [
        profile
        for profile in profiles.values()
        if profile.consumer_profile is None
    ]
    assert {profile.container_profile.container_id for profile in generic} == {
        "constrained-csv",
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
    for identifier in UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS:
        assert all(profile.selector[0] != identifier for profile in profiles.values())
    assert (
        "parquet",
        1,
        None,
        None,
    ) in profiles


def test_planned_container_refuses_before_source_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ExportService()
    source_opened = False

    def fail_if_opened(*_args: object, **_kwargs: object) -> None:
        nonlocal source_opened
        source_opened = True
        raise AssertionError("planned containers must fail before source access")

    monkeypatch.setattr(service, "verified_source", fail_if_opened)
    for container_id, item in UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS.items():
        with pytest.raises(
            ExportContractError,
            match=f"planned for item {item}",
        ):
            service.dry_run_export(_planned_request(container_id))
    assert source_opened is False


@pytest.mark.parametrize("container_id", tuple(UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS))
def test_planned_container_refusal_is_visible_on_the_cli(container_id: str) -> None:
    payload = _planned_request(container_id).canonical_bytes().decode("utf-8")
    result = RUNNER.invoke(app, ["export", "dry-run", "--request-json", payload])
    assert result.exit_code != 0
    later_item = UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS[container_id]
    assert f"planned for item {later_item}" in result.output
    assert container_id in result.output


def test_columnar_extra_is_declared_empty() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in text
    assert "trl = []" in text
    assert "mlx-lm = []" in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pyarrow"\n' not in lock
    assert 'name = "datasets"\n' not in lock
    assert 'name = "pandas"\n' not in lock
    assert 'provides-extras = ["test", "trl", "mlx-lm", "columnar"]' in lock
