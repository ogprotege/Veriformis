import json
from pathlib import Path
from types import MappingProxyType

import pytest

from veriformis.contracts import (
    DETERMINISTIC_V1_OBJECTIVE_KINDS,
    TAXONOMY_CONTRACT_ID,
    TAXONOMY_CONTRACT_VERSION,
    TAXONOMY_SCHEMA_ID,
    V1_ROW_SCHEMA_KINDS,
)
from veriformis.errors import TaxonomyError
from veriformis.identity import lossless_json_bytes, sha256_digest
from veriformis.taxonomy import (
    CANONICAL_CONSUMER_PROFILE,
    EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES,
    IMPLEMENTED_CONSUMER_PROFILES,
    IMPLEMENTED_PHYSICAL_CONTAINERS,
    IMPLEMENTED_TRAINING_FAMILIES,
    LOSS_POLICY_IDS,
    PLANNED_TRAINING_FAMILIES,
    ROW_SCHEMA_UI_ALIASES,
    TAXONOMY_AXES,
    assert_compile_combination,
    assert_objective_row_compatible,
    assert_profile_row_compatible,
    catalog,
    compatible_row_schemas,
    default_row_schema,
    family_for_objective,
    implemented_discovery,
    loss_boundary,
    loss_policy_for_row,
    require_axis,
    require_identifier,
)


TAXONOMY_V1_CATALOG = (
    Path(__file__).parent / "fixtures" / "taxonomy" / "v1" / "catalog.json"
)
TAXONOMY_V1_CATALOG_SHA256 = (
    "acda1b61db563b5d6241b023b3a1d8a441224a63d06561f281654c78d7c53eb5"
)


def test_taxonomy_contract_constants_are_exact() -> None:
    assert TAXONOMY_CONTRACT_ID == "veriformis.taxonomy"
    assert TAXONOMY_CONTRACT_VERSION == 1
    assert TAXONOMY_SCHEMA_ID == "veriformis.taxonomy/v1"
    assert TAXONOMY_AXES == (
        "training_family",
        "objective",
        "semantic_row",
        "physical_container",
        "consumer_profile",
        "loss_policy",
    )
    assert "format" not in TAXONOMY_AXES


def test_taxonomy_catalog_v1_golden_canonical_json_round_trip() -> None:
    stored = TAXONOMY_V1_CATALOG.read_bytes()
    assert stored.endswith(b"\n")
    canonical = stored.removesuffix(b"\n")

    assert sha256_digest(canonical) == TAXONOMY_V1_CATALOG_SHA256
    payload = json.loads(canonical)
    assert lossless_json_bytes(payload) == canonical
    assert payload == {
        key: list(values) for key, values in implemented_discovery().items()
    }
    assert payload["contract_id"] == [TAXONOMY_CONTRACT_ID]
    assert payload["contract_version"] == [str(TAXONOMY_CONTRACT_VERSION)]
    assert payload["schema_id"] == [TAXONOMY_SCHEMA_ID]
    assert set(payload) == {
        "consumer_profile",
        "contract_id",
        "contract_version",
        "loss_policy",
        "objective",
        "physical_container",
        "schema_id",
        "semantic_row",
        "training_family",
    }
    assert "format" not in payload


def test_registry_reuses_existing_objective_and_row_identifiers() -> None:
    assert tuple(
        entry.identifier
        for entry in catalog()
        if entry.axis == "objective" and entry.state == "implemented"
    ) == DETERMINISTIC_V1_OBJECTIVE_KINDS
    assert tuple(
        entry.identifier
        for entry in catalog()
        if entry.axis == "semantic_row" and entry.state == "implemented"
    ) == V1_ROW_SCHEMA_KINDS


def test_implemented_families_are_conservative_and_complete_for_current_objectives() -> (
    None
):
    assert IMPLEMENTED_TRAINING_FAMILIES == (
        "source-grounded-language-modeling",
        "source-grounded-supervised-fine-tuning",
    )
    assert family_for_objective("full_text") == "source-grounded-language-modeling"
    for kind in DETERMINISTIC_V1_OBJECTIVE_KINDS:
        if kind == "full_text":
            continue
        assert (
            family_for_objective(kind) == "source-grounded-supervised-fine-tuning"
        )


def test_future_families_are_named_but_not_implemented() -> None:
    assert "preference-and-ranking" in PLANNED_TRAINING_FAMILIES
    assert "explicit-label-classification" in PLANNED_TRAINING_FAMILIES
    assert "tool-call-conversations" in PLANNED_TRAINING_FAMILIES
    assert "stepwise-supervision" in PLANNED_TRAINING_FAMILIES
    assert "pre-tokenized-training" in PLANNED_TRAINING_FAMILIES
    assert "governed-generated-candidates" in PLANNED_TRAINING_FAMILIES
    assert EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES == ("multimodal-training",)
    implemented = {
        entry.identifier
        for entry in catalog()
        if entry.axis == "training_family" and entry.state == "implemented"
    }
    assert implemented == set(IMPLEMENTED_TRAINING_FAMILIES)
    assert implemented.isdisjoint(PLANNED_TRAINING_FAMILIES)
    assert implemented.isdisjoint(EXPLICITLY_UNSUPPORTED_TRAINING_FAMILIES)


