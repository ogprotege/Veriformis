"""Goal catalog v1: versioned plain-language data closed over the taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from veriformis.contracts import (
    GOAL_CATALOG_CONTRACT_ID,
    GOAL_CATALOG_CONTRACT_VERSION,
    GOAL_CATALOG_SCHEMA_ID,
    PRODUCT_OBJECTIVE_KINDS,
    PRODUCT_ROW_SCHEMA_KINDS,
)
from veriformis.errors import GoalCatalogError
from veriformis.goals import (
    GOAL_CATALOG_DATA_NAME,
    GoalCatalog,
    discover_goals,
    goal_catalog,
    goal_catalog_json,
    goal_for_objective,
    parse_goal_catalog,
    representation_for_row_schema,
    resolve_goal,
)
from veriformis.identity import sha256_digest
from veriformis.recipes import RECIPE_LIBRARY_IDS
from veriformis.taxonomy import (
    DEFAULT_ROW_SCHEMA,
    LOSS_POLICY_IDS,
    OBJECTIVE_FAMILY,
    OBJECTIVE_ROW_COMPATIBILITY,
    ROW_LOSS_POLICY,
    ROW_SCHEMA_UI_ALIASES,
)

DATA_PATH = Path(__file__).parents[2] / "src" / "veriformis" / "goals" / "catalog-v1.json"
DATA_SHA256 = "064cffb87981d88b6211597ac72bc75168d7673c61d074b7a1e12e02b8b33bfb"
FROZEN_FIXTURE = (
    Path(__file__).parents[1] / "regressions" / "fixtures" / "phase6" / "goal-catalog.json"
)

PLAIN_FIELDS = (
    "title",
    "plain_language",
    "what_the_model_learns",
    "what_you_provide",
    "instruction_template",
    "instruction_task",
)


def _payload() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_goal_catalog_contract_constants_are_exact() -> None:
    assert GOAL_CATALOG_CONTRACT_ID == "veriformis.goal-catalog"
    assert GOAL_CATALOG_CONTRACT_VERSION == 1
    assert GOAL_CATALOG_SCHEMA_ID == "veriformis.goal-catalog/v1"
    assert GOAL_CATALOG_DATA_NAME == "catalog-v1.json"


def test_packaged_data_is_canonical_pinned_and_loads() -> None:
    stored = DATA_PATH.read_text(encoding="utf-8")
    assert sha256_digest(stored) == DATA_SHA256
    payload = json.loads(stored)
    assert json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n" == stored
    catalog = goal_catalog()
    assert isinstance(catalog, GoalCatalog)
    assert catalog.schema_id == GOAL_CATALOG_SCHEMA_ID
    assert catalog.contract_id == GOAL_CATALOG_CONTRACT_ID
    assert catalog.contract_version == GOAL_CATALOG_CONTRACT_VERSION
    assert goal_catalog() is catalog
    assert goal_catalog_json() == stored


def test_frozen_discovery_fixture_equals_packaged_data() -> None:
    assert FROZEN_FIXTURE.read_text(encoding="utf-8") == goal_catalog_json()


def test_catalog_closes_over_every_objective_and_row_schema() -> None:
    catalog = goal_catalog()
    objectives = tuple(goal.objective for goal in catalog.goals)
    assert objectives == PRODUCT_OBJECTIVE_KINDS
    assert tuple(rep.row_schema for rep in catalog.representations) == PRODUCT_ROW_SCHEMA_KINDS
    by_rep = {rep.representation_id: rep for rep in catalog.representations}
    for goal in catalog.goals:
        assert goal.state == "implemented"
        assert goal.training_family == OBJECTIVE_FAMILY[goal.objective]
        assert goal.recipe_library_id in RECIPE_LIBRARY_IDS
        assert goal.recipe_library_id.split(".", 1)[0] == goal.objective
        rows = tuple(by_rep[rep].row_schema for rep in goal.compatible_representations)
        assert rows == OBJECTIVE_ROW_COMPATIBILITY[goal.objective]
        assert by_rep[goal.default_representation].row_schema == DEFAULT_ROW_SCHEMA[
            goal.objective
        ]
        assert goal.default_representation in goal.compatible_representations
    for rep in catalog.representations:
        assert rep.loss_policy == ROW_LOSS_POLICY[rep.row_schema]
        assert rep.loss_policy in LOSS_POLICY_IDS
        assert rep.requires_operator_instruction is (rep.row_schema == "instruction_output")


def test_plain_language_fields_contain_no_machine_identifiers() -> None:
    """Usability criterion U1: a person never needs the internal vocabulary."""
    machine_tokens = {
        *(kind for kind in PRODUCT_OBJECTIVE_KINDS),
        *(kind for kind in PRODUCT_ROW_SCHEMA_KINDS),
        *LOSS_POLICY_IDS,
        *RECIPE_LIBRARY_IDS,
        *ROW_SCHEMA_UI_ALIASES,
    }
    machine_tokens = {token for token in machine_tokens if any(c in token for c in "_-.")}
    catalog = goal_catalog()
    for goal in catalog.goals:
        texts = [getattr(goal, field) for field in PLAIN_FIELDS] + list(goal.not_this)
        for text in texts:
            assert text.strip() == text and text
            for token in machine_tokens:
                assert token not in text, (goal.goal_id, token)
    for rep in catalog.representations:
        for text in (rep.title, rep.plain_language, rep.supervised_region):
            assert text.strip() == text and text
            for token in machine_tokens:
                assert token not in text, (rep.representation_id, token)


def test_no_goal_or_representation_claims_an_absent_transformation() -> None:
    catalog = goal_catalog()
    for goal in catalog.goals:
        for field in PLAIN_FIELDS:
            lowered = getattr(goal, field).lower()
            for fragment in ("summar", "answer", "translat"):
                assert fragment not in lowered, (goal.goal_id, field, fragment)
        assert goal.not_this, goal.goal_id
    for rep in catalog.representations:
        for text in (rep.title, rep.plain_language, rep.supervised_region):
            for fragment in ("summar", "answer", "translat"):
                assert fragment not in text.lower(), (rep.representation_id, fragment)


def test_lookups_and_resolution_are_exact() -> None:
    goal = goal_for_objective("section_reconstruction")
    assert goal.goal_id == "recover-a-section-from-its-heading"
    rep = representation_for_row_schema("messages")
    assert rep.representation_id == "conversation"
    resolved = resolve_goal("continue-a-passage", "conversation")
    assert resolved == (
        "continuation",
        "messages",
        "continuation.default",
        "final-assistant-suffix",
    )
    assert resolve_goal("learn-the-text") == (
        "full_text",
        "text",
        "full_text.default",
        "full-sequence",
    )
    with pytest.raises(GoalCatalogError, match="unknown goal"):
        resolve_goal("summarize-the-document")
    with pytest.raises(GoalCatalogError, match="unknown representation"):
        resolve_goal("learn-the-text", "chat")
    with pytest.raises(GoalCatalogError, match="does not allow"):
        resolve_goal("learn-the-text", "conversation")
    with pytest.raises(GoalCatalogError, match="unknown objective"):
        goal_for_objective("summary")
    with pytest.raises(GoalCatalogError, match="unknown row schema"):
        representation_for_row_schema("chat")


def test_discover_goals_is_fresh_json_ready_and_mutation_safe() -> None:
    first = discover_goals()
    second = discover_goals()
    assert first == second and first is not second
    assert json.loads(goal_catalog_json()) == first
    first["goals"].clear()
    assert discover_goals()["goals"]
    assert set(first) == {
        "contract_id",
        "contract_version",
        "schema_id",
        "goals",
        "representations",
    }


def _mutated(edit) -> dict:
    payload = _payload()
    edit(payload)
    return payload


@pytest.mark.parametrize(
    ("label", "edit", "message"),
    [
        (
            "wrong schema id",
            lambda p: p.__setitem__("schema_id", "veriformis.goal-catalog/v2"),
            "schema_id",
        ),
        (
            "unknown key",
            lambda p: p.__setitem__("format", "jsonl"),
            "format",
        ),
        (
            "duplicate goal id",
            lambda p: p["goals"][1].__setitem__("goal_id", p["goals"][0]["goal_id"]),
            "duplicate goal",
        ),
        (
            "two goals share an objective",
            lambda p: p["goals"][1].update(
                {
                    "objective": "full_text",
                    "training_family": "source-grounded-language-modeling",
                    "recipe_library_id": "full_text.default",
                    "default_representation": "whole-text",
                    "compatible_representations": ["whole-text"],
                }
            ),
            "exactly one goal",
        ),
        (
            "contract_version as float",
            lambda p: p.__setitem__("contract_version", 1.0),
            "contract_version",
        ),
        (
            "contract_version as bool",
            lambda p: p.__setitem__("contract_version", True),
            "contract_version",
        ),
        (
            "goal id with space",
            lambda p: p["goals"][0].__setitem__("goal_id", "learn the text"),
            "goal_id",
        ),
        (
            "representation id with uppercase",
            lambda p: p["representations"][0].__setitem__("representation_id", "Whole-Text"),
            "representation_id",
        ),
        (
            "embedded newline in title",
            lambda p: p["goals"][0].__setitem__("title", "Learn\nthe text"),
            "control",
        ),
        (
            "representation claims a summary",
            lambda p: p["representations"][0].__setitem__(
                "plain_language", "A summary of the passage."
            ),
            "summar",
        ),
        (
            "goal claims answering",
            lambda p: p["goals"][0].__setitem__(
                "plain_language", "Teach the model to answer questions about the docs."
            ),
            "answer",
        ),
        (
            "uppercase machine identifier",
            lambda p: p["goals"][0].__setitem__("what_you_provide", "Any FULL_TEXT source."),
            "identifier",
        ),
        (
            "duplicate not_this",
            lambda p: p["goals"][0].__setitem__(
                "not_this", [p["goals"][0]["not_this"][0]] * 2
            ),
            "repeat",
        ),
        (
            "missing objective goal",
            lambda p: p["goals"].pop(),
            "every objective",
        ),
        (
            "unknown objective",
            lambda p: p["goals"][0].__setitem__("objective", "summary"),
            "objective",
        ),
        (
            "recipe id for another objective",
            lambda p: p["goals"][0].__setitem__("recipe_library_id", "continuation.default"),
            "recipe",
        ),
        (
            "default not compatible",
            lambda p: p["goals"][0].__setitem__("default_representation", "conversation"),
            "default",
        ),
        (
            "compatibility drifts from taxonomy",
            lambda p: p["goals"][1].__setitem__(
                "compatible_representations", ["prompt-and-completion"]
            ),
            "taxonomy",
        ),
        (
            "wrong loss policy",
            lambda p: p["representations"][0].__setitem__("loss_policy", "completion-only"),
            "loss",
        ),
        (
            "ui alias as row schema",
            lambda p: p["representations"][3].__setitem__("row_schema", "chat"),
            "row_schema",
        ),
        (
            "empty not_this",
            lambda p: p["goals"][0].__setitem__("not_this", []),
            "not_this",
        ),
        (
            "machine identifier in plain language",
            lambda p: p["goals"][0].__setitem__("plain_language", "Uses full_text rows."),
            "identifier",
        ),
        (
            "summary claim",
            lambda p: p["goals"][0].__setitem__("title", "Summarize the document"),
            "summar",
        ),
        (
            "state not implemented",
            lambda p: p["goals"][0].__setitem__("state", "planned"),
            "state",
        ),
        (
            "instruction flag drift",
            lambda p: p["representations"][2].__setitem__(
                "requires_operator_instruction", False
            ),
            "instruction",
        ),
        (
            "template omits the task phrase",
            lambda p: p["goals"][1].__setitem__(
                "instruction_template", "Continue the supplied opening."
            ),
            "instruction_task",
        ),
        (
            "template claims a summary",
            lambda p: p["goals"][1].__setitem__(
                "instruction_template",
                "Summarize the passage with its exact source remainder.",
            ),
            "summar",
        ),
        (
            "duplicate instruction task",
            lambda p: (
                p["goals"][2].__setitem__(
                    "instruction_task", p["goals"][1]["instruction_task"]
                ),
                p["goals"][2].__setitem__(
                    "instruction_template", p["goals"][1]["instruction_template"]
                ),
            ),
            "unique",
        ),
    ],
)
def test_malformed_catalog_payloads_fail_closed(label, edit, message) -> None:
    with pytest.raises(GoalCatalogError) as excinfo:
        parse_goal_catalog(json.dumps(_mutated(edit)))
    assert message.lower() in excinfo.value.message.lower(), label


def test_duplicate_json_keys_and_noncanonical_bytes_fail_closed(tmp_path) -> None:
    with pytest.raises(GoalCatalogError, match="duplicate"):
        parse_goal_catalog('{"schema_id": "a", "schema_id": "b"}')
    with pytest.raises(GoalCatalogError, match="canonical"):
        parse_goal_catalog(json.dumps(_payload()), require_canonical=True)
    with pytest.raises(GoalCatalogError, match="JSON"):
        parse_goal_catalog("{not json")
