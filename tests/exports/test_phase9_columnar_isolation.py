"""Phase 9 isolation: extras stay empty after taxonomy promotion."""

from __future__ import annotations

from pathlib import Path

from veriformis.exports import ExportService
from veriformis.exports.split_jsonl import (
    SPLIT_JSONL_CONTAINER_ID,
    SPLIT_JSONL_CONTAINER_VERSION,
)
from veriformis.taxonomy import (
    IMPLEMENTED_PHYSICAL_CONTAINERS,
    PLANNED_PHYSICAL_CONTAINERS,
    UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS,
    catalog,
)

ROOT = Path(__file__).resolve().parents[2]
COLUMNAR_CONTAINERS = ("parquet", "arrow", "hugging-face-dataset")


def test_planned_container_item_map_is_empty_after_promotion() -> None:
    assert PLANNED_PHYSICAL_CONTAINERS == ()
    assert dict(UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS) == {}
    assert IMPLEMENTED_PHYSICAL_CONTAINERS[-3:] == COLUMNAR_CONTAINERS


def test_taxonomy_lists_columnar_containers_as_implemented() -> None:
    entries = {
        (entry.axis, entry.identifier): entry.state for entry in catalog()
    }
    for identifier in COLUMNAR_CONTAINERS:
        assert entries[("physical_container", identifier)] == "implemented"


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
    assert named == {"aptus", "axolotl", "llama-factory", "mlx-lm", "trl"}
    for identifier in COLUMNAR_CONTAINERS:
        profile = profiles[(identifier, 1, None, None)]
        assert profile.consumer_profile is None
        assert profile.container_profile.determinism_claim == "semantic_content_only"


def test_no_unexecutable_physical_container_remains_on_the_cli() -> None:
    assert UNEXECUTABLE_PHYSICAL_CONTAINER_ITEMS == {}


def test_columnar_extra_is_declared_empty() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "columnar = []" in text
    assert "trl = []" in text
    assert "mlx-lm = []" in text
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "pyarrow"\n' not in lock
    assert 'name = "datasets"\n' not in lock
    assert 'name = "pandas"\n' not in lock
    assert (
        'provides-extras = ["test", "trl", "mlx-lm", "columnar", "axolotl", '
        '"llama-factory", "unsloth", "ocr"]' in lock
    )
    assert "axolotl = []" in text