def test_objective_row_compatibility_matches_construction_rules() -> None:
    assert compatible_row_schemas("full_text") == ("text",)
    for kind in DETERMINISTIC_V1_OBJECTIVE_KINDS:
        if kind == "full_text":
            continue
        assert compatible_row_schemas(kind) == (
            "prompt_completion",
            "instruction_output",
            "messages",
        )
    assert_objective_row_compatible("full_text", "text")
    assert_objective_row_compatible("continuation", "prompt_completion")
    with pytest.raises(
        TaxonomyError,
        match="full_text recipes require the product 'text' row schema",
    ):
        assert_objective_row_compatible("full_text", "prompt_completion")
    with pytest.raises(
        TaxonomyError,
        match="objective 'continuation' requires a supervised row schema",
    ):
        assert_objective_row_compatible("continuation", "text")


def test_default_row_schema_matches_current_surfaces() -> None:
    assert default_row_schema("full_text") == "text"
    for kind in DETERMINISTIC_V1_OBJECTIVE_KINDS:
        if kind == "full_text":
            continue
        assert default_row_schema(kind) == "prompt_completion"


def test_each_row_schema_has_one_loss_policy() -> None:
    expected = {
        "text": (
            "full-sequence",
            "Entire text sequence is supervised.",
        ),
        "prompt_completion": (
            "completion-only",
            "Prompt is context; completion receives supervision.",
        ),
        "instruction_output": (
            "output-only",
            "Instruction and input are context; output receives supervision.",
        ),
        "messages": (
            "final-assistant-suffix",
            "Only the final assistant message receives supervision.",
        ),
    }
    assert LOSS_POLICY_IDS == (
        "full-sequence",
        "completion-only",
        "output-only",
        "final-assistant-suffix",
    )
    assert set(expected) == set(V1_ROW_SCHEMA_KINDS)
    for row_schema, (policy, notes) in expected.items():
        assert loss_policy_for_row(row_schema) == policy
        assert loss_boundary(policy) == notes


def test_canonical_profile_accepts_text_and_aptus_refuses_it() -> None:
    assert IMPLEMENTED_CONSUMER_PROFILES == (
        CANONICAL_CONSUMER_PROFILE,
        "aptus-handoff-v1",
    )
    assert_profile_row_compatible(CANONICAL_CONSUMER_PROFILE, "text")
    assert_compile_combination("full_text", "text")
    with pytest.raises(TaxonomyError, match="aptus-handoff-v1"):
        assert_profile_row_compatible("aptus-handoff-v1", "text")
    with pytest.raises(TaxonomyError, match="aptus-handoff-v1"):
        assert_compile_combination(
            "full_text",
            "text",
            profile="aptus-handoff-v1",
        )


def test_planned_profile_cannot_be_selected_for_compile() -> None:
    with pytest.raises(TaxonomyError, match="trl"):
        assert_compile_combination(
            "continuation",
            "prompt_completion",
            profile="trl",
        )


def test_ui_aliases_and_unknown_identifiers_fail_closed() -> None:
    assert ROW_SCHEMA_UI_ALIASES == MappingProxyType(
        {
            "completion": "prompt_completion",
            "instruction": "instruction_output",
            "chat": "messages",
        }
    )
    with pytest.raises(TaxonomyError, match="UI alias"):
        require_identifier("semantic_row", "completion")
    with pytest.raises(TaxonomyError, match="summary"):
        require_identifier("objective", "summary")
    with pytest.raises(TaxonomyError, match="format"):
        require_axis("format")


def test_implemented_discovery_names_axes_and_omits_format() -> None:
    discovery = implemented_discovery()
    assert "format" not in discovery
    assert discovery["training_family"] == IMPLEMENTED_TRAINING_FAMILIES
    assert discovery["objective"] == DETERMINISTIC_V1_OBJECTIVE_KINDS
    assert discovery["semantic_row"] == V1_ROW_SCHEMA_KINDS
    assert discovery["physical_container"] == IMPLEMENTED_PHYSICAL_CONTAINERS
    assert discovery["consumer_profile"] == IMPLEMENTED_CONSUMER_PROFILES
    assert "preference-and-ranking" not in discovery["training_family"]
    assert "split-jsonl-directory" in discovery["physical_container"]
    assert "json" in discovery["physical_container"]
    assert "constrained-csv" in discovery["physical_container"]
    assert "deterministic-export-pack-zip-v1" in discovery["physical_container"]


def test_admitted_physical_containers_are_implemented_only() -> None:
    implemented = {
        entry.identifier
        for entry in catalog()
        if entry.axis == "physical_container" and entry.state == "implemented"
    }
    assert implemented == {
        "minimal-v1",
        "deterministic-vfbundle-zip-v1",
        "deterministic-export-pack-zip-v1",
        "split-jsonl-directory",
        "json",
        "constrained-csv",
    }
