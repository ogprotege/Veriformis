"""Recipe presets v1: the single versioned source of every recipe default."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.contracts import (
    RECIPE_PRESET_CONTRACT_ID,
    RECIPE_PRESET_CONTRACT_VERSION,
    RECIPE_PRESET_SCHEMA_ID,
)
from veriformis.errors import GoalCatalogError
from veriformis.goals import (
    RECIPE_PRESET_DATA_NAME,
    PresetCatalog,
    discover_presets,
    goal_catalog,
    parse_preset_catalog,
    preset_catalog,
    preset_catalog_json,
    recipe_defaults,
    resolve_recipe_settings,
)
from veriformis.identity import sha256_digest
from veriformis.recipes import RECIPE_LIBRARY_IDS

DATA_PATH = Path(__file__).parents[2] / "src" / "veriformis" / "goals" / "presets-v1.json"
DATA_SHA256 = "26c90b78bd685eff74cd9a1866b6696f7989b6af586715a9476ee0069aedfffb"
FROZEN = Path(__file__).parents[1] / "regressions" / "fixtures" / "phase6" / "recipe-presets.json"


def _payload() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_preset_contract_constants_and_packaged_data_are_exact() -> None:
    assert RECIPE_PRESET_CONTRACT_ID == "veriformis.recipe-preset"
    assert RECIPE_PRESET_CONTRACT_VERSION == 1
    assert RECIPE_PRESET_SCHEMA_ID == "veriformis.recipe-preset/v1"
    assert RECIPE_PRESET_DATA_NAME == "presets-v1.json"
    stored = DATA_PATH.read_text(encoding="utf-8")
    assert sha256_digest(stored) == DATA_SHA256
    assert json.dumps(json.loads(stored), ensure_ascii=False, indent=2, sort_keys=True) + "\n" == stored
    assert FROZEN.read_text(encoding="utf-8") == stored
    catalog = preset_catalog()
    assert isinstance(catalog, PresetCatalog)
    assert preset_catalog() is catalog
    assert preset_catalog_json() == stored
    first = discover_presets()
    first["presets"].clear()
    assert discover_presets()["presets"]


def test_one_safe_preset_per_goal_in_catalog_order_and_closed_over_goals() -> None:
    catalog = preset_catalog()
    goals = goal_catalog()
    assert [preset.goal_id for preset in catalog.presets] == [g.goal_id for g in goals.goals]
    for preset in catalog.presets:
        goal = goals.goal(preset.goal_id)
        assert preset.preset_id == f"{goal.goal_id}.safe"
        assert preset.representation_id == goal.default_representation
        assert preset.curation == goal.curation_defaults
        assert preset.review_policy == goal.review_policy_default
        assert preset.construction.consumer_profile == "veriformis-canonical-v1"
        expected_strategy = (
            "structure" if goal.objective == "section_reconstruction" else "paragraph"
        )
        assert preset.segmentation.strategy == expected_strategy
    defaults = recipe_defaults()
    assert defaults.segmentation.model_dump() == {"strategy": "paragraph", "size": 1000, "overlap": 100}
    assert defaults.construction.model_dump() == {
        "split_ratio_ppm": 500_000,
        "require_review": False,
        "consumer_profile": "veriformis-canonical-v1",
    }
    assert defaults.curation == goals.goals[0].curation_defaults
    assert defaults.review_policy == "none"


def test_every_selection_path_resolves_to_the_same_effective_settings() -> None:
    for goal in goal_catalog().goals:
        by_goal = resolve_recipe_settings(goal=goal.goal_id)
        by_objective = resolve_recipe_settings(objective=goal.objective)
        by_preset = resolve_recipe_settings(preset=f"{goal.goal_id}.safe")
        assert by_goal.settings_digest == by_objective.settings_digest == by_preset.settings_digest
        assert by_goal.objective == goal.objective
        assert by_goal.recipe_library_id == goal.recipe_library_id
        assert by_goal.recipe_library_id in RECIPE_LIBRARY_IDS
        assert by_goal.representation_id == goal.default_representation
        assert by_goal.preset_id is None and by_preset.preset_id == f"{goal.goal_id}.safe"
        assert by_goal.review_policy == "none" and by_goal.construction.require_review is False


def test_overrides_apply_on_top_of_the_preset_and_are_validated() -> None:
    resolved = resolve_recipe_settings(
        preset="continue-a-passage.safe",
        representation="conversation",
        split_ratio_ppm=400_000,
        minimum_target_characters=3,
        balance_mode="primary-source-cap",
        maximum_records_per_primary_source=2,
        evaluation_required=False,
        require_review=True,
        size=500,
        overlap=50,
    )
    assert resolved.row_schema == "messages"
    assert resolved.construction.split_ratio_ppm == 400_000
    assert resolved.construction.require_review is True and resolved.review_policy == "required"
    assert resolved.curation.balance_mode == "primary_source_cap"
    assert resolved.curation.maximum_records_per_primary_source == 2
    assert resolved.curation.evaluation_required is False
    assert resolved.segmentation.model_dump() == {"strategy": "paragraph", "size": 500, "overlap": 50}
    legacy = resolve_recipe_settings(objective="continuation", target_row_schema="messages")
    assert legacy.representation_id == "conversation" and legacy.row_schema == "messages"
    assert resolve_recipe_settings(objective="continuation").settings_digest != resolved.settings_digest


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "select a goal"),
        ({"preset": "learn-the-text.safe", "goal": "continue-a-passage"}, "belongs to goal"),
        ({"goal": "learn-the-text", "objective": "continuation"}, "resolves to objective"),
        ({"goal": "learn-the-text", "representation": "conversation"}, "does not allow"),
        ({"goal": "learn-the-text", "representation": "whole-text", "target_row_schema": "messages"}, "not"),
        ({"preset": "learn-the-text.turbo"}, "unknown preset"),
        ({"goal": "continue-a-passage", "size": 10, "overlap": 10}, "not an executable"),
        ({"goal": "continue-a-passage", "split_ratio_ppm": 0}, "split_ratio_ppm"),
        ({"goal": "continue-a-passage", "balance_mode": "cap"}, "balance mode"),
        ({"goal": "continue-a-passage", "maximum_records_per_primary_source": 3}, "executable policy"),
        ({"goal": "continue-a-passage", "consumer_profile": "unsloth"}, "not implemented"),
        ({"goal": "learn-the-text", "consumer_profile": "aptus-handoff-v1"}, "not compilable"),
        ({"goal": "continue-a-passage", "review_policy": "maybe"}, "review policy"),
    ],
)
def test_conflicting_or_invalid_selections_fail_closed(kwargs, message) -> None:
    with pytest.raises(GoalCatalogError) as excinfo:
        resolve_recipe_settings(**kwargs)
    assert message.lower() in excinfo.value.message.lower()


def _mutated(edit) -> dict:
    payload = _payload()
    edit(payload)
    return payload


@pytest.mark.parametrize(
    ("label", "edit", "message"),
    [
        ("wrong schema", lambda p: p.__setitem__("schema_id", "veriformis.recipe-preset/v2"), "schema_id"),
        ("unknown key", lambda p: p.__setitem__("format", "jsonl"), "format"),
        ("missing safe preset", lambda p: p["presets"].pop(), "one safe preset per goal"),
        ("preset id drift", lambda p: p["presets"][0].__setitem__("preset_id", "learn-the-text-safe"), "preset_id"),
        ("duplicate preset", lambda p: p["presets"].append(dict(p["presets"][0])), "duplicate preset_id"),
        ("incompatible representation", lambda p: p["presets"][0].__setitem__("representation_id", "conversation"), "does not allow"),
        ("bad overlap", lambda p: p["presets"][0]["segmentation"].__setitem__("overlap", 1000), "executable"),
        ("candidate profile", lambda p: p["defaults"]["construction"].__setitem__("consumer_profile", "unsloth"), "not implemented"),
        ("float version", lambda p: p.__setitem__("contract_version", 1.0), "contract_version"),
        ("cap without balance", lambda p: p["defaults"]["curation"].__setitem__("maximum_records_per_primary_source", 2), "executable policy"),
    ],
)
def test_malformed_preset_payloads_fail_closed(label, edit, message) -> None:
    with pytest.raises(GoalCatalogError) as excinfo:
        parse_preset_catalog(json.dumps(_mutated(edit)))
    assert message.lower() in excinfo.value.message.lower(), label
    with pytest.raises(GoalCatalogError, match="canonical"):
        parse_preset_catalog(json.dumps(_payload()), require_canonical=True)


def test_review_policy_and_require_review_must_agree() -> None:
    with pytest.raises(GoalCatalogError, match="conflicts with review_policy"):
        resolve_recipe_settings(goal="learn-the-text", require_review=False, review_policy="required")
    assert resolve_recipe_settings(goal="learn-the-text", require_review=True).review_policy == "required"
    with pytest.raises(GoalCatalogError, match="require_review must equal"):
        parse_goal_catalog_payload = _payload()
        parse_goal_catalog_payload["presets"][0]["construction"]["require_review"] = True
        parse_preset_catalog(json.dumps(parse_goal_catalog_payload))
